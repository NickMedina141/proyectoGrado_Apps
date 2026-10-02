# modal_chatbot.py
# --------------------------------------------------------------------
# Asistente Virtual del Panel Docente — Chatbot basado en reglas.
# El diseño se adapta al tema claro/oscuro mediante los archivos CSS.
# El contenido (preguntas/respuestas) se gestiona en base_conocimiento.py.
# --------------------------------------------------------------------

import re

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QScrollArea, QWidget, QSizePolicy,
    QFrame, QApplication
)
from PyQt6.QtCore import Qt, QTimer, QSize
from PyQt6.QtGui import QFont

from vista.base_conocimiento import MENU_PRINCIPAL, ARBOL, BIENVENIDA


# ─────────────────────────────────────────────────────────────────────
# Conversor Markdown → HTML para las burbujas del bot
# ─────────────────────────────────────────────────────────────────────

def _md_to_html(text: str) -> str:
    """
    Convierte el subconjunto de Markdown usado en base_conocimiento.py a HTML
    que entiende QLabel (RichText / Qt HTML subset).
    Opera línea a línea para manejar tablas y listas sin conflictos.
    """
    # 1. Separar por saltos de línea para procesar cada línea
    lines = text.split('\n')
    html_lines = []
    in_table = False

    for raw in lines:
        stripped = raw.strip()

        # ── Separadores de tabla (|---|---| → ignorar)
        if re.match(r'^\|[\-| ]+\|$', stripped):
            continue

        # ── Filas de tabla (| celda | celda |)
        if re.match(r'^\|.+\|$', stripped):
            if not in_table:
                html_lines.append('<table cellpadding="4" cellspacing="0" '
                                  'style="border-collapse:collapse;margin:4px 0;">')
                in_table = True
            cells = [c.strip() for c in stripped.strip('|').split('|')]
            row_html = '<tr>' + ''.join(
                '<td style="border:1px solid #ccc;padding:3px 8px;">'
                + _inline_md(c) + '</td>'
                for c in cells
            ) + '</tr>'
            html_lines.append(row_html)
            continue

        # Cerrar tabla si salimos de ella
        if in_table:
            html_lines.append('</table>')
            in_table = False

        # ── Bullet (• o -)
        m_bullet = re.match(r'^([•\-])\s+(.*)', raw)
        if m_bullet:
            html_lines.append(
                '&nbsp;&nbsp;&bull;&nbsp;' + _inline_md(m_bullet.group(2))
            )
            continue

        # ── Línea numerada (1. 2. ...)
        m_num = re.match(r'^(\d+)\.\s+(.*)', raw)
        if m_num:
            html_lines.append(
                '<b>' + m_num.group(1) + '.</b>&nbsp;' + _inline_md(m_num.group(2))
            )
            continue

        # ── Línea vacía → espacio vertical
        if stripped == '':
            html_lines.append('<br>')
            continue

        # ── Línea normal
        html_lines.append(_inline_md(raw))

    if in_table:
        html_lines.append('</table>')

    # Unir con <br>, evitando doble <br> junto a bloques de tabla
    result = []
    for i, part in enumerate(html_lines):
        result.append(part)
        # No añadir <br> después de filas de tabla o de <br> ya existente
        if not part.startswith('<tr') and not part.startswith('<table') \
                and not part.startswith('</table') and part != '<br>':
            result.append('<br>')

    return ''.join(result)


def _inline_md(text: str) -> str:
    """Aplica transformaciones inline: negrita, código."""
    # Escapar caracteres especiales HTML (solo en texto plano, no en HTML generado)
    text = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    # **negrita**
    text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
    # `código`
    text = re.sub(
        r'`([^`]+)`',
        r'<code style="background-color:#f0f0f0;padding:1px 5px;'
        r'border-radius:3px;font-family:Consolas,monospace;">\1</code>',
        text
    )
    return text


# ─────────────────────────────────────────────────────────────────────
# Widgets de burbuja
# ─────────────────────────────────────────────────────────────────────

