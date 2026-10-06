import time
import threading
import numpy as np
import pyaudio
import cv2
import torch

try:
  from silero_vad import load_silero_vad, VADIterator
except ImportError:
  load_silero_vad = None
  print("ADVERTENCIA: 'silero-vad' no instalado. El modulo de Audio estara inactivo.")

class MonitorAudio:
  def __init__(self, funcion_alerta=None):
    self.activo = False
    self.hilo_audio = None
    self.funcion_alerta = funcion_alerta
    self.esta_hablando = False  # Para Fusion de Sensores
    
    # Umbrales por defecto (Media)
    self.umbral_prob = 0.3
    self.chunks_requeridos = 15
    
    # Configuracion de Silero VAD (16kHz, chunks de 512 = 32ms)
    self.RATE = 16000
    self.CHUNK = 512
    
    self.ultimo_tiempo_alerta = 0
    self.configurar_sensibilidad("MEDIA") # Valores por defecto
    
    if load_silero_vad:
      print("Cargando modelo Silero VAD (Micro-IA)...")
      try:
        self.modelo = load_silero_vad(onnx=True)
        self.vad_iterator = VADIterator(self.modelo)
        print("Modelo Silero VAD cargado exitosamente.")
      except Exception as e:
        print(f"Error cargando Silero VAD: {e}")
        self.modelo = None
    else:
      self.modelo = None

  def configurar_sensibilidad(self, nivel: str):
      # 1 segundo = 31.25 chunks (a 16000 Hz y chunks de 512)
      self.nivel_sensibilidad = nivel.upper()
      
      if self.nivel_sensibilidad == "ALTA":
          # Examen estricto: 1.5s de voz en una ventana de 3s activa la alerta
          self.umbral_prob = 0.20
          self.segundos_requeridos = 1.5
          self.segundos_ventana = 3.0
      elif self.nivel_sensibilidad == "BAJA":
          # Examen flexible (ej. Matematicas): 5s de voz en una ventana de 8s activa la alerta
          self.umbral_prob = 0.30
          self.segundos_requeridos = 5.0
          self.segundos_ventana = 8.0
      else:
          # MEDIA por defecto: 3s de voz en una ventana de 5s
          self.umbral_prob = 0.25
          self.segundos_requeridos = 3.0
          self.segundos_ventana = 5.0
          
      chunks_por_segundo = self.RATE / self.CHUNK
      self.chunks_requeridos = int(self.segundos_requeridos * chunks_por_segundo)
      self.max_chunks_ventana = int(self.segundos_ventana * chunks_por_segundo)

  def iniciar(self):
    if self.activo: return
    self.activo = True
    self.hilo_audio = threading.Thread(target=self._ciclo_escucha, daemon=True)
    self.hilo_audio.start()

  def detener(self):
    self.activo = False

  def _ciclo_escucha(self):
    if not self.modelo:
      return

    p = pyaudio.PyAudio()
    try:
      stream = p.open(format=pyaudio.paInt16,
              channels=1,
              rate=self.RATE,
              input=True,
              frames_per_buffer=self.CHUNK)
    except Exception as e:
      print(f"No se pudo iniciar el microfono: {e}")
      return

    print("[AUDIO] Monitoreo VAD Inteligente iniciado...")
    
    buffer_ventana = []
    buffer_grabacion = []
    estado_grabando = False
    silencio_continuo = 0

    while self.activo:
      try:
        data = stream.read(self.CHUNK, exception_on_overflow=False)
        audio_data = np.frombuffer(data, dtype=np.int16)
        audio_float32 = audio_data.astype(np.float32) / 32768.0
        
        tensor_audio = torch.from_numpy(audio_float32)
        probabilidad = self.modelo(tensor_audio, self.RATE).item()
        
        # Mantener el buffer de contexto siempre rodando
        if not estado_grabando:
            buffer_ventana.append((audio_data, probabilidad))
            if len(buffer_ventana) > self.max_chunks_ventana:
                buffer_ventana.pop(0)
                
            chunks_con_voz = sum(1 for _, prob in buffer_ventana if prob > self.umbral_prob)
            self.esta_hablando = chunks_con_voz > 3
            
            # Disparar grabacion si supera el umbral estricto configurado por el profesor
            if chunks_con_voz >= self.chunks_requeridos:
                estado_grabando = True
                silencio_continuo = 0
                buffer_grabacion = list(buffer_ventana)  # Copiar el contexto
                print(f"[AUDIO] Voz continua detectada ({self.segundos_requeridos}s). Grabando evidencia...")
        
        else:
            # ESTADO GRABANDO
            buffer_grabacion.append((audio_data, probabilidad))
            self.esta_hablando = True
            
            if probabilidad < self.umbral_prob:
                silencio_continuo += 1
            else:
                silencio_continuo = 0
                
            # Detener si hay 2.5 segundos de silencio continuo (aprox 78 chunks)
            # O si la grabacion ya dura mas de 25 segundos (evitar archivos gigantes)
            if silencio_continuo > 78 or len(buffer_grabacion) > (self.RATE / self.CHUNK * 25.0):
                print("[AUDIO] Fin de voz. Empaquetando y enviando audio completo.")
                
                if self.funcion_alerta:
                    import wave, io, base64
                    audio_np = np.concatenate([chunk for chunk, _ in buffer_grabacion])
                    buf = io.BytesIO()
                    with wave.open(buf, 'wb') as wf:
                        wf.setnchannels(1)
                        wf.setsampwidth(2)
                        wf.setframerate(self.RATE)
                        wf.writeframes(audio_np.tobytes())
                    audio_b64 = base64.b64encode(buf.getvalue()).decode('utf-8')
                    
                    duracion_segundos = len(buffer_grabacion) * self.CHUNK / self.RATE
                    
                    alerta_dict = {
                      "claseAlerta": "AUDIO",
                      "nivelRiesgo": "ALTO",
                      "vocesDetectadas": 1,
                      "confianzaVoz": float(round(max(p for _, p in buffer_grabacion), 2)),
                      "transcripcion": f"Actividad vocal prolongada detectada (Clip de {duracion_segundos:.1f}s)",
                      "urlAudio": audio_b64
                    }
                    self.funcion_alerta(alerta_dict)
                
                estado_grabando = False
                buffer_ventana = []  # Limpiar contexto para evitar re-disparos inmediatos
                self.esta_hablando = False
                
      except Exception as e:
        print(f"Error en bucle de audio: {e}")
        time.sleep(1)

    stream.stop_stream()
    stream.close()
    p.terminate()
monitor_audio = MonitorAudio()

