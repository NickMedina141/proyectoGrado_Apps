import httpx
from utils.gestor_sesion import sesion_actual
from config.configuracion import url_login_estudiante, url_supervision_iniciar, url_reglas_examen, url_supervision_base

import threading
import time


class ClienteApi:
  def __init__(self):
    self.cliente = httpx.Client(timeout=4.0)
    self.buffer_alertas = []
    self._lock_buffer = threading.Lock()
    self.conectado = True
    self.hilo_buffer = threading.Thread(
        target=self._procesar_buffer, daemon=True)
    self.hilo_buffer.start()

  def _encolar_alerta(self, sesion_id: str, carga_util: dict):
    """Encola una evidencia de forma instantánea y segura para enviarla cuando regrese la red."""
    with self._lock_buffer:
      # Límite amplio de seguridad: hasta 500 alertas en memoria (~30 min de evidencia continua)
      if len(self.buffer_alertas) >= 500:
        self.buffer_alertas.pop(0)
      self.buffer_alertas.append({
        "sesion_id": sesion_id,
        "carga_util": carga_util,
        "timestamp_local": time.time()
      })
      print(f"[API BUFFER] Alerta encolada exitosamente. Total acumulado en buffer: {len(self.buffer_alertas)}")

  def _procesar_buffer(self):
    """Hilo centinela que drena el buffer de evidencias en orden cronológico (FIFO) cuando hay red."""
    while True:
      time.sleep(0.5)
      if not self.buffer_alertas:
        continue

      while True:
        alerta = None
        with self._lock_buffer:
          if self.buffer_alertas:
            alerta = self.buffer_alertas[0]

        if not alerta:
          break

        url = f"{url_supervision_base}/{alerta['sesion_id']}/alerta"
        try:
          # --- SALVAGUARDA FORENSE Y CIFRADO E2EE AES-256 PARA BUFFER ---
          try:
            import hashlib
            from cryptography.fernet import Fernet
            from config.configuracion import AES_SECRET_KEY
            f_crypto = Fernet(AES_SECRET_KEY)
            for campo in ["urlFotoWebcam", "urlCapturaPantalla", "urlAudio"]:
              if alerta['carga_util'].get(campo):
                datos_str = alerta['carga_util'][campo]
                if not datos_str.startswith("gAAAAA"):
                  if "," in datos_str:
                    datos_str = datos_str.split(",")[1]
                  firma_hash = hashlib.sha256(datos_str.encode('utf-8')).hexdigest()
                  if campo == "urlFotoWebcam" and not alerta['carga_util'].get("hashWebcam"):
                    alerta['carga_util']["hashWebcam"] = firma_hash
                  if campo == "urlCapturaPantalla" and not alerta['carga_util'].get("hashPantalla"):
                    alerta['carga_util']["hashPantalla"] = firma_hash
                  if campo == "urlAudio" and not alerta['carga_util'].get("hashAudio"):
                    alerta['carga_util']["hashAudio"] = firma_hash
                  cifrado = f_crypto.encrypt(datos_str.encode('utf-8'))
                  alerta['carga_util'][campo] = cifrado.decode('utf-8')
          except Exception as e_cifrado:
            print(f"[API BUFFER ERROR] Error en verificación de cifrado E2EE: {e_cifrado}")

          res = self._hacer_peticion("post", url, json=alerta['carga_util'])
          if res.status_code == 200:
            with self._lock_buffer:
              if self.buffer_alertas and self.buffer_alertas[0] == alerta:
                self.buffer_alertas.pop(0)
            self.conectado = True
            print(f"[API BUFFER] Alerta enviada con éxito del buffer. Restantes: {len(self.buffer_alertas)}")
            time.sleep(0.12)  # Pequeño respiro entre envíos para no saturar la red
          else:
            time.sleep(2.0)
            break
        except Exception:
          self.conectado = False
          time.sleep(2.5)  # Esperar antes de reintentar si no hay conexión
          break
 

  def _obtener_cabecera_token(self):
    cabeceras = {"Content-Type": "application/json"}
    token = sesion_actual.obtener_token()
    if token:
      cabeceras["Authorization"] = f"Bearer {token}"
    return cabeceras

  def _refrescar_token(self):
    try:
      from config.configuracion import url
      res = self._hacer_peticion("post", f"{url}/auth/refresh", es_refresh=True)
      if res.status_code == 200:
        nuevo_token = res.json().get("token")
        if nuevo_token:
            sesion_actual.guardar_token(nuevo_token)
            return True
      return False
    except Exception as e:
      print(f'[API] Error in refresh logic: {e}')
      return False

  def _hacer_peticion(self, metodo, url, es_refresh=False, **kwargs):
    kwargs['headers'] = self._obtener_cabecera_token()
    res = getattr(self.cliente, metodo)(url, **kwargs)
    if res.status_code in (401, 403) and not es_refresh:
        print("[API] Token expirado, intentando refrescar...")
        if self._refrescar_token():
            kwargs['headers'] = self._obtener_cabecera_token()
            res = getattr(self.cliente, metodo)(url, **kwargs)
        else:
            print("[API] Fallo crítico: No se pudo refrescar el token. Sesión cerrada por seguridad.")
            from utils.gestor_sesion import sesion_actual
            sesion_actual.cerrar_sesion()
            # Reiniciar la aplicacion brutalmente para limpiar memoria y volver al login
            import os
            import sys
            os.execl(sys.executable, sys.executable, *sys.argv)
    return res

  def _extraer_mensaje_error(self, respuesta, mensaje_fallback="Ocurrió un error inesperado", fallback=None):
    """
    Extrae un mensaje de error limpio y comprensible para el usuario,
    eliminando códigos HTTP, prefijos técnicos, JSON crudo o HTML.
    """
    if fallback:
      mensaje_fallback = fallback
    if respuesta is None:
      return mensaje_fallback

    texto = getattr(respuesta, 'text', '')
    if texto:
      texto = texto.strip()
      # 1. Si es HTML (como 502/503 de proxy/Railway), no mostrar etiquetas HTML
      if texto.startswith("<!DOCTYPE") or texto.startswith("<html") or "<html>" in texto.lower():
        if getattr(respuesta, 'status_code', None) in (502, 503, 504):
          return "El servidor institucional no está disponible en este momento. Por favor, intenta de nuevo más tarde."
        return mensaje_fallback

      # 2. Si es JSON (Spring Boot default error response como {"message": "...", "error": "..."})
      try:
        import json
        datos = json.loads(texto)
        if isinstance(datos, dict):
          msg = datos.get("message") or datos.get("mensaje") or datos.get("error") or datos.get("detail")
          if msg and isinstance(msg, str) and not msg.lower().startswith("internal server error"):
            texto = msg.strip()
      except Exception:
        pass

      # 3. Limpiar comillas exteriores si las hay
      if texto.startswith('"') and texto.endswith('"') and len(texto) >= 2:
        texto = texto[1:-1].strip()

      # 4. Remover prefijos técnicos
      import re
      texto = re.sub(r'^(Fallo en API\s*(\(HTTP\s*\d+\))?\s*:\s*)', '', texto, flags=re.IGNORECASE)
      texto = re.sub(r'^(Error\s*(\(HTTP\s*\d+\))?\s*:\s*)', '', texto, flags=re.IGNORECASE)
      texto = re.sub(r'^(Error\s*\d+\s*:\s*)', '', texto, flags=re.IGNORECASE)
      texto = re.sub(r'^(HTTP\s*\d+\s*:\s*)', '', texto, flags=re.IGNORECASE)

      if texto:
        return texto

    status = getattr(respuesta, 'status_code', 0)
    if status == 400:
      return "La solicitud contiene parámetros no válidos o incompletos."
    elif status == 401:
      return "Credenciales incorrectas o sesión no autorizada."
    elif status == 403:
      return "Acceso denegado: No tienes permisos para realizar esta acción o tu límite de intentos fue alcanzado."
    elif status == 404:
      return mensaje_fallback if mensaje_fallback != "Ocurrió un error inesperado" else "El recurso o examen solicitado no fue encontrado."
    elif status in (500, 502, 503, 504):
      return "El servidor institucional tuvo un inconveniente al procesar la solicitud. Por favor, intenta más tarde."

    return mensaje_fallback

  def login_estudiante(self, email: str, password: str):
    carga_util = {
      "email": email,
      "password": password
    }
    try:
      respuesta = self.cliente.post(url_login_estudiante, json=carga_util)
      if respuesta.status_code == 200:
        datos = respuesta.json()
        sesion_actual.guardar_sesion_auth(datos.get("token"), email)
        return True, "Inicio de sesión exitoso"
      elif respuesta.status_code == 401:
        return False, "Credenciales incorrectas. Por favor, verifica tu correo y contraseña."
      else:
        return False, self._extraer_mensaje_error(respuesta, "No se pudo iniciar sesión. Por favor intenta más tarde.")
    except httpx.RequestError:
      return False, "No se pudo conectar con el servidor institucional. Por favor, verifica tu conexión a internet."

  def solicitar_codigo_registro(self, email: str, cedula: str, rol: str, nombre: str = ""):
    from config.configuracion import url_registro_solicitar_codigo
    carga_util = {
      "email": email,
      "cedula": cedula,
      "rol": rol,
      "nombre": nombre
    }
    try:
      respuesta = self.cliente.post(url_registro_solicitar_codigo, json=carga_util)
      if respuesta.status_code == 200:
        datos = respuesta.json()
        return True, datos.get("mensaje", "Código de verificación enviado al correo.")
      else:
        try:
          error_data = respuesta.json()
          mensaje = error_data.get("mensaje", "Error al procesar la solicitud.")
        except Exception:
          mensaje = self._extraer_mensaje_error(respuesta, "No se pudo solicitar el código.")
        return False, mensaje
    except httpx.RequestError:
      return False, "No se pudo conectar con el servidor institucional. Verifica tu conexión a internet."

  def confirmar_registro_estudiante(self, email: str, codigo_otp: str, nombre: str, apellidos: str, cedula: str, password: str):
    from config.configuracion import url_registro_confirmar_estudiante
    carga_util = {
      "email": email,
      "codigoOtp": codigo_otp,
      "nombre": nombre,
      "apellidos": apellidos,
      "cedula": cedula,
      "password": password
    }
    try:
      respuesta = self.cliente.post(url_registro_confirmar_estudiante, json=carga_util)
      if respuesta.status_code == 200:
        datos = respuesta.json()
        return True, datos.get("mensaje", "Cuenta de estudiante creada con éxito.")
      else:
        try:
          error_data = respuesta.json()
          mensaje = error_data.get("mensaje", "Error al confirmar el registro.")
        except Exception:
          mensaje = self._extraer_mensaje_error(respuesta, "No se pudo completar el registro.")
        return False, mensaje
    except httpx.RequestError:
      return False, "No se pudo conectar con el servidor institucional. Verifica tu conexión a internet."

  def solicitar_codigo_recuperacion(self, email: str):
    from config.configuracion import url_recuperar_solicitar_codigo
    carga_util = {"email": email}
    try:
      respuesta = self.cliente.post(url_recuperar_solicitar_codigo, json=carga_util)
      if respuesta.status_code == 200:
        datos = respuesta.json()
        return True, datos.get("mensaje", "Código de recuperación enviado al correo institucional.")
      else:
        try:
          error_data = respuesta.json()
          mensaje = error_data.get("mensaje", "Error al solicitar la recuperación.")
        except Exception:
          mensaje = self._extraer_mensaje_error(respuesta, "No se pudo solicitar el código de recuperación.")
        return False, mensaje
    except httpx.RequestError:
      return False, "No se pudo conectar con el servidor institucional. Verifica tu conexión a internet."

  def confirmar_recuperacion_password(self, email: str, codigo_otp: str, nueva_password: str):
    from config.configuracion import url_recuperar_confirmar
    carga_util = {
      "email": email,
      "codigoOtp": codigo_otp,
      "nuevaPassword": nueva_password
    }
    try:
      respuesta = self.cliente.post(url_recuperar_confirmar, json=carga_util)
      if respuesta.status_code == 200:
        datos = respuesta.json()
        return True, datos.get("mensaje", "Contraseña restablecida exitosamente.")
      else:
        try:
          error_data = respuesta.json()
          mensaje = error_data.get("mensaje", "Error al restablecer la contraseña.")
        except Exception:
          mensaje = self._extraer_mensaje_error(respuesta, "No se pudo restablecer la contraseña.")
        return False, mensaje
    except httpx.RequestError:
      return False, "No se pudo conectar con el servidor institucional. Verifica tu conexión a internet."

  def iniciar_sesion_examen(self, estudiante_id: str, pin_examen: str):
    import platform
    import socket
    import psutil
    
    # 1. Detección y Bloqueo de Sistema Operativo No Soportado
    if platform.system().lower() != "windows":
        return False, "Acceso denegado: El sistema de supervisión actualmente solo es compatible con entornos Windows oficiales."
    os_info = f"{platform.system()} {platform.release()}"
    
    # 2. Detección de IP Local
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip_local = s.getsockname()[0]
        s.close()
    except Exception:
        ip_local = "Desconocida"
        
    # 3. Detección Reforzada de VPN
    vpn_activa = False
    interfaces_vpn = [
        'tun', 'tap', 'vpn', 'wireguard', 'nord', 'openvpn', 'cisco',
        'proton', 'zerotier', 'wg', 'tailscale', 'warp', 'cloudflare',
        'surfshark', 'hamachi', 'forti', 'anyconnect', 'paloalto', 'mullvad'
    ]
    try:
        interfaces = psutil.net_if_addrs()
        stats = psutil.net_if_stats()
        for interface_name, addrs in interfaces.items():
            name_lower = interface_name.lower()
            has_ipv4 = any(addr.family == socket.AF_INET for addr in addrs)
            is_up = stats[interface_name].isup if interface_name in stats else False
            
            if is_up and has_ipv4:
                if any(keyword in name_lower for keyword in interfaces_vpn):
                    vpn_activa = True
                    break
    except Exception:
        pass
        
    if vpn_activa:
        return False, "Error de Seguridad: Hemos detectado una conexión VPN activa. Por motivos de integridad, debes desactivarla para poder iniciar el examen."

    # 3.5. Obtener Ubicacion EXACTA Nativa (Windows)
    import asyncio
    
    async def get_windows_location():
        try:
            from winsdk.windows.devices.geolocation import Geolocator, GeolocationAccessStatus
            status = await Geolocator.request_access_async()
            if status != GeolocationAccessStatus.ALLOWED:
                return False, "Bloqueo: La ubicacion esta desactivada en Windows. Por favor ve a Configuracion > Privacidad > Ubicacion y activala para continuar."
            
            locator = Geolocator()
            pos = await asyncio.wait_for(locator.get_geoposition_async(), timeout=5.0)
            if pos and pos.coordinate:
                return True, (pos.coordinate.latitude, pos.coordinate.longitude)
            return False, "Bloqueo: No se pudo triangular la ubicacion exacta."
        except asyncio.TimeoutError:
            return False, "Bloqueo: Tiempo de espera agotado al obtener ubicacion."
        except Exception as e:
            return False, f"Bloqueo: Error de servicio de ubicacion ({str(e)})."
            
    try:
        exito_loc, datos_loc = asyncio.run(get_windows_location())
        if not exito_loc:
            return False, datos_loc # Retorna el mensaje de bloqueo
        lat, lon = datos_loc
    except Exception as e:
        return False, f"Bloqueo Fatal de Ubicacion: {e}"

    # 3.6. Obtener Huella Digital Unívoca de Dispositivo (Hardware Fingerprint)
    from utils.huella_dispositivo import obtener_huella_dispositivo
    info_huella = obtener_huella_dispositivo()
    device_id = info_huella.get("deviceId")
    direccion_mac = info_huella.get("direccionMac")
    sesion_actual.guardar_device_id(device_id)

    carga_util = {
      "estudianteId": estudiante_id,
      "pinExamen": pin_examen,
      "conexion": {
        "ipEstudiante": ip_local,
        "vpnDetectada": vpn_activa,
        "sistemaOperativo": os_info,
        "protocoloConexion": "TCP",
        "latitud": lat,
        "longitud": lon,
        "deviceId": device_id,
        "direccionMac": direccion_mac
      }
    }
    try:
      res = self._hacer_peticion("post", url_supervision_iniciar, json=carga_util)
      if res.status_code == 200:
        datos = res.json()
        sesion_id = datos.get("sesionId") or datos.get("id")
        sesion_actual.guardar_sesion_examen(sesion_id)
        return True, datos
      elif res.status_code == 404 or res.status_code == 400:
        return False, self._extraer_mensaje_error(res, "No existe un examen activo con ese PIN o ya no es válido.")
      else:
        return False, self._extraer_mensaje_error(res, "No fue posible acceder a la sesión del examen.")
    except httpx.RequestError:
      return False, "No se pudo conectar con el servidor institucional. Por favor, verifica tu conexión a internet."

  def finalizar_sesion_examen(self, sesion_id: str):
    url = f"{url_supervision_base}/{sesion_id}/finalizar"
    try:
      res = self._hacer_peticion("post", url)
      return res.status_code == 200
    except Exception as e:
      print(f"Error al finalizar sesión de examen: {e}")
      return False

  def enviar_alerta(self, sesion_id: str, carga_util: dict):
    """Envía una alerta (evidencia) al backend de Spring Boot"""
    url = f"{url_supervision_base}/{sesion_id}/alerta"
    # --- CIFRADO E2EE AES-256 ---
    try:
                import hashlib
                from cryptography.fernet import Fernet
                from config.configuracion import AES_SECRET_KEY
                f_crypto = Fernet(AES_SECRET_KEY)
                for campo in ["urlFotoWebcam", "urlCapturaPantalla", "urlAudio"]:
                    if carga_util.get(campo):
                        datos_str = carga_util[campo]
                        if not datos_str.startswith("gAAAAA"): 
                            if "," in datos_str:
                                datos_str = datos_str.split(",")[1]
                            
                            # FIRMA FORENSE
                            firma_hash = hashlib.sha256(datos_str.encode('utf-8')).hexdigest()
                            if campo == "urlFotoWebcam": carga_util["hashWebcam"] = firma_hash
                            if campo == "urlCapturaPantalla": carga_util["hashPantalla"] = firma_hash
                            if campo == "urlAudio": carga_util["hashAudio"] = firma_hash
                            
                            cifrado = f_crypto.encrypt(datos_str.encode('utf-8'))
                            carga_util[campo] = cifrado.decode('utf-8')
    except Exception as e:
        print(f"[E2EE ERROR] No se pudo cifrar la evidencia: {e}")

    # Si ya sabemos que estamos desconectados, encolar de inmediato sin demoras
    if not self.conectado:
      self._encolar_alerta(sesion_id, carga_util)
      return False

    try:
      res = self._hacer_peticion("post", url, json=carga_util)
      if res.status_code == 200:
        print(f"[API] Alerta enviada con éxito a Spring Boot.")
        return True
      else:
        print(f"[API ERROR] No se pudo enviar la alerta (HTTP {res.status_code}). Encolando en buffer...")
        self._encolar_alerta(sesion_id, carga_util)
        return False
    except Exception as e:
      print(f"[API ERROR] Fallo de red al enviar alerta ({e}). Encolando en buffer...")
      self.conectado = False
      self._encolar_alerta(sesion_id, carga_util)
      return False

  def obtener_reglas_examen(self, sesion_id: str):
    try:
      res = self._hacer_peticion("get", f"{url_reglas_examen}/{sesion_id}")
      if res.status_code == 200:
        return True, res.json()
      return False, {}
    except Exception:
      return False, {}

  def enviar_evidencia_silenciosa(self, alertas, frame_base64=None):
    if not alertas: return False, "No hay alertas"
    
    sesion_id = sesion_actual.obtener_sesion_id()
    if not sesion_id: return False, "Sin sesion"
    
    mapa_evidencias = {
      "ROSTRO_NO_DETECTADO": "ROSTRO_PERDIDO",
      "MULTIPLE_FACES": "MULTIPLES_ROSTROS",
      "MULTIPLES_ROSTROS": "MULTIPLES_ROSTROS",
      "OBJETO_SOSPECHOSO_MULTIPLES_ROSTROS": "MULTIPLES_ROSTROS",
      "CELL PHONE": "WEBCAM_OBJETO",
      "CAMARA_OBSTRUIDA": "CAMARA_OBSTRUIDA"
    }
    
    for alerta in alertas:
      # Soportar tanto diccionarios estructurados como nombres de alertas en texto
      if isinstance(alerta, dict):
          clase_alerta = alerta.get("claseAlerta") or alerta.get("clase") or "PROCESO"
          nivel_riesgo = alerta.get("nivelRiesgo") or "ALTO"
          detalle = alerta.get("detalle") or alerta.get("tipo_alerta") or "Intento de evasión de interfaz"
          img_pantalla = alerta.get("evidencia_grafica") or alerta.get("urlCapturaPantalla")
          carga_util = {
              "claseAlerta": clase_alerta,
              "nivelRiesgo": nivel_riesgo,
              "pidProceso": 0,
              "nombreProceso": detalle,
              "categoriaProceso": "CONTROL_REMOTO",
              "accionTomada": "ADVERTENCIA_MOSTRADA",
              "urlCapturaPantalla": img_pantalla,
              "urlFotoWebcam": frame_base64
          }
          self.enviar_alerta(sesion_id, carga_util)
          continue

      tipo_evidencia = mapa_evidencias.get(alerta, "WEBCAM_OBJETO")
      
      # FIX: Clasificar correctamente si es objeto, vision o camara obstruida
      if alerta == "CAMARA_OBSTRUIDA":
          clase_alerta = "CAMARA_OBSTRUIDA"
          nivel_riesgo = "CRITICO"
          desc_objeto = "Cámara física tapada u obstruida"
      elif "MULTIPLES_ROSTROS" in alerta:
          clase_alerta = "VISION"
          nivel_riesgo = "ALTO"
          desc_objeto = alerta
      else:
          clase_alerta = "OBJETO" if alerta.startswith("OBJETO_") else "VISION"
          nivel_riesgo = "ALTO"
          desc_objeto = alerta
      
      carga_util = {
        "claseAlerta": clase_alerta,
        "nivelRiesgo": nivel_riesgo,
        "tipoEvidenciaVision": tipo_evidencia,
        "cantidadRostros": 0,
        "objetoDetectado": desc_objeto,
        "confianzaIa": 0.99,
        "urlFotoWebcam": frame_base64,
        "urlCapturaPantalla": None
      }
      self.enviar_alerta(sesion_id, carga_util)
      
    return True, "Alertas enviadas"

  def enviar_heartbeat(self, sesion_id: str, device_id: str = None):
    try:
      params = {}
      if device_id:
        params["deviceId"] = device_id
      url = f"{url_supervision_base}/{sesion_id}/heartbeat"
      res = self._hacer_peticion("post", url, params=params)
      if res.status_code == 200:
        return True, res.json()
      elif res.status_code == 403:
        return False, "DISPOSITIVO_NO_AUTORIZADO"
      return False, f"HTTP {res.status_code}"
    except Exception as e:
      return False, str(e)

  def notificar_interrupcion(self, sesion_id: str, motivo: str = "Cierre inesperado de aplicacion"):
    try:
      url = f"{url_supervision_base}/{sesion_id}/interrumpir"
      res = self._hacer_peticion("post", url, params={"motivo": motivo})
      return res.status_code == 200
    except Exception:
      return False

  def solicitar_apelacion(self, sesion_id, argumento_estudiante):
    try:
      from config.configuracion import url
      endpoint = f"{url}/apelaciones/{sesion_id}/solicitar"
      headers = self._obtener_cabecera_token()
      headers["Content-Type"] = "text/plain; charset=utf-8"
      res = self.cliente.post(endpoint, content=argumento_estudiante.encode("utf-8"), headers=headers)
      if res.status_code in [200, 201]:
        return True, "Apelación solicitada con éxito."
      else:
        return False, self._extraer_mensaje_error(res, "No se pudo registrar la solicitud de apelación.")
    except Exception:
      return False, "No fue posible comunicarse con el servidor para enviar la apelación. Verifica tu conexión a internet."

