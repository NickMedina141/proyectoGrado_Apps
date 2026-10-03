# main.py
import sys
import os
import platform

if __name__ == '__main__':
    # Validación estricta de Sistema Operativo Soportado (Solo Windows)
    if platform.system().lower() != "windows":
        print("FATAL: AppProfesor ha sido diseñada y certificada exclusivamente para sistemas operativos Windows.")
        try:
            from PyQt6.QtWidgets import QApplication, QMessageBox
            _temp_app = QApplication(sys.argv)
            QMessageBox.critical(
                None,
                "Sistema No Compatible",
                "Sistema no compatible: AppProfesor ha sido diseñada y certificada exclusivamente para sistemas operativos Windows.\n\n"
                "Para garantizar la correcta visualización del mapa GPS y la seguridad, ejecute la aplicación en Windows."
            )
        except Exception:
            pass
        sys.exit(1)

    from PyQt6.QtWebEngineWidgets import QWebEngineView  # IMPORTANTE: Debe importarse antes de crear QApplication
    from PyQt6.QtWidgets import QApplication
    from vista.ventana_login import VentanaLogin
    from utils.actualizador import sincronizar_parches

    aplicacion = QApplication(sys.argv)
    ventana = VentanaLogin()
    ventana.show()

    # Bucle de eventos de la aplicación
    sys.exit(aplicacion.exec())