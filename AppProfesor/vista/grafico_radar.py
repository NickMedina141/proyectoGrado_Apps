# vista/grafico_radar.py
# --------------------------------------------------------------------
# Gráfico de Radar / Telaraña Forense Interactivo para Análisis de Anomalías
# Desarrollado con QPainter nativo de alta resolución.
# Mapea con precisión matemática el porcentaje de incidencias de cada vector.
# Incluye interactividad (hover, tooltips, nodos reactivos) y gradientes modernos.
# Compatible automáticamente con temas claro y oscuro.
# --------------------------------------------------------------------

import math
from PyQt6.QtWidgets import QWidget, QSizePolicy, QToolTip
from PyQt6.QtGui import (
    QPainter, QColor, QPen, QBrush, QPolygonF, QFont,
    QPaintEvent, QMouseEvent, QLinearGradient
)
from PyQt6.QtCore import Qt, QPointF, QRectF


class GraficoRadar(QWidget):
    """
    Renderiza un gráfico de radar / telaraña interactivo para el Análisis de Anomalías.
    Cada eje representa el porcentaje real de incidencias capturado por el sistema:
    Arriba: Visión | Derecha: Procesos | Abajo: Teclado | Izquierda: Audio.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("grafico_radar_forense")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumSize(220, 200)
        self.setMaximumSize(300, 280)
        self.setMouseTracking(True)

        # Estructura de datos por vector
        self.datos = {
            "Visión": {"pct": 0, "alertas": 0},
            "Procesos": {"pct": 0, "alertas": 0},
            "Teclado": {"pct": 0, "alertas": 0},
            "Audio": {"pct": 0, "alertas": 0}
        }
        self.total_alertas = 0
        self.hovered_eje = None
        self.puntos_cache = {}  # Posición en pantalla de cada nodo para interacción táctil/ratón

    def actualizar_datos(self, anomalias_audio: int = 0, anomalias_vision: int = 0,
                         anomalias_procesos: int = 0, anomalias_teclado: int = 0,
                         pct_audio: int = 0, pct_vision: int = 0,
                         pct_procesos: int = 0, pct_teclado: int = 0,
                         total_alertas: int = 0):
        """
        Actualiza los porcentajes y conteos de anomalías de cada vector.
        El polígono escala dinámicamente destacando el vector predominante.
        """
        self.total_alertas = total_alertas
        self.datos["Audio"] = {"pct": max(0, pct_audio), "alertas": max(0, anomalias_audio)}
        self.datos["Visión"] = {"pct": max(0, pct_vision), "alertas": max(0, anomalias_vision)}
        self.datos["Procesos"] = {"pct": max(0, pct_procesos), "alertas": max(0, anomalias_procesos)}
        self.datos["Teclado"] = {"pct": max(0, pct_teclado), "alertas": max(0, anomalias_teclado)}
        self.update()

    def _es_modo_oscuro(self) -> bool:
        """Determina con certeza si la aplicación está en modo oscuro."""
        win = self.window()
        if hasattr(win, "modo_oscuro"):
            return bool(win.modo_oscuro)

        widget = self
        while widget:
            st = widget.styleSheet() or ""
            if "#1E293B" in st or "#0F172A" in st or "DARK MODE" in st:
                return True
            if "#F4F6F6" in st or "tema_claro" in st:
                return False
            widget = widget.parentWidget()

        return False

    def mouseMoveEvent(self, event: QMouseEvent):
        pos = event.position()
        detectado = None
        for eje, pt in self.puntos_cache.items():
            dist = math.hypot(pos.x() - pt.x(), pos.y() - pt.y())
            if dist <= 20:
                detectado = eje
                break

        if detectado != self.hovered_eje:
            self.hovered_eje = detectado
            if detectado:
                self.setCursor(Qt.CursorShape.PointingHandCursor)
                info = self.datos.get(detectado, {})
                pct = info.get("pct", 0)
                cnt = info.get("alertas", 0)
                plur = "s" if cnt != 1 else ""
                QToolTip.showText(
                    event.globalPosition().toPoint(),
                    f"<b>{detectado}</b><br>{cnt} alerta{plur} ({pct}% del total)",
                    self
                )
            else:
                self.setCursor(Qt.CursorShape.ArrowCursor)
            self.update()

        super().mouseMoveEvent(event)

    def leaveEvent(self, event):
        if self.hovered_eje is not None:
            self.hovered_eje = None
            self.setCursor(Qt.CursorShape.ArrowCursor)
            self.update()
        super().leaveEvent(event)

    def paintEvent(self, event: QPaintEvent):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        ancho = self.width()
        alto = self.height()
        cx = ancho / 2
        cy = alto / 2

        # Radio base disponible dejando márgenes proporcionados para etiquetas
        radio = min(cx - 62, cy - 32)
        if radio <= 20:
            return

        es_oscuro = self._es_modo_oscuro()

        # Paleta de colores visual moderna (Tecnología / Forense)
        color_rejilla = QColor("#334155") if es_oscuro else QColor("#D1D5DB")
        color_ejes = QColor("#475569") if es_oscuro else QColor("#9CA3AF")
        color_texto = QColor("#F8FAFC") if es_oscuro else QColor("#2C3E50")
        color_porcentaje = QColor("#A78BFA") if es_oscuro else QColor("#6D28D9")

        # Gradiente moderno Violeta Neón / Azul Tecnológico para el polígono
        gradiente = QLinearGradient(cx - radio, cy - radio, cx + radio, cy + radio)
        if es_oscuro:
            gradiente.setColorAt(0.0, QColor(139, 92, 246, 140))  # Violeta neón 55% opaco
            gradiente.setColorAt(1.0, QColor(59, 130, 246, 110))   # Azul eléctrico 45% opaco
            color_borde = QColor("#A78BFA")
            color_nodo_borde = QColor("#FFFFFF")
            color_nodo_centro = QColor("#8B5CF6")
        else:
            gradiente.setColorAt(0.0, QColor(124, 58, 237, 130))  # Púrpura profundo 50% opaco
            gradiente.setColorAt(1.0, QColor(37, 99, 235, 100))   # Azul cobalto 40% opaco
            color_borde = QColor("#7C3AED")
            color_nodo_borde = QColor("#FFFFFF")
            color_nodo_centro = QColor("#6D28D9")

        # Definición de los 4 ejes:
        # Arriba (-90°): Visión | Derecha (0°): Procesos | Abajo (90°): Teclado | Izquierda (180°): Audio
        ejes = [
            ("Visión", -90),
            ("Procesos", 0),
            ("Teclado", 90),
            ("Audio", 180)
        ]

        # 1. Dibujar anillos concéntricos de la telaraña (25%, 50%, 75%, 100%)
        pen_rejilla = QPen(color_rejilla, 1, Qt.PenStyle.DashLine)
        painter.setPen(pen_rejilla)
        painter.setBrush(Qt.BrushStyle.NoBrush)

        for nivel in [0.25, 0.50, 0.75, 1.0]:
            r_nivel = radio * nivel
            puntos_anillo = []
            for _, angulo in ejes:
                rad = math.radians(angulo)
                puntos_anillo.append(QPointF(cx + r_nivel * math.cos(rad), cy + r_nivel * math.sin(rad)))
            painter.drawPolygon(QPolygonF(puntos_anillo))

        # 2. Dibujar líneas de los 4 ejes cardinales
        painter.setPen(QPen(color_ejes, 1, Qt.PenStyle.SolidLine))
        for _, angulo in ejes:
            rad = math.radians(angulo)
            painter.drawLine(
                int(cx), int(cy),
                int(cx + radio * math.cos(rad)),
                int(cy + radio * math.sin(rad))
            )

        # 3. Calcular puntos del polígono con escalamiento dinámico y base visual
        puntos_datos = []
        self.puntos_cache.clear()

        # Determinar el porcentaje máximo de anomalías para normalizar
        max_pct = max((self.datos.get(eje, {}).get("pct", 0) for eje, _ in ejes), default=0)

        for nombre_eje, angulo in ejes:
            pct = self.datos.get(nombre_eje, {}).get("pct", 0)

            if self.total_alertas == 0 or max_pct == 0:
                proporcion = 0.20
            else:
                # Escalamiento dinámico con base:
                # - La anomalía predominante (max_pct) se proyecta al 92% del radio.
                # - Los vectores en 0% se repliegan limpiamente al núcleo base (20%).
                # - Los vectores intermedios se distribuyen proporcionalmente.
                ratio = pct / max_pct
                proporcion = 0.20 + (ratio * 0.72)

            r_dato = radio * proporcion
            rad = math.radians(angulo)
            pt = QPointF(cx + r_dato * math.cos(rad), cy + r_dato * math.sin(rad))
            puntos_datos.append(pt)
            self.puntos_cache[nombre_eje] = pt

        # 4. Dibujar el polígono de anomalías (si hay incidencias)
        if self.total_alertas > 0:
            poligono = QPolygonF(puntos_datos)
            painter.setBrush(QBrush(gradiente))
            painter.setPen(QPen(color_borde, 2.5))
            painter.drawPolygon(poligono)

            # 5. Dibujar los nodos en cada vértice (con efecto reactivo al pasar el ratón)
            for nombre_eje, pt in self.puntos_cache.items():
                es_hover = (nombre_eje == self.hovered_eje)
                radio_nodo = 7.0 if es_hover else 4.5

                if es_hover:
                    # Halo exterior brillante al pasar el ratón
                    halo_color = QColor(56, 189, 248, 160) if es_oscuro else QColor(2, 132, 199, 140)
                    painter.setBrush(QBrush(halo_color))
                    painter.setPen(Qt.PenStyle.NoPen)
                    painter.drawEllipse(pt, radio_nodo + 4.5, radio_nodo + 4.5)

                painter.setBrush(QBrush(color_nodo_centro))
                painter.setPen(QPen(color_nodo_borde, 2))
                painter.drawEllipse(pt, radio_nodo, radio_nodo)
        else:
            # Caso clase limpia (0 anomalías): indicador verde sutil en el centro
            color_limpio = QColor("#10B981") if es_oscuro else QColor("#059669")
            painter.setBrush(QBrush(QColor(16, 185, 129, 35)))
            painter.setPen(QPen(color_limpio, 1.5, Qt.PenStyle.DashLine))
            painter.drawEllipse(QPointF(cx, cy), radio * 0.20, radio * 0.20)

            painter.setBrush(QBrush(color_limpio))
            painter.setPen(QPen(QColor("#FFFFFF"), 2))
            painter.drawEllipse(QPointF(cx, cy), 5.5, 5.5)

        # 6. Etiquetas de los vértices (Nombre + Porcentaje en negrita)
        # Visión (Arriba)
        pct_vis = self.datos.get("Visión", {}).get("pct", 0)
        painter.setFont(QFont("Segoe UI", 9, QFont.Weight.DemiBold))
        painter.setPen(color_texto)
        painter.drawText(QRectF(cx - 60, cy - radio - 28, 120, 15), Qt.AlignmentFlag.AlignCenter, "👁️ Visión")
        painter.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        painter.setPen(color_porcentaje)
        painter.drawText(QRectF(cx - 60, cy - radio - 14, 120, 14), Qt.AlignmentFlag.AlignCenter, f"{pct_vis}%")

        # Procesos (Derecha)
        pct_proc = self.datos.get("Procesos", {}).get("pct", 0)
        painter.setFont(QFont("Segoe UI", 9, QFont.Weight.DemiBold))
        painter.setPen(color_texto)
        painter.drawText(QRectF(cx + radio + 6, cy - 14, 64, 15), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, "💻 Procesos")
        painter.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        painter.setPen(color_porcentaje)
        painter.drawText(QRectF(cx + radio + 6, cy + 1, 64, 14), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, f"{pct_proc}%")

        # Teclado (Abajo)
        pct_tec = self.datos.get("Teclado", {}).get("pct", 0)
        painter.setFont(QFont("Segoe UI", 9, QFont.Weight.DemiBold))
        painter.setPen(color_texto)
        painter.drawText(QRectF(cx - 60, cy + radio + 6, 120, 15), Qt.AlignmentFlag.AlignCenter, "⌨️ Teclado")
        painter.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        painter.setPen(color_porcentaje)
        painter.drawText(QRectF(cx - 60, cy + radio + 20, 120, 14), Qt.AlignmentFlag.AlignCenter, f"{pct_tec}%")

        # Audio (Izquierda)
        pct_aud = self.datos.get("Audio", {}).get("pct", 0)
        painter.setFont(QFont("Segoe UI", 9, QFont.Weight.DemiBold))
        painter.setPen(color_texto)
        painter.drawText(QRectF(cx - radio - 64, cy - 14, 58, 15), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, "🎙️ Audio")
        painter.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        painter.setPen(color_porcentaje)
        painter.drawText(QRectF(cx - radio - 64, cy + 1, 58, 14), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, f"{pct_aud}%")

