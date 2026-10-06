# vista/modal_recuperar_clave.py
"""
Modal de Recuperación de Contraseña con Verificación OTP de Correo Electrónico
y medidor interactivo de fortaleza de clave.
Universidad Popular del Cesar - UPC Proctor.
"""

import os
import re
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QLineEdit, QStackedWidget, QWidget,
    QMessageBox, QFrame, QProgressBar
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread
from PyQt6.QtGui import QIcon, QFont, QIntValidator
from api.cliente_respuesta import cliente_api


class HiloRecuperacion(QThread):
    resultado_obtenido = pyqtSignal(bool, str)

    def __init__(self, funcion_tarea):
        super().__init__()
        self.funcion_tarea = funcion_tarea

    def run(self):
        try:
            exito, mensaje = self.funcion_tarea()
            self.resultado_obtenido.emit(exito, mensaje)
        except Exception as e:
            self.resultado_obtenido.emit(False, f"Error inesperado: {str(e)}")


class ModalRecuperarClave(QDialog):
    recuperacion_completada = pyqtSignal(str) # Emite el email restablecido

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(520, 600)
        self.setModal(True)
        self.setWindowTitle("UPC Proctor - Recuperación de Contraseña")

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
            QPushButton#btn_ojo {
                background-color: #F1F5F9;
                border: 1px solid #CBD5E1;
                border-radius: 6px;
            }
            QPushButton#btn_ojo:hover {
                background-color: #E2E8F0;
            }
        """)

        layout_principal = QVBoxLayout(self)
        layout_principal.setContentsMargins(28, 22, 28, 22)
        layout_principal.setSpacing(14)

        # Encabezado institucional
        layout_encabezado = QHBoxLayout()
        etiqueta_logo = QLabel("🔑")
        etiqueta_logo.setFont(QFont("Segoe UI Emoji", 24))
        etiqueta_logo.setFixedWidth(40)

        layout_titulos = QVBoxLayout()
        layout_titulos.setSpacing(2)
        titulo = QLabel("Recuperación de Contraseña")
        titulo.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold))
        titulo.setStyleSheet("color: #0F5132;")
        subtitulo = QLabel("Servicio de credenciales institucionales UPC Proctor")
        subtitulo.setFont(QFont("Segoe UI", 9))
        subtitulo.setStyleSheet("color: #64748B;")
        layout_titulos.addWidget(titulo)
        layout_titulos.addWidget(subtitulo)

        layout_encabezado.addWidget(etiqueta_logo)
        layout_encabezado.addLayout(layout_titulos)
        layout_principal.addLayout(layout_encabezado)

        linea_div = QFrame()
        linea_div.setFrameShape(QFrame.Shape.HLine)
        linea_div.setStyleSheet("color: #E2E8F0;")
        layout_principal.addWidget(linea_div)

        # Stack de pasos (Paso 1: Email, Paso 2: OTP + Nueva Clave)
        self.stack = QStackedWidget()
        self.paso1_widget = self._crear_paso1()
        self.paso2_widget = self._crear_paso2()
        self.stack.addWidget(self.paso1_widget)
        self.stack.addWidget(self.paso2_widget)
        layout_principal.addWidget(self.stack)

    # ================= PASO 1: SOLICITUD DE CÓDIGO =================
    def _crear_paso1(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.setSpacing(12)

        info = QLabel(
            "Ingresa tu correo institucional registrado. Te enviaremos un código de seguridad "
            "de 6 dígitos para validar tu identidad y restablecer tu clave."
        )
        info.setWordWrap(True)
        info.setStyleSheet("color: #475569; font-size: 12px; line-height: 1.4;")
        layout.addWidget(info)

        lbl_email = QLabel("Correo Institucional *")
        lbl_email.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        layout.addWidget(lbl_email)

        self.input_email = QLineEdit()
        self.input_email.setPlaceholderText("✉️ tu_correo@unicesar.edu.co")
        self.input_email.returnPressed.connect(self._solicitar_codigo)
        layout.addWidget(self.input_email)

        layout.addStretch()

        layout_botones = QHBoxLayout()
        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.setObjectName("btn_secundario")
        btn_cancelar.clicked.connect(self.reject)
        layout_botones.addWidget(btn_cancelar)

        self.btn_enviar_codigo = QPushButton("Enviar Código OTP")
        self.btn_enviar_codigo.setObjectName("btn_primario")
        self.btn_enviar_codigo.clicked.connect(self._solicitar_codigo)
        layout_botones.addWidget(self.btn_enviar_codigo)

        layout.addLayout(layout_botones)
        return widget

    # ================= PASO 2: VERIFICACIÓN Y NUEVA CLAVE =================
    def _crear_paso2(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 4, 0, 0)
        layout.setSpacing(8)

        self.lbl_destino = QLabel("Código enviado a:")
        self.lbl_destino.setWordWrap(True)
        self.lbl_destino.setStyleSheet("color: #196F3D; font-weight: bold; font-size: 11px;")
        layout.addWidget(self.lbl_destino)

        # Entrada OTP
        lbl_otp = QLabel("Código de Verificación (6 dígitos) *")
        lbl_otp.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        layout.addWidget(lbl_otp)

        self.input_otp = QLineEdit()
        self.input_otp.setPlaceholderText("Ej: 489201")
        self.input_otp.setMaxLength(6)
        self.input_otp.setValidator(QIntValidator(0, 999999, self))
        self.input_otp.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.input_otp.setStyleSheet("font-size: 17px; font-weight: bold; letter-spacing: 5px; color: #196F3D;")
        layout.addWidget(self.input_otp)

        # Entrada Nueva Contraseña con botón ojo
        lbl_pass = QLabel("Nueva Contraseña *")
        lbl_pass.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        layout.addWidget(lbl_pass)

        layout_pass = QHBoxLayout()
        layout_pass.setSpacing(6)
        self.input_pass = QLineEdit()
        self.input_pass.setEchoMode(QLineEdit.EchoMode.Password)
        self.input_pass.setPlaceholderText("Mínimo 8 caracteres seguros")
        self.input_pass.textChanged.connect(self._actualizar_medidor_fuerza)
        self.input_pass.textChanged.connect(self._verificar_coincidencia)

        self.btn_ojo_pass = QPushButton()
        self.btn_ojo_pass.setObjectName("btn_ojo")
        self.btn_ojo_pass.setFixedSize(36, 34)
        self.btn_ojo_pass.setCursor(Qt.CursorShape.PointingHandCursor)
        self._configurar_icono_ojo(self.btn_ojo_pass, self.ruta_ojo_cerrado)
        self.btn_ojo_pass.clicked.connect(lambda: self._alternar_ojo(self.input_pass, self.btn_ojo_pass))

        layout_pass.addWidget(self.input_pass)
        layout_pass.addWidget(self.btn_ojo_pass)
        layout.addLayout(layout_pass)

        # Medidor dinámico de fuerza de contraseña
        self.barra_fuerza = QProgressBar()
        self.barra_fuerza.setFixedHeight(5)
        self.barra_fuerza.setTextVisible(False)
        self.barra_fuerza.setRange(0, 4)
        self.barra_fuerza.setValue(0)
        self.barra_fuerza.setStyleSheet("""
            QProgressBar { background-color: #E2E8F0; border-radius: 2px; }
            QProgressBar::chunk { background-color: #CBD5E1; border-radius: 2px; }
        """)
        layout.addWidget(self.barra_fuerza)

        self.lbl_fuerza = QLabel("Seguridad: Pendiente")
        self.lbl_fuerza.setFont(QFont("Segoe UI", 8))
        self.lbl_fuerza.setStyleSheet("color: #64748B;")
        layout.addWidget(self.lbl_fuerza)

        # Checklist visual de requerimientos
        layout_checks = QVBoxLayout()
        layout_checks.setSpacing(2)
        self.chk_longitud = QLabel("• Mínimo 8 caracteres")
        self.chk_mayus_minus = QLabel("• Mayúsculas y minúsculas")
        self.chk_numero = QLabel("• Al menos un número")
        self.chk_especial = QLabel("• Carácter especial (@$!%*#?&)")
        for chk in [self.chk_longitud, self.chk_mayus_minus, self.chk_numero, self.chk_especial]:
            chk.setFont(QFont("Segoe UI", 8))
            chk.setStyleSheet("color: #94A3B8;")
            layout_checks.addWidget(chk)
        layout.addLayout(layout_checks)

        # Confirmar Contraseña con botón ojo
        lbl_conf = QLabel("Confirmar Nueva Contraseña *")
        lbl_conf.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        layout.addWidget(lbl_conf)

        layout_conf = QHBoxLayout()
        layout_conf.setSpacing(6)
        self.input_conf = QLineEdit()
        self.input_conf.setEchoMode(QLineEdit.EchoMode.Password)
        self.input_conf.setPlaceholderText("Repite tu nueva contraseña")
        self.input_conf.textChanged.connect(self._verificar_coincidencia)

        self.btn_ojo_conf = QPushButton()
        self.btn_ojo_conf.setObjectName("btn_ojo")
        self.btn_ojo_conf.setFixedSize(36, 34)
        self.btn_ojo_conf.setCursor(Qt.CursorShape.PointingHandCursor)
        self._configurar_icono_ojo(self.btn_ojo_conf, self.ruta_ojo_cerrado)
        self.btn_ojo_conf.clicked.connect(lambda: self._alternar_ojo(self.input_conf, self.btn_ojo_conf))

        layout_conf.addWidget(self.input_conf)
        layout_conf.addWidget(self.btn_ojo_conf)
        layout.addLayout(layout_conf)

        self.lbl_coincidencia = QLabel("")
        self.lbl_coincidencia.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        layout.addWidget(self.lbl_coincidencia)

        layout.addStretch()

        # Botones de acción del paso 2
        layout_botones = QHBoxLayout()
        btn_volver = QPushButton("Atrás")
        btn_volver.setObjectName("btn_secundario")
        btn_volver.clicked.connect(lambda: self.stack.setCurrentIndex(0))
        layout_botones.addWidget(btn_volver)

        self.btn_confirmar = QPushButton("Restablecer Contraseña")
        self.btn_confirmar.setObjectName("btn_primario")
        self.btn_confirmar.clicked.connect(self._confirmar_recuperacion)
        layout_botones.addWidget(self.btn_confirmar)

        layout.addLayout(layout_botones)
        return widget

    def _configurar_icono_ojo(self, boton, ruta_svg):
        if os.path.exists(ruta_svg):
            boton.setIcon(QIcon(ruta_svg))
            boton.setText("")
        else:
            boton.setText("👁️")

    def _alternar_ojo(self, input_widget, boton_widget):
        if input_widget.echoMode() == QLineEdit.EchoMode.Password:
            input_widget.setEchoMode(QLineEdit.EchoMode.Normal)
            self._configurar_icono_ojo(boton_widget, self.ruta_ojo_abierto)
        else:
            input_widget.setEchoMode(QLineEdit.EchoMode.Password)
            self._configurar_icono_ojo(boton_widget, self.ruta_ojo_cerrado)

    def _actualizar_medidor_fuerza(self, texto):
        tiene_longitud = len(texto) >= 8
        tiene_mayus_minus = bool(re.search(r'[A-Z]', texto)) and bool(re.search(r'[a-z]', texto))
        tiene_numero = bool(re.search(r'[0-9]', texto))
        tiene_especial = bool(re.search(r'[^A-Za-z0-9]', texto))

        # Actualizar checklist
        self._estilizar_check(self.chk_longitud, tiene_longitud, "Mínimo 8 caracteres")
        self._estilizar_check(self.chk_mayus_minus, tiene_mayus_minus, "Mayúsculas y minúsculas")
        self._estilizar_check(self.chk_numero, tiene_numero, "Al menos un número")
        self._estilizar_check(self.chk_especial, tiene_especial, "Carácter especial (@$!%*#?&)")

        puntos = sum([tiene_longitud, tiene_mayus_minus, tiene_numero, tiene_especial])
        self.barra_fuerza.setValue(puntos)

        if puntos == 0:
            color = "#CBD5E1"
            txt = "Pendiente"
            txt_color = "#64748B"
        elif puntos <= 2:
            color = "#EF4444"
            txt = "Débil"
            txt_color = "#DC2626"
        elif puntos == 3:
            color = "#F59E0B"
            txt = "Aceptable"
            txt_color = "#D97706"
        else:
            color = "#10B981"
            txt = "Fuerte y Segura"
            txt_color = "#059669"

        self.barra_fuerza.setStyleSheet(f"""
            QProgressBar {{ background-color: #E2E8F0; border-radius: 2px; }}
            QProgressBar::chunk {{ background-color: {color}; border-radius: 2px; }}
        """)
        self.lbl_fuerza.setText(f"Seguridad: {txt}")
        self.lbl_fuerza.setStyleSheet(f"color: {txt_color}; font-weight: bold;")

    def _estilizar_check(self, label, cumple, texto_base):
        if cumple:
            label.setText(f"✓ {texto_base}")
            label.setStyleSheet("color: #16A34A; font-weight: bold;")
        else:
            label.setText(f"• {texto_base}")
            label.setStyleSheet("color: #94A3B8;")

    def _verificar_coincidencia(self):
        p1 = self.input_pass.text()
        p2 = self.input_conf.text()
        if not p2:
            self.lbl_coincidencia.setText("")
            return
        if p1 == p2:
            self.lbl_coincidencia.setText("✓ Las contraseñas coinciden")
            self.lbl_coincidencia.setStyleSheet("color: #16A34A;")
        else:
            self.lbl_coincidencia.setText("✗ Las contraseñas no coinciden")
            self.lbl_coincidencia.setStyleSheet("color: #DC2626;")

    # ================= LLAMADAS A LA API =================
    def _solicitar_codigo(self):
        email = self.input_email.text().strip().lower()
        if not email:
            QMessageBox.warning(self, "Campo Vacío", "Por favor ingresa tu correo institucional.")
            return

        if not re.match(r'^[A-Za-z0-9._%+-]+@(unicesar\.edu\.co|gmail\.com)$', email):
            QMessageBox.warning(self, "Correo Inválido", "El correo debe pertenecer al dominio institucional (@unicesar.edu.co).")
            return

        self.btn_enviar_codigo.setEnabled(False)
        self.btn_enviar_codigo.setText("Enviando código...")

        def _tarea():
            return cliente_api.solicitar_codigo_recuperacion(email)

        self.hilo = HiloRecuperacion(_tarea)
        self.hilo.resultado_obtenido.connect(lambda exito, msg: self._al_solicitar_codigo(exito, msg, email))
        self.hilo.start()

    def _al_solicitar_codigo(self, exito, mensaje, email):
        self.btn_enviar_codigo.setEnabled(True)
        self.btn_enviar_codigo.setText("Enviar Código OTP")

        if exito:
            self.email_en_proceso = email
            self.lbl_destino.setText(f"Código enviado a: {email}")
            self.input_otp.clear()
            self.input_pass.clear()
            self.input_conf.clear()
            self.stack.setCurrentIndex(1)
            self.input_otp.setFocus()
            QMessageBox.information(
                self, "Código Enviado",
                f"Hemos enviado un código de 6 dígitos a:\n{email}\n\nRevisa tu bandeja de entrada o spam."
            )
        else:
            QMessageBox.critical(self, "Error al Enviar Código", mensaje)

    def _confirmar_recuperacion(self):
        otp = self.input_otp.text().strip()
        p1 = self.input_pass.text()
        p2 = self.input_conf.text()

        if not otp or len(otp) != 6:
            QMessageBox.warning(self, "Código Incompleto", "Por favor ingresa el código numérico de 6 dígitos.")
            return

        if len(p1) < 8:
            QMessageBox.warning(self, "Contraseña Débil", "La nueva contraseña debe tener al menos 8 caracteres.")
            return

        if p1 != p2:
            QMessageBox.warning(self, "Contraseñas Diferentes", "Las contraseñas no coinciden. Por favor verifícalas.")
            return

        self.btn_confirmar.setEnabled(False)
        self.btn_confirmar.setText("Actualizando contraseña...")

        def _tarea():
            return cliente_api.confirmar_recuperacion_password(self.email_en_proceso, otp, p1)

        self.hilo = HiloRecuperacion(_tarea)
        self.hilo.resultado_obtenido.connect(self._al_confirmar_recuperacion)
        self.hilo.start()

    def _al_confirmar_recuperacion(self, exito, mensaje):
        self.btn_confirmar.setEnabled(True)
        self.btn_confirmar.setText("Restablecer Contraseña")

        if exito:
            QMessageBox.information(
                self, "Contraseña Restablecida",
                "¡Tu contraseña ha sido actualizada con éxito!\nYa puedes iniciar sesión con tu nueva contraseña."
            )
            self.recuperacion_completada.emit(self.email_en_proceso)
            self.accept()
        else:
            QMessageBox.critical(self, "Error de Restablecimiento", mensaje)