class BurbujaWidget(QFrame):
    """
    Burbuja de chat individual.
    es_usuario=True  → alineada a la derecha, texto plano
    es_usuario=False → alineada a la izquierda, HTML enriquecido
    El color real lo pone el CSS a través de los objectName.
    """
    def __init__(self, texto: str, es_usuario: bool, parent=None):
        super().__init__(parent)
        self.setObjectName("burbuja_usuario" if es_usuario else "burbuja_bot")
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)

        lbl = QLabel()
        lbl.setObjectName("texto_burbuja")
        lbl.setWordWrap(True)
        lbl.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
        lbl.setMaximumWidth(440)
        lbl.setOpenExternalLinks(False)

        if es_usuario:
            # Burbujas del usuario: texto limpio, sin markdown
            lbl.setTextFormat(Qt.TextFormat.PlainText)
            lbl.setText(texto)
        else:
            # Burbujas del bot: renderizar markdown como HTML
            lbl.setTextFormat(Qt.TextFormat.RichText)
            lbl.setText(_md_to_html(texto))

        inner = QVBoxLayout(self)
        inner.setContentsMargins(14, 10, 14, 10)
        inner.addWidget(lbl)


# ─────────────────────────────────────────────────────────────────────
# Ventana principal del chatbot
# ─────────────────────────────────────────────────────────────────────

