import os
import psutil
import time
import threading
import ctypes
from ctypes import wintypes
import io
import base64
from PIL import ImageGrab

# Estructura Win32 RECT para medir dimensiones de la ventana
class RECT(ctypes.Structure):
    _fields_ = [
        ('left', wintypes.LONG),
        ('top', wintypes.LONG),
        ('right', wintypes.LONG),
        ('bottom', wintypes.LONG)
    ]

# Procesos esenciales del sistema operativo Windows y componentes autorizados
PROCESOS_SISTEMA_BASE = {
    "explorer.exe",
    "svchost.exe",
    "dwm.exe",
    "system",
    "idle",
    "python.exe",
    "qtwebengineprocess.exe",
    # Shell de Windows 10/11, Quick Settings, volumen, red, batería, reloj
    "shellexperiencehost.exe",
    "shellhost.exe",
    "startmenuexperiencehost.exe",
    "searchhost.exe",
    "searchindexer.exe",
    "textinputhost.exe",
    "runtimebroker.exe",
    "systemsettings.exe",
    "systemsettingsadminflows.exe",
    "ctfmon.exe",
    "useroobebroker.exe",
    # Autenticación nativa y seguridad de Windows (Passkeys, Windows Hello, PIN, Huellas)
    "credentialuibroker.exe",
    "authhost.exe",
    "pickerhost.exe",
    "consent.exe",
    "securityhealthsystray.exe",
    "securityhealthhost.exe",
    "smartscreen.exe",
    "lockapp.exe"
}

# Títulos de ventanas nativas del sistema permitidas (evita falsos positivos en modales)
TITULOS_SISTEMA_PERMITIDOS = (
    "seguridad de windows",
    "windows security",
    "iniciar sesión con una clave de paso",
    "configuración",
    "settings"
)

