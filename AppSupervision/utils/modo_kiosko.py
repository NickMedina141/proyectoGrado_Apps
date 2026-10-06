"""
Módulo de Modo Kiosko Seguro (Inspirado en la arquitectura Safe Exam Browser - SEB).
Responsabilidades:
1. Anclaje de Pantalla Completa Exclusiva (Frameless, WindowStaysOnTopHint).
2. Intercepción y Bloqueo de Teclas de Escape a nivel de Núcleo Windows (Hook WH_KEYBOARD_LL):
   - Tecla Windows (Win)
   - Alt + Tab (Conmutador de aplicaciones)
   - Alt + Esc (Conmutador directo de ventanas)
   - Alt + F4 (Cierre forzado)
   - Ctrl + Esc (Menú de inicio)
   - Ctrl + Shift + Esc (Acceso directo a Administrador de Tareas)
   - PrtScn (Captura de pantalla)
   - Teclas de acceso rápido de Windows (Win+D, Win+R, Win+Tab, Win+A, Win+L)
3. Detección de Entrada Inyectada (LLKHF_INJECTED) indicando control remoto o automatización.
4. Deshabilitación temporal del Administrador de Tareas (HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Policies\\System\\DisableTaskMgr).
5. Restauración garantizada en caso de cierre normal, forzado o crash (atexit).
"""

import sys
import os
import winreg
import atexit
import ctypes
from ctypes import wintypes

# Constantes de Windows API
WH_KEYBOARD_LL = 13
WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101
WM_SYSKEYDOWN = 0x0104
WM_SYSKEYUP = 0x0105

VK_TAB = 0x09
VK_ESCAPE = 0x1B
VK_SNAPSHOT = 0x2C  # PrintScreen
VK_LWIN = 0x5B
VK_RWIN = 0x5C
VK_F4 = 0x73
VK_CONTROL = 0x11
VK_SHIFT = 0x10
VK_MENU = 0x12  # Alt

# Teclas para Escritorios Virtuales y Centro de Notificaciones
VK_LEFT = 0x25
VK_UP = 0x26
VK_RIGHT = 0x27
VK_DOWN = 0x28
VK_D = 0x44  # Win + Ctrl + D (Nuevo escritorio virtual)
VK_A = 0x41  # Win + A (Centro de acciones / Phone Link)
VK_N = 0x4E  # Win + N (Notificaciones)
VK_L = 0x4C  # Win + L (Bloquear pantalla)
VK_C = 0x43  # Win + C (Copilot Windows 11) / Ctrl + C (Copiar)
VK_G = 0x47  # Win + G (Xbox Game Bar)
VK_V = 0x56  # Win + V (Historial Portapapeles) / Ctrl + V (Pegar)
VK_S = 0x53  # Win + Shift + S (Herramienta Recortes)
VK_X = 0x58  # Ctrl + X (Cortar)

LLKHF_EXTENDED = 0x01
LLKHF_INJECTED = 0x01  # Bit 0 de flags indica entrada inyectada artificialmente
LLKHF_ALTDOWN = 0x20

# Estructura del Hook de Teclado
class KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("vkCode", wintypes.DWORD),
        ("scanCode", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_ulonglong)
    ]

# Firma del Callback del Hook
HOOKPROC = ctypes.WINFUNCTYPE(ctypes.c_longlong, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM)


