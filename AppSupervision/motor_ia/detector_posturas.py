import cv2
import mediapipe as mp
import numpy as np
import time

class DetectorPostura:
  """
  Detecta la postura del cuerpo del estudiante usando MediaPipe Pose.
  Identifica si el el estudainte tiene comportamientos sospechosos como levantarse,
  girarse, o sacar las manos fuera del campo visual.
  """

  def __init__(self, funcion_alerta=None):
    BaseOptions = mp.tasks.BaseOptions
    PoseLandmarkerOptions = mp.tasks.vision.PoseLandmarkerOptions
    from mediapipe.tasks.python.vision import drawing_utils, PoseLandmarker, RunningMode
    import os
    ruta_modelo = os.path.join(os.path.dirname(__file__), "pose_landmarker.task")
    
    options = PoseLandmarkerOptions(
      base_options=BaseOptions(model_asset_path=ruta_modelo),
      running_mode=RunningMode.IMAGE,
      min_pose_detection_confidence=0.6,
      min_pose_presence_confidence=0.6,
      min_tracking_confidence=0.6
    )
    self.pose = PoseLandmarker.create_from_options(options)
    self.dibujo_mp = drawing_utils
    self.POSE_CONNECTIONS = mp.tasks.vision.PoseLandmarksConnections.POSE_LANDMARKS

    #Indices de puntos claves para Mediapipe pose 
    self.HOMBRO_IZQ = 11
    self.HOMBRO_DER = 12
    self.CADERA_IZQ = 23
    self.CADERA_DER = 24
    self.MUNECA_IZQ = 15
    self.MUNECA_DER = 16
    self.NARIZ = 0
    self.OREJA_IZQ = 7
    self.OREJA_DER = 8

    # Umbrales de alerta
    self.UMBRAL_GIRO_HOMBROS = 40.0 # grados - giro lateral sospechoso
    self.UMBRAL_MANOS_ABAJO = 0.90 # proporcion vertical - manos muy abajo
    self.UMBRAL_TIEMPO = 5.0 # segundos sostenidos

    # --- Ventanas Deslizantes ---
    self.historial_giro = []
    self.historial_manos = []
    self.historial_cuerpo = []
    self.historial_levantado = []
    self.ultimo_reporte = 0.0

    self.funcion_alerta = funcion_alerta

  def configurar_sensibilidad(self, nivel: str):
    if nivel == "ALTA":
        self.UMBRAL_GIRO_HOMBROS = 25.0
        self.UMBRAL_TIEMPO = 2.0
    elif nivel == "BAJA":
        self.UMBRAL_GIRO_HOMBROS = 50.0
        self.UMBRAL_TIEMPO = 6.0
    else:
        self.UMBRAL_GIRO_HOMBROS = 40.0
        self.UMBRAL_TIEMPO = 4.0


  #METODO PRINCIPAL DEL detector de posturas
  def procesar_frame(self, frame):
    """
    Recibe un frame BGR, analiza la postura y devuelve:
    -frame anotado con visualizaciones
    -dict con resultados del análisis, incluyendo alertas
    """

    datos = {
      "cuerpo_detectado": False,
      "angulo_hombros": 0.0,
      "manos_visibles": True,
      "alertas": []
    }

    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)
    resultado_mp = self.pose.detect(mp_image)

    alto, ancho = frame.shape[:2]

    # Si no se detecta un cuerpo
    if not resultado_mp.pose_landmarks:
      self._manejar_sin_cuerpo(frame, datos)
      return frame, datos
    
    #Si se detecta un cuerpo, registrar False en historial_cuerpo
    tamano_ventana = int(30 * self.UMBRAL_TIEMPO)
    self.historial_cuerpo.append(False)
    if len(self.historial_cuerpo) > tamano_ventana: self.historial_cuerpo.pop(0)

    datos["cuerpo_detectado"] = True

    puntos_lista = resultado_mp.pose_landmarks[0]
    lm = puntos_lista
    frame_limpio_evidencia = frame.copy()

    #Dibujar esqueleto liviano
    self.dibujo_mp.draw_landmarks(
      frame, puntos_lista,
      self.POSE_CONNECTIONS,
      landmark_drawing_spec = self.dibujo_mp.DrawingSpec(
        color = (0,200,255), thickness=1, circle_radius=0
      ),
      connection_drawing_spec = self.dibujo_mp.DrawingSpec(
        color = (0,150,200), thickness=1
      )
    )

    # Verificar giro lateral de hombros
    angulo_hombros = self._calcular_angulo_hombros(lm, ancho, alto)
    datos["angulo_hombros"] = angulo_hombros
    self._verificar_giro(angulo_hombros, datos, frame_limpio_evidencia)

    # Verificar si las manos estan visibles
    manos_visibles = self._verificar_manos(lm, alto)
    datos["manos_visibles"] = manos_visibles
    
    # Ventana para manos
    self.historial_manos.append(not manos_visibles)
    if len(self.historial_manos) > tamano_ventana: self.historial_manos.pop(0)
    
    ahora = time.time()
    if sum(self.historial_manos) / max(1, tamano_ventana) >= 0.85 and (ahora - self.ultimo_reporte > 10.0):
        alerta = "MANOS_NO_VISIBLES"
        datos["alertas"].append(alerta)
        if self.funcion_alerta: self.funcion_alerta(alerta, 1.0, frame_limpio_evidencia.copy())
        self.ultimo_reporte = ahora
        self.historial_manos = []
    

    #Verificar que el estudiante siga sentado
    self._verificar_posicion_sentado(lm, ancho, alto, datos, frame_limpio_evidencia)

    # HRUD en pantalla
    self.dibujar_hud(frame, datos)

    return frame, datos
  
  #ANGULO DE GIRO DE HOMBROS
  def _calcular_angulo_hombros(self, lm, ancho, alto):
    """
    Calcula el ángulo de la linea entre homrbos respecto al horizonte.
    Un ángulo grande indica que el estudiante se ha girado hacia un lado, 
    lo cual puede ser sospechoso.
    """

    hombro_izq = lm[self.HOMBRO_IZQ]
    hombro_der = lm[self.HOMBRO_DER]

    xi = int(hombro_izq.x * ancho)
    yi = int(hombro_izq.y * alto)
    xd = int(hombro_der.x * ancho)
    yd = int(hombro_der.y * alto)

    delta_y = yd - yi
    delta_x = xd - xi

    if delta_x == 0:
      return 0.0
    
    angulo = np.degrees(np.arctan2(delta_y, delta_x))
    return angulo
  
  # Visibilidad de manos
  def _verificar_manos(self, lm, alto):
    """
    Verifica si las manos del estudiante están visibles y en posición normal
    en el frame (sobre el escritorio, no debajo ni fuera del campo visual).
    Retornar True si las manos parecen estar en posición normal, False si parecen ocultas o fuera de lugar.
    """

    muneca_izq = lm[self.MUNECA_IZQ]
    muneca_der = lm[self.MUNECA_DER]

    #Mediapipe asigna visibilidad de 0 a 1
    if muneca_izq.visibility < 0.5 and muneca_der.visibility < 0.5:
      return False # ambas manos fuera del campo visual
    
    #verificar si las manos están muy abajo (debajo del escritorio)
    if(muneca_izq.visibility>0.5 and muneca_izq.y>
        self.UMBRAL_MANOS_ABAJO):
      return False
    
    if(muneca_der.visibility>0.5 and muneca_der.y>
        self.UMBRAL_MANOS_ABAJO):
      return False
    
    return True
  
  #Posición sentado
  def _verificar_posicion_sentado(self, lm, ancho, alto, datos, frame):
    nariz = lm[self.NARIZ]
    hombro_izq = lm[self.HOMBRO_IZQ]
    hombro_der = lm[self.HOMBRO_DER]
    promedio_y_hombros = (hombro_izq.y + hombro_der.y) / 2

    is_levantandose = nariz.y < 0.15 and promedio_y_hombros < 0.3
    
    tamano_ventana = int(30 * self.UMBRAL_TIEMPO)
    if tamano_ventana < 15: tamano_ventana = 15
    self.historial_levantado.append(is_levantandose)
    if len(self.historial_levantado) > tamano_ventana: self.historial_levantado.pop(0)
    
    ahora = time.time()
    if sum(self.historial_levantado) / tamano_ventana >= 0.85 and (ahora - self.ultimo_reporte > 10.0):
      alerta = "Estudiante_levantandose"
      datos["alertas"].append(alerta)
      if self.funcion_alerta: self.funcion_alerta(alerta, 1.0, frame.copy())
      self.ultimo_reporte = ahora
      self.historial_levantado = []

  def _verificar_giro(self, angulo, datos, frame):
    tamano_ventana = int(30 * self.UMBRAL_TIEMPO)
    if tamano_ventana < 15: tamano_ventana = 15
    
    is_fuera = abs(angulo) > self.UMBRAL_GIRO_HOMBROS
    self.historial_giro.append(is_fuera)
    if len(self.historial_giro) > tamano_ventana: self.historial_giro.pop(0)
    
    ahora = time.time()
    if sum(self.historial_giro) / tamano_ventana >= 0.85 and (ahora - self.ultimo_reporte > 10.0):
      lado = "DERECHA" if angulo > 0 else "IZQUIERDA"
      alerta = f"GIRO_SOSPECHOSO_{lado}"
      datos["alertas"].append(alerta)
      if self.funcion_alerta: self.funcion_alerta(alerta, abs(angulo), frame.copy())
      self.ultimo_reporte = ahora
      self.historial_giro = []

  def _alertar_manos_ocultas(self, datos, frame):
    # Ya no se usa directamente con if/else, se maneja en procesar_frame
    pass

  def _manejar_sin_cuerpo(self, frame, datos):
    tamano_ventana = int(30 * self.UMBRAL_TIEMPO)
    if tamano_ventana < 15: tamano_ventana = 15
    
    self.historial_cuerpo.append(True)
    if len(self.historial_cuerpo) > tamano_ventana: self.historial_cuerpo.pop(0)
    
    ahora = time.time()
    if sum(self.historial_cuerpo) / tamano_ventana >= 0.85 and (ahora - self.ultimo_reporte > 10.0):
      alerta = "CUERPO_NO_DETECTADO"
      datos["alertas"].append(alerta)
      if self.funcion_alerta: self.funcion_alerta(alerta, 1.0, frame.copy())
      self.ultimo_reporte = ahora
      self.historial_cuerpo = []

  # ─────────────────────────────────────────────
  # HUD
  # ─────────────────────────────────────────────
  def dibujar_hud(self, frame, datos):
    angulo = datos["angulo_hombros"]
    manos = datos["manos_visibles"]

    color_giro = (0, 255, 0) if abs(angulo) < self.UMBRAL_GIRO_HOMBROS else (0, 0, 255)
    color_manos = (0, 255, 0) if manos else (0, 0, 255)

    cv2.putText(frame, f"Giro hombros: {angulo:+.1f} grados",
          (10, 86), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color_giro, 2)
    cv2.putText(frame, f"Manos: {'visibles' if manos else 'NO VISIBLES'}",
          (10, 114), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color_manos, 2)

    for i, alerta in enumerate(datos["alertas"]):
      cv2.putText(frame, f"ALERTA: {alerta}",
            (10, 150 + i * 28),
            cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 0, 255), 2)


  def liberar(self):
    self.pose.close()
