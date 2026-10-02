import cv2
import mediapipe as mp
import numpy as np
import time

class DetectorRostro:
  """
  Detecta rostro, ojos y orientacion de cabeza del estudiante
  usando MediaPipe Face Mesh.
  """

  def __init__(self, funcion_alerta=None):
    # --- Inicializar MediaPipe ---
    BaseOptions = mp.tasks.BaseOptions
    FaceLandmarkerOptions = mp.tasks.vision.FaceLandmarkerOptions
    from mediapipe.tasks.python.vision import drawing_utils, FaceLandmarker, RunningMode
    
    # Resolviendo problema de rutas si se llama desde main.py
    import os
    ruta_modelo = os.path.join(os.path.dirname(__file__), "face_landmarker.task")
    
    options = FaceLandmarkerOptions(
      base_options=BaseOptions(model_asset_path=ruta_modelo),
      running_mode=RunningMode.IMAGE,
      num_faces=2,
      min_face_detection_confidence=0.4,
      min_face_presence_confidence=0.4,
      min_tracking_confidence=0.4
    )
    self.malla_facial = FaceLandmarker.create_from_options(options)
    self.dibujo_mp = drawing_utils
    self.FACEMESH_CONTOURS = mp.tasks.vision.FaceLandmarksConnections.FACE_LANDMARKS_CONTOURS

    # --- Indices de landmarks clave (MediaPipe Face Mesh - 468 puntos) ---
    # Ojos
    self.OJO_IZQ_INTERNO = 133
    self.OJO_IZQ_EXTERNO = 33
    self.OJO_DER_INTERNO = 362
    self.OJO_DER_EXTERNO = 263
    # Iris (requiere refine_landmarks=True)
    self.IRIS_IZQUIERDO = 468
    self.IRIS_DERECHO = 473
    # Puntos de referencia para angulo de cabeza
    self.SIEN_IZQUIERDA = 234
    self.SIEN_DERECHA = 454

    # --- Umbrales de alerta (ajustables desde config.py) ---
    self.UMBRAL_INCLINACION = 35  
    self.UMBRAL_MIRADA = 0.95     
    self.UMBRAL_TIEMPO = 5.0      
    
    self.funcion_alerta = funcion_alerta

    # --- Ventanas Deslizantes ---
    self.historial_mirada = []
    self.historial_inclinacion = []
    self.historial_rostro = []
    self.ultimo_reporte = 0.0
    self.cooldowns = {}

    # --- Inicializar OpenCV DNN (SSD ResNet-10) para rostros multiples de fondo ---
    ruta_prototxt = os.path.join(os.path.dirname(__file__), "dnn_model", "deploy.prototxt")
    ruta_caffemodel = os.path.join(os.path.dirname(__file__), "dnn_model", "res10_300x300_ssd_iter_140000.caffemodel")
    self.dnn_disponible = False
    if os.path.exists(ruta_prototxt) and os.path.exists(ruta_caffemodel):
        try:
            self.red_rostros = cv2.dnn.readNetFromCaffe(ruta_prototxt, ruta_caffemodel)
            self.red_rostros.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
            self.red_rostros.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)
            self.dnn_disponible = True
            print("[INFO] OpenCV DNN SSD ResNet-10 cargado para rostros de fondo.")
        except Exception as e:
            print(f"[ERROR] No se pudo cargar DNN ResNet-10: {e}")
  def configurar_sensibilidad(self, nivel: str):
    if nivel == "ALTA":
        self.UMBRAL_MIRADA = 0.75
        self.UMBRAL_TIEMPO = 2.0
    elif nivel == "BAJA":
        self.UMBRAL_MIRADA = 0.98
        self.UMBRAL_TIEMPO = 6.0
    else:
        self.UMBRAL_MIRADA = 0.90
        self.UMBRAL_TIEMPO = 4.0

  def procesar_frame(self, frame):
    datos = {
      "rostro_detectado": False,
      "inclinacion": 0.0,
      "mirada_x": 0.0,
      "mirada_y": 0.0,
      "alertas": []
    }

    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)
    resultado_mp = self.malla_facial.detect(mp_image)

    alto, ancho = frame.shape[:2]

    # --- Sin rostro ---
    if not resultado_mp.face_landmarks:
      self._manejar_sin_rostro(frame, datos)
      return frame, datos

    # --- Rostro detectado ---
    datos["rostro_detectado"] = True
    self._registrar_rostro_presente()
    
    # --- Multiples Rostros (Fondo con DNN) ---
    multiples = False
    if self.dnn_disponible:
        blob = cv2.dnn.blobFromImage(frame, 1.0, (300, 300), (104.0, 177.0, 123.0))
        self.red_rostros.setInput(blob)
        detecciones = self.red_rostros.forward()
        count_faces = 0
        for i in range(0, detecciones.shape[2]):
            confianza = detecciones[0, 0, i, 2]
            if confianza > 0.45: # Umbral balanceado para rostros de fondo
                count_faces += 1
        if count_faces > 1:
            multiples = True
    elif len(resultado_mp.face_landmarks) > 1:
        multiples = True

    if multiples:
        ahora = time.time()
        # Cooldown simple de 5 segundos para no hacer spam
        if "MULTIPLES_ROSTROS" not in self.cooldowns or (ahora - self.cooldowns["MULTIPLES_ROSTROS"] > 5.0):
            datos["alertas"].append("MULTIPLES_ROSTROS")
            if self.funcion_alerta: self.funcion_alerta("MULTIPLES_ROSTROS", 1.0, frame.copy())
            self.cooldowns["MULTIPLES_ROSTROS"] = ahora

    puntos_lista = resultado_mp.face_landmarks[0]
    lm = puntos_lista # acceso rapido a los 468 puntos

    # Dibujar contorno facial liviano
    # Dummy drawing struct to bridge tasks API with drawing_utils
    self.dibujo_mp.draw_landmarks(
      image = frame,
      landmark_list = puntos_lista,
      connections = self.FACEMESH_CONTOURS,
      landmark_drawing_spec = self.dibujo_mp.DrawingSpec(color=(0, 255, 120), thickness=1, circle_radius=0),
      connection_drawing_spec = self.dibujo_mp.DrawingSpec(color=(0, 255, 120), thickness=1, circle_radius=0)
    )

    # --- Inclinacion de cabeza ---
    inclinacion = self._calcular_inclinacion(lm, ancho, alto)
    datos["inclinacion"] = inclinacion
    self._verificar_inclinacion(inclinacion, datos, frame)

    # --- Direccion de la mirada ---
    mirada_x, mirada_y = self._calcular_mirada(lm)
    datos["mirada_x"] = mirada_x
    datos["mirada_y"] = mirada_y
    self._verificar_mirada(mirada_x, datos, frame)

    # --- HUD en pantalla ---
    self._dibujar_hud(frame, datos)

    return frame, datos


  def _calcular_inclinacion(self, lm, ancho, alto):
    sien_izq = lm[self.SIEN_IZQUIERDA]
    sien_der = lm[self.SIEN_DERECHA]

    xi, yi = int(sien_izq.x * ancho), int(sien_izq.y * alto)
    xd, yd = int(sien_der.x * ancho), int(sien_der.y * alto)

    delta_y = yd - yi
    # USAR ABSOLUTO en X para ignorar el efecto espejo de la camara
    delta_x = abs(xd - xi)
    
    # Si delta_x es muy pequenio, evitar errores
    if delta_x == 0: delta_x = 1

    angulo = np.degrees(np.arctan2(delta_y, delta_x))
    return angulo


  def _calcular_mirada(self, lm):
    try:
      iris_izq = lm[self.IRIS_IZQUIERDO]
      ojo_izq_i = lm[self.OJO_IZQ_INTERNO]
      ojo_izq_e = lm[self.OJO_IZQ_EXTERNO]

      iris_der = lm[self.IRIS_DERECHO]
      ojo_der_i = lm[self.OJO_DER_INTERNO]
      ojo_der_e = lm[self.OJO_DER_EXTERNO]

      # Reparacion del calculo para evitar divisores negativos y falsos positivos al instante:
      # Calculamos la distancia total como un valor absoluto
      ancho_ojo_izq = abs(ojo_izq_e.x - ojo_izq_i.x)
      ancho_ojo_der = abs(ojo_der_e.x - ojo_der_i.x)

      if ancho_ojo_izq < 0.001 or ancho_ojo_der < 0.001:
        return 0.0, 0.0 

      # Forzar valores absolutos reales para evitar ratios invertidos
      dist_izq = abs(iris_izq.x - ojo_izq_i.x)
      dist_der = abs(iris_der.x - ojo_der_i.x)
      
      ratio_izq = dist_izq / ancho_ojo_izq
      ratio_der = dist_der / ancho_ojo_der

      mirada_x = ((ratio_izq + ratio_der) / 2.0 - 0.5) * 2
      mirada_y = max(-1.0, min(1.0, (iris_izq.y - ojo_izq_i.y) * 10))

      return round(mirada_x, 3), round(mirada_y, 3)

    except IndexError:
      return 0.0, 0.0 

  def _verificar_inclinacion(self, angulo, datos, frame):
    tamano_ventana = int(30 * self.UMBRAL_TIEMPO) # asumiendo 30fps
    if tamano_ventana < 15: tamano_ventana = 15
    
    is_fuera = abs(angulo) > self.UMBRAL_INCLINACION
    self.historial_inclinacion.append(is_fuera)
    if len(self.historial_inclinacion) > tamano_ventana:
        self.historial_inclinacion.pop(0)
        
    porcentaje = sum(self.historial_inclinacion) / tamano_ventana
    
    ahora = time.time()
    if porcentaje >= 0.85 and (ahora - self.ultimo_reporte > 10.0):
        lado = "DERECHA" if angulo > 0 else "IZQUIERDA"
        alerta = f"CABEZA_INCLINADA_{lado}"
        datos["alertas"].append(alerta)
        if self.funcion_alerta: self.funcion_alerta(alerta, abs(angulo), frame.copy())
        self.ultimo_reporte = ahora
        self.historial_inclinacion = []

  def _verificar_mirada(self, mirada_x, datos, frame):
    tamano_ventana = int(30 * self.UMBRAL_TIEMPO)
    if tamano_ventana < 15: tamano_ventana = 15
    
    is_fuera = abs(mirada_x) > self.UMBRAL_MIRADA
    self.historial_mirada.append(is_fuera)
    if len(self.historial_mirada) > tamano_ventana:
        self.historial_mirada.pop(0)
        
    porcentaje = sum(self.historial_mirada) / tamano_ventana
    
    ahora = time.time()
    if porcentaje >= 0.85 and (ahora - self.ultimo_reporte > 10.0):
        lado = "DERECHA" if mirada_x > 0 else "IZQUIERDA"
        alerta = f"MIRADA_{lado}"
        datos["alertas"].append(alerta)
        if self.funcion_alerta: self.funcion_alerta(alerta, abs(mirada_x), frame.copy())
        self.ultimo_reporte = ahora
        self.historial_mirada = []

  def _manejar_sin_rostro(self, frame, datos):
    tamano_ventana = int(30 * self.UMBRAL_TIEMPO)
    if tamano_ventana < 15: tamano_ventana = 15
    
    # Si entra a este metodo, significa que no hay rostro (True = Falta rostro)
    self.historial_rostro.append(True)
    if len(self.historial_rostro) > tamano_ventana:
        self.historial_rostro.pop(0)
        
    porcentaje = sum(self.historial_rostro) / tamano_ventana
    
    ahora = time.time()
    if porcentaje >= 0.85 and (ahora - self.ultimo_reporte > 10.0):
        alerta = "ROSTRO_NO_DETECTADO"
        datos["alertas"].append(alerta)
        if self.funcion_alerta: self.funcion_alerta(alerta, 1.0, frame.copy())
        self.ultimo_reporte = ahora
        self.historial_rostro = []

    # Registrar el HUD
    import cv2
    cv2.putText(frame, "! Sin rostro detectado", (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
    
  def _registrar_rostro_presente(self):
    # Metodo auxiliar para cuando SI hay rostro, meter False en el historial
    tamano_ventana = int(30 * self.UMBRAL_TIEMPO)
    self.historial_rostro.append(False)
    if len(self.historial_rostro) > tamano_ventana:
        self.historial_rostro.pop(0)

  def _dibujar_hud(self, frame, datos):
    inclinacion = datos["inclinacion"]
    mirada_x = datos["mirada_x"]

    color_inclinacion = (0, 255, 0) if abs(inclinacion) < self.UMBRAL_INCLINACION else (0, 0, 255)
    color_mirada = (0, 255, 0) if abs(mirada_x)  < self.UMBRAL_MIRADA   else (0, 0, 255)

    cv2.putText(frame, f"Inclinacion: {inclinacion:+.1f} grados",
          (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color_inclinacion, 2)
    cv2.putText(frame, f"Mirada X: {mirada_x:+.2f}",
          (10, 58), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color_mirada, 2)

    for i, alerta in enumerate(datos["alertas"]):
      cv2.putText(frame, f"ALERTA: {alerta}",
            (10, 90 + i * 28), cv2.FONT_HERSHEY_SIMPLEX,
            0.65, (0, 0, 255), 2)


  def liberar(self):
    self.malla_facial.close()
