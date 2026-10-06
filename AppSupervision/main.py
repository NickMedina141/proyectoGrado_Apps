import sys
import os

if getattr(sys, 'frozen', False):
    import multiprocessing
    multiprocessing.freeze_support()

if len(sys.argv) > 1 and sys.argv[1] == '--run-api':
    import uvicorn
    from motor_ia.main_api import app
    print("Iniciando FastAPI desde ejecutable...")
    uvicorn.run(app, host="127.0.0.1", port=8005, reload=False)
    sys.exit(0)

# Validación estricta de Sistema Operativo Soportado (Solo Windows)
import platform
if platform.system().lower() != "windows":
    print("FATAL: UPC SecureExam ha sido diseñada y certificada exclusivamente para entornos Windows.")
    try:
        from PyQt6.QtWidgets import QApplication, QMessageBox
        _temp_app = QApplication(sys.argv)
        QMessageBox.critical(
            None,
            "Sistema No Compatible",
            "Acceso denegado: UPC SecureExam ha sido diseñada y certificada exclusivamente para sistemas operativos Windows.\n\n"
            "Por motivos de seguridad e integridad, no es posible ejecutar el entorno de supervisión en este sistema operativo."
        )
    except Exception:
        pass
    sys.exit(1)

# Registrar AppUserModelID en Windows para icono propio en barra de tareas
if sys.platform == "win32":
    import ctypes
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("UPC.SecureExam.Estudiante.1.0")
    except Exception:
        pass

# Asegurar que los imports relativos funcionen correctamente
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# --- SINCRONIZADOR DESACTIVADO EN ENTORNO DE DESARROLLO (VENV) ---
# Descomentar al compilar ejecutables finales
# try:
#     from utils.actualizador import sincronizar_parches
#     base_dir = os.path.dirname(os.path.abspath(__file__))
#     if sincronizar_parches("AppSupervision", base_dir):
#         import subprocess
#         subprocess.Popen([sys.executable, os.path.join(base_dir, "main.py")] + sys.argv[1:])
#         sys.exit(0)
# except Exception as e:
#     print(f"[ACTUALIZADOR] Error comprobando parches: {e}")

# FIX CRÍTICO: QtWebEngine requiere ser importado ANTES de crear QApplication
try:
  from PyQt6.QtWebEngineWidgets import QWebEngineView
except ImportError:
  pass

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QShortcut, QKeySequence, QIcon
from vista.ventana_login import VentanaLogin
from vista.ventana_principal import VentanaPrincipal
from PyQt6.QtWidgets import QWidget

import subprocess
import atexit

def aplicar_icono_institucional_windows(widget, ruta_ico):
  """
  Inyecta el icono nativo tanto en PyQt6 como a través de la API de Windows (WM_SETICON),
  garantizando que el Administrador de Tareas y la barra de tareas muestren el escudo de la UPC.
  """
  if not widget or not ruta_ico or not os.path.exists(ruta_ico):
    return
  try:
    from PyQt6.QtGui import QIcon
    widget.setWindowIcon(QIcon(ruta_ico))
  except Exception:
    pass

  if sys.platform == "win32":
    try:
      import ctypes
      hwnd = int(widget.winId())
      if hwnd:
        WM_SETICON = 0x0080
        ICON_SMALL = 0
        ICON_BIG = 1
        IMAGE_ICON = 1
        LR_LOADFROMFILE = 0x00000010
        LR_DEFAULTSIZE = 0x00000040
        abs_ico = os.path.abspath(ruta_ico)
        
        h_icon_big = ctypes.windll.user32.LoadImageW(0, abs_ico, IMAGE_ICON, 32, 32, LR_LOADFROMFILE)
        h_icon_small = ctypes.windll.user32.LoadImageW(0, abs_ico, IMAGE_ICON, 16, 16, LR_LOADFROMFILE)
        
        if h_icon_big:
          ctypes.windll.user32.SendMessageW(hwnd, WM_SETICON, ICON_BIG, h_icon_big)
        if h_icon_small:
          ctypes.windll.user32.SendMessageW(hwnd, WM_SETICON, ICON_SMALL, h_icon_small)
    except Exception as e:
      print(f"[ICONO] Error inyectando WM_SETICON: {e}")

