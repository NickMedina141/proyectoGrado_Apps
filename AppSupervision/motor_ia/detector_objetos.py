import cv2
import time
from ultralytics import YOLO

class DetectorObjetos:
  def __init__(self, funcion_alerta=None, frames_entre_analisis=5):
    import sys
    import os
    if getattr(sys, 'frozen', False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ruta_yolo_s = os.path.join(base_dir, "yolo11s.pt")
    ruta_yolo_m = os.path.join(base_dir, "yolo11m.pt")
    if os.path.exists(ruta_yolo_s):
        ruta_yolo = ruta_yolo_s
    elif os.path.exists(ruta_yolo_m):
        ruta_yolo = ruta_yolo_m
    else:
        ruta_yolo = "yolo11s.pt"
    self.modelo = YOLO(ruta_yolo)
    self.objetos_sospechosos = {
      "cell phone": "celular", "earphones": "audifonos", "book": "libro",
      "laptop": "computadora portatil", "tablet": "tableta",
      "headphones": "audifonos"
    }
    self.frames_entre_analisis = frames_entre_analisis
    self.contador_frames = 0
    self.ultimo_resultado = []
    self.CONFIANZA_MINIMA = 0.12  # Base YOLO para capturar celulares ocluidos y en oreja
    self.CONF_CELULAR = 0.20      # MEDIA por defecto
    self.CONF_LAPTOP = 0.55
    self.CONF_OTROS = 0.40
    self.UMBRAL_TIEMPO = 2.5      # Segundos reales para ventana
    self.min_tiempo_sostenido = 1.8
    self.tiempo_retiro_episodio = 5.0 # Segundos de ausencia para cerrar episodio
    self.historial_objetos = {}   # { 'celular': [(timestamp, True/False)] }
    self.primer_visto = {}        # { 'celular': timestamp }
    self.ultimo_momento_visto = {} # { 'celular': timestamp }
    self.episodio_activo = {}      # { 'celular': bool }
    self.ultimo_reporte = {}      # Para cooldown
    self.funcion_alerta = funcion_alerta

  def configurar_sensibilidad(self, nivel: str):
    self.CONFIANZA_MINIMA = 0.12 # Para YOLO crudo, capturar todo
    if nivel == "ALTA":
        self.CONF_CELULAR = 0.15
        self.CONF_LAPTOP = 0.45
        self.CONF_OTROS = 0.30
        self.UMBRAL_TIEMPO = 1.5
        self.min_tiempo_sostenido = 1.0
        self.tiempo_retiro_episodio = 4.0
    elif nivel == "BAJA":
        self.CONF_CELULAR = 0.32
        self.CONF_LAPTOP = 0.70
        self.CONF_OTROS = 0.55
        self.UMBRAL_TIEMPO = 4.0
        self.min_tiempo_sostenido = 3.0
        self.tiempo_retiro_episodio = 6.0
    else: # MEDIA
        self.CONF_CELULAR = 0.20
        self.CONF_LAPTOP = 0.55
        self.CONF_OTROS = 0.40
        self.UMBRAL_TIEMPO = 2.5
        self.min_tiempo_sostenido = 1.8
        self.tiempo_retiro_episodio = 5.0

  def procesar_frame(self, frame):
    datos = {"objetos_detectados": [], "alertas": []}
    self.contador_frames += 1

    if self.contador_frames % self.frames_entre_analisis == 0:
      self.ultimo_resultado = self._ejecutar_deteccion(frame)

    objetos_activos = set()
    for nombre, confianza, caja in self.ultimo_resultado:
      datos["objetos_detectados"].append(nombre)
      objetos_activos.add(nombre)
      self._dibujar_caja(frame, nombre, confianza, caja)

    # Solo actualizar el historial de ventana deslizante cuando YOLO evalua
    if self.contador_frames % self.frames_entre_analisis == 0:
      self._actualizar_ventana_deslizante(objetos_activos, datos, frame)

    return frame, datos

  def _actualizar_ventana_deslizante(self, objetos_activos, datos, frame):
    ahora = time.time()

    for nombre in self.objetos_sospechosos.values():
      activo = nombre in objetos_activos

      if nombre not in self.historial_objetos:
        self.historial_objetos[nombre] = []
        self.primer_visto[nombre] = None
        self.ultimo_momento_visto[nombre] = 0.0
        self.episodio_activo[nombre] = False
        self.ultimo_reporte[nombre] = 0.0

      if activo:
        self.ultimo_momento_visto[nombre] = ahora
        if self.primer_visto.get(nombre) is None:
          self.primer_visto[nombre] = ahora
        self.historial_objetos[nombre].append((ahora, True))
      else:
        self.historial_objetos[nombre].append((ahora, False))
        # Si el episodio estaba activo pero el objeto ausente por >= tiempo_retiro_episodio,
        # se cierra el episodio para permitir reportar de nuevo si el estudiante lo saca otra vez.
        if self.episodio_activo.get(nombre, False):
          if ahora - self.ultimo_momento_visto.get(nombre, 0.0) >= getattr(self, "tiempo_retiro_episodio", 5.0):
            self.episodio_activo[nombre] = False
            self.primer_visto[nombre] = None
            self.historial_objetos[nombre] = []
        else:
          # Si no habia episodio pero pasa mas de 1.0 segundo sin verse, resetear primer_visto
          if self.primer_visto.get(nombre) is not None:
            recientes = [d for t, d in self.historial_objetos[nombre] if ahora - t <= 1.0 and d]
            if not recientes:
              self.primer_visto[nombre] = None

      # Mantener solo muestras dentro de la ventana de UMBRAL_TIEMPO
      self.historial_objetos[nombre] = [
        (t, d) for t, d in self.historial_objetos[nombre] if ahora - t <= self.UMBRAL_TIEMPO
      ]

      # Evaluar disparo: SOLO si el objeto está activo y NO hay un episodio ya reportado en curso
      if activo and not self.episodio_activo.get(nombre, False):
        if self.primer_visto.get(nombre) is not None:
          tiempo_acumulado = ahora - self.primer_visto[nombre]
          min_requerido = getattr(self, "min_tiempo_sostenido", self.UMBRAL_TIEMPO * 0.70)
          if tiempo_acumulado >= min_requerido:
            muestras = self.historial_objetos[nombre]
            positivos = sum(1 for _, d in muestras if d)
            porcentaje = positivos / len(muestras) if muestras else 0

            if porcentaje >= 0.50:
              alerta = f"OBJETO_SOSPECHOSO_{nombre.upper()}"
              datos["alertas"].append(alerta)
              if self.funcion_alerta:
                self.funcion_alerta(alerta, porcentaje, frame.copy())
              self.episodio_activo[nombre] = True
              self.ultimo_reporte[nombre] = ahora

  def _ejecutar_deteccion(self, frame):
    alto_analisis = 640
    escala = alto_analisis / frame.shape[0]
    ancho_analisis = int(frame.shape[1] * escala)
    frame_reducido = cv2.resize(frame, (ancho_analisis, alto_analisis))
    
    # Se deshabilita CLAHE: distorsiona el contraste natural con el que YOLO fue entrenado.
    # Usamos una confianza base muy baja (0.15) para capturar todo y luego filtramos por clase.
    resultados = self.modelo(frame_reducido, verbose=False, conf=self.CONFIANZA_MINIMA, imgsz=640)
    encontrados = []

    for resultado in resultados:
      for caja in resultado.boxes:
        nombre_en = self.modelo.names[int(caja.cls)]
        if nombre_en not in self.objetos_sospechosos:
          continue
          
        confianza = float(caja.conf)
        
        # Filtros de confianza especificos por clase y dinamicos segun configuracion del profesor
        if nombre_en == "cell phone" and confianza < self.CONF_CELULAR:
            continue
        elif nombre_en == "laptop" and confianza < self.CONF_LAPTOP:
            continue
        elif nombre_en not in ["cell phone", "laptop"] and confianza < self.CONF_OTROS:
            continue

        nombre = self.objetos_sospechosos[nombre_en]
        x1, y1, x2, y2 = caja.xyxy[0].tolist()
        caja_original = (int(x1 / escala), int(y1 / escala), int(x2 / escala), int(y2 / escala))
        encontrados.append((nombre, confianza, caja_original))

    return encontrados

  def _verificar_alerta(self, nombre_objeto, confianza, datos, frame):
    ahora = time.time()
    if nombre_objeto not in self.objeto_detectado_desde:
      self.objeto_detectado_desde[nombre_objeto] = ahora
    elif ahora - self.objeto_detectado_desde[nombre_objeto] >= self.UMBRAL_TIEMPO:
      alerta = f"Objeto sospechoso: {nombre_objeto.upper()}"
      if alerta not in datos["alertas"]:
        datos["alertas"].append(alerta)
      if self.funcion_alerta:
        self.funcion_alerta(alerta, confianza, frame.copy())

  def _dibujar_caja(self, frame, nombre, confianza, caja):
    x1, y1, x2, y2 = caja
    porcentaje = int(confianza * 100)
    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 2)
    etiqueta = f"{nombre} {porcentaje}%"
    cv2.putText(frame, etiqueta, (x1, y1 - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

  def liberar(self):
    pass
