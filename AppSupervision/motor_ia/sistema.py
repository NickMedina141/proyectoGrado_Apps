import psutil
import time
import threading
import ctypes
import io
import base64
from PIL import ImageGrab

class MonitorSistema:
  """
  Monitor silencioso de procesos y ventanas.
  Si el estudiante abre o enfoca una aplicación que no está en la lista blanca,
  el sistema NO la cierra ni le avisa, captura la pantalla silenciosamente
  como evidencia para el profesor (modo infraganti).
  """
  def __init__(self, funcion_alerta=None):
    # Lista blanca dinámica (se inicializa vacía o con base, se inyecta desde la API)
    self.procesos_permitidos = set()
    
    self.activo = False
    self.hilo_monitoreo = None
    self.intervalo = 1.0 # Revisar cada segundo
    self.funcion_alerta = funcion_alerta
    
    self.ultima_app_infractora = None
    self.vm_detectada = False
    self.razon_vm = ""
    self.alertas_persistentes_enviadas = set()
    self.monitores_detectados = 1

  def iniciar(self):
    if self.activo: return
    self.activo = True
    self.hilo_monitoreo = threading.Thread(target=self._ciclo_monitoreo, daemon=True)
    self.hilo_monitoreo.start()

  def detener(self):
    self.activo = False

  def actualizar_lista_blanca(self, nuevas_apps):
    """El backend llamará a esto para inyectar configuraciones dinámicas de la API"""
    self.procesos_permitidos = {app.lower().strip() for app in nuevas_apps}
    # Asegurar procesos básicos del sistema para que no salten falsos positivos
    self.procesos_permitidos.update(["explorer.exe", "svchost.exe", "dwm.exe", "system", "idle", "python.exe"])

  def _ciclo_monitoreo(self):
    # Comprobacion de entorno al iniciar (VM y Monitores)
    self._comprobar_entorno()
    
    while self.activo:
      self._verificar_entorno_persistente()
      self._verificar_ventana_activa()
      time.sleep(self.intervalo)

  def _comprobar_entorno(self):
    # Deteccion de Maquina Virtual (Procesos conocidos de hipervisores)
    vm_procesos = {"vmtoolsd.exe", "vboxservice.exe", "vboxtray.exe", "qemu-ga.exe", "prl_cc.exe", "prl_tools.exe"}
    
    for proc in psutil.process_iter(['name']):
        try:
            if proc.info['name'].lower() in vm_procesos:
                self.vm_detectada = True
                self.razon_vm = f"Proceso {proc.info['name']} (VM) detectado."
                break
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
            
    # Podriamos detectar multiples ESCRITORIOS VIRTUALES o RDP en Windows
    # Tambien detectamos la cantidad de monitores
    try:
        user32 = ctypes.windll.user32
        # SM_CMONITORS = 80
        self.monitores_detectados = user32.GetSystemMetrics(80)
    except Exception:
        self.monitores_detectados = 1

  def _verificar_entorno_persistente(self):
    """Envia una alerta silenicosa unica si hay multiples pantallas o maquina virtual"""
    
    if self.vm_detectada and "VM" not in self.alertas_persistentes_enviadas:
        self._enviar_evidencia_sistema("MAQUINA VIRTUAL DETECTADA", "CRITICO", self.razon_vm)
        self.alertas_persistentes_enviadas.add("VM")
        
    try:
        # Re-comprobar monitores periodicamente en caso de que lo conecten en medio del examen
        user32 = ctypes.windll.user32
        actual_monitores = user32.GetSystemMetrics(80)
        
        if actual_monitores > 1 and "MONITOR_MULTIPLE" not in self.alertas_persistentes_enviadas:
            self._enviar_evidencia_sistema(f"MULTIPLES MONITORES DETECTADOS ({actual_monitores})", "ALTO", "El estudiante tiene monitores adicionales conectados.")
            self.alertas_persistentes_enviadas.add("MONITOR_MULTIPLE")
    except Exception:
        pass

  def _enviar_evidencia_sistema(self, alerta_str, riesgo, desc=""):
    img_b64 = self._capturar_pantalla_b64()
    evidencia = {
        "claseAlerta": "ENTORNO",
        "nivelRiesgo": riesgo,
        "pidProceso": 0,
        "nombreProceso": alerta_str,
        "categoriaProceso": desc,
        "accionTomada": "ADVERTENCIA_MOSTRADA",
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
                print(f"[EVIDENCIA SISTEMA] {alerta_str}")
        except Exception as e:
            print(f"Error enviando evidencia de sistema: {e}")

  def _obtener_proceso_activo(self):
    """Obtiene el nombre del ejecutable (.exe) que el usuario está viendo actualmente"""
    try:
      hwnd = ctypes.windll.user32.GetForegroundWindow()
      if hwnd:
        pid = ctypes.c_ulong(0)
        ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if pid.value>0:
          proceso = psutil.Process(pid.value)
          return proceso.name().lower()
    except Exception:
      pass
    return None

  def _capturar_pantalla_b64(self):
    """Toma una captura silenciosa de la pantalla completa y la convierte a base64 usando WebP ultra ligero"""
    try:
      captura = ImageGrab.grab(all_screens=True)
      buffer = io.BytesIO()
      # Guardar en WebP para ahorrar muchísimo peso sin sacrificar legibilidad
      captura.save(buffer, format="WEBP", quality=50)
      return base64.b64encode(buffer.getvalue()).decode('utf-8')
    except Exception as e:
      print(f"Error al capturar pantalla: {e}")
      return None

  def _verificar_ventana_activa(self):
    app_actual = self._obtener_proceso_activo()
    
    if not app_actual:
      return

    # Si está en la lista blanca, todo está bien
    if app_actual in self.procesos_permitidos:
      self.ultima_app_infractora = None
      return
      
    # Si NO está en la lista blanca y es nueva infractora, generamos evidencia silenciosa (Infraganti)
    if app_actual != self.ultima_app_infractora:
      self.ultima_app_infractora = app_actual
      
      # Capturamos infraganti
      img_b64 = self._capturar_pantalla_b64()
      
      # Armar la evidencia estructurada (NuevaAlertaRequest de Spring Boot)
      evidencia = {
        "claseAlerta": "PROCESO",
        "nivelRiesgo": "ALTO",
        "pidProceso": 0,
        "nombreProceso": app_actual,
        "categoriaProceso": "CHAT",
        "accionTomada": "ADVERTENCIA_MOSTRADA",
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
            print(f"[EVIDENCIA SILENCIOSA] Enviada captura de: {app_actual}.")
        except Exception as e:
          print(f"Error enviando alerta infraganti: {e}")

# Instancia global para ser importada
monitor_sys = MonitorSistema()
