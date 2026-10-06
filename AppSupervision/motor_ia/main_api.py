from fastapi import FastAPI, BackgroundTasks, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import base64
import cv2
import numpy as np

# Importar los submódulos del cerebro interno
from motor_ia.sistema import monitor_sys
from motor_ia.audio import monitor_audio
from motor_ia.vision import analizador_vision
from motor_ia.perifericos import monitor_perifericos

app = FastAPI(title="Motor IA Estudiante - UPC")

# Habilitar CORS para peticiones locales desde la UI
app.add_middleware(
  CORSMiddleware,
  allow_origins=["*"],
  allow_credentials=True,
  allow_methods=["*"],
  allow_headers=["*"],
)

@app.get("/health")
def health_check():
  """Verificar que el motor de IA local está vivo"""
  return {"status": "ok", "message": "Motor IA corriendo en background"}

@app.post("/iniciar_supervision")
def iniciar_supervision():
  """Enciende los hilos de audio y psutil (control de sistema)"""
  try:
      from api.cliente_respuesta import cliente_api
      monitor_audio.funcion_alerta = lambda alerta: cliente_api.enviar_evidencia_silenciosa([alerta["claseAlerta"]], frame_base64=alerta.get("urlAudio"))
  except Exception as e:
      print(f"Error conectando cliente_api al audio: {e}")
  monitor_sys.iniciar()
  monitor_audio.iniciar()
  monitor_perifericos.iniciar()
  return {"status": "ok", "message": "Supervisión de audio y sistema iniciada"}

@app.post("/detener_supervision")
def detener_supervision():
  """Apaga los hilos locales"""
  monitor_sys.detener()
  monitor_audio.detener()
  monitor_perifericos.detener()
  return {"status": "ok", "message": "Supervisión detenida"}

from pydantic import BaseModel

class SensibilidadRequest(BaseModel):
  nivel: str

@app.post("/configurar_sensibilidad")
def configurar_sensibilidad(req: SensibilidadRequest):
  """Configura la sensibilidad del cerebro de visión (MediaPipe, YOLO, etc.)"""
  try:
    analizador_vision.configurar_sensibilidad(req.nivel)
    return {"status": "ok", "nivel": req.nivel}
  except Exception as e:
    return {"status": "error", "message": str(e)}

class FrameRequest(BaseModel):
  frame_base64: str

@app.post("/analizar_frame")
def analizar_frame(request: FrameRequest):
  """
  Recibe un frame de la webcam desde PyQt6,
  corre la IA (MediaPipe, YOLO, HuggingFace) y devuelve las alertas.
  """
  try:
    nparr = np.frombuffer(base64.b64decode(request.frame_base64), np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    # Preservar snapshot limpio original de la cámara para evidencia forense
    img_evidencia_limpia = img.copy()

    # Ejecutar el análisis de visión (esto dibuja el HUD/landmarks en 'img' para streaming en vivo)
    resultados = analizador_vision.analizar_frame(img)
    
    # 1. Preview ultra-liviano para streaming continuo al profesor (640x360 cal 55, ~8 KB)
    stream_preview = cv2.resize(img, (640, 360), interpolation=cv2.INTER_AREA)
    _, buffer_anotado = cv2.imencode('.jpg', stream_preview, [cv2.IMWRITE_JPEG_QUALITY, 55])
    frame_anotado_b64 = base64.b64encode(buffer_anotado).decode('utf-8')
    
    # 2. Snapshot de alta definición (1280x720 HD cal 80) para evidencia forense
    # Se genera usando el frame LIMPIO capturado de la webcam, sin mallas artificiales de MediaPipe
    frame_evidencia_b64 = None
    tiene_alertas = bool(resultados.get("alertas")) or bool(resultados.get("alertas_crudas"))
    if tiene_alertas:
      _, buffer_hd = cv2.imencode('.jpg', img_evidencia_limpia, [cv2.IMWRITE_JPEG_QUALITY, 80])
      frame_evidencia_b64 = base64.b64encode(buffer_hd).decode('utf-8')
    
    return {
      "status": "ok", 
      "resultados": resultados,
      "frame_anotado": frame_anotado_b64,
      "frame_evidencia": frame_evidencia_b64
    }
  except Exception as e:
    print(f"ERROR EN VISION: {e}")
    return {"status": "error", "message": str(e)}

if __name__ == "__main__":
  uvicorn.run(app, host="127.0.0.1", port=8005)