class ModalChatbot(QDialog):
    """
    Ventana modal del Asistente Virtual.
    Navega por el árbol de conocimiento definido en base_conocimiento.py.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Asistente Virtual")
        self.setObjectName("ModalChatbot")
        self.setModal(True)
        from PyQt6.QtWidgets import QApplication
        _screen = QApplication.primaryScreen().availableSize()
        _w = max(500, min(640, int(_screen.width() * 0.38)))
        _h = max(550, min(720, int(_screen.height() * 0.78)))
        self.setMinimumSize(_w, _h)
        self.resize(_w + 20, _h + 40)

        # Heredar el stylesheet de la ventana principal
        if parent and parent.styleSheet():
            self.setStyleSheet(parent.styleSheet())

        self._historial_nodos = []   # pila de navegación para el botón "Volver"
        self._construir_ui()
        self._mostrar_bienvenida()

    # ─────────────────────────────────────────────
    # Construcción de la interfaz
    # ─────────────────────────────────────────────

    def _construir_ui(self):
        root = QVBoxLayout(self)
        root.setSpacing(0)
        root.setContentsMargins(0, 0, 0, 0)

        # Cabecera
        header = QFrame()
        header.setObjectName("chatbot_header")
        header.setFixedHeight(64)
        hl = QHBoxLayout(header)
        hl.setContentsMargins(16, 0, 16, 0)

        icono = QLabel("🤖")
        icono.setFont(QFont("Segoe UI Emoji", 22))
        hl.addWidget(icono)

        txt_header = QVBoxLayout()
        lbl_nombre = QLabel("Asistente Virtual")
        lbl_nombre.setObjectName("chatbot_header_nombre")
        lbl_estado = QLabel("● En línea")
        lbl_estado.setObjectName("chatbot_header_estado")
        txt_header.addWidget(lbl_nombre)
        txt_header.addWidget(lbl_estado)
        hl.addLayout(txt_header)
        hl.addStretch()


        root.addWidget(header)

        # Separador
        sep = QFrame()
        sep.setObjectName("chatbot_separador")
        sep.setFixedHeight(1)
        root.addWidget(sep)

        # Área de chat (scroll)
        self.scroll = QScrollArea()
        self.scroll.setObjectName("chatbot_scroll")
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.contenedor_chat = QWidget()
        self.contenedor_chat.setObjectName("chatbot_contenedor")
        self.lay_chat = QVBoxLayout(self.contenedor_chat)
        self.lay_chat.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.lay_chat.setSpacing(8)
        self.lay_chat.setContentsMargins(16, 16, 16, 16)

        self.scroll.setWidget(self.contenedor_chat)
        root.addWidget(self.scroll, 1)

        # Separador
        sep2 = QFrame()
        sep2.setObjectName("chatbot_separador")
        sep2.setFixedHeight(1)
        root.addWidget(sep2)

        # Panel de botones de opciones
        self.panel_opciones = QWidget()
        self.panel_opciones.setObjectName("chatbot_panel_opciones")
        self.lay_opciones = QVBoxLayout(self.panel_opciones)
        self.lay_opciones.setSpacing(6)
        self.lay_opciones.setContentsMargins(16, 12, 16, 12)
        root.addWidget(self.panel_opciones)

    # ─────────────────────────────────────────────
    # Lógica de navegación
    # ─────────────────────────────────────────────

    def _mostrar_bienvenida(self):
        self._limpiar_opciones()
        self._agregar_burbuja_bot(BIENVENIDA)
        QTimer.singleShot(300, self._mostrar_menu_principal)

    def _mostrar_menu_principal(self):
        self._historial_nodos.clear()
        self._limpiar_opciones()
        self._render_menu(MENU_PRINCIPAL["opciones"], incluir_volver=False)

    def _mostrar_nodo(self, nodo_id: str, desde_menu: bool = False):
        nodo = ARBOL.get(nodo_id)
        if not nodo:
            return

        if "opciones" in nodo:
            # Es un submenú: el usuario seleccionó una categoría
            self._limpiar_opciones()
            self._agregar_burbuja_bot(nodo.get("intro", nodo["titulo"]))
            QTimer.singleShot(200, lambda: self._render_menu(nodo["opciones"], incluir_volver=True))
        else:
            # Es una hoja: el usuario seleccionó una pregunta
            respuesta = nodo.get("respuesta", "")
            self._agregar_burbuja_bot(respuesta)
            self._limpiar_opciones()
            QTimer.singleShot(200, self._render_botones_post_respuesta)

    def _render_menu(self, opciones: list, incluir_volver: bool):
        self._limpiar_opciones()
        for op in opciones:
            btn = self._crear_boton_opcion(op["etiqueta"])
            nodo_destino = op["nodo"]
            btn.clicked.connect(lambda checked, n=nodo_destino, e=op["etiqueta"]: self._on_opcion(n, e))
            self.lay_opciones.addWidget(btn)

        if incluir_volver:
            btn_volver = self._crear_boton_volver()
            self.lay_opciones.addWidget(btn_volver)

    def _render_botones_post_respuesta(self):
        self._limpiar_opciones()
        # Determinar el nodo padre (submenú) para volver a él
        nodo_padre = self._historial_nodos[-1] if self._historial_nodos else None

        if nodo_padre:
            btn_repetir = self._crear_boton_opcion("🔄  Hacer otra pregunta de este tema")
            btn_repetir.clicked.connect(lambda: self._mostrar_nodo(nodo_padre))
            self.lay_opciones.addWidget(btn_repetir)

        btn_inicio = self._crear_boton_opcion("🏠  Volver al menú principal")
        btn_inicio.clicked.connect(self._mostrar_menu_principal)
        self.lay_opciones.addWidget(btn_inicio)

    def _on_opcion(self, nodo_id: str, etiqueta: str):
        # El usuario hizo clic en una opción: agregar burbuja de usuario
        self._agregar_burbuja_usuario(etiqueta)
        nodo = ARBOL.get(nodo_id)

        if nodo and "opciones" in nodo:
            # Es un submenú → guardar en historial
            self._historial_nodos.append(nodo_id)

        # Simular efecto de escritura con pequeño delay
        QTimer.singleShot(400, lambda: self._mostrar_nodo(nodo_id))

    # ─────────────────────────────────────────────
    # Helpers de UI
    # ─────────────────────────────────────────────

    def _agregar_burbuja_usuario(self, texto: str):
        fila = QHBoxLayout()
        fila.addStretch()
        burbuja = BurbujaWidget(texto, es_usuario=True)
        fila.addWidget(burbuja)
        wrapper = QWidget()
        wrapper.setLayout(fila)
        self.lay_chat.addWidget(wrapper)
        self._scroll_abajo()

    def _agregar_burbuja_bot(self, texto: str):
        fila = QHBoxLayout()
        burbuja = BurbujaWidget(texto, es_usuario=False)
        fila.addWidget(burbuja)
        fila.addStretch()
        wrapper = QWidget()
        wrapper.setLayout(fila)
        self.lay_chat.addWidget(wrapper)
        self._scroll_abajo()

    def _crear_boton_opcion(self, texto: str) -> QPushButton:
        btn = QPushButton(texto)
        btn.setObjectName("chatbot_btn_opcion")
        btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        btn.setFixedHeight(38)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        return btn

    def _crear_boton_volver(self) -> QPushButton:
        btn = QPushButton("← Volver al menú principal")
        btn.setObjectName("chatbot_btn_volver")
        btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        btn.setFixedHeight(36)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.clicked.connect(self._mostrar_menu_principal)
        return btn

    def _limpiar_opciones(self):
        while self.lay_opciones.count():
            item = self.lay_opciones.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _scroll_abajo(self):
        QTimer.singleShot(50, lambda: self.scroll.verticalScrollBar().setValue(
            self.scroll.verticalScrollBar().maximum()
        ))
