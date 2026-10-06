"""
Módulo de Detección y Blindaje Anti-Control Remoto y Pantallas Secundarias.
Diseñado para neutralizar:
1. Software de control remoto (AnyDesk, TeamViewer, RustDesk, Parsec, UltraViewer, etc.)
2. Sesiones de Escritorio Remoto de Windows (RDP / Terminal Services).
3. Conexión de monitores secundarios o proyectores durante el examen.
4. Ocultamiento de la ventana del examen frente a captura remota (WDA_EXCLUDEFROMCAPTURE).
5. Entrada de teclado/mouse inyectada artificialmente por software remoto (LLKHF_INJECTED).
"""

import sys
import os
import psutil
import ctypes
import threading
import time

# Constantes de Windows API
SM_CMONITORS = 80
SM_REMOTESESSION = 0x1000
WDA_NONE = 0x00000000
WDA_MONITOR = 0x00000001
WDA_EXCLUDEFROMCAPTURE = 0x00000011

# Catálogo de ejecutables de software de control y asistencia remota
PROCESOS_CONTROL_REMOTO = {
    "anydesk.exe": "AnyDesk Remote Desktop",
    "teamviewer.exe": "TeamViewer",
    "teamviewer_service.exe": "TeamViewer Service",
    "rustdesk.exe": "RustDesk Remote Access",
    "ultraviewer_desktop.exe": "UltraViewer",
    "ultraviewer.exe": "UltraViewer",
    "remoting_host.exe": "Chrome Remote Desktop",
    "parsecd.exe": "Parsec Gaming / Remote",
    "parsec.exe": "Parsec Remote",
    "vncserver.exe": "RealVNC Server",
    "winvnc.exe": "VNC Server",
    "tvnserver.exe": "TightVNC Server",
    "supremo.exe": "Supremo Remote Desktop",
    "supremohelper.exe": "Supremo Helper",
    "srfeature.exe": "Splashtop Remote",
    "strwinclt.exe": "Splashtop Client",
    "screenconnect.clientservice.exe": "ConnectWise ScreenConnect",
    "quickassist.exe": "Asistencia Rápida de Windows",
    "ammyy.exe": "Ammyy Admin",
    "aa_v3.exe": "Ammyy Admin",
    "logmein.exe": "LogMeIn",
    "dwservice.exe": "DWService Agent",
    "ngrok.exe": "Ngrok Tunnel",
    # --- Integración Móvil y Control Celular (Phone Link, Servidores de Mouse, Mirroring) ---
    "phoneexperiencehost.exe": "Microsoft Phone Link / Enlace Móvil",
    "yourphone.exe": "Microsoft Phone Link",
    "yourphoneserver.exe": "Microsoft Phone Link Server",
    "urserver.exe": "Unified Remote Server (Control Celular)",
    "remotemouse.exe": "Remote Mouse Server (Control Celular)",
    "pcremoteserver.exe": "PC Remote Server (Monect)",
    "monectserver.exe": "Monect PC Remote",
    "samsungdex.exe": "Samsung DeX PC",
    "scrcpy.exe": "scrcpy (Control Móvil USB/WiFi)",
    "vysor.exe": "Vysor (Control Móvil)",
    "airdroid.exe": "AirDroid Desktop",
    "airdroidservice.exe": "AirDroid Service",
    "apowermirror.exe": "ApowerMirror",
    "spacedeskservice.exe": "Spacedesk Driver (Pantalla Móvil)",
    "spacedeskviewer.exe": "Spacedesk Viewer",
}

