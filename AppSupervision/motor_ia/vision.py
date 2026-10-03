import cv2
from motor_ia.detector_rostros import DetectorRostro
from motor_ia.detector_posturas import DetectorPostura
from motor_ia.detector_objetos import DetectorObjetos
from motor_ia.analisis_comportamiento import AnalizadorComportamiento

class AnalizadorVision:
  """
  Cerebro de visión computacional.
  Integra YOLOv8n, MediaPipe Pose y MediaPipe Face Mesh.
  """
  def __init__(self):
    # Instanciar los detectores individuales
    try:
      self.detector_rostro = DetectorRostro()
      self.detector_postura = DetectorPostura()
      self.mediapipe_disponible = True
    except Exception as e:
      print(f'Error inicializando MediaPipe: {e}')
      # Si MediaPipe falla por incompatibilidad con Python 3.13
      self.detector_rostro = None
      self.detector_postura = None
      self.mediapipe_disponible = False
      print("ADVERTENCIA: MediaPipe no compatible con esta versión de Python. Análisis facial desactivado.")
      
    self.detector_objetos = DetectorObjetos(frames_entre_analisis=1)
    
    # Instanciar el cerebro que evalúa el comportamiento global
    self.analizador_comportamiento = AnalizadorComportamiento()
    
    self.activo = True

  def configurar_sensibilidad(self, nivel: str):
    """
    Ajusta la sensibilidad de todos los detectores de la IA.
    """
    if self.detector_rostro:
        if hasattr(self.detector_rostro, "configurar_sensibilidad"):
            self.detector_rostro.configurar_sensibilidad(nivel)
    if self.detector_postura:
        if hasattr(self.detector_postura, "configurar_sensibilidad"):
            self.detector_postura.configurar_sensibilidad(nivel)
    if self.detector_objetos:
        if hasattr(self.detector_objetos, "configurar_sensibilidad"):
            self.detector_objetos.configurar_sensibilidad(nivel)
    if self.analizador_comportamiento:
        if hasattr(self.analizador_comportamiento, "configurar_sensibilidad"):
            self.analizador_comportamiento.configurar_sensibilidad(nivel)

  def analizar_frame(self, frame_cv2):
    """
    Recibe una imagen OpenCV, ejecuta los modelos y devuelve el resumen.
    """
    if not self.activo or frame_cv2 is None:
      return {"nivel_riesgo": 1, "alertas_confirmadas": [], "descripcion": "Inactivo"}
      
    datos_rostro = {}
    datos_postura = {}
    
    if self.mediapipe_disponible:
      _, datos_rostro = self.detector_rostro.procesar_frame(frame_cv2)
      _, datos_postura = self.detector_postura.procesar_frame(frame_cv2)
      
    _, datos_objetos = self.detector_objetos.procesar_frame(frame_cv2)
    
    # 2. Fusion de Sensores - Leer Audio
    try:
        from motor_ia.audio import monitor_audio
        audio_hablando = getattr(monitor_audio, 'esta_hablando', False)
    except Exception:
        audio_hablando = False
        
    datos_audio = {"hablando": audio_hablando}
    
    # 3. Enviar al Juez Central
    resumen = self.analizador_comportamiento.analizar(
      datos_rostro, datos_objetos, datos_postura, datos_audio
    )
    
    crudas = list(datos_rostro.get("alertas", [])) + list(datos_postura.get("alertas", [])) + list(datos_objetos.get("alertas", []))
    
    # Extraer estados raw para alimentar el Buho continuamente
    if not datos_rostro.get("rostro_detectado", True): crudas.append("MINOR_ROSTRO_NO_DETECTADO")
    if abs(datos_rostro.get("inclinacion", 0)) > 20: crudas.append("MINOR_CABEZA_INCLINADA")
    
    mx, my = datos_rostro.get("mirada_x", 0.0), datos_rostro.get("mirada_y", 0.0)
    if abs(mx) > 0.65: crudas.append("MINOR_MIRADA")

    return {
      "nivel_riesgo": resumen["nivel_riesgo"],
      "alertas": resumen["alertas_confirmadas"],
      "descripcion": resumen["descripcion"],
      "alertas_crudas": crudas
    }

analizador_vision = AnalizadorVision()
