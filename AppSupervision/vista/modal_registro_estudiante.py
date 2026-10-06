# vista/modal_registro_estudiante.py
"""
Modal de Registro Institucional para Estudiantes con Verificación OTP de Correo Electrónico.
Incluye validación visual de seguridad de contraseña y código estudiantil autogenerado.
Universidad Popular del Cesar - UPC SecureExam.
"""

import os
import re
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QPushButton, QLineEdit, QStackedWidget, QWidget,
    QMessageBox, QFrame, QCheckBox, QProgressBar
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QIcon, QFont, QIntValidator
from api.cliente_respuesta import cliente_api


class ModalRegistroEstudiante(QDialog):
    registro_completado = pyqtSignal(str) # Emite el email registrado con éxito

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(540, 710)
        self.setModal(True)
        self.setWindowTitle("UPC SecureExam - Registro de Estudiante")

        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        ruta_ico = os.path.join(base_dir, "recursos", "installer_icon.ico")
        ruta_png = os.path.join(base_dir, "vista", "recursos", "logo_upc.png")
        ruta_icono = ruta_ico if os.path.exists(ruta_ico) else ruta_png
        if os.path.exists(ruta_icono):
            self.setWindowIcon(QIcon(ruta_icono))

        # Rutas de íconos de ojo
        self.ruta_ojo_abierto = os.path.join(base_dir, "recursos", "ojo_abierto.svg")
        self.ruta_ojo_cerrado = os.path.join(base_dir, "recursos", "ojo_cerrado.svg")

        self.email_en_proceso = ""
        self._construir_ui()

    def _construir_ui(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #F8FAFC;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QLabel {
                color: #2D3748;
            }
            QLineEdit {
                background-color: #FFFFFF;
                border: 1px solid #CBD5E1;
                border-radius: 6px;
                padding: 7px 10px;
                font-size: 13px;
                color: #1E293B;
            }
            QLineEdit:focus {
                border: 1.5px solid #196F3D;
                background-color: #FAFCFA;
            }
            QLineEdit:read-only {
                background-color: #F1F5F9;
                color: #475569;
                border: 1px dashed #94A3B8;
                font-weight: bold;
            }
            QPushButton#btn_primario {
                background-color: #196F3D;
                color: #FFFFFF;
                font-weight: bold;
                font-size: 13px;
                border-radius: 6px;
                padding: 10px 18px;
                border: none;
            }
            QPushButton#btn_primario:hover {
                background-color: #145A32;
            }
            QPushButton#btn_primario:disabled {
                background-color: #94A3B8;
            }
            QPushButton#btn_secundario {
                background-color: #E2E8F0;
                color: #475569;
                font-size: 13px;
                border-radius: 6px;
                padding: 10px 18px;
                border: none;
            }
            QPushButton#btn_secundario:hover {
                background-color: #CBD5E1;
            }
            QPushButton#btn_enlace {
                background: transparent;
                border: none;
                color: #196F3D;
                font-size: 12px;
                text-decoration: underline;
                font-weight: bold;
            }
            QPushButton#btn_enlace:hover {
                color: #0E4424;
            }
            QPushButton.btn_ojo {
                background: transparent;
                border: none;
                padding: 4px;
            }
            QPushButton.btn_ojo:hover {
                background-color: #E2E8F0;
                border-radius: 4px;
            }
            QFrame#tarjeta_paso {
                background-color: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 10px;
                padding: 16px;
            }
            QProgressBar {
                border: none;
                border-radius: 3px;
                background-color: #E2E8F0;
                height: 6px;
            }
            QProgressBar::chunk {
                border-radius: 3px;
            }
            QCheckBox {
                color: #475569;
                font-size: 12px;
            }
        """)

        layout_principal = QVBoxLayout(self)
        layout_principal.setContentsMargins(22, 16, 22, 16)
        layout_principal.setSpacing(10)

        # Encabezado institucional
        header = QHBoxLayout()
        header.setSpacing(12)

        lbl_logo = QLabel()
        logo_path = os.path.join(os.path.dirname(__file__), "recursos", "logo_upc.png")
        if os.path.exists(logo_path):
            lbl_logo.setText("")
            lbl_logo.setStyleSheet(f"border-image: url('{logo_path.replace(chr(92), '/')}'); border-radius: 20px;")
            lbl_logo.setFixedSize(38, 38)
            header.addWidget(lbl_logo)

        info_header = QVBoxLayout()
        info_header.setSpacing(2)
        lbl_titulo = QLabel("Registro Institucional de Estudiante")
        lbl_titulo.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        lbl_titulo.setStyleSheet("color: #003B13;")
        lbl_sub = QLabel("Universidad Popular del Cesar")
        lbl_sub.setFont(QFont("Segoe UI", 9))
        lbl_sub.setStyleSheet("color: #64748B;")
        info_header.addWidget(lbl_titulo)
        info_header.addWidget(lbl_sub)
        header.addLayout(info_header)
        header.addStretch()

        layout_principal.addLayout(header)

        # Indicador de paso (Stepper)
        self.lbl_stepper = QLabel("PASO 1 DE 2: DATOS DEL ESTUDIANTE")
        self.lbl_stepper.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self.lbl_stepper.setStyleSheet("color: #196F3D; letter-spacing: 1px;")
        layout_principal.addWidget(self.lbl_stepper)

        # Stack de Pasos
        self.stack = QStackedWidget(self)
        layout_principal.addWidget(self.stack)

        self._crear_paso1_datos()
        self._crear_paso2_otp()

    def _crear_paso1_datos(self):
        widget1 = QWidget()
        layout1 = QVBoxLayout(widget1)
        layout1.setContentsMargins(0, 0, 0, 0)
        layout1.setSpacing(10)

        tarjeta = QFrame()
        tarjeta.setObjectName("tarjeta_paso")
        t_layout = QVBoxLayout(tarjeta)
        t_layout.setSpacing(7)

        # Fila Nombre y Apellidos
        fila_nom = QHBoxLayout()
        v_nom = QVBoxLayout()
        v_nom.setSpacing(3)
        v_nom.addWidget(QLabel("Nombre:"))
        self.txt_nombre = QLineEdit()
        self.txt_nombre.setPlaceholderText("Ej: Carlos")
        v_nom.addWidget(self.txt_nombre)
        fila_nom.addLayout(v_nom)

        v_ape = QVBoxLayout()
        v_ape.setSpacing(3)
        v_ape.addWidget(QLabel("Apellidos:"))
        self.txt_apellidos = QLineEdit()
        self.txt_apellidos.setPlaceholderText("Ej: Gomez")
        v_ape.addWidget(self.txt_apellidos)
        fila_nom.addLayout(v_ape)
        t_layout.addLayout(fila_nom)

        # Fila Cédula y Código Estudiantil (Autogenerado)
        fila_id = QHBoxLayout()
        v_ced = QVBoxLayout()
        v_ced.setSpacing(3)
        v_ced.addWidget(QLabel("Cédula de Ciudadanía:"))
        self.txt_cedula = QLineEdit()
        self.txt_cedula.setPlaceholderText("Ej: 1090123456")
        self.txt_cedula.setValidator(QIntValidator(1, 999999999, self))
        self.txt_cedula.textChanged.connect(self._actualizar_codigo_estudiante)
        v_ced.addWidget(self.txt_cedula)
        fila_id.addLayout(v_ced)

        v_cod = QVBoxLayout()
        v_cod.setSpacing(3)
        v_cod.addWidget(QLabel("Código Estudiantil (Asignado por API):"))
        self.txt_codigo_est = QLineEdit()
        self.txt_codigo_est.setReadOnly(True)
        self.txt_codigo_est.setPlaceholderText("Auto-generado (EST-Cédula)")
        v_cod.addWidget(self.txt_codigo_est)
        fila_id.addLayout(v_cod)
        t_layout.addLayout(fila_id)

        # Correo Institucional
        t_layout.addWidget(QLabel("Correo Institucional (@unicesar.edu.co):"))
        self.txt_email = QLineEdit()
        self.txt_email.setPlaceholderText("ejemplo@unicesar.edu.co")
        t_layout.addWidget(self.txt_email)

        # Fila Contraseñas con Botones de Ojo
        fila_pass = QHBoxLayout()
        
        # Campo Pass 1
        v_p1 = QVBoxLayout()
        v_p1.setSpacing(3)
        v_p1.addWidget(QLabel("Contraseña:"))
        box_p1 = QHBoxLayout()
        box_p1.setSpacing(2)
        self.txt_pass1 = QLineEdit()
        self.txt_pass1.setEchoMode(QLineEdit.EchoMode.Password)
        self.txt_pass1.setPlaceholderText("Mínimo 8 caracteres")
        self.txt_pass1.textChanged.connect(self._evaluar_seguridad_clave)
        box_p1.addWidget(self.txt_pass1)

        self.btn_ojo1 = QPushButton()
        self.btn_ojo1.setProperty("class", "btn_ojo")
        self.btn_ojo1.setIcon(QIcon(self.ruta_ojo_cerrado))
        self.btn_ojo1.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_ojo1.setFixedSize(30, 30)
        self.btn_ojo1.clicked.connect(lambda: self._alternar_ojo(self.txt_pass1, self.btn_ojo1))
        box_p1.addWidget(self.btn_ojo1)
        v_p1.addLayout(box_p1)
        fila_pass.addLayout(v_p1)

        # Campo Pass 2
        v_p2 = QVBoxLayout()
        v_p2.setSpacing(3)
        v_p2.addWidget(QLabel("Confirmar Contraseña:"))
        box_p2 = QHBoxLayout()
        box_p2.setSpacing(2)
        self.txt_pass2 = QLineEdit()
        self.txt_pass2.setEchoMode(QLineEdit.EchoMode.Password)
        self.txt_pass2.setPlaceholderText("Repite la contraseña")
        self.txt_pass2.textChanged.connect(self._evaluar_seguridad_clave)
        box_p2.addWidget(self.txt_pass2)

        self.btn_ojo2 = QPushButton()
        self.btn_ojo2.setProperty("class", "btn_ojo")
        self.btn_ojo2.setIcon(QIcon(self.ruta_ojo_cerrado))
        self.btn_ojo2.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_ojo2.setFixedSize(30, 30)
        self.btn_ojo2.clicked.connect(lambda: self._alternar_ojo(self.txt_pass2, self.btn_ojo2))
        box_p2.addWidget(self.btn_ojo2)
        v_p2.addLayout(box_p2)
        fila_pass.addLayout(v_p2)
        t_layout.addLayout(fila_pass)

        # Barra de Fuerza de Contraseña
        layout_fuerza = QHBoxLayout()
        layout_fuerza.setSpacing(8)
        self.barra_fuerza = QProgressBar()
        self.barra_fuerza.setRange(0, 100)
        self.barra_fuerza.setValue(0)
        self.barra_fuerza.setTextVisible(False)
        self.barra_fuerza.setFixedHeight(5)
        layout_fuerza.addWidget(self.barra_fuerza)

        self.lbl_fuerza_texto = QLabel("Seguridad: N/A")
        self.lbl_fuerza_texto.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        self.lbl_fuerza_texto.setStyleSheet("color: #64748B;")
        layout_fuerza.addWidget(self.lbl_fuerza_texto)
        t_layout.addLayout(layout_fuerza)

        # Checklist Visual de Requisitos
        box_req = QFrame()
        box_req.setStyleSheet("background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 6px; padding: 6px;")
        grid_req = QGridLayout(box_req)
        grid_req.setContentsMargins(6, 4, 6, 4)
        grid_req.setSpacing(4)

        self.lbl_req_longitud = QLabel("• Mínimo 8 caracteres")
        self.lbl_req_longitud.setFont(QFont("Segoe UI", 8))
        self.lbl_req_longitud.setStyleSheet("color: #94A3B8;")
        grid_req.addWidget(self.lbl_req_longitud, 0, 0)

        self.lbl_req_mayus = QLabel("• Mayúscula y minúscula")
        self.lbl_req_mayus.setFont(QFont("Segoe UI", 8))
        self.lbl_req_mayus.setStyleSheet("color: #94A3B8;")
        grid_req.addWidget(self.lbl_req_mayus, 0, 1)

        self.lbl_req_num = QLabel("• Al menos un número")
        self.lbl_req_num.setFont(QFont("Segoe UI", 8))
        self.lbl_req_num.setStyleSheet("color: #94A3B8;")
        grid_req.addWidget(self.lbl_req_num, 1, 0)

        self.lbl_req_simbolo = QLabel("• Símbolo especial (!@#$%)")
        self.lbl_req_simbolo.setFont(QFont("Segoe UI", 8))
        self.lbl_req_simbolo.setStyleSheet("color: #94A3B8;")
        grid_req.addWidget(self.lbl_req_simbolo, 1, 1)

        t_layout.addWidget(box_req)

        # Indicador de Coincidencia de Contraseñas
        self.lbl_coincidencia = QLabel("")
        self.lbl_coincidencia.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        self.lbl_coincidencia.setAlignment(Qt.AlignmentFlag.AlignCenter)
        t_layout.addWidget(self.lbl_coincidencia)

        # Términos y Ley 1581
        layout_terminos = QHBoxLayout()
        layout_terminos.setSpacing(4)
        self.check_terminos = QCheckBox("Acepto la")
        self.check_terminos.setChecked(True)
        layout_terminos.addWidget(self.check_terminos)

        btn_politica = QPushButton("Política de Protección de Datos (Ley 1581)")
        btn_politica.setObjectName("btn_enlace")
        btn_politica.clicked.connect(self._ver_politica)
        layout_terminos.addWidget(btn_politica)
        layout_terminos.addStretch()
        t_layout.addLayout(layout_terminos)

        layout1.addWidget(tarjeta)

        # Botones inferiores Paso 1
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        self.btn_cancelar = QPushButton("Cancelar")
        self.btn_cancelar.setObjectName("btn_secundario")
        self.btn_cancelar.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_cancelar)

        self.btn_solicitar_otp = QPushButton("Continuar y Enviar Código ➜")
        self.btn_solicitar_otp.setObjectName("btn_primario")
        self.btn_solicitar_otp.clicked.connect(self._procesar_paso1_solicitud)
        btn_layout.addWidget(self.btn_solicitar_otp)

        layout1.addLayout(btn_layout)
        self.stack.addWidget(widget1)

    def _crear_paso2_otp(self):
        widget2 = QWidget()
        layout2 = QVBoxLayout(widget2)
        layout2.setContentsMargins(0, 0, 0, 0)
        layout2.setSpacing(12)

        tarjeta = QFrame()
        tarjeta.setObjectName("tarjeta_paso")
        t_layout = QVBoxLayout(tarjeta)
        t_layout.setSpacing(14)
        t_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        lbl_icono = QLabel("✉️")
        lbl_icono.setFont(QFont("Segoe UI", 36))
        lbl_icono.setAlignment(Qt.AlignmentFlag.AlignCenter)
        t_layout.addWidget(lbl_icono)

        lbl_instruccion = QLabel("Código de Verificación")
        lbl_instruccion.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        lbl_instruccion.setAlignment(Qt.AlignmentFlag.AlignCenter)
        t_layout.addWidget(lbl_instruccion)

        self.lbl_correo_destino = QLabel("Enviamos un código de 6 dígitos a tu correo institucional.")
        self.lbl_correo_destino.setWordWrap(True)
        self.lbl_correo_destino.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_correo_destino.setStyleSheet("color: #475569; font-size: 13px;")
        t_layout.addWidget(self.lbl_correo_destino)

        self.txt_otp = QLineEdit()
        self.txt_otp.setMaxLength(6)
        self.txt_otp.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.txt_otp.setPlaceholderText("• • • • • •")
        self.txt_otp.setFont(QFont("Consolas", 24, QFont.Weight.Bold))
        self.txt_otp.setValidator(QIntValidator(0, 999999, self))
        self.txt_otp.setStyleSheet("""
            QLineEdit {
                background-color: #F8FAFC;
                border: 2px solid #196F3D;
                border-radius: 8px;
                padding: 10px;
                color: #003B13;
                letter-spacing: 8px;
            }
        """)
        t_layout.addWidget(self.txt_otp)

        self.btn_reenviar = QPushButton("¿No recibiste el código? Reenviar código")
        self.btn_reenviar.setObjectName("btn_enlace")
        self.btn_reenviar.clicked.connect(self._reenviar_codigo)
        t_layout.addWidget(self.btn_reenviar)

        layout2.addWidget(tarjeta)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        self.btn_volver = QPushButton("⬅ Volver a Datos")
        self.btn_volver.setObjectName("btn_secundario")
        self.btn_volver.clicked.connect(lambda: self._cambiar_paso(0))
        btn_layout.addWidget(self.btn_volver)

        self.btn_confirmar_registro = QPushButton("Verificar y Crear Cuenta ✓")
        self.btn_confirmar_registro.setObjectName("btn_primario")
        self.btn_confirmar_registro.clicked.connect(self._procesar_paso2_confirmacion)
        btn_layout.addWidget(self.btn_confirmar_registro)

        layout2.addLayout(btn_layout)
        self.stack.addWidget(widget2)

    def _actualizar_codigo_estudiante(self, texto):
        cedula = texto.strip()
        if cedula:
            self.txt_codigo_est.setText(f"EST-{cedula}")
        else:
            self.txt_codigo_est.setText("")

    def _alternar_ojo(self, line_edit, boton):
        if line_edit.echoMode() == QLineEdit.EchoMode.Password:
            line_edit.setEchoMode(QLineEdit.EchoMode.Normal)
            boton.setIcon(QIcon(self.ruta_ojo_abierto))
        else:
            line_edit.setEchoMode(QLineEdit.EchoMode.Password)
            boton.setIcon(QIcon(self.ruta_ojo_cerrado))

    def _evaluar_seguridad_clave(self):
        clave = self.txt_pass1.text()
        conf = self.txt_pass2.text()

        # Criterios
        tiene_long = len(clave) >= 8
        tiene_mayus = bool(re.search(r'[A-Z]', clave)) and bool(re.search(r'[a-z]', clave))
        tiene_num = bool(re.search(r'[0-9]', clave))
        tiene_simb = bool(re.search(r'[!@#$%^&*(),.?":{}|<>\-_=+/\\;]', clave))

        # Actualizar Checklist visual
        self._set_check(self.lbl_req_longitud, tiene_long, "Mínimo 8 caracteres")
        self._set_check(self.lbl_req_mayus, tiene_mayus, "Mayúscula y minúscula")
        self._set_check(self.lbl_req_num, tiene_num, "Al menos un número")
        self._set_check(self.lbl_req_simbolo, tiene_simb, "Símbolo especial (!@#$%)")

        # Puntuación
        puntos = sum([tiene_long, tiene_mayus, tiene_num, tiene_simb])
        if not clave:
            self.barra_fuerza.setValue(0)
            self.lbl_fuerza_texto.setText("Seguridad: N/A")
            self.lbl_fuerza_texto.setStyleSheet("color: #64748B;")
        elif puntos <= 1:
            self.barra_fuerza.setValue(25)
            self.barra_fuerza.setStyleSheet("QProgressBar::chunk { background-color: #E74C3C; }")
            self.lbl_fuerza_texto.setText("Seguridad: Débil")
            self.lbl_fuerza_texto.setStyleSheet("color: #E74C3C;")
        elif puntos in (2, 3):
            self.barra_fuerza.setValue(65)
            self.barra_fuerza.setStyleSheet("QProgressBar::chunk { background-color: #F39C12; }")
            self.lbl_fuerza_texto.setText("Seguridad: Aceptable")
            self.lbl_fuerza_texto.setStyleSheet("color: #D35400;")
        else:
            self.barra_fuerza.setValue(100)
            self.barra_fuerza.setStyleSheet("QProgressBar::chunk { background-color: #27AE60; }")
            self.lbl_fuerza_texto.setText("Seguridad: Fuerte ✓")
            self.lbl_fuerza_texto.setStyleSheet("color: #1E8449;")

        # Coincidencia
        if not conf:
            self.lbl_coincidencia.setText("")
        elif clave == conf:
            self.lbl_coincidencia.setText("✓ Las contraseñas coinciden")
            self.lbl_coincidencia.setStyleSheet("color: #196F3D;")
        else:
            self.lbl_coincidencia.setText("✕ Las contraseñas no coinciden")
            self.lbl_coincidencia.setStyleSheet("color: #C0392B;")

    def _set_check(self, label, cumplido, texto):
        if cumplido:
            label.setText(f"✓ {texto}")
            label.setStyleSheet("color: #196F3D; font-weight: bold;")
        else:
            label.setText(f"• {texto}")
            label.setStyleSheet("color: #94A3B8;")

    def _ver_politica(self):
        from vista.modal_politica_datos import ModalPoliticaDatos
        modal = ModalPoliticaDatos(self)
        modal.exec()

    def _cambiar_paso(self, indice):
        self.stack.setCurrentIndex(indice)
        if indice == 0:
            self.lbl_stepper.setText("PASO 1 DE 2: DATOS DEL ESTUDIANTE")
        else:
            self.lbl_stepper.setText("PASO 2 DE 2: VERIFICACIÓN INSTITUCIONAL (OTP)")

    def _procesar_paso1_solicitud(self):
        nombre = self.txt_nombre.text().strip()
        apellidos = self.txt_apellidos.text().strip()
        cedula = self.txt_cedula.text().strip()
        email = self.txt_email.text().strip().lower()
        p1 = self.txt_pass1.text()
        p2 = self.txt_pass2.text()

        if not self.check_terminos.isChecked():
            QMessageBox.warning(self, "Términos Requeridos", 
                "Debes aceptar la Política de Protección de Datos Personales (Ley 1581) para registrarte.")
            return

        if not nombre or not apellidos or not cedula or not email or not p1 or not p2:
            QMessageBox.warning(self, "Campos Incompletos", "Por favor completa todos los campos obligatorios.")
            return

        if not email.endswith("@unicesar.edu.co") and not email.endswith("@gmail.com"):
            QMessageBox.warning(self, "Correo No Válido", 
                "El correo debe pertenecer al dominio institucional de la universidad:\n\n@unicesar.edu.co")
            return

        if len(cedula) < 6:
            QMessageBox.warning(self, "Cédula No Válida", "El documento debe tener al menos 6 dígitos numéricos.")
            return

        if len(p1) < 8:
            QMessageBox.warning(self, "Contraseña Insegura", "Por seguridad institucional, la contraseña debe contener al menos 8 caracteres.")
            return

        if p1 != p2:
            QMessageBox.warning(self, "Contraseña No Coincide", "Las contraseñas ingresadas no coinciden.")
            return

        self.btn_solicitar_otp.setEnabled(False)
        self.btn_solicitar_otp.setText("Enviando código al correo...")

        try:
            exito, mensaje = cliente_api.solicitar_codigo_registro(
                email=email,
                cedula=cedula,
                rol="ESTUDIANTE",
                nombre=f"{nombre} {apellidos}"
            )
            if exito:
                self.email_en_proceso = email
                self.lbl_correo_destino.setText(
                    f"Hemos enviado un código institucional de 6 dígitos a:\n<b>{email}</b>\n\n"
                    f"Revisa tu bandeja de entrada o spam e ingrésalo a continuación (expira en 10 min):"
                )
                self.txt_otp.clear()
                self._cambiar_paso(1)
                self.txt_otp.setFocus()
            else:
                QMessageBox.warning(self, "No se pudo continuar", mensaje)
        except Exception as e:
            QMessageBox.critical(self, "Error de Red", f"Ocurrió un error al procesar la solicitud: {str(e)}")
        finally:
            self.btn_solicitar_otp.setEnabled(True)
            self.btn_solicitar_otp.setText("Continuar y Enviar Código ➜")

    def _reenviar_codigo(self):
        if not self.email_en_proceso:
            return
        self.btn_reenviar.setEnabled(False)
        self.btn_reenviar.setText("Reenviando...")
        try:
            exito, mensaje = cliente_api.solicitar_codigo_registro(
                email=self.email_en_proceso,
                cedula=self.txt_cedula.text().strip(),
                rol="ESTUDIANTE",
                nombre=self.txt_nombre.text().strip()
            )
            if exito:
                QMessageBox.information(self, "Código Reenviado", "Se ha enviado un nuevo código a tu correo institucional.")
            else:
                QMessageBox.warning(self, "Error al Reenviar", mensaje)
        finally:
            self.btn_reenviar.setEnabled(True)
            self.btn_reenviar.setText("¿No recibiste el código? Reenviar código")

    def _procesar_paso2_confirmacion(self):
        codigo = self.txt_otp.text().strip()
        if len(codigo) != 6:
            QMessageBox.warning(self, "Código Incompleto", "Por favor ingresa el código completo de 6 dígitos.")
            return

        self.btn_confirmar_registro.setEnabled(False)
        self.btn_confirmar_registro.setText("Verificando...")

        try:
            exito, mensaje = cliente_api.confirmar_registro_estudiante(
                email=self.email_en_proceso,
                codigo_otp=codigo,
                nombre=self.txt_nombre.text().strip(),
                apellidos=self.txt_apellidos.text().strip(),
                cedula=self.txt_cedula.text().strip(),
                password=self.txt_pass1.text()
            )
            if exito:
                QMessageBox.information(
                    self, 
                    "¡Registro Exitoso!", 
                    "Tu cuenta de estudiante ha sido creada y activada exitosamente.\n\n"
                    "Ya puedes iniciar sesión con tu correo institucional y contraseña."
                )
                self.registro_completado.emit(self.email_en_proceso)
                self.accept()
            else:
                QMessageBox.warning(self, "Verificación Fallida", mensaje)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Ocurrió un error al verificar el código: {str(e)}")
        finally:
            self.btn_confirmar_registro.setEnabled(True)
            self.btn_confirmar_registro.setText("Verificar y Crear Cuenta ✓")
