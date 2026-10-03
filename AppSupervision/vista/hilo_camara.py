import cv2
import base64
from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtGui import QImage
import time
import requests

class HiloCamara(QThread):
  senal_frame = pyqtSignal(QImage)
  senal_error = pyqtSignal(str)
  senal_advertencia = pyqtSignal(int)
  senal_frame_anotado = pyqtSignal(str)

  def __init__(self, url_api_analisis="http://127.0.0.1:8005/analizar_frame"):
    super().__init__()
    self.activo = True
    self.pausado = False
    self.url_api = url_api_analisis
    self.contador_frames = 0
    self.FRAME_SKIP = 6 # (5 FPS) Reduce carga de red y CPU sin perder detalle
    self.procesando_ia = False # Flag de protección
    self.ultimo_frame_ia = None # Cache del último frame dibujado
    
    # --- Variables del Buho (Temporizador de Atencion) ---
    self.tiempo_distraido = 0.0
    self.tiempo_ultima_revision = time.time()
    self.nivel_buho_previo = 1

    # --- Variables de Biometría Robusta (Anti Falsos Positivos) ---
    self.fallos_consecutivos_suplantacion = 0
    self.UMBRAL_CONFIRMACION_SUPLANTACION = 3
    self.emb_base_cache = None
    self.ruta_emb_cacheada = None

  def run(self):
    captura = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    
    if not captura.isOpened():
      self.senal_error.emit("No se pudo acceder a la camara")
      return

    while self.activo:
      if self.pausado:
          time.sleep(0.1)
          continue
          
      ret, frame = captura.read()
      if not ret:
        time.sleep(0.1)
        continue

      frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
      h, w, ch = frame_rgb.shape
      bytes_por_linea = ch * w
      imagen_qt = QImage(frame_rgb.data, w, h, bytes_por_linea, QImage.Format.Format_RGB888)
      imagen_escalada = imagen_qt.scaled(300, 225)
      self.senal_frame.emit(imagen_escalada)

      self.contador_frames += 1
      if self.contador_frames % self.FRAME_SKIP == 0:
        frame_redimensionado = cv2.resize(frame, (1280, 720))
        
        exito, buffer = cv2.imencode('.jpg', frame_redimensionado, [cv2.IMWRITE_JPEG_QUALITY, 60])
        if not exito:
          _, buffer = cv2.imencode('.jpg', frame_redimensionado, [cv2.IMWRITE_JPEG_QUALITY, 45])
          
        frame_b64 = base64.b64encode(buffer).decode('utf-8')
        
        # EMISIÓN INMEDIATA Y FLUIDA AL PROFESOR (Con dibujos si hay, o limpio si la IA va lenta/caída)
        if hasattr(self, 'senal_frame_anotado'):
          if self.ultimo_frame_ia:
            self.senal_frame_anotado.emit(self.ultimo_frame_ia)
          else:
            frame_fallback = cv2.resize(frame, (640, 360), interpolation=cv2.INTER_AREA)
            _, buf_fallback = cv2.imencode('.jpg', frame_fallback, [cv2.IMWRITE_JPEG_QUALITY, 55])
            self.senal_frame_anotado.emit(base64.b64encode(buf_fallback).decode('utf-8'))
        
        # --- BIOMETRIA ROBUSTA (InsightFace) cada 15 seg ---
        if hasattr(self, 'biometria_check_time'):
            if time.time() - self.biometria_check_time > 15:
                from motor_ia.biometria_facial import biometria_motor
                import json, os
                import numpy as np

                # Cargar / refrescar embedding de referencia en memoria
                ruta_emb = getattr(biometria_motor, 'ruta_emb_actual', None)
                if ruta_emb and os.path.exists(ruta_emb):
                    if self.emb_base_cache is None or getattr(self, 'ruta_emb_cacheada', None) != ruta_emb:
                        try:
                            with open(ruta_emb, 'r') as f:
                                self.emb_base_cache = np.array(json.load(f))
                                self.ruta_emb_cacheada = ruta_emb
                        except Exception as e:
                            print(f"[BIOMETRIA] Error leyendo embedding: {e}")

                if self.emb_base_cache is not None:
                    # Ejecutar verificación con filtro geométrico de frontalidad 3D integrado
                    es_misma, cert, apto, motivo = biometria_motor.verificar_identidad_detallada(frame, self.emb_base_cache)
                    
                    if not apto:
                        # Rostro no frontal (inclinado, girado, mirando abajo o ausente):
                        # NO castigar como suplantación. Esperamos a que esté de frente.
                        self.fallos_consecutivos_suplantacion = 0
                        # Reintentar en 2 segundos cuando el estudiante mire al monitor
                        self.biometria_check_time = time.time() - 13.0
                    else:
                        # Rostro confirmado 100% frontal
                        if es_misma:
                            # Coincidencia exitosa del estudiante
                            self.fallos_consecutivos_suplantacion = 0
                            self.biometria_check_time = time.time()
                        else:
                            # Discrepancia con rostro frontal: acumular confirmación
                            self.fallos_consecutivos_suplantacion += 1
                            print(f"[BIOMETRIA] Discrepancia frontal detectada ({self.fallos_consecutivos_suplantacion}/{self.UMBRAL_CONFIRMACION_SUPLANTACION}) - Similitud: {cert*100:.1f}%")
                            
                            if self.fallos_consecutivos_suplantacion >= self.UMBRAL_CONFIRMACION_SUPLANTACION:
                                print(f"[ALERTA BIOMETRICA CONFIRMADA] SUPLANTACION_IDENTIDAD tras {self.UMBRAL_CONFIRMACION_SUPLANTACION} verificaciones ({cert*100:.1f}%)")
                                from api.cliente_respuesta import cliente_api
                                cliente_api.enviar_evidencia_silenciosa(["SUPLANTACION_IDENTIDAD"], frame_base64=frame_b64)
                                self.fallos_consecutivos_suplantacion = 0
                                self.biometria_check_time = time.time()
                            else:
                                # Reintentar en 3 segundos para confirmar la discrepancia
                                self.biometria_check_time = time.time() - 12.0
                else:
                    self.biometria_check_time = time.time()
        else:
            self.biometria_check_time = time.time()

        # ENVIAR A LA IA EN SEGUNDO PLANO
        if not getattr(self, 'procesando_ia', False):
          self.procesando_ia = True
          import threading
          threading.Thread(target=self._enviar_y_procesar_ia, args=(frame_b64,), daemon=True).start()

      time.sleep(0.01)

    captura.release()

  def _enviar_y_procesar_ia(self, frame_b64):
    try:
      payload = {"frame_base64": frame_b64}
      resp = requests.post(self.url_api, json=payload, timeout=5.0)
      
      if resp.status_code == 200:
        data = resp.json()
        # Guardamos el frame ligero anotado (640x360) para que el streaming continuo sea ultra-fluido
        self.ultimo_frame_ia = data.get("frame_anotado", frame_b64)
        
        # Frame de alta definición (1280x720 HD) para evidencia forense
        frame_evidencia = data.get("frame_evidencia") or frame_b64
          
        if "resultados" in data:
          self._procesar_resultados_ia(data["resultados"], frame_evidencia)
      else:
        self.ultimo_frame_ia = frame_b64
    except Exception:
      self.ultimo_frame_ia = frame_b64
    finally:
      self.procesando_ia = False

  def _procesar_resultados_ia(self, resultados, frame_anotado_b64):
    try:
      ahora = time.time()
      dt = ahora - self.tiempo_ultima_revision
      self.tiempo_ultima_revision = ahora
      
      alertas_crudas = resultados.get("alertas_crudas", [])
      
      # 1. Comprobar anomalias menores (Mirada, Cabeza Inclinada, Giro) para alimentar al Buho
      alertas_menores = [
          "MINOR_", 
          "MIRADA_", 
          "CABEZA_INCLINADA_", 
          "GIRO_SOSPECHOSO_", 
          "MANOS_NO_VISIBLES",
          "ROSTRO_NO_DETECTADO",
          "CUERPO_NO_DETECTADO",
          "ESTUDIANTE_LEVANTANDOSE"
      ]
      
      comportamiento_anomalo = any(any(a.startswith(minor) for minor in alertas_menores) for a in alertas_crudas)
      
      # Quality Gate: Actualizar estado de inclinación o rostro ausente
      self.rostro_apto_biometria = not any(
          "CABEZA_INCLINADA" in a or 
          "ROSTRO_NO_DETECTADO" in a or 
          "GIRO_SOSPECHOSO" in a or 
          "LEVANTANDOSE" in a 
          for a in alertas_crudas
      )
      
      if comportamiento_anomalo:
        self.tiempo_distraido += dt
      else:
        self.tiempo_distraido -= dt * 1.5 
        
      self.tiempo_distraido = max(0.0, min(15.0, self.tiempo_distraido))
      
      # 2. Calcular nivel de buho (0 a 5)
      nivel = int((self.tiempo_distraido / 15.0) * 5)
      if hasattr(self, 'senal_advertencia'):
        self.senal_advertencia.emit(nivel)
      
      # 3. Disparar alerta de FALTA DE ATENCION si llega a nivel 5 (Rojo)
      if nivel == 5 and self.nivel_buho_previo < 5:
        from api.cliente_respuesta import cliente_api
        cliente_api.enviar_evidencia_silenciosa(["DESATENCION_PROLONGADA"], frame_base64=frame_anotado_b64)
        
      self.nivel_buho_previo = nivel
      
      # 4. Procesar unicamente alertas CRITICAS ignorando las menores (que ya procesa el buho)
      alertas_confirmadas = resultados.get("alertas", [])
      alertas_criticas = [
          a for a in alertas_confirmadas 
          if not any(a.startswith(minor) for minor in alertas_menores)
      ]
      
      if alertas_criticas:
        from api.cliente_respuesta import cliente_api
        cliente_api.enviar_evidencia_silenciosa(alertas_criticas, frame_base64=frame_anotado_b64)
          
    except Exception as e:
      print(f"Error procesando resultados IA: {e}")

  def detener(self):
    self.activo = False
    self.wait()