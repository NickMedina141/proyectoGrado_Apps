# vista/modal_politica_datos.py
"""
Modal Institucional de Política de Tratamiento de Datos Personales y Biométricos.
Alineado con la Ley Estatutaria 1581 de 2012 y el Decreto 1377 de 2013 (Colombia).
Diseño sobrio, institucional y elegante con la identidad visual de la UPC.
"""

import os
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTextBrowser, QFrame
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon, QFont


class ModalPoliticaDatos(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(650, 580)
        self.setModal(True)
        self.setWindowTitle("UPC SecureExam - Política de Protección de Datos (Ley 1581)")
        
        # Ícono institucional
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        ruta_ico = os.path.join(base_dir, "recursos", "installer_icon.ico")
        ruta_png = os.path.join(os.path.dirname(__file__), "recursos", "logo_upc.png")
        ruta_icono = ruta_ico if os.path.exists(ruta_ico) else ruta_png
        if os.path.exists(ruta_icono):
            self.setWindowIcon(QIcon(ruta_icono))

        self._construir_ui()

    def _construir_ui(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #FFFFFF;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QTextBrowser {
                background-color: #F8FAFC;
                border: 1px solid #E2E8F0;
                border-radius: 8px;
                padding: 16px;
                color: #2D3748;
                font-size: 13px;
                line-height: 1.5;
            }
            QPushButton#btn_cerrar_politica {
                background-color: #196F3D;
                color: #FFFFFF;
                font-weight: bold;
                font-size: 13px;
                border-radius: 6px;
                padding: 10px 24px;
                min-width: 140px;
                border: none;
            }
            QPushButton#btn_cerrar_politica:hover {
                background-color: #145A32;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)

        # Encabezado institucional
        header_layout = QHBoxLayout()
        header_layout.setSpacing(14)

        logo_path = os.path.join(os.path.dirname(__file__), "recursos", "logo_upc.png").replace("\\", "/")
        lbl_logo = QLabel()
        lbl_logo.setFixedSize(48, 48)
        if os.path.exists(logo_path):
            lbl_logo.setStyleSheet(f"border-image: url('{logo_path}');")
        else:
            lbl_logo.setText("🏛️")
            lbl_logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(lbl_logo)

        titulos_layout = QVBoxLayout()
        titulos_layout.setSpacing(2)

        lbl_tit = QLabel("Política de Tratamiento de Datos Personales y Biométricos")
        lbl_tit.setStyleSheet("font-size: 16px; font-weight: bold; color: #196F3D;")
        titulos_layout.addWidget(lbl_tit)

        lbl_sub = QLabel("Universidad Popular del Cesar | Ley 1581 de 2012 y Decreto 1377 de 2013")
        lbl_sub.setStyleSheet("font-size: 12px; color: #64748B;")
        titulos_layout.addWidget(lbl_sub)

        header_layout.addLayout(titulos_layout)
        header_layout.addStretch()
        layout.addLayout(header_layout)

        # Separador fino
        linea = QFrame()
        linea.setFrameShape(QFrame.Shape.HLine)
        linea.setFrameShadow(QFrame.Shadow.Plain)
        linea.setStyleSheet("color: #E2E8F0; background-color: #E2E8F0; height: 1px;")
        layout.addWidget(linea)

        # Contenido legal scrollable
        self.browser = QTextBrowser()
        self.browser.setOpenExternalLinks(True)
        self.browser.setHtml(self._obtener_texto_legal())
        layout.addWidget(self.browser)

        # Botón de cierre
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.btn_cerrar = QPushButton("Entendido y Cerrar")
        self.btn_cerrar.setObjectName("btn_cerrar_politica")
        self.btn_cerrar.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_cerrar.clicked.connect(self.accept)
        btn_layout.addWidget(self.btn_cerrar)
        layout.addLayout(btn_layout)

    def _obtener_texto_legal(self):
        return """
        <h3 style="color: #196F3D; margin-top: 0px;">1. Marco Normativo y Responsable del Tratamiento</h3>
        <p>En cumplimiento de la <b>Ley Estatutaria 1581 de 2012</b>, el <b>Decreto Reglamentario 1377 de 2013</b> y demás normas concordantes sobre protección de datos personales en la República de Colombia, la <b>Universidad Popular del Cesar (UPC)</b>, identificada como Responsable del Tratamiento, informa a la comunidad estudiantil las condiciones de tratamiento de los datos recolectados a través de la plataforma <b>UPC SecureExam</b>.</p>

        <h3 style="color: #196F3D;">2. Naturaleza de los Datos Tratados (Datos Sensibles)</h3>
        <p>Durante la sesión de examen supervisada, el sistema recolecta y procesa datos catalogados como <b>sensibles</b> (Art. 5 y 6, Ley 1581/2012):</p>
        <ul>
            <li><b>Datos Biométricos Faciales:</b> Captura de imagen facial, vectores matemáticos de rasgos antropométricos (embeddings) y orientación de la mirada para verificación de identidad y detección de suplantación.</li>
            <li><b>Datos Acústicos:</b> Detección de actividad de voz ambiental (VAD) mediante el micrófono con el fin exclusivo de registrar evidencias ante posibles comunicaciones no autorizadas.</li>
            <li><b>Datos de Entorno y Conectividad:</b> Dirección IP de conexión, estado de la red (verificación de ausencia de túneles VPN) y coordenadas de geolocalización aproximada para asegurar la pertenencia geográfica del evaluado.</li>
        </ul>

        <h3 style="color: #196F3D;">3. Finalidad Estricta del Tratamiento</h3>
        <p>Los datos personales y biométricos serán tratados con el <b>único y exclusivo fin de garantizar la autenticidad, transparencia y validez académica</b> de las evaluaciones virtuales programadas por la institución. Bajo ninguna circunstancia estos datos serán comercializados, transferidos ni cedidos a terceros con fines comerciales o de lucro.</p>

        <h3 style="color: #196F3D;">4. Privacidad por Diseño y Seguridad Técnica</h3>
        <p>La plataforma incorpora principios de <i>Privacy by Design</i>:</p>
        <ul>
            <li>El procesamiento de los vectores de inteligencia artificial se ejecuta de forma <b>local en la máquina del estudiante</b>.</li>
            <li>Las evidencias transmitidas hacia el servidor institucional viajan cifradas bajo canales seguros (TLS/HTTPS y cifrado de carga útil).</li>
            <li>Las evidencias se conservan únicamente durante el periodo legal de auditoría y apelación de calificaciones establecido en el reglamento estudiantil de la UPC.</li>
        </ul>

        <h3 style="color: #196F3D;">5. Derechos del Titular (Habeas Data)</h3>
        <p>De conformidad con el artículo 8 de la Ley 1581 de 2012, el titular de los datos tiene derecho a:</p>
        <ul>
            <li>Conocer, actualizar y rectificar sus datos personales frente a la institución.</li>
            <li>Solicitar prueba de la autorización otorgada para el tratamiento.</li>
            <li>Ser informado respecto del uso que se le ha dado a sus datos personales.</li>
            <li>Presentar quejas ante la Superintendencia de Industria y Comercio (SIC) por infracciones a la ley.</li>
        </ul>

        <h3 style="color: #196F3D;">6. Carácter Facultativo y Alternativa Presencial</h3>
        <p>Por tratarse de datos sensibles, el otorgamiento de la autorización es de carácter <b>voluntario</b>. En el evento en que el estudiante decida no autorizar el tratamiento biométrico remoto o no disponga de los requerimientos técnicos requeridos (cámara o micrófono funcional), <b>asistirá a su derecho de solicitar la presentación de su evaluación en modalidad presencial tradicional</b> en las salas de cómputo o aulas asignadas por su facultad en la Universidad Popular del Cesar.</p>
        """
