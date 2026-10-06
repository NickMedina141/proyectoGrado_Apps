# main.py
import sys
import os
import platform

if __name__ == '__main__':
    # Validación estricta de Sistema Operativo Soportado (Solo Windows)
    if platform.system().lower() != "windows":
        print("FATAL: UPC Proctor ha sido diseñado y certificado exclusivamente para sistemas operativos Windows.")
        try:
            from PyQt6.QtWidgets import QApplication, QMessageBox
            _temp_app = QApplication(sys.argv)
            QMessageBox.critical(
                None,
                "Sistema No Compatible",
                "Sistema no compatible: UPC Proctor ha sido diseñado y certificado exclusivamente para sistemas operativos Windows.\n\n"
                "Para garantizar la correcta visualización del mapa GPS y la seguridad, ejecute la aplicación en Windows."
            )
        except Exception:
            pass
        sys.exit(1)

    # Registrar AppUserModelID en Windows para icono propio en barra de tareas
    if sys.platform == "win32":
        import ctypes
        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("UPC.Proctor.Docente.1.0")
        except Exception:
            pass

    from PyQt6.QtWebEngineWidgets import QWebEngineView  # IMPORTANTE: Debe importarse antes de crear QApplication
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtGui import QIcon
    from vista.ventana_login import VentanaLogin
    base_dir = os.path.dirname(os.path.abspath(__file__))
    try:
        from utils.actualizador import sincronizar_parches
        if sincronizar_parches("AppProfesor", base_dir):
            import subprocess
            subprocess.Popen([sys.executable, os.path.join(base_dir, "main.py")] + sys.argv[1:])
            sys.exit(0)
    except Exception as e:
        print(f"[ACTUALIZADOR] Error comprobando parches: {e}")

    aplicacion = QApplication(sys.argv)
    aplicacion.setApplicationName("UPC Proctor")
    aplicacion.setApplicationDisplayName("")

    # Configuración de ícono institucional UPC
    ruta_ico = os.path.join(base_dir, "recursos", "installer_icon.ico")
    ruta_png = os.path.join(base_dir, "vista", "recursos", "logo_upc.png")
    ruta_icono = ruta_ico if os.path.exists(ruta_ico) else ruta_png
    if os.path.exists(ruta_icono):
        aplicacion.setWindowIcon(QIcon(ruta_icono))

    def aplicar_icono_institucional_windows(widget, ruta_ico):
        if not widget or not ruta_ico or not os.path.exists(ruta_ico):
            return
        try:
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
                    abs_ico = os.path.abspath(ruta_ico)
                    h_icon_big = ctypes.windll.user32.LoadImageW(0, abs_ico, IMAGE_ICON, 32, 32, LR_LOADFROMFILE)
                    h_icon_small = ctypes.windll.user32.LoadImageW(0, abs_ico, IMAGE_ICON, 16, 16, LR_LOADFROMFILE)
                    if h_icon_big:
                        ctypes.windll.user32.SendMessageW(hwnd, WM_SETICON, ICON_BIG, h_icon_big)
                    if h_icon_small:
                        ctypes.windll.user32.SendMessageW(hwnd, WM_SETICON, ICON_SMALL, h_icon_small)
            except Exception as e:
                print(f"[ICONO] Error inyectando WM_SETICON: {e}")

    ventana = VentanaLogin()
    ventana.show()
    aplicar_icono_institucional_windows(ventana, ruta_icono)

    # Bucle de eventos de la aplicación
    sys.exit(aplicacion.exec())