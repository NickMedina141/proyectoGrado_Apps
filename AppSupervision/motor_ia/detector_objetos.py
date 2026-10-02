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
    ruta_yolo = os.path.join(base_dir, "yolo11m.pt")
    self.modelo = YOLO(ruta_yolo)
    self.objetos_sospechosos = {
      "cell phone": "celular", "earphones": "audifonos", "book": "libro",
      "laptop": "computadora portatil", "tablet": "tableta",
      "headphones": "audifonos", "remote": "control remoto"
    }
    self.frames_entre_analisis = frames_entre_analisis
    self.contador_frames = 0
    self.ultimo_resultado = []
    self.CONFIANZA_MINIMA = 0.15  # Base YOLO ultra-baja para capturar todo
    self.CONF_CELULAR = 0.25
    self.CONF_LAPTOP = 0.55
    self.CONF_OTROS = 0.40
    self.UMBRAL_TIEMPO = 3.0      # Segundos para ventana de tiempo
    self.historial_objetos = {}   # { 'celular': [True, False, True...] }
    self.ultimo_reporte = {}      # Para cooldown
    self.funcion_alerta = funcion_alerta

  def configurar_sensibilidad(self, nivel: str):
    self.CONFIANZA_MINIMA = 0.15 # Para YOLO crudo, siempre bajo
    if nivel == "ALTA":
        self.CONF_CELULAR = 0.15
        self.CONF_LAPTOP = 0.45
        self.CONF_OTROS = 0.30
        self.UMBRAL_TIEMPO = 2.0
    elif nivel == "BAJA":
        self.CONF_CELULAR = 0.40
        self.CONF_LAPTOP = 0.70
        self.CONF_OTROS = 0.55
        self.UMBRAL_TIEMPO = 4.0
    else: # MEDIA
        self.CONF_CELULAR = 0.25
        self.CONF_LAPTOP = 0.55
        self.CONF_OTROS = 0.40
        self.UMBRAL_TIEMPO = 3.0

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
    # Calcular tamano de la ventana en base a fps asumido de yolo (aprox 6 fps si la camara va a 30 y saltamos 5)
    fps_yolo = 30.0 / max(1, self.frames_entre_analisis)
    tamano_ventana = int(fps_yolo * self.UMBRAL_TIEMPO)
    if tamano_ventana < 5: tamano_ventana = 5

    # Para todos los objetos sospechosos conocidos
    for nombre in self.objetos_sospechosos.values():
      if nombre not in self.historial_objetos:
        self.historial_objetos[nombre] = []
        
      # Agregar estado actual
      self.historial_objetos[nombre].append(nombre in objetos_activos)
      
      # Mantener tamano de ventana
      if len(self.historial_objetos[nombre]) > tamano_ventana:
        self.historial_objetos[nombre].pop(0)

      # Calcular porcentaje (regla del 85%)
      veces_detectado = sum(self.historial_objetos[nombre])
      porcentaje = veces_detectado / tamano_ventana if tamano_ventana > 0 else 0

      ahora = time.time()
      if porcentaje >= 0.50:
        # Solo disparar si pasaron 5 seg desde el ultimo reporte para no hacer spam (cooldown interno)
        if nombre not in self.ultimo_reporte or (ahora - self.ultimo_reporte[nombre] > 5.0):
          alerta = f"OBJETO_SOSPECHOSO_{nombre.upper()}"
          datos["alertas"].append(alerta)
          if self.funcion_alerta:
            self.funcion_alerta(alerta, porcentaje, frame.copy())
          self.ultimo_reporte[nombre] = ahora
          self.historial_objetos[nombre] = []

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
