import threading
import io
import base64
from PIL import ImageGrab
from pynput import keyboard, mouse

class MonitorPerifericos:
  def __init__(self, funcion_alerta=None):
    self.activo = False
    self.funcion_alerta = funcion_alerta
    self.teclado_listener = None
    self.ctrl_presionado = False
    self.alt_presionado = False
    self.ultimo_reporte = ""
    self.timer_reporte = None

  def iniciar(self):
    if self.activo: return
    self.activo = True
    self.teclado_listener = keyboard.Listener(on_press=self._on_press, on_release=self._on_release)
    self.teclado_listener.start()

  def detener(self):
    self.activo = False
    if self.teclado_listener:
      self.teclado_listener.stop()

  def _reset_reporte(self):
    self.ultimo_reporte = ""

  def _capturar_pantalla_b64(self):
    try:
      captura = ImageGrab.grab(all_screens=True)
      buffer = io.BytesIO()
      captura.save(buffer, format="WEBP", quality=50)
      return base64.b64encode(buffer.getvalue()).decode('utf-8')
    except Exception as e:
      print(f"Error al capturar pantalla teclado: {e}")
      return None

  def _emitir_alerta(self, mensaje):
    if self.ultimo_reporte == mensaje: return
    self.ultimo_reporte = mensaje
    if self.timer_reporte: self.timer_reporte.cancel()
    self.timer_reporte = threading.Timer(2.0, self._reset_reporte)
    self.timer_reporte.start()

    img_b64 = self._capturar_pantalla_b64()

    evidencia = {
      "claseAlerta": "TECLADO",
      "nivelRiesgo": "ALTO",
      "combinacionTeclas": mensaje,
      "patronSospechoso": "USO_PROHIBIDO",
      "urlCapturaPantalla": img_b64
    }
    
    if self.funcion_alerta:
      self.funcion_alerta(evidencia)
    else:
      try:
        from api.cliente_respuesta import cliente_api
        from utils.gestor_sesion import sesion_actual
        sesion_id = sesion_actual.obtener_sesion_id()
        if sesion_id:
          cliente_api.enviar_alerta(sesion_id, evidencia)
          print(f"[EVIDENCIA TECLADO ENVIADA] {mensaje}")
      except Exception as e:
        print(f"Error enviando evidencia de teclado: {e}")

  def _on_press(self, key):
    if not self.activo: return
    try:
      if key == keyboard.Key.ctrl_l or key == keyboard.Key.ctrl_r:
        self.ctrl_presionado = True
      elif key == keyboard.Key.alt_l or key == keyboard.Key.alt_r or key == keyboard.Key.alt_gr:
        self.alt_presionado = True
      elif key == keyboard.Key.shift or key == keyboard.Key.shift_r:
        self.shift_presionado = True
        
      if self.ctrl_presionado and hasattr(self, 'shift_presionado') and self.shift_presionado and key == keyboard.Key.esc:
        self._emitir_alerta("Administrador de Tareas (Ctrl+Shift+Esc)")
        
      if self.ctrl_presionado and hasattr(key, 'char') and key.char:
        char_lower = key.char.lower()
        if char_lower == 'c': self._emitir_alerta("Intento de Copiar (Ctrl+C)")
        elif char_lower == 'v': self._emitir_alerta("Intento de Pegar (Ctrl+V)")
        elif char_lower == 'a': self._emitir_alerta("Intento de Seleccionar Todo (Ctrl+A)")
        else: self.ctrl_presionado = False
      
      if self.alt_presionado and hasattr(key, 'char') and key.char:
        self.alt_presionado = False
      
      if self.alt_presionado and key == keyboard.Key.tab:
        self._emitir_alerta("Cambio de ventana (Alt+Tab)")
        
      if key == keyboard.Key.print_screen:
        self._emitir_alerta("Captura de pantalla (PrtScn)")
        
      if key == keyboard.Key.cmd or key == keyboard.Key.cmd_r:
        self._emitir_alerta("Menu Inicio (Tecla Windows)")
    except Exception:
      pass

  def _on_release(self, key):
    if key == keyboard.Key.ctrl_l or key == keyboard.Key.ctrl_r:
      self.ctrl_presionado = False
    elif key == keyboard.Key.alt_l or key == keyboard.Key.alt_r or key == keyboard.Key.alt_gr:
      self.alt_presionado = False
    elif key == keyboard.Key.shift or key == keyboard.Key.shift_r:
      self.shift_presionado = False

monitor_perifericos = MonitorPerifericos()