class AppEstudiante:
  def __init__(self):
    self.app = QApplication(sys.argv)
    self.app.setApplicationName("UPC SecureExam")
    self.app.setApplicationDisplayName("UPC SecureExam")

    # Configuración de ícono institucional UPC
    base_dir = os.path.dirname(os.path.abspath(__file__))
    ruta_ico = os.path.join(base_dir, "recursos", "installer_icon.ico")
    ruta_png = os.path.join(base_dir, "vista", "recursos", "logo_upc.png")
    self.ruta_icono = ruta_ico if os.path.exists(ruta_ico) else ruta_png
    if os.path.exists(self.ruta_icono):
      self.app.setWindowIcon(QIcon(self.ruta_icono))
    
    # Iniciar FastAPI Automáticamente en segundo plano
    self.proceso_ia = self._iniciar_fastapi()
    
    # Inicializar gestor de temas
    from vista.gestor_temas import GestorTemas
    self.gestor_temas = GestorTemas(self.app)
    
    # Instanciar vistas
    self.ventana_login = VentanaLogin(app_principal=self)
    self.ventana_principal = VentanaPrincipal(app_principal=self)
    
    # Conectar atajo (F10) para cada ventana
    self.atajos = [] # Guardar referencia para evitar recolección de basura
    self._conectar_atajo(self.ventana_login)
    self._conectar_atajo(self.ventana_principal)
    
  def _conectar_atajo(self, ventana):
    atajo = QShortcut(QKeySequence("F10"), ventana)
    atajo.activated.connect(self.gestor_temas.alternar_tema)
    self.atajos.append(atajo)
    
  def _iniciar_fastapi(self):
    if getattr(sys, 'frozen', False):
      print("Iniciando Motor de IA compilado en segundo plano...")
      try:
        proc = subprocess.Popen([sys.executable, "--run-api"], creationflags=0x08000000)
        atexit.register(proc.terminate)
        return proc
      except Exception as e:
        print(f"Error al iniciar IA compilada: {e}")
        return None
    else:
      script_ia = os.path.join(os.path.dirname(os.path.abspath(__file__)), "iniciar_IA.py")
      print("Iniciando Motor de IA (Dev) en segundo plano...")
      try:
        proc = subprocess.Popen([sys.executable, script_ia], creationflags=0x08000000)
        atexit.register(proc.terminate)
        return proc
      except Exception as e:
        print(f"Error al iniciar IA: {e}")
        return None
    
  def mostrar_ventana_login(self):
    self.ventana_principal.hide()
    if hasattr(self.ventana_principal, 'hilo_audio_test') and self.ventana_principal.hilo_audio_test:
      self.ventana_principal.hilo_audio_test.detener()
      self.ventana_principal.hilo_audio_test = None
    # Asegurar que se limpia la UI al volver a login
    self.ventana_login.entrada_correo.clear()
    self.ventana_login.entrada_clave.clear()
    if hasattr(self.ventana_login, 'check_politica_login'):
      self.ventana_login.check_politica_login.setChecked(False)
    self.ventana_login.show()
    aplicar_icono_institucional_windows(self.ventana_login, self.ruta_icono)
    
  def mostrar_ventana_principal(self):
    self.ventana_login.hide()
    # Reiniciar a la pestaña del PIN siempre que entremos a la principal
    self.ventana_principal.stack_vistas.setCurrentIndex(0)
    self.ventana_principal.entrada_pin.clear()
    self.ventana_principal.show()
    aplicar_icono_institucional_windows(self.ventana_principal, self.ruta_icono)
    if hasattr(self.ventana_principal, '_ejecutar_diagnostico_hardware'):
      self.ventana_principal._ejecutar_diagnostico_hardware()
    
  def iniciar(self):
    # Eliminado el salto temporal. Ahora inicia en Login para obtener el Token.
    self.mostrar_ventana_login()
    sys.exit(self.app.exec())

if __name__ == "__main__":
  aplicacion = AppEstudiante()
  aplicacion.iniciar()
