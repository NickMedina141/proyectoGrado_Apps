from PyQt6.QtWidgets import QWidget, QMessageBox, QLineEdit
from PyQt6.QtGui import QIcon
from PyQt6.uic import loadUi
from api.cliente_respuesta import cliente_api
import os

class VentanaLogin(QWidget):
    def __init__(self, app_principal=None):
        super().__init__()
        self.app_principal = app_principal
        
        # Cargar UI
        ruta_ui = os.path.join(os.path.dirname(__file__), "ventana_login.xml")
        loadUi(ruta_ui, self)
        
        # Identidad visual e ícono de la ventana
        self.setWindowTitle("UPC SecureExam - Iniciar Sesión")
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        ruta_ico = os.path.join(base_dir, "recursos", "installer_icon.ico")
        ruta_png = os.path.join(os.path.dirname(__file__), "recursos", "logo_upc.png")
        ruta_icono = ruta_ico if os.path.exists(ruta_ico) else ruta_png
        if os.path.exists(ruta_icono):
            self.setWindowIcon(QIcon(ruta_icono))

        logo_path = os.path.join(os.path.dirname(__file__), "recursos", "logo_upc.png").replace("\\", "/")
        if os.path.exists(logo_path):
            self.etiqueta_logo.setText("")
            self.etiqueta_logo.setStyleSheet(f"border-image: url('{logo_path}'); border-radius: 30px;")
        
        # Conectar botones y atajos de teclado (Enter)
        self.boton_ingresar.clicked.connect(self.procesar_login)
        self.boton_ojo.clicked.connect(self.alternar_visibilidad_clave)
        self.entrada_correo.returnPressed.connect(self.entrada_clave.setFocus)
        self.entrada_clave.returnPressed.connect(self.procesar_login)
        if hasattr(self, 'boton_politica_datos'):
            self.boton_politica_datos.clicked.connect(self._abrir_politica_datos)
        if hasattr(self, 'boton_registro_estudiante'):
            self.boton_registro_estudiante.clicked.connect(self._abrir_registro_estudiante)
        if hasattr(self, 'boton_olvido_clave'):
            self.boton_olvido_clave.clicked.connect(self._abrir_recuperar_clave)
        
        # Rutas de los íconos (Nivel de carpeta anterior + recursos)
        self.ruta_ojo_abierto = os.path.join(os.path.dirname(os.path.dirname(__file__)), "recursos", "ojo_abierto.svg")
        self.ruta_ojo_cerrado = os.path.join(os.path.dirname(os.path.dirname(__file__)), "recursos", "ojo_cerrado.svg")
        
        # Restaurar a tamaño cuadrado de ícono original
        # boton_ojo sizing defined in ventana_login.xml
        self.boton_ojo.setText("") # Quitar cualquier texto residual
        self.boton_ojo.setIcon(QIcon(self.ruta_ojo_cerrado))
        
        # Overlay Spinner para transiciones y operaciones de red
        from vista.overlay_carga import OverlayCarga
        self.overlay_carga = OverlayCarga(self)
        
    def _abrir_politica_datos(self):
        from vista.modal_politica_datos import ModalPoliticaDatos
        modal = ModalPoliticaDatos(self)
        modal.exec()

    def _abrir_registro_estudiante(self):
        from vista.modal_registro_estudiante import ModalRegistroEstudiante
        modal = ModalRegistroEstudiante(self)
        modal.registro_completado.connect(self._al_completar_registro_estudiante)
        modal.exec()

    def _al_completar_registro_estudiante(self, email_registrado):
        self.entrada_correo.setText(email_registrado)
        self.entrada_clave.clear()
        self.entrada_clave.setFocus()

    def _abrir_recuperar_clave(self):
        from vista.modal_recuperar_clave import ModalRecuperarClave
        modal = ModalRecuperarClave(self)
        modal.recuperacion_completada.connect(self._al_completar_recuperacion_clave)
        modal.exec()

    def _al_completar_recuperacion_clave(self, email_restablecido):
        self.entrada_correo.setText(email_restablecido)
        self.entrada_clave.clear()
        self.entrada_clave.setFocus()
        
    def alternar_visibilidad_clave(self):
        if self.entrada_clave.echoMode() == QLineEdit.EchoMode.Password:
            self.entrada_clave.setEchoMode(QLineEdit.EchoMode.Normal)
            self.boton_ojo.setIcon(QIcon(self.ruta_ojo_abierto))
        else:
            self.entrada_clave.setEchoMode(QLineEdit.EchoMode.Password)
            self.boton_ojo.setIcon(QIcon(self.ruta_ojo_cerrado))

    def procesar_login(self):
        correo = self.entrada_correo.text().strip()
        clave = self.entrada_clave.text().strip()
        
        if not correo or not clave:
            QMessageBox.warning(self, "Campos Incompletos", "Por favor ingresa tu correo y contraseña.")
            return

        if hasattr(self, 'check_politica_login') and not self.check_politica_login.isChecked():
            QMessageBox.warning(
                self,
                "Consentimiento Requerido",
                "Para iniciar sesión es obligatorio leer y aceptar la Política de Tratamiento de Datos Personales y Biométricos en cumplimiento de la Ley 1581 de 2012."
            )
            return
            
        self.boton_ingresar.setEnabled(False)
        self.boton_ingresar.setText("Iniciando sesión...")

        def _tarea_login():
            return cliente_api.login_estudiante(correo, clave)

        def _al_terminar_login(res):
            exito, mensaje = res
            self.boton_ingresar.setEnabled(True)
            self.boton_ingresar.setText("Iniciar Sesión")
            
            if exito:
                from motor_ia.biometria_facial import biometria_motor
                import cv2
                import json
                
                import sys
                if getattr(sys, 'frozen', False):
                    base_dir = os.path.dirname(sys.executable)
                else:
                    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                ruta_datos = os.path.join(base_dir, "datos_biometricos")
                os.makedirs(ruta_datos, exist_ok=True)
                correo_limpio = correo.replace("@", "_").replace(".", "_")
                ruta_emb = os.path.join(ruta_datos, f"emb_{correo_limpio}.json")
                
                if not os.path.exists(ruta_emb):
                    from vista.modal_registro_biometrico import ModalRegistroBiometrico
                    modal = ModalRegistroBiometrico(correo_estudiante=correo, parent=self)
                    resultado = modal.exec()
                    
                    if resultado != ModalRegistroBiometrico.DialogCode.Accepted:
                        QMessageBox.warning(
                            self, 
                            "Registro Requerido", 
                            "El registro facial es obligatorio para poder ingresar a la plataforma de supervisión."
                        )
                        return

                # Guardar la ruta globalmente para que hilo_camara la lea
                biometria_motor.ruta_emb_actual = ruta_emb

                if self.app_principal:
                    self.app_principal.mostrar_ventana_principal()
            else:
                QMessageBox.critical(self, "Error de Inicio", mensaje)

        self.overlay_carga.ejecutar_tarea(
            _tarea_login,
            _al_terminar_login,
            mensaje="Iniciando sesión..."
        )