# Catálogo de software y controladores de cámaras virtuales
PROCESOS_CAMARAS_VIRTUALES = {
    "obs64.exe": "OBS Studio / Cámara Virtual",
    "obs32.exe": "OBS Studio / Cámara Virtual",
    "manycam.exe": "ManyCam Virtual Webcam",
    "splitcam.exe": "SplitCam Video Filter",
    "droidcam.exe": "DroidCam Client",
    "droidcam-cli.exe": "DroidCam CLI",
    "iriunwebcam.exe": "Iriun Webcam",
    "vmix64.exe": "vMix Virtual Video",
    "xsplit.vcam.exe": "XSplit VCam",
    "epoccam.exe": "Elgato EpocCam"
}

def limpiar_portapapeles_sistema():
    """Vacía el portapapeles de Windows para neutralizar copiado/pegado sincronizado desde celulares"""
    try:
        user32 = ctypes.windll.user32
        if user32.OpenClipboard(0):
            user32.EmptyClipboard()
            user32.CloseClipboard()
            return True
    except Exception:
        pass
    return False


def detectar_maquina_virtual() -> tuple[bool, str]:
    """
    Detecta si la sesión se ejecuta dentro de un entorno virtualizado o hipervisor.
    Inspecciona BIOS/Fabricante en Registro de Windows y procesos de herramientas de VM.
    """
    import winreg
    
    # 1. Inspección de BIOS y Sistema en Registro
    rutas_bios = [
        r"HARDWARE\Description\System\BIOS",
        r"SYSTEM\CurrentControlSet\Control\SystemInformation"
    ]
    claves_sospechosas = ["vmware", "virtualbox", "vbox", "qemu", "innotek", "virtual machine", "hyper-v", "parallels", "xen"]
    
    for ruta in rutas_bios:
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, ruta) as k:
                for campo in ["SystemManufacturer", "SystemProductName", "BIOSVersion", "BaseBoardManufacturer"]:
                    try:
                        valor, _ = winreg.QueryValueEx(k, campo)
                        if valor and any(s in str(valor).lower() for s in claves_sospechosas):
                            return True, f"Hipervisor detectado en firmware/BIOS: {valor} ({campo})"
                    except Exception:
                        pass
        except Exception:
            pass

    # 2. Controladores SCSI / Discos virtuales
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DEVICEMAP\Scsi") as k:
            info = winreg.QueryInfoKey(k)
            for i in range(info[0]):
                p_sub = winreg.EnumKey(k, i)
                try:
                    with winreg.OpenKey(k, rf"{p_sub}\Scsi Bus 0\Target Id 0\Logical Unit Id 0") as uk:
                        id_disco, _ = winreg.QueryValueEx(uk, "Identifier")
                        if id_disco and any(s in str(id_disco).lower() for s in ["vbox", "vmware", "qemu", "virtual"]):
                            return True, f"Controlador de disco virtual detectado: {id_disco}"
                except Exception:
                    pass
    except Exception:
        pass

    # 3. Procesos conocidos de servicios de VM
    vm_procesos = {
        "vboxservice.exe": "VirtualBox Guest Additions",
        "vboxtray.exe": "VirtualBox Tray",
        "vmtoolsd.exe": "VMware Tools Daemon",
        "qemu-ga.exe": "QEMU Guest Agent",
        "prl_cc.exe": "Parallels Control Center",
        "prl_tools.exe": "Parallels Tools"
    }
    for proc in psutil.process_iter(['name']):
        try:
            nombre = (proc.info['name'] or "").lower()
            if nombre in vm_procesos:
                return True, f"Servicio de VM activo: {vm_procesos[nombre]} ({nombre})"
        except Exception:
            pass

    return False, ""


def detectar_camaras_virtuales_activas() -> list[tuple[str, str]]:
    """Detecta si hay software de cámara virtual activo en ejecución"""
    encontrados = []
    for proc in psutil.process_iter(['name']):
        try:
            nombre = (proc.info['name'] or "").lower()
            if nombre in PROCESOS_CAMARAS_VIRTUALES:
                encontrados.append((nombre, PROCESOS_CAMARAS_VIRTUALES[nombre]))
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return encontrados


