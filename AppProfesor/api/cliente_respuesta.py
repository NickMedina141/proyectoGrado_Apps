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

  def login_profesor(self, email: str, password: str):
    
    carga_util = {
      "email": email,
      "password": password
    }
    
    try:
      #Petición a la API de Spring boot
      respuesta = self.cliente.post(url_login_profesor, json=carga_util)
      
      if respuesta.status_code == 200:
        datos = respuesta.json()
        #Guardamos el token y el ID del profesor en la memoria
        from utils.gestor_sesion import sesion_actual
        prof_id_real = datos.get("profesorId", email) # Fallback al email por si acaso
        sesion_actual.guardar_sesion(datos.get("token"), prof_id_real)
        return True, "Inicio de sesión exitoso"
      elif respuesta.status_code == 401:
        return False, "Credenciales incorrectas"
      else:
        return False, f"Error del servidor: {respuesta.status_code}"
        
    except httpx.RequestError as e:
      return False, f"Error de red: No se pudo conectar a Spring boot {str(e)}"

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
        return False, f"Error al crear examen: {res.text}"
    except httpx.RequestError as e:
      return False, f"Error de red: {str(e)}"

  def configurar_examen(self, codigo_examen, configuracion_payload):
    try:
      from config.configuracion import url_examenes
      respuesta = self.cliente.put(
        f"{url_examenes}/{codigo_examen}/configurar",
        json=configuracion_payload,
        headers=self._obtener_cabecera_token()
      )
      if respuesta.status_code == 200:
        return True, respuesta.json()
      return False, f"Error: {respuesta.status_code} - {respuesta.text}"
    except Exception as e:
      return False, f"Excepción de conexión: {str(e)}"

  def abrir_examen(self, codigo_examen):
    try:
      from config.configuracion import url_examenes
      respuesta = self.cliente.post(f"{url_examenes}/{codigo_examen}/abrir", headers=self._obtener_cabecera_token())
      if respuesta.status_code == 200:
        return True, "Sala abierta exitosamente"
      return False, f"Error: {respuesta.status_code} - {respuesta.text}"
    except Exception as e:
      return False, f"Excepción de conexión: {str(e)}"

  def cerrar_examen(self, codigo_examen):
    try:
      from config.configuracion import url_examenes
      respuesta = self.cliente.post(f"{url_examenes}/{codigo_examen}/cerrar", headers=self._obtener_cabecera_token())
      if respuesta.status_code == 200:
        return True, "Sala cerrada exitosamente"
      return False, f"Error: {respuesta.status_code} - {respuesta.text}"
    except Exception as e:
      return False, f"Excepción de conexión: {str(e)}"

  def obtener_mis_examenes(self, profesor_id):
    try:
      from config.configuracion import url_examenes
      url = f"{url_examenes}/profesor/{profesor_id}"
      res = self._hacer_peticion("get", url)
      if res.status_code == 200:
        return True, res.json()
      else:
        return False, f"Error: {res.text}"
    except httpx.RequestError as e:
      return False, f"Error de red: {str(e)}"

  def obtener_sesiones_examen(self, codigo_examen, todas=False):
    try:
      from config.configuracion import url
      endpoint = f"{url}/supervision/examen/{codigo_examen}/sesiones"
      params = {"todas": "true"} if todas else {}
      res = self._hacer_peticion("get", endpoint, params=params)
      if res.status_code == 200:
        return True, res.json()
      else:
        return False, f"Error: {res.text}"
    except httpx.RequestError as e:
      return False, f"Error de red: {str(e)}"

  def obtener_sesion(self, sesion_id):
    try:
      from config.configuracion import url
      endpoint = f"{url}/supervision/sesion/{sesion_id}"
      res = self._hacer_peticion("get", endpoint)
      if res.status_code == 200:
        return True, res.json()
      else:
        return False, f"Error: {res.text}"
    except Exception as e:
      return False, f"Error de red: {str(e)}"

  def obtener_alertas_examen(self, codigo_examen):
    try:
      from config.configuracion import url
      endpoint = f"{url}/supervision/examen/{codigo_examen}/alertas"
      res = self._hacer_peticion("get", endpoint)
      if res.status_code == 200:
        return True, res.json()
      else:
        return False, f"Error: {res.text}"
    except httpx.RequestError as e:
      return False, f"Error de red: {str(e)}"

  def obtener_apelaciones_pendientes(self, profesor_id):
    try:
      from config.configuracion import url
      endpoint = f"{url}/apelaciones/profesor/{profesor_id}/pendientes"
      res = self._hacer_peticion("get", endpoint)
      if res.status_code == 200:
        return True, res.json()
      else:
        return False, f"Error: {res.text}"
    except httpx.RequestError as e:
      return False, f"Error de red: {str(e)}"

  def resolver_apelacion(self, sesion_id, resolucion_comite, estado_apelacion):
    try:
      from config.configuracion import url
      endpoint = f"{url}/apelaciones/{sesion_id}/resolver"
      params = {
        "resolucionComite": resolucion_comite,
        "estadoApelacion": estado_apelacion
      }
      res = self.cliente.put(endpoint, params=params, headers=self._obtener_cabecera_token())
      if res.status_code == 200:
        return True, res.text
      else:
        return False, f"Error {res.status_code}: {res.text}"
    except httpx.RequestError as e:
      return False, f"Error de red: {str(e)}"

  def obtener_alertas(self, sesion_id):
    try:
      from config.configuracion import url
      endpoint = f"{url}/supervision/{sesion_id}/alertas"
      res = self._hacer_peticion("get", endpoint)
      if res.status_code == 200:
        return True, res.json()
      else:
        return False, f"Error: {res.text}"
    except httpx.RequestError as e:
      return False, f"Error de red: {str(e)}"

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
        return False, f"Error {res.status_code}: {res.text}"
    except httpx.RequestError as e:
      return False, f"Error de red: {str(e)}"

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
      return False, None

#Instancia global lista para usarse en las vistas
cliente_api = ClienteApi()
