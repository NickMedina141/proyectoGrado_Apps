from PyQt6.QtCore import QThread, pyqtSignal
import websocket
import json
from config.configuracion import url_websocket
from utils.gestor_sesion import sesion_actual

class HiloWebSocket(QThread):
  alerta_recibida = pyqtSignal(dict)
  frame_recibido = pyqtSignal(str) # Señal para el video base64
  conexion_perdida = pyqtSignal(str)
  conectado = pyqtSignal() # Señal para saber cuando conectó al broker STOMP

  #Constructor con parametros de la clase
  def __init__(self, ruta_sala="", topico_base="/topic/alertas"):
    super().__init__()
    self.url_conexion = url_websocket
    self.ruta_sala = ruta_sala
    self.topico_base = topico_base
    self.ws = None
    self.corriendo = True

  def run(self):
    import time
    while self.corriendo:
        cabeceras = []
        token = sesion_actual.obtener_token()
        if token:
          cabeceras.append(f"Authorization: Bearer {token}")

        self.ws = websocket.WebSocketApp(
          self.url_conexion,
          header=cabeceras,
          on_open=self.al_abrir,
          on_message=self.al_recibir_mensaje,
          on_error=self.al_tener_error,
          on_close=self.al_cerrar
        )

        try:
          # ping_interval y ping_timeout evitan cuelgues fantasmas
          self.ws.run_forever(ping_interval=30, ping_timeout=10)
        except Exception as e:
          print(f"[WS-PROFESOR] Excepción fatal atrapada en run_forever: {e}")

        if self.corriendo:
            print("[WS-PROFESOR] Intentando reconectar en 3 segundos...")
            time.sleep(3)

  def al_abrir(self, ws):
    print(f"[WS-PROFESOR] Abriendo túnel STOMP hacia {self.url_conexion}...")
    try:
      import socket
      if hasattr(ws, 'sock') and ws.sock:
        ws.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    except Exception:
      pass
    # Enviar trama STOMP CONNECT (host es obligatorio en STOMP 1.2)
    connect_frame = "CONNECT\naccept-version:1.1,1.2\nhost:localhost\nheart-beat:10000,10000\n\n\x00"
    ws.send(connect_frame)

  def enviar_comando(self, destino, payload_dict):
    if self.ws and self.ws.sock and self.ws.sock.connected:
      cuerpo = json.dumps(payload_dict)
      longitud = len(cuerpo.encode('utf-8'))
      frame = f"SEND\ndestination:{destino}\ncontent-type:application/json\ncontent-length:{longitud}\n\n{cuerpo}\x00"
      self.ws.send(frame)
      print(f"[WS-PROFESOR] Enviando comando a {destino}: {payload_dict}")

  def al_recibir_mensaje(self, ws, mensaje):
    if mensaje.startswith("CONNECTED"):
      print(f"[WS-PROFESOR] ¡Conectado a STOMP! Suscribiéndose a {self.ruta_sala}...")
      # Suscribirse al tópico UNA VEZ conectados
      topico = f"{self.topico_base}/{self.ruta_sala}" if self.ruta_sala and not self.ruta_sala.startswith("/") else (self.topico_base + self.ruta_sala if self.ruta_sala else self.topico_base)
      sub_frame = f"SUBSCRIBE\nid:sub-0\ndestination:{topico}\n\n\x00"
      ws.send(sub_frame)
      self.conectado.emit()
      return
    if mensaje.startswith("MESSAGE"):
      try:
        # El cuerpo está despues de una linea en blanco en el protocolo STOMP
        partes = mensaje.split("\n\n", 1)
        if len(partes)>= 2:
          cuerpo = partes[1].replace('\x00', '').strip()
          if cuerpo:
            datos_json = json.loads(cuerpo)
            
            # Si es un frame de video
            if "frameBase64" in datos_json:
              self.frame_recibido.emit(datos_json["frameBase64"])
            else:
              self.alerta_recibida.emit(datos_json)
      except Exception as e:
        pass # Evitar spammear la consola con errores de parseo a 30fps

  def al_tener_error(self, ws, error):
    print(f"[WS-PROFESOR] ERROR EN WEBSOCKET: {error}")
    self.conexion_perdida.emit(f"Error de la red en el túnel: {str(error)}")

  def al_cerrar(self, ws, codigo, mensaje):
    print(f"[WS-PROFESOR] CONEXION CERRADA. Codigo: {codigo}, Msj: {mensaje}")
    if self.corriendo:
      self.conexion_perdida.emit("El servidor cerró la conexión en vivo")

  def detener(self):
    self.corriendo = False
    if self.ws:
      self.ws.close()
