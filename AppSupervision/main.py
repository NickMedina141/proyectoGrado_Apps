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
    print("FATAL: AppSupervision ha sido diseñada y certificada exclusivamente para entornos Windows.")
    try:
        from PyQt6.QtWidgets import QApplication, QMessageBox
        _temp_app = QApplication(sys.argv)
        QMessageBox.critical(
            None,
            "Sistema No Compatible",
            "Acceso denegado: AppSupervision ha sido diseñada y certificada exclusivamente para sistemas operativos Windows.\n\n"
            "Por motivos de seguridad e integridad, no es posible ejecutar el entorno de supervisión en este sistema operativo."
        )
    except Exception:
        pass
    sys.exit(1)

# Asegurar que los imports relativos funcionen correctamente
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Sincronización silenciosa de parches desde GitHub Releases (DESACTIVADA PARA DESARROLLO LOCAL)
# from utils.actualizador import sincronizar_parches
# base_dir = os.path.dirname(os.path.abspath(__file__))
# if sincronizar_parches("AppSupervision", base_dir):
#     os.execl(sys.executable, sys.executable, *sys.argv)

# FIX CRÍTICO: QtWebEngine requiere ser importado ANTES de crear QApplication
try:
  from PyQt6.QtWebEngineWidgets import QWebEngineView
except ImportError:
  pass

from PyQt6.QtWidgets import QApplication
from vista.ventana_login import VentanaLogin
from vista.ventana_principal import VentanaPrincipal

from PyQt6.QtGui import QShortcut, QKeySequence
from PyQt6.QtWidgets import QWidget

import subprocess
import atexit

class AppEstudiante:
  def __init__(self):
    self.app = QApplication(sys.argv)
    
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
    # Asegurar que se limpia la UI al volver a login
    self.ventana_login.entrada_correo.clear()
    self.ventana_login.entrada_clave.clear()
    self.ventana_login.show()
    
  def mostrar_ventana_principal(self):
    self.ventana_login.hide()
    # Reiniciar a la pestaña del PIN siempre que entremos a la principal
    self.ventana_principal.stack_vistas.setCurrentIndex(0)
    self.ventana_principal.entrada_pin.clear()
    self.ventana_principal.show()
    
  def iniciar(self):
    # Eliminado el salto temporal. Ahora inicia en Login para obtener el Token.
    self.mostrar_ventana_login()
    sys.exit(self.app.exec())

if __name__ == "__main__":
  aplicacion = AppEstudiante()
  aplicacion.iniciar()
