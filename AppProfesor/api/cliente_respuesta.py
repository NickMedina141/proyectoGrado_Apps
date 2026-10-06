# api/rest_client.py
import httpx
from utils.gestor_sesion import sesion_actual
from config.configuracion import url_login_profesor

class ClienteApi:
  def __init__(self):
    # Mantenemos una sesión abierta para no gastar recursos abriendo y cerrando conexiones
    # Timeout bajo (2.0s) para evitar congelar la interfaz grafica cuando se cae el internet
    # Timeout 30s para Railway que puede tardar en despertar tras inactividad
    self.cliente = httpx.Client(timeout=90.0)

  def _obtener_cabecera_token(self):
    #Se inyecta el token en la sesión del profesor al momento de logearse
    cabeceras = {"Content-Type": "application/json"}
    #Obtenemos el token de la sesión
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

      # 2. Si es JSON estructurado de Spring Boot
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
      return "Acceso denegado: No tienes permisos para realizar esta acción."
    elif status == 404:
      return mensaje_fallback if mensaje_fallback != "Ocurrió un error inesperado" else "El recurso o examen solicitado no fue encontrado."
    elif status in (500, 502, 503, 504):
      return "El servidor institucional tuvo un inconveniente al procesar la solicitud. Por favor, intenta más tarde."

    return mensaje_fallback

  def login_profesor(self, email: str, password: str):
    carga_util = {
      "email": email,
      "password": password
    }
    try:
      respuesta = self.cliente.post(url_login_profesor, json=carga_util)
      if respuesta.status_code == 200:
        datos = respuesta.json()
        from utils.gestor_sesion import sesion_actual
        prof_id_real = datos.get("profesorId", email)
        rol = datos.get("rol", "PROFESOR")
        nombre = datos.get("nombre", "")
        sesion_actual.guardar_sesion(datos.get("token"), prof_id_real, rol, nombre)
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

  def confirmar_registro_profesor(self, email: str, codigo_otp: str, nombre: str, apellidos: str, cedula: str, password: str, codigo_profesor: str = ""):
    from config.configuracion import url_registro_confirmar_profesor
    carga_util = {
      "email": email,
      "codigoOtp": codigo_otp,
      "nombre": nombre,
      "apellidos": apellidos,
      "cedula": cedula,
      "password": password,
      "codigoProfesor": codigo_profesor
    }
    try:
      respuesta = self.cliente.post(url_registro_confirmar_profesor, json=carga_util)
      if respuesta.status_code == 200:
        datos = respuesta.json()
        return True, datos.get("mensaje", "Cuenta docente creada con éxito.")
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

  def crear_examen(self, profesor_id, materia_codigo, fechaExamen=None):
    import uuid
    codigo_examen = f"EXM-{uuid.uuid4().hex[:8].upper()}"
    carga_util = {
      "codigoExamen": codigo_examen,
      "profesorId": profesor_id,
      "materiaCodigo": materia_codigo
    }
    if fechaExamen:
      carga_util["fechaExamen"] = fechaExamen
    try:
      from config.configuracion import url_crear_examen
      res = self._hacer_peticion("post", url_crear_examen, json=carga_util)
      if res.status_code == 200:
        return True, res.json()
      else:
        return False, self._extraer_mensaje_error(res, "No se pudo crear el examen.")
    except httpx.RequestError:
      return False, "No fue posible comunicarse con el servidor para crear el examen. Verifica tu conexión a internet."

  def configurar_examen(self, codigo_examen, configuracion_payload):
    try:
      from config.configuracion import url_examenes
      respuesta = self._hacer_peticion(
        "put",
        f"{url_examenes}/{codigo_examen}/configurar",
        json=configuracion_payload
      )
      if respuesta.status_code == 200:
        return True, respuesta.json()
      return False, self._extraer_mensaje_error(respuesta, "No se pudo guardar la configuración del examen.")
    except Exception:
      return False, "No fue posible comunicarse con el servidor. Verifica tu conexión a internet."

  def abrir_examen(self, codigo_examen):
    try:
      from config.configuracion import url_examenes
      respuesta = self._hacer_peticion("post", f"{url_examenes}/{codigo_examen}/abrir")
      if respuesta.status_code == 200:
        return True, "Sala abierta exitosamente"
      return False, self._extraer_mensaje_error(respuesta, "No se pudo abrir la sala del examen.")
    except Exception:
      return False, "No fue posible comunicarse con el servidor. Verifica tu conexión a internet."

  def cerrar_examen(self, codigo_examen):
    try:
      from config.configuracion import url_examenes
      respuesta = self._hacer_peticion("post", f"{url_examenes}/{codigo_examen}/cerrar")
      if respuesta.status_code == 200:
        return True, "Sala cerrada exitosamente"
      return False, self._extraer_mensaje_error(respuesta, "No se pudo cerrar la sala del examen.")
    except Exception:
      return False, "No fue posible comunicarse con el servidor. Verifica tu conexión a internet."

  def obtener_mis_examenes(self, profesor_id):
    try:
      from config.configuracion import url_examenes
      url = f"{url_examenes}/profesor/{profesor_id}"
      res = self._hacer_peticion("get", url)
      if res.status_code == 200:
        return True, res.json()
      else:
        return False, self._extraer_mensaje_error(res, "No se pudieron obtener los exámenes.")
    except httpx.RequestError:
      return False, "No fue posible comunicarse con el servidor. Verifica tu conexión a internet."

  def obtener_sesiones_examen(self, codigo_examen, todas=False):
    try:
      from config.configuracion import url
      endpoint = f"{url}/supervision/examen/{codigo_examen}/sesiones"
      params = {"todas": "true"} if todas else {}
      res = self._hacer_peticion("get", endpoint, params=params)
      if res.status_code == 200:
        return True, res.json()
      else:
        return False, self._extraer_mensaje_error(res, "No se pudieron obtener las sesiones del examen.")
    except httpx.RequestError:
      return False, "Error de red al consultar sesiones del examen. Verifica tu conexión a internet."

  def obtener_sesion(self, sesion_id):
    try:
      from config.configuracion import url
      endpoint = f"{url}/supervision/sesion/{sesion_id}"
      res = self._hacer_peticion("get", endpoint)
      if res.status_code == 200:
        return True, res.json()
      else:
        return False, self._extraer_mensaje_error(res, "No se pudo obtener la sesión.")
    except Exception:
      return False, "Error de comunicación al consultar la sesión. Verifica tu conexión a internet."

  def obtener_alertas_examen(self, codigo_examen):
    try:
      from config.configuracion import url
      endpoint = f"{url}/supervision/examen/{codigo_examen}/alertas"
      res = self._hacer_peticion("get", endpoint)
      if res.status_code == 200:
        return True, res.json()
      else:
        return False, self._extraer_mensaje_error(res, "No se pudieron obtener las alertas del examen.")
    except httpx.RequestError:
      return False, "Error de red al consultar alertas del examen. Verifica tu conexión a internet."

  def obtener_apelaciones_pendientes(self, profesor_id):
    try:
      from config.configuracion import url
      endpoint = f"{url}/apelaciones/profesor/{profesor_id}/pendientes"
      res = self._hacer_peticion("get", endpoint)
      if res.status_code == 200:
        return True, res.json()
      else:
        return False, self._extraer_mensaje_error(res, "No se pudieron obtener las apelaciones pendientes.")
    except httpx.RequestError:
      return False, "Error de comunicación al consultar las apelaciones. Verifica tu conexión a internet."

  def resolver_apelacion(self, sesion_id, resolucion_comite, estado_apelacion):
    try:
      from config.configuracion import url
      endpoint = f"{url}/apelaciones/{sesion_id}/resolver"
      params = {
        "resolucionComite": resolucion_comite,
        "estadoApelacion": estado_apelacion
      }
      res = self._hacer_peticion("put", endpoint, params=params)
      if res.status_code == 200:
        return True, res.text
      else:
        return False, self._extraer_mensaje_error(res, "No se pudo resolver la apelación.")
    except httpx.RequestError:
      return False, "Error de red al resolver la apelación. Verifica tu conexión a internet."

  def obtener_alertas(self, sesion_id):
    try:
      from config.configuracion import url
      endpoint = f"{url}/supervision/{sesion_id}/alertas"
      res = self._hacer_peticion("get", endpoint)
      if res.status_code == 200:
        return True, res.json()
      else:
        return False, self._extraer_mensaje_error(res, "No se pudieron obtener las alertas de la sesión.")
    except httpx.RequestError:
      return False, "Error de red al consultar alertas de la sesión. Verifica tu conexión a internet."

  def descargar_evidencia(self, ruta_remota, ruta_local):
    try:
      from config.configuracion import url
      endpoint = f"{url}/supervision/evidencia/descargar"
      res = self._hacer_peticion("get", endpoint, params={"ruta": ruta_remota})
      if res.status_code == 200:
        with open(ruta_local, 'wb') as file:
            file.write(res.content)
        return True
      else:
        return False
    except Exception as e:
      print(f"Error descargando evidencia {ruta_remota}: {e}")
      return False


  def subir_estudiantes_bulk(self, codigo_examen, estudiantes_list):
    try:
      from config.configuracion import url
      endpoint = f"{url}/examenes/{codigo_examen}/estudiantes/bulk"
      import httpx
      res = self._hacer_peticion("post", endpoint, json=estudiantes_list)
      if res.status_code == 200:
        return True, res.text
      else:
        return False, self._extraer_mensaje_error(res, "No se pudo registrar la lista de estudiantes.")
    except httpx.RequestError:
      return False, "Error de red al subir la lista de estudiantes. Verifica tu conexión a internet."

  def guardar_analisis_ia(self, codigo_examen, resumen, veredicto, probabilidad, modelo_ia):
    """Guarda el análisis global de la IA en el examen (reemplaza si ya existe)."""
    try:
      from config.configuracion import url
      endpoint = f"{url}/examenes/{codigo_examen}/analisis-ia"
      payload = {
        "resumenDetallado": f"{resumen}\n\nVeredicto: {veredicto}",
        "puntajeRiesgoCalculado": int(probabilidad),
        "modeloIaUtilizado": str(modelo_ia)
      }
      res = self._hacer_peticion("put", endpoint, json=payload)
      if res.status_code == 200:
          return True
      else:
          print(f"[API] Error al guardar análisis: {res.status_code} - {res.text}")
          return False
    except Exception as e:
      print(f"[API] Error guardando análisis IA: {e}")
      return False

  def obtener_analisis_ia(self, codigo_examen):
    """Carga el análisis global de la IA guardado en el examen. Retorna (exito, datos_dict o None)."""
    try:
      from config.configuracion import url
      endpoint = f"{url}/examenes/{codigo_examen}/analisis-ia"
      res = self._hacer_peticion("get", endpoint)
      if res.status_code == 200:
        return True, res.json()
      elif res.status_code == 204:
        return True, None  # No hay análisis aún
      else:
        return False, None
    except Exception as e:
      print(f"[API] Error obteniendo análisis IA: {e}")
  def admin_obtener_resumen(self):
    from config.configuracion import url_admin_resumen
    try:
      res = self._hacer_peticion("get", url_admin_resumen)
      if res.status_code == 200:
        return True, res.json()
      return False, self._extraer_mensaje_error(res, "No se pudo obtener el resumen administrativo.")
    except Exception as e:
      return False, f"Error de conexión: {e}"

  def admin_listar_profesores(self):
    from config.configuracion import url_admin_profesores
    try:
      res = self._hacer_peticion("get", url_admin_profesores)
      if res.status_code == 200:
        return True, res.json()
      return False, self._extraer_mensaje_error(res, "No se pudo obtener la lista de docentes.")
    except Exception as e:
      return False, f"Error de conexión: {e}"

  def admin_listar_estudiantes(self):
    from config.configuracion import url_admin_estudiantes
    try:
      res = self._hacer_peticion("get", url_admin_estudiantes)
      if res.status_code == 200:
        return True, res.json()
      return False, self._extraer_mensaje_error(res, "No se pudo obtener la lista de estudiantes.")
    except Exception as e:
      return False, f"Error de conexión: {e}"

  def admin_cambiar_estado_profesor(self, codigo_profesor: str, nuevo_estado: str):
    from config.configuracion import url_admin_profesores
    endpoint = f"{url_admin_profesores}/{codigo_profesor}/estado"
    try:
      res = self._hacer_peticion("put", endpoint, json={"estado": nuevo_estado})
      if res.status_code == 200:
        return True, res.json().get("mensaje", "Estado del docente actualizado con éxito.")
      return False, self._extraer_mensaje_error(res, "No se pudo actualizar el estado del docente.")
    except Exception as e:
      return False, f"Error de conexión: {e}"

  def admin_cambiar_estado_estudiante(self, estudiante_id: str, nuevo_estado: str):
    from config.configuracion import url_admin_estudiantes
    endpoint = f"{url_admin_estudiantes}/{estudiante_id}/estado"
    try:
      res = self._hacer_peticion("put", endpoint, json={"estado": nuevo_estado})
      if res.status_code == 200:
        return True, res.json().get("mensaje", "Estado del estudiante actualizado con éxito.")
      return False, self._extraer_mensaje_error(res, "No se pudo actualizar el estado del estudiante.")
    except Exception as e:
      return False, f"Error de conexión: {e}"

  # --- Gestión administrativa de cuentas (SuperADMIN) ---
  def _admin_peticion(self, metodo: str, endpoint: str, mensaje_error: str, **kwargs):
    """Petición administrativa genérica. Devuelve (True, dict) o (False, mensaje)."""
    try:
      res = self._hacer_peticion(metodo, endpoint, **kwargs)
      if res.status_code in (200, 201):
        try:
          return True, res.json()
        except Exception:
          return True, {}
      return False, self._extraer_mensaje_error(res, mensaje_error)
    except Exception as e:
      return False, f"Error de conexión: {e}"

  def admin_editar_profesor(self, codigo: str, datos: dict):
    from config.configuracion import url_admin_profesores
    return self._admin_peticion("put", f"{url_admin_profesores}/{codigo}", "No se pudo actualizar el docente.", json=datos)

  def admin_editar_estudiante(self, est_id: str, datos: dict):
    from config.configuracion import url_admin_estudiantes
    return self._admin_peticion("put", f"{url_admin_estudiantes}/{est_id}", "No se pudo actualizar el estudiante.", json=datos)

  def admin_crear_profesor(self, datos: dict):
    from config.configuracion import url_admin_profesores
    return self._admin_peticion("post", url_admin_profesores, "No se pudo crear el docente.", json=datos)

  def admin_crear_estudiante(self, datos: dict):
    from config.configuracion import url_admin_estudiantes
    return self._admin_peticion("post", url_admin_estudiantes, "No se pudo crear el estudiante.", json=datos)

  def admin_restablecer_clave_profesor(self, codigo: str):
    from config.configuracion import url_admin_profesores
    return self._admin_peticion("post", f"{url_admin_profesores}/{codigo}/restablecer-clave", "No se pudo restablecer la contraseña.")

  def admin_restablecer_clave_estudiante(self, est_id: str):
    from config.configuracion import url_admin_estudiantes
    return self._admin_peticion("post", f"{url_admin_estudiantes}/{est_id}/restablecer-clave", "No se pudo restablecer la contraseña.")

  def admin_eliminar_profesor(self, codigo: str):
    from config.configuracion import url_admin_profesores
    return self._admin_peticion("delete", f"{url_admin_profesores}/{codigo}", "No se pudo eliminar el docente.")

  def admin_eliminar_estudiante(self, est_id: str):
    from config.configuracion import url_admin_estudiantes
    return self._admin_peticion("delete", f"{url_admin_estudiantes}/{est_id}", "No se pudo eliminar el estudiante.")

#Instancia global lista para usarse en las vistas
cliente_api = ClienteApi()

