# vista/ventana_login.py
import os
from PyQt6.QtWidgets import QWidget, QMessageBox, QLineEdit
from PyQt6.QtGui import QIcon
from PyQt6 import uic

# Importamos nuestro cliente API
from api.cliente_respuesta import cliente_api

class VentanaLogin(QWidget):
    def __init__(self):
        super().__init__()
        
        # Leemos el diseño XML de forma dinámica
        base_path = os.path.dirname(__file__)
        uic.loadUi(os.path.join(base_path, "ventana_login.xml"), self)
        
        logo_path = os.path.join(base_path, "recursos", "logo_upc.png").replace("\\", "/")
        if os.path.exists(logo_path):
            self.etiqueta_logo.setText("")
            self.etiqueta_logo.setStyleSheet(f"border-image: url('{logo_path}'); border-radius: 50px;")
        
        # Conectamos botones
        self.boton_ingresar.clicked.connect(self.intentar_login)
        self.boton_ojo.clicked.connect(self.alternar_ojo)
        self.clave_visible = False
        
        # Cargar Íconos
        self.ruta_ojo_abierto = os.path.join(os.path.dirname(os.path.dirname(__file__)), "recursos", "ojo_abierto.svg")
        self.ruta_ojo_cerrado = os.path.join(os.path.dirname(os.path.dirname(__file__)), "recursos", "ojo_cerrado.svg")
        self.boton_ojo.setText("")
        self.boton_ojo.setIcon(QIcon(self.ruta_ojo_cerrado))
        
        self.aplicar_estilos_locales()

    def alternar_ojo(self):
        self.clave_visible = not self.clave_visible
        if self.clave_visible:
            self.entrada_clave.setEchoMode(QLineEdit.EchoMode.Normal)
            self.boton_ojo.setIcon(QIcon(self.ruta_ojo_abierto))
        else:
            self.entrada_clave.setEchoMode(QLineEdit.EchoMode.Password)
            self.boton_ojo.setIcon(QIcon(self.ruta_ojo_cerrado))

    def aplicar_estilos_locales(self):
        estilo = """
        QWidget#VentanaLogin {
            background-color: #F4F6F8; /* Fondo gris súper claro */
        }
        QFrame#tarjeta_login {
            background-color: #FFFFFF;
            border-radius: 8px;
            border: 1px solid #E0E0E0;
            /* Se removió la línea verde superior según requerimiento */
        }
        QLabel#etiqueta_titulo {
            color: #005A1C; /* Verde oscuro para el título */
        }
        QLabel#etiqueta_logo {
            background-color: transparent;
            border: 2px dashed #CCCCCC;
            border-radius: 50px; /* Para hacerlo redondo (100x100) */
        }
        QLabel#etiqueta_correo, QLabel#etiqueta_clave {
            color: #333333;
            font-weight: bold;
        }
        QLineEdit#entrada_correo, QLineEdit#entrada_clave {
            border: 1px solid #CCCCCC;
            border-radius: 4px;
            padding-left: 10px;
            font-size: 14px;
            color: #333333;
            background-color: #FFFFFF;
        }
        QLineEdit#entrada_correo:focus, QLineEdit#entrada_clave:focus {
            border: 1px solid #147B2C;
        }
        QPushButton#boton_ojo {
            background-color: transparent;
            border: 1px solid #CCCCCC;
            border-radius: 4px;
            font-size: 16px;
        }
        QPushButton#boton_ojo:hover {
            background-color: #F4F6F8;
        }
        QPushButton#boton_ingresar {
            background-color: #147B2C; /* Verde UPC */
            color: white;
            border-radius: 4px;
        }
        QPushButton#boton_ingresar:hover {
            background-color: #005A1C; /* Verde oscuro hover */
        }
        """
        self.setStyleSheet(estilo)

    def intentar_login(self):
        correo = self.entrada_correo.text().strip()
        clave = self.entrada_clave.text().strip()

        if not correo or not clave:
            QMessageBox.warning(self, "Campos Vacíos", "Por favor, llene el correo y la contraseña.")
            return
        
        self.boton_ingresar.setEnabled(False)
        self.boton_ingresar.setText("Cargando...")

        # Viajamos a Spring Boot a través de nuestro cliente
        exito, resultado = cliente_api.login_profesor(correo, clave)

        if exito:
            self.login_exitoso()
        else:
            QMessageBox.critical(self, "Acceso Denegado", resultado)
            self.boton_ingresar.setEnabled(True)
            self.boton_ingresar.setText("Iniciar Sesión")

    def login_exitoso(self):
        # El ID y token ya se guardan dentro de cliente_api.login_profesor
        
        # Cerrar el login y abrir la principal
        from vista.ventana_principal import VentanaPrincipal
        self.ventana_principal = VentanaPrincipal()
        
        # FIX GEOMETRÍA: Establecemos un mínimo duro para que Windows no intente forzar resoluciones imposibles 
        # basadas en el número de tarjetas en el dashboard.
        from PyQt6.QtWidgets import QApplication
        _screen = QApplication.primaryScreen().availableSize()
        self.ventana_principal.setMinimumSize(
            max(800, int(_screen.width() * 0.55)),
            max(550, int(_screen.height() * 0.65)))
        
        self.ventana_principal.showMaximized()
        self.close()