class MonitorSistema:
    """
    Monitor silencioso de procesos y ventanas.
    Si el estudiante abre o enfoca una aplicación que no está en la lista blanca,
    el sistema espera a que la aplicación esté completamente abierta y renderizada
    (al menos 2.2 segundos activa y visible) para capturar una evidencia infraganti
    clara y contundente para el docente, evitando falsos positivos y parpadeos fugaces.
    """
    def __init__(self, funcion_alerta=None):
        # Lista blanca dinámica (se inicializa con base del sistema, se inyecta desde la API)
        self.procesos_permitidos = set(PROCESOS_SISTEMA_BASE)
        
        self.activo = False
        self.hilo_monitoreo = None
        self.intervalo = 0.5 # Revisión frecuente (cada 500 ms) para responder con precisión
        self.funcion_alerta = funcion_alerta
        
        # Control de captura infraganti con estabilización de renderizado
        self.candidato_infractor = None
        self.tiempo_inicio_infraccion = 0.0
        self.captura_tomada_para_infraccion = False
        self.tiempo_estabilizacion = 2.2 # Segundos que la app debe estar visible y desplegada antes de tomar la captura
        self.cooldown_duracion = 25.0 # Segundos de enfriamiento para no repetir capturas del mismo proceso
        self.cooldown_apps = {} # {nombre_proceso: timestamp_expiracion}
        
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
        self.procesos_permitidos.update(PROCESOS_SISTEMA_BASE)

    def ejecutar_barrido_inicial(self, nuevas_apps_permitidas=None):
        """
        Barrido forense inicial ejecutado al iniciar la sesión del examen en modo kiosko.
        Analiza todos los procesos activos. Si detecta aplicaciones no autorizadas abiertas
        (navegadores ajenos, mensajería, grabadores, herramientas de trampa):
        1. Captura evidencia fotográfica de la pantalla.
        2. Emite la alerta de auditoría forense al docente.
        3. Cierra y neutraliza el proceso para dejar el escritorio sanitizado.
        """
        if nuevas_apps_permitidas is not None:
            self.actualizar_lista_blanca(nuevas_apps_permitidas)

        print("[BARRIDO INICIAL] Iniciando inspección forense de procesos...")
        user32 = ctypes.windll.user32
        mi_pid = os.getpid()

        # Recopilar PIDs con ventanas visibles en el escritorio
        pids_con_ventana = set()
        def enum_windows_proc(hwnd, lParam):
            if user32.IsWindowVisible(hwnd) and user32.GetWindowTextLengthW(hwnd) > 0:
                pid = wintypes.DWORD()
                user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                if pid.value:
                    pids_con_ventana.add(pid.value)
            return True

        WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
        try:
            user32.EnumWindows(WNDENUMPROC(enum_windows_proc), 0)
        except Exception:
            pass

        # Conjunto de nombres de procesos típicamente sospechosos de fondo
        procesos_sospechosos_fondo = {
            "discord.exe", "telegram.exe", "whatsapp.exe", "spotify.exe",
            "steam.exe", "epicgameslauncher.exe", "chatgpt.exe", "notion.exe",
            "slack.exe", "zoom.exe", "teams.exe", "skype.exe", "obs64.exe",
            "obs32.exe", "anydesk.exe", "teamviewer.exe", "rustdesk.exe",
            "chrome.exe", "msedge.exe", "firefox.exe", "brave.exe", "opera.exe"
        }

        procesos_sancionados = []

        for proc in psutil.process_iter(['pid', 'name']):
            try:
                pid = proc.info['pid']
                nombre = (proc.info['name'] or "").lower()

                if pid == mi_pid or pid == 0:
                    continue
                if nombre in self.procesos_permitidos:
                    continue

                # Si tiene ventana gráfica activa o es un proceso sospechoso de fondo
                es_candidato = (pid in pids_con_ventana) or (nombre in procesos_sospechosos_fondo)

                if es_candidato:
                    print(f"[BARRIDO INICIAL] Proceso no autorizado detectado: {nombre} (PID {pid})")
                    img_b64 = self._capturar_pantalla_b64()
                    categoria = self._determinar_categoria_proceso(nombre)

                    evidencia = {
                        "claseAlerta": "PROCESO",
                        "nivelRiesgo": "ALTO",
                        "pidProceso": pid,
                        "nombreProceso": nombre,
                        "categoriaProceso": categoria,
                        "accionTomada": "PROCESO_TERMINADO",
                        "urlCapturaPantalla": img_b64,
                        "detalle": f"Proceso no autorizado detectado al inicio del examen: {nombre}. Cerrado automáticamente."
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
                        except Exception:
                            pass

                    # Terminar el proceso infractor para sanitizar el escritorio
                    try:
                        proc.terminate()
                        proc.wait(timeout=0.6)
                    except Exception:
                        try:
                            proc.kill()
                        except Exception:
                            pass

                    procesos_sancionados.append(nombre)
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass

        print(f"[BARRIDO INICIAL] Finalizado. Procesos neutralizados: {len(procesos_sancionados)}")
        return procesos_sancionados

    def _ciclo_monitoreo(self):
        # Comprobacion de entorno al iniciar (VM y Monitores)
        self._comprobar_entorno()
        
        while self.activo:
            self._neutralizar_taskmgr()
            self._verificar_entorno_persistente()
            self._verificar_ventana_activa()
            time.sleep(self.intervalo)

    def _neutralizar_taskmgr(self):
        """Cierra inmediatamente cualquier intento de abrir el Administrador de Tareas"""
        for proc in psutil.process_iter(['name']):
            try:
                if proc.info['name'] and proc.info['name'].lower() == 'taskmgr.exe':
                    proc.terminate()
                    if "TASKMGR" not in self.alertas_persistentes_enviadas:
                        self._enviar_evidencia_sistema("ADMINISTRADOR_TAREAS_BLOQUEADO", "ALTO", "El estudiante intentó abrir el Administrador de Tareas y fue cerrado de inmediato.")
                        self.alertas_persistentes_enviadas.add("TASKMGR")
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass

    def _comprobar_entorno(self):
        # Deteccion exhaustiva de Maquina Virtual (Firmware, BIOS, SCSI y Procesos)
        try:
            from motor_ia.anti_remoto import detectar_maquina_virtual
            es_vm, razon = detectar_maquina_virtual()
            if es_vm:
                self.vm_detectada = True
                self.razon_vm = razon
        except Exception:
            pass
                
        # Cantidad de monitores
        try:
            user32 = ctypes.windll.user32
            # SM_CMONITORS = 80
            self.monitores_detectados = user32.GetSystemMetrics(80)
        except Exception:
            self.monitores_detectados = 1

    def _verificar_entorno_persistente(self):
        """Envia una alerta silenciosa única si hay múltiples pantallas o máquina virtual"""
        if self.vm_detectada and "VM" not in self.alertas_persistentes_enviadas:
            self._enviar_evidencia_sistema("MAQUINA VIRTUAL DETECTADA", "CRITICO", self.razon_vm)
            self.alertas_persistentes_enviadas.add("VM")
            
        try:
            # Re-comprobar monitores periódicamente en caso de que lo conecten en medio del examen
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

    def _obtener_info_ventana_activa(self):
        """Obtiene información detallada de la ventana en primer plano vía Win32 API"""
        try:
            user32 = ctypes.windll.user32
            hwnd = user32.GetForegroundWindow()
            if not hwnd:
                return None
          
            pid = wintypes.DWORD(0)
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            pid_val = pid.value
          
            nombre_proceso = ""
            if pid_val > 0:
                try:
                    nombre_proceso = psutil.Process(pid_val).name().lower()
                except Exception:
                    nombre_proceso = ""
          
            # Título de la ventana
            longitud_titulo = user32.GetWindowTextLengthW(hwnd)
            titulo = ""
            if longitud_titulo > 0:
                buffer = ctypes.create_unicode_buffer(longitud_titulo + 1)
                user32.GetWindowTextW(hwnd, buffer, longitud_titulo + 1)
                titulo = buffer.value.strip()
          
            # Visibilidad y estado de la ventana
            es_visible = bool(user32.IsWindowVisible(hwnd))
            esta_minimizada = bool(user32.IsIconic(hwnd))
          
            # Dimensiones de la ventana
            rect = RECT()
            user32.GetWindowRect(hwnd, ctypes.byref(rect))
            ancho = rect.right - rect.left
            alto = rect.bottom - rect.top
          
            return {
                "hwnd": hwnd,
                "pid": pid_val,
                "proceso": nombre_proceso,
                "titulo": titulo,
                "es_visible": es_visible,
                "esta_minimizada": esta_minimizada,
                "ancho": ancho,
                "alto": alto
            }
        except Exception:
            return None

    def _es_ventana_permitida(self, info):
        """Determina si la ventana o proceso es legítimo y no debe alertarse"""
        if not info:
            return True
        
        proc = info.get("proceso", "")
        titulo = info.get("titulo", "").lower()
        pid = info.get("pid", 0)
        
        # 1. Proceso de la propia aplicación de examen o hijos del proceso actual
        try:
            if pid == os.getpid():
                return True
        except Exception:
            pass
          
        # 2. Si el proceso está en la lista blanca (incluyendo base de sistema)
        if proc in self.procesos_permitidos:
            return True
          
        # 3. Títulos legítimos del sistema operativo (Passkey / Windows Hello)
        for titulo_seguro in TITULOS_SISTEMA_PERMITIDOS:
            if titulo_seguro in titulo:
                return True
            
        return False

    def _determinar_categoria_proceso(self, proc_name):
        """Categoriza el proceso respetando el enum CategoriaProceso de Spring Boot (GRABADOR, CHAT, VM, CONTROL_REMOTO)"""
        proc = proc_name.lower()
        if any(k in proc for k in ["anydesk", "teamviewer", "rustdesk", "vnc", "ultraviewer", "remotedesktop", "mstsc"]):
            return "CONTROL_REMOTO"
        if any(k in proc for k in ["obs", "bandicam", "camtasia", "fraps", "sharex", "streamlabs"]):
            return "GRABADOR"
        if any(k in proc for k in ["vbox", "vmware", "qemu", "virtualbox"]):
            return "VM"
        return "CHAT"

    def _obtener_proceso_activo(self):
        """Retrocompatibilidad: devuelve el nombre del proceso activo"""
        info = self._obtener_info_ventana_activa()
        return info["proceso"] if info else None

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
        info = self._obtener_info_ventana_activa()
        if not info:
            return

        # Si la ventana activa es permitida (o del sistema), no hay infracción
        if self._es_ventana_permitida(info):
            # Si el usuario volvió a la app autorizada, limpiamos el candidato infractor pendiente
            self.candidato_infractor = None
            self.captura_tomada_para_infraccion = False
            return

        app_actual = info.get("proceso", "")
        if not app_actual:
            return

        ahora = time.time()

        # Si la app está en periodo de cooldown (ya se reportó recientemente), no repetir capturas
        if self.cooldown_apps.get(app_actual, 0) > ahora:
            return

        # Si es una nueva app infractora o recién toma foco
        if app_actual != self.candidato_infractor:
            self.candidato_infractor = app_actual
            self.tiempo_inicio_infraccion = ahora
            self.captura_tomada_para_infraccion = False
            return

        # Si la misma app infractora continúa en foco y aún no se ha tomado la captura
        if not self.captura_tomada_para_infraccion:
            tiempo_transcurrido = ahora - self.tiempo_inicio_infraccion
            
            # Requisitos para confirmar que la aplicación está COMPLETAMENTE ABIERTA Y RENDERIZADA:
            # 1. Ventana visible
            # 2. No minimizada
            # 3. Tamaño real de UI (al menos 300x200 px)
            # 4. Superó el tiempo de estabilización (2.2 segundos) para renderizar su interfaz gráfica
            es_visible = info.get("es_visible", False)
            esta_minimizada = info.get("esta_minimizada", True)
            ancho = info.get("ancho", 0)
            alto = info.get("alto", 0)
            
            if es_visible and not esta_minimizada and ancho >= 300 and alto >= 200:
                if tiempo_transcurrido >= self.tiempo_estabilizacion:
                    # ¡Aplicación completamente abierta y desplegada! Tomamos la evidencia infraganti
                    self.captura_tomada_para_infraccion = True
                    self.cooldown_apps[app_actual] = ahora + self.cooldown_duracion
                    
                    img_b64 = self._capturar_pantalla_b64()
                    categoria = self._determinar_categoria_proceso(app_actual)
                    
                    evidencia = {
                        "claseAlerta": "PROCESO",
                        "nivelRiesgo": "ALTO",
                        "pidProceso": info.get("pid", 0),
                        "nombreProceso": app_actual,
                        "categoriaProceso": categoria,
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
                                print(f"[EVIDENCIA SILENCIOSA] Captura de aplicación completamente abierta: {app_actual} ({categoria}).")
                        except Exception as e:
                            print(f"Error enviando alerta infraganti: {e}")

# Instancia global para ser importada
monitor_sys = MonitorSistema()