class GestorModoKiosko:
    def __init__(self, ventana_principal=None, funcion_alerta=None):
        self.ventana = ventana_principal
        self.funcion_alerta = funcion_alerta
        self.kiosko_activo = False
        self.hook_id = None
        self._hook_callback = None
        self.politicas_deshabilitadas = False
        self.codigo_maestro_emergencia = "UPC911"
        self._teclas_control_pulsadas = set()
        self.hilo_vigilancia_foco = None
        self.vigilancia_foco_activa = False
        self.procesos_permitidos_examen = set()
        self._cooldown_teclas = {}
        self._cooldown_foco = 0.0
        
        # Registrar restauración automática obligatoria al salir del proceso
        atexit.register(self.desactivar_kiosko)

    def actualizar_procesos_permitidos(self, lista_apps: list[str]):
        """Actualiza la lista de aplicaciones externas autorizadas para el examen (ej: excel.exe, calc.exe)"""
        self.procesos_permitidos_examen = {a.lower().strip() for a in lista_apps if a and a.strip()}
        print(f"[KIOSKO] Aplicaciones autorizadas para el examen: {self.procesos_permitidos_examen}")
        if self.kiosko_activo and self.ventana:
            from PyQt6.QtCore import Qt
            # Si el examen permite aplicaciones externas, quitamos WindowStaysOnTopHint para que
            # la aplicación autorizada (ej. Excel) pueda posicionarse al frente o en split-screen
            flags = Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint
            if len(self.procesos_permitidos_examen) == 0:
                flags |= Qt.WindowType.WindowStaysOnTopHint
            self.ventana.setWindowFlags(flags)
            self.ventana.showFullScreen()
            self.ventana.raise_()
            self.ventana.activateWindow()

    def activar_kiosko(self, ventana=None):
        """Activa el modo kiosko completo: pantalla completa fija, bloqueo de teclas y políticas de sistema"""
        if self.kiosko_activo:
            return
        
        if ventana:
            self.ventana = ventana

        self.kiosko_activo = True
        print("[KIOSKO] Activando Modo Kiosko Seguro (UPC SecureExam)...")

        # 1. Deshabilitar Administrador de Tareas y Cambio Rápido de Usuario en HKCU
        self._configurar_politicas_sistema(deshabilitar=True)

        # 2. Instalar Hook de Teclado de Bajo Nivel
        self._instalar_hook_teclado()

        # 3. Iniciar Vigilancia Activa de Foco y Escritorio Virtual
        self._iniciar_vigilancia_foco()

        # 4. Configurar ventana en pantalla completa sin bordes ni barra de tareas
        if self.ventana:
            from PyQt6.QtCore import Qt
            # En examen estricto se ancla siempre al frente; en examen con apps permitidas se adapta
            flags = Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint
            if len(self.procesos_permitidos_examen) == 0:
                flags |= Qt.WindowType.WindowStaysOnTopHint

            self.ventana.setWindowFlags(flags)
            self.ventana.showFullScreen()
            self.ventana.raise_()
            self.ventana.activateWindow()

            # Aplicar blindaje contra captura remota (AnyDesk / Discord / Zoom verán negro)
            try:
                from motor_ia.anti_remoto import blindaje_remoto
                hwnd = int(self.ventana.winId())
                blindaje_remoto.aplicar_blindaje_ventana(hwnd)
            except Exception as e:
                print(f"[KIOSKO] Error aplicando blindaje de pantalla: {e}")

    def desactivar_kiosko(self):
        """Restaura el entorno de Windows y la ventana a su estado normal"""
        if not self.kiosko_activo:
            return
        
        self.kiosko_activo = False
        print("[KIOSKO] Desactivando Modo Kiosko Seguro y restaurando Windows...")

        # 1. Detener Vigilancia de Foco
        self._detener_vigilancia_foco()

        # 2. Desinstalar Hook de Teclado
        self._desinstalar_hook_teclado()

        # 3. Habilitar nuevamente Administrador de Tareas y Cambio Rápido de Usuario
        self._configurar_politicas_sistema(deshabilitar=False)

        # 4. Remover blindaje de captura
        if self.ventana:
            try:
                from motor_ia.anti_remoto import blindaje_remoto
                hwnd = int(self.ventana.winId())
                blindaje_remoto.remover_blindaje_ventana(hwnd)
            except Exception:
                pass

            # Restaurar ventana con controles estándar
            from PyQt6.QtCore import Qt
            self.ventana.setWindowFlags(Qt.WindowType.Window)
            self.ventana.showNormal()

    def _configurar_politicas_sistema(self, deshabilitar: bool):
        """
        Modifica las políticas de usuario en HKCU:
        - DisableTaskMgr: Bloquea el Administrador de Tareas.
        - HideFastUserSwitching: Oculta la opción de 'Cambiar de usuario' para evitar abandono de sesión.
        No requiere privilegios de Administrador.
        """
        ruta_clave = r"Software\Microsoft\Windows\CurrentVersion\Policies\System"
        try:
            if deshabilitar:
                key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, ruta_clave)
                winreg.SetValueEx(key, "DisableTaskMgr", 0, winreg.REG_DWORD, 1)
                winreg.SetValueEx(key, "HideFastUserSwitching", 0, winreg.REG_DWORD, 1)
                winreg.CloseKey(key)
                self.politicas_deshabilitadas = True
                print("[KIOSKO] Políticas de sistema aplicadas (TaskMgr off, FastUserSwitching oculto).")
            else:
                try:
                    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, ruta_clave, 0, winreg.KEY_SET_VALUE)
                    for valor in ("DisableTaskMgr", "HideFastUserSwitching"):
                        try:
                            winreg.DeleteValue(key, valor)
                        except FileNotFoundError:
                            pass
                    winreg.CloseKey(key)
                except FileNotFoundError:
                    pass
                self.politicas_deshabilitadas = False
                print("[KIOSKO] Políticas de sistema restauradas a la normalidad.")
        except Exception as e:
            print(f"[KIOSKO] Advertencia al configurar políticas de sistema: {e}")

    def _iniciar_vigilancia_foco(self):
        if self.vigilancia_foco_activa:
            return
        import threading
        self.vigilancia_foco_activa = True
        self.hilo_vigilancia_foco = threading.Thread(target=self._bucle_vigilancia_foco, daemon=True)
        self.hilo_vigilancia_foco.start()

    def _detener_vigilancia_foco(self):
        self.vigilancia_foco_activa = False

    def _bucle_vigilancia_foco(self):
        import time
        contador_fuera = 0
        while self.vigilancia_foco_activa:
            try:
                if self.ventana and self.kiosko_activo:
                    hwnd_kiosko = int(self.ventana.winId())
                    user32 = ctypes.windll.user32
                    hwnd_fore = user32.GetForegroundWindow()
                    
                    if hwnd_fore and hwnd_fore != hwnd_kiosko:
                        fore_pid = wintypes.DWORD()
                        user32.GetWindowThreadProcessId(hwnd_fore, ctypes.byref(fore_pid))
                        if fore_pid.value != os.getpid() and fore_pid.value != 0:
                            # Verificar si la ventana pertenece al sistema o autenticación (Windows Hello / Passkeys / Quick Settings)
                            es_sistema = False
                            try:
                                import psutil
                                proc_nombre = psutil.Process(fore_pid.value).name().lower()
                                from motor_ia.sistema import PROCESOS_SISTEMA_BASE, TITULOS_SISTEMA_PERMITIDOS
                                if proc_nombre in PROCESOS_SISTEMA_BASE or proc_nombre in self.procesos_permitidos_examen:
                                    es_sistema = True
                                else:
                                    # Verificar título de la ventana
                                    longitud_titulo = user32.GetWindowTextLengthW(hwnd_fore)
                                    if longitud_titulo > 0:
                                        buffer = ctypes.create_unicode_buffer(longitud_titulo + 1)
                                        user32.GetWindowTextW(hwnd_fore, buffer, longitud_titulo + 1)
                                        titulo = buffer.value.strip().lower()
                                        if any(t in titulo for t in TITULOS_SISTEMA_PERMITIDOS):
                                            es_sistema = True
                            except Exception:
                                pass

                            if not es_sistema:
                                contador_fuera += 1
                                if contador_fuera >= 2:
                                    ahora = time.time()
                                    if ahora >= self._cooldown_foco:
                                        self._cooldown_foco = ahora + 20.0
                                        self._emitir_alerta_tecla(
                                            "DESVIO_FOCO_O_ESCRITORIO_VIRTUAL",
                                            "ALTO",
                                            "La ventana del examen perdió el foco principal frente a otra aplicación o escritorio."
                                        )
                                    # Forzar retorno inmediato a pantalla completa en primer plano
                                    user32.ShowWindow(hwnd_kiosko, 3) # SW_MAXIMIZE
                                    user32.SetForegroundWindow(hwnd_kiosko)
                                    user32.BringWindowToTop(hwnd_kiosko)
                                    contador_fuera = 0
                            else:
                                contador_fuera = 0
                        else:
                            contador_fuera = 0
                    else:
                        contador_fuera = 0
            except Exception:
                pass
            time.sleep(1.2)

    def _instalar_hook_teclado(self):
        """Instala el Hook WH_KEYBOARD_LL en Windows"""
        if self.hook_id:
            return
        
        def _low_level_keyboard_proc(nCode, wParam, lParam):
            if nCode >= 0:
                kb = ctypes.cast(lParam, ctypes.POINTER(KBDLLHOOKSTRUCT)).contents
                vk = kb.vkCode
                flags = kb.flags
                alt_down = bool(flags & LLKHF_ALTDOWN)
                es_inyectado = bool(flags & LLKHF_INJECTED)

                user32 = ctypes.windll.user32
                win_down = bool(user32.GetAsyncKeyState(VK_LWIN) & 0x8000) or bool(user32.GetAsyncKeyState(VK_RWIN) & 0x8000)
                ctrl_down = bool(user32.GetAsyncKeyState(VK_CONTROL) & 0x8000)

                # Detección de entrada inyectada (Control remoto / Macros)
                if es_inyectado and wParam == WM_KEYDOWN:
                    self._emitir_alerta_tecla("ENTRADA_INYECTADA_CONTROL_REMOTO", "CRITICO", f"Teclado virtual o remoto inyectó código VK {vk}")

                # 1. Bloquear Tecla Windows (Izquierda y Derecha sueltas)
                if vk in (VK_LWIN, VK_RWIN):
                    if wParam == WM_KEYDOWN:
                        self._emitir_alerta_tecla("TECLA_WINDOWS_BLOQUEADA", "MEDIO", "Intento de abrir menú inicio")
                    return 1

                # 2. Bloquear Atajos de Windows (Copilot, Game Bar, Portapapeles, Recortes, Escritorios Virtuales)
                if win_down:
                    if vk in (VK_LEFT, VK_RIGHT, VK_UP, VK_DOWN, VK_D):
                        if wParam in (WM_KEYDOWN, WM_SYSKEYDOWN):
                            self._emitir_alerta_tecla("ATAJO_ESCRITORIO_VIRTUAL_BLOQUEADO", "ALTO", f"Intento de conmutar o crear escritorio virtual (Win+VK {vk})")
                        return 1
                    if vk in (VK_A, VK_N):
                        if wParam in (WM_KEYDOWN, WM_SYSKEYDOWN):
                            self._emitir_alerta_tecla("NOTIFICACIONES_WINDOWS_BLOQUEADAS", "MEDIO", f"Intento de abrir notificaciones o Phone Link (Win+VK {vk})")
                        return 1
                    if vk == VK_L:
                        if wParam in (WM_KEYDOWN, WM_SYSKEYDOWN):
                            self._emitir_alerta_tecla("INTENTO_BLOQUEO_SESION_BLOQUEADO", "CRITICO", "Intento de bloquear pantalla o conmutar usuario (Win+L)")
                        return 1
                    if vk == VK_C:
                        if wParam in (WM_KEYDOWN, WM_SYSKEYDOWN):
                            self._emitir_alerta_tecla("COPILOT_BLOQUEADO", "CRITICO", "Intento de abrir Windows Copilot IA (Win+C)")
                        return 1
                    if vk == VK_G:
                        if wParam in (WM_KEYDOWN, WM_SYSKEYDOWN):
                            self._emitir_alerta_tecla("GAME_BAR_BLOQUEADO", "ALTO", "Intento de abrir Xbox Game Bar overlay (Win+G)")
                        return 1
                    if vk == VK_V:
                        if wParam in (WM_KEYDOWN, WM_SYSKEYDOWN):
                            self._emitir_alerta_tecla("HISTORIAL_PORTAPAPELES_BLOQUEADO", "ALTO", "Intento de abrir historial de portapapeles (Win+V)")
                        return 1
                    if vk == VK_S:
                        if wParam in (WM_KEYDOWN, WM_SYSKEYDOWN):
                            self._emitir_alerta_tecla("RECORTES_BLOQUEADO", "ALTO", "Intento de captura de pantalla con Recortes (Win+Shift+S)")
                        return 1
                    if vk in (VK_TAB, VK_ESCAPE):
                        return 1

                # 3. Bloquear Alt + Tab (en examen estricto; en examen con apps permitidas se autoriza la alternancia)
                if alt_down and vk == VK_TAB:
                    if len(self.procesos_permitidos_examen) == 0:
                        if wParam in (WM_KEYDOWN, WM_SYSKEYDOWN):
                            self._emitir_alerta_tecla("ALT_TAB_BLOQUEADO", "MEDIO", "Intento de conmutar aplicación")
                        return 1

                # 4. Bloquear Alt + Esc
                if alt_down and vk == VK_ESCAPE:
                    if wParam in (WM_KEYDOWN, WM_SYSKEYDOWN):
                        self._emitir_alerta_tecla("ALT_ESC_BLOQUEADO", "MEDIO", "Intento de salir de la aplicación")
                    return 1

                # 5. Bloquear Alt + F4
                if alt_down and vk == VK_F4:
                    if wParam in (WM_KEYDOWN, WM_SYSKEYDOWN):
                        self._emitir_alerta_tecla("ALT_F4_BLOQUEADO", "ALTO", "Intento de forzar cierre de ventana")
                    return 1

                # 6. Bloquear Ctrl + Esc
                if ctrl_down and vk == VK_ESCAPE:
                    if wParam == WM_KEYDOWN:
                        self._emitir_alerta_tecla("CTRL_ESC_BLOQUEADO", "ALTO", "Intento de abrir menú de inicio")
                    return 1

                # 7. Bloquear PrintScreen (PrtScn)
                if vk == VK_SNAPSHOT:
                    if wParam == WM_KEYDOWN:
                        self._emitir_alerta_tecla("PRTSCN_BLOQUEADO", "ALTO", "Intento de captura de pantalla física")
                    return 1

                # 8. Bloquear Copiar y Pegar (Ctrl+C, Ctrl+V, Ctrl+X) en examen estricto
                if ctrl_down and vk in (VK_C, VK_V, VK_X):
                    if len(self.procesos_permitidos_examen) == 0:
                        if wParam in (WM_KEYDOWN, WM_SYSKEYDOWN):
                            self._emitir_alerta_tecla("COPIAR_PEGAR_BLOQUEADO", "MEDIO", f"Intento de copiar o pegar texto prohibido (Ctrl+VK {vk})")
                        return 1

            return ctypes.windll.user32.CallNextHookEx(self.hook_id, nCode, wParam, lParam)

        self._hook_callback = HOOKPROC(_low_level_keyboard_proc)
        user32 = ctypes.windll.user32
        user32.SetWindowsHookExW.argtypes = [ctypes.c_int, HOOKPROC, wintypes.HINSTANCE, wintypes.DWORD]
        user32.SetWindowsHookExW.restype = wintypes.HHOOK
        user32.UnhookWindowsHookEx.argtypes = [wintypes.HHOOK]
        user32.UnhookWindowsHookEx.restype = wintypes.BOOL

        self.hook_id = user32.SetWindowsHookExW(
            WH_KEYBOARD_LL,
            self._hook_callback,
            None,
            0
        )
        if self.hook_id:
            print("[KIOSKO] Hook de bajo nivel WH_KEYBOARD_LL instalado exitosamente.")
        else:
            print("[KIOSKO] No se pudo instalar el hook de bajo nivel de teclado.")

    def _desinstalar_hook_teclado(self):
        """Desinstala el hook WH_KEYBOARD_LL"""
        if self.hook_id is not None:
            try:
                ctypes.windll.user32.UnhookWindowsHookEx(self.hook_id)
            except Exception:
                pass
            self.hook_id = None
            self._hook_callback = None
            print("[KIOSKO] Hook WH_KEYBOARD_LL desinstalado.")

    def _emitir_alerta_tecla(self, evento: str, nivel: str, detalle: str):
        import time
        ahora = time.time()
        if self._cooldown_teclas.get(evento, 0) > ahora:
            return
        self._cooldown_teclas[evento] = ahora + 3.0  # 3 segundos de cooldown por tecla

        if self.funcion_alerta:
            try:
                nombre_legible = evento.replace("_BLOQUEADO", "").replace("_BLOQUEADA", "").replace("_", " ").title()
                evidencia = {
                    "claseAlerta": "TECLADO",
                    "nivelRiesgo": nivel,
                    "combinacionTeclas": nombre_legible,
                    "patronSospechoso": "ATAJO_PROHIBIDO",
                    "pidProceso": 0,
                    "nombreProceso": evento,
                    "categoriaProceso": "CONTROL_REMOTO",
                    "accionTomada": "BLOQUEADO",
                    "detalle": detalle,
                    "descripcion": f"Atajo no permitido: {nombre_legible} ({detalle})"
                }
                self.funcion_alerta(evidencia)
            except Exception:
                pass


# Instancia singleton para el modo kiosko
gestor_kiosko = GestorModoKiosko()