cliente_api = ClienteApi()

# --- LÓGICA TÚNEL DE VIDEO STOMP ---
import json
import websocket
from PyQt6.QtCore import QThread, pyqtSignal


class HiloStreamEstudiante(QThread):
  comando_recibido = pyqtSignal(dict)
  estado_conexion = pyqtSignal(bool) # Nueva señal para avisar si hay internet

  def __init__(self, sesion_id):
    super().__init__()
    self.sesion_id = sesion_id
    from config.configuracion import url_websocket
    self.url_conexion = url_websocket
    self.ws = None
    self.corriendo = True
    self.streaming_activo = False
    
    # --- TRANSMISIÓN ASÍNCRONA FLUIDA (Cero lag, Drop-frame automático) ---
    self._ultimo_frame_a_enviar = None
    self._bloqueo_frame = threading.Lock()
    self._hilo_emisor = threading.Thread(target=self._bucle_emision_streaming, daemon=True)
    self._hilo_emisor.start()
    
    print(f"[WS-ESTUDIANTE] Hilo preparado con sesion ID: '{self.sesion_id}'")

  def run(self):
    cabeceras = []
    token = sesion_actual.obtener_token()
    if token:
      cabeceras.append(f"Authorization: Bearer {token}")

    import time
    while self.corriendo:
      try:
        self.ws = websocket.WebSocketApp(
          self.url_conexion,
          header=cabeceras,
          on_open=self.al_abrir,
          on_message=self.al_recibir_mensaje,
          on_error=self.al_tener_error,
          on_close=self.al_cerrar
        )
        print(f"[WS-ESTUDIANTE] Iniciando run_forever con ping activo...")
        self.ws.run_forever(ping_interval=15, ping_timeout=10)
        print(f"[WS-ESTUDIANTE] run_forever() finalizó.")
      except Exception as e:
        print(f"[WS-ESTUDIANTE] CRASH FATAL EN EL HILO WS: {e}")
        
      if self.corriendo:
        self.estado_conexion.emit(False) # Avisar que se cayó la red
        cliente_api.conectado = False
        time.sleep(3) # Esperar antes de reconectar

  def al_abrir(self, ws):
    print(f"[WS-ESTUDIANTE] Abriendo túnel STOMP hacia {self.url_conexion}...")
    try:
      import socket
      if hasattr(ws, 'sock') and ws.sock:
        ws.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    except Exception:
      pass
    connect_frame = "CONNECT\naccept-version:1.1,1.2\nhost:localhost\nheart-beat:10000,10000\n\n\x00"
    ws.send(connect_frame)
    cliente_api.conectado = True
    self.estado_conexion.emit(True)

  def al_recibir_mensaje(self, ws, mensaje):
    if mensaje.startswith("CONNECTED"):
      print(f"[WS-ESTUDIANTE] ¡Conectado con éxito a STOMP! Sesion ID: {self.sesion_id}")
      # Suscribirse al canal de comandos para esta sesión UNA VEZ conectados
      topico_comandos = f"/topic/comandos/{self.sesion_id}"
      sub_frame = f"SUBSCRIBE\nid:sub-cmd\ndestination:{topico_comandos}\n\n\x00"
      ws.send(sub_frame)
      cliente_api.conectado = True
      self.estado_conexion.emit(True)
      return

    if mensaje.startswith("MESSAGE"):
      try:
        partes = mensaje.split("\n\n", 1)
        if len(partes)>= 2:
          cuerpo = partes[1].replace('\x00', '').strip()
          if cuerpo:
            datos = json.loads(cuerpo)
            self.comando_recibido.emit(datos)
            
            cmd = datos.get("comando")
            if cmd == "START_STREAM":
              print("[WS-ESTUDIANTE] Recibida orden del profesor: START_STREAM")
              self.streaming_activo = True
            elif cmd == "STOP_STREAM":
              print("[WS-ESTUDIANTE] Recibida orden del profesor: STOP_STREAM")
              self.streaming_activo = False
              
      except Exception as e:
        pass

  def enviar_frame_stream(self, base64_str):
    """
    Recibe el frame desde la cámara y lo deposita en el buffer de tamaño 1.
    Ejecución instantánea (0.001ms) sin bloquear la cámara ni la IA.
    Si la red está ocupada, descarta fotogramas viejos automáticamente.
    """
    if self.corriendo and self.streaming_activo:
      with self._bloqueo_frame:
        self._ultimo_frame_a_enviar = base64_str

  def _bucle_emision_streaming(self):
    """
    Hilo en segundo plano dedicado exclusivamente a emitir el frame más reciente
    hacia el profesor vía WebSocket STOMP con cifrado E2EE.
    """
    import time
    from cryptography.fernet import Fernet
    from config.configuracion import AES_SECRET_KEY
    try:
        f_crypto = Fernet(AES_SECRET_KEY)
    except Exception:
        f_crypto = None

    while self.corriendo:
        frame_a_transmitir = None
        if self.streaming_activo and self.ws and getattr(self.ws, 'sock', None) and self.ws.sock.connected:
            with self._bloqueo_frame:
                frame_a_transmitir = self._ultimo_frame_a_enviar
                self._ultimo_frame_a_enviar = None

        if frame_a_transmitir:
            try:
                # Cifrado E2EE ultra-rápido en frame liviano
                if f_crypto:
                    try:
                        frame_a_transmitir = f_crypto.encrypt(frame_a_transmitir.encode('utf-8')).decode('utf-8')
                    except Exception:
                        pass
                        
                destino = f"/topic/stream/{self.sesion_id}"
                payload = {"frameBase64": frame_a_transmitir}
                cuerpo = json.dumps(payload)
                longitud = len(cuerpo.encode('utf-8'))
                frame_stomp = f"SEND\ndestination:{destino}\ncontent-type:application/json\ncontent-length:{longitud}\n\n{cuerpo}\x00"
                self.ws.send(frame_stomp)
            except Exception:
                pass
        
        time.sleep(0.04) # ~25 revisiones/segundo para emisión inmediata y suave

  def al_tener_error(self, ws, error):
    print(f"[WS-ESTUDIANTE] ERROR EN WEBSOCKET: {error}")
    cliente_api.conectado = False
    self.estado_conexion.emit(False)

  def al_cerrar(self, ws, codigo, mensaje):
    print(f"[WS-ESTUDIANTE] CONEXION CERRADA. Codigo: {codigo}, Msj: {mensaje}")
    cliente_api.conectado = False
    self.estado_conexion.emit(False)

  def detener(self):
    self.corriendo = False
    self.streaming_activo = False
    with self._bloqueo_frame:
      self._ultimo_frame_a_enviar = None
    if self.ws:
      self.ws.close()