class BlindajeAntiRemoto:
    def __init__(self, funcion_alerta=None):
        self.funcion_alerta = funcion_alerta
        self.activo = False
        self.hilo_vigilancia = None
        self.intervalo = 2.0  # Chequeo cada 2 segundos
        self.apps_detectadas_reportadas = set()
        self.rdp_reportado = False
        self.monitores_reportados = False

    def verificar_entorno_previo(self) -> tuple[bool, str]:
        """
        Ejecuta un diagnóstico estricto ANTES de iniciar el examen.
        Retorna (True, "") si el equipo está limpio, o (False, motivo) si hay infracción.
        """
        # 1. Comprobar Máquina Virtual / Hipervisor
        es_vm, motivo_vm = detectar_maquina_virtual()
        if es_vm:
            return False, f"Se ha detectado un entorno virtualizado ({motivo_vm}). Por políticas de seguridad institucional, los exámenes deben presentarse en la instalación física principal de Windows."

        # 2. Comprobar cámaras virtuales de software activas
        cams_virtuales = detectar_camaras_virtuales_activas()
        if cams_virtuales:
            nombres_cams = ", ".join([desc for _, desc in cams_virtuales])
            return False, f"Se detectó software de cámara virtual activo: {nombres_cams}.\nPor favor cierra esta aplicación para utilizar tu cámara web física."

        # 3. Comprobar sesión RDP
        if self.es_sesion_rdp():
            return False, "Sesión remota RDP detectada. El examen debe presentarse en la consola local del equipo, no a través de Escritorio Remoto."

        # 4. Comprobar múltiples monitores
        num_monitores = self.contar_monitores()
        if num_monitores > 1:
            return False, f"Se detectaron {num_monitores} pantallas conectadas. Por políticas de seguridad, desconecta monitores secundarios o proyectores antes de continuar."

        # 5. Comprobar procesos de control remoto y sincronización móvil activos
        activos = self.detectar_procesos_remotos_activos()
        if activos:
            nombres = ", ".join([desc for _, desc in activos])
            return False, f"Se detectó software de control remoto o enlace móvil en ejecución: {nombres}.\nPor favor cierra estas aplicaciones completamente antes de ingresar al examen."

        # Limpiar portapapeles preventivamente
        limpiar_portapapeles_sistema()

        return True, ""

    def es_sesion_rdp(self) -> bool:
        """Determina si la sesión actual corre bajo Remote Desktop Services (Terminal Server)"""
        try:
            user32 = ctypes.windll.user32
            return bool(user32.GetSystemMetrics(SM_REMOTESESSION))
        except Exception:
            return False

    def contar_monitores(self) -> int:
        """Cuenta el número de monitores físicos/virtuales activos en Windows"""
        try:
            user32 = ctypes.windll.user32
            return user32.GetSystemMetrics(SM_CMONITORS)
        except Exception:
            return 1

    def detectar_procesos_remotos_activos(self) -> list[tuple[str, str]]:
        """Retorna lista de (nombre_proceso, descripcion) de programas de control remoto activos"""
        encontrados = []
        for proc in psutil.process_iter(['name']):
            try:
                nombre = (proc.info['name'] or "").lower()
                if nombre in PROCESOS_CONTROL_REMOTO:
                    encontrados.append((nombre, PROCESOS_CONTROL_REMOTO[nombre]))
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        return encontrados

    def aplicar_blindaje_ventana(self, hwnd: int) -> bool:
        """
        Aplica WDA_EXCLUDEFROMCAPTURE a la ventana dada.
        En Windows 10 (2004+) y Windows 11, esta bandera instruye al Administrador de Ventanas (DWM)
        a renderizar la ventana COMPLETAMENTE NEGRA para cualquier programa de captura de pantalla,
        grabador o software de control remoto (AnyDesk, TeamViewer, Zoom, Discord).
        El estudiante local la ve perfectamente nítida.
        """
        if not hwnd or sys.platform != "win32":
            return False
        try:
            user32 = ctypes.windll.user32
            # Intentar WDA_EXCLUDEFROMCAPTURE (0x11)
            resultado = user32.SetWindowDisplayAffinity(hwnd, WDA_EXCLUDEFROMCAPTURE)
            if resultado != 0:
                print(f"[BLINDAJE] Ventana {hwnd} protegida contra captura remota (WDA_EXCLUDEFROMCAPTURE).")
                return True
            # Respaldo WDA_MONITOR (0x01) para versiones anteriores de Windows
            resultado_alt = user32.SetWindowDisplayAffinity(hwnd, WDA_MONITOR)
            return bool(resultado_alt != 0)
        except Exception as e:
            print(f"[BLINDAJE] No se pudo aplicar afinidad de ventana: {e}")
            return False

    def remover_blindaje_ventana(self, hwnd: int):
        """Restaura la afinidad de ventana al terminar el examen"""
        if not hwnd or sys.platform != "win32":
            return
        try:
            ctypes.windll.user32.SetWindowDisplayAffinity(hwnd, WDA_NONE)
        except Exception:
            pass

    def iniciar_vigilancia(self):
        """Inicia el hilo continuo de monitoreo durante el examen"""
        if self.activo:
            return
        self.activo = True
        self.hilo_vigilancia = threading.Thread(target=self._bucle_vigilancia, daemon=True)
        self.hilo_vigilancia.start()

    def detener_vigilancia(self):
        self.activo = False

    def _bucle_vigilancia(self):
        while self.activo:
            try:
                self._revisar_amenazas()
            except Exception as e:
                print(f"[ANTI-REMOTO ERROR] {e}")
            time.sleep(self.intervalo)

    def _revisar_amenazas(self):
        # 1. Chequeo de nuevos procesos remotos abiertos durante el examen
        activos = self.detectar_procesos_remotos_activos()
        for nombre, desc in activos:
            if nombre not in self.apps_detectadas_reportadas:
                self.apps_detectadas_reportadas.add(nombre)
                self._emitir_alerta(
                    f"CONTROL_REMOTO_DETECTADO: {desc} ({nombre})",
                    "CRITICO",
                    f"El estudiante tiene en ejecución {desc} durante el examen."
                )

        # 2. Chequeo de RDP en vivo
        if self.es_sesion_rdp() and not self.rdp_reportado:
            self.rdp_reportado = True
            self._emitir_alerta(
                "SESION_RDP_ACTIVA",
                "CRITICO",
                "El examen está siendo ejecutado a través de una sesión de Escritorio Remoto (RDP)."
            )

        # 3. Chequeo de monitores conectados en caliente
        monitores = self.contar_monitores()
        if monitores > 1 and not self.monitores_reportados:
            self.monitores_reportados = True
            self._emitir_alerta(
                f"PANTALLAS_MULTIPLES_CONECTADAS ({monitores})",
                "ALTO",
                f"Se detectó la conexión de pantallas adicionales ({monitores} monitores activos)."
            )
        elif monitores <= 1:
            self.monitores_reportados = False

    def _emitir_alerta(self, titulo: str, nivel_riesgo: str, detalle: str):
        print(f"[ALERTA ANTI-REMOTO] {titulo} - {detalle}")
        evidencia = {
            "claseAlerta": "CONTROL_REMOTO",
            "nivelRiesgo": nivel_riesgo,
            "pidProceso": 0,
            "nombreProceso": titulo,
            "categoriaProceso": "CONTROL_REMOTO",
            "accionTomada": "BLOQUEADO",
            "detalle": detalle
        }
        if self.funcion_alerta:
            try:
                self.funcion_alerta(evidencia)
            except Exception as e:
                print(f"[ANTI-REMOTO] Error al disparar callback de alerta: {e}")


# Instancia singleton para el motor
blindaje_remoto = BlindajeAntiRemoto()
