# main.py
import sys
import os
from PyQt6.QtWebEngineWidgets import QWebEngineView  # IMPORTANTE: Debe importarse antes de crear QApplication
from PyQt6.QtWidgets import QApplication
from vista.ventana_login import VentanaLogin
from utils.actualizador import sincronizar_parches

if __name__ == '__main__':
    # Sincronización silenciosa de parches desde GitHub Releases
    base_dir = os.path.dirname(os.path.abspath(__file__))
    if sincronizar_parches("AppProfesor", base_dir):
        os.execl(sys.executable, sys.executable, *sys.argv)

    aplicacion = QApplication(sys.argv)
    ventana = VentanaLogin()
    ventana.show()

    # Bucle de eventos de la aplicación
    sys.exit(aplicacion.exec())