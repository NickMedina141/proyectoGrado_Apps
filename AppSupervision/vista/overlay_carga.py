# vista/overlay_carga.py
"""
Componente reutilizable de Spinner y Overlay de Carga para transiciones suaves y operaciones de red.
Diseño sobrio, elegante e institucional con la paleta de la UPC.
"""

from PyQt6.QtWidgets import QWidget, QFrame, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal, QRectF
from PyQt6.QtGui import QPainter, QPen, QColor, QFont


class WidgetSpinnerVectorial(QWidget):
    """
    Widget que dibuja un arco giratorio continuo a 60 FPS con QPainter.
    Color predeterminado: Verde Institucional UPC (#196F3D).
    """
    def __init__(self, color="#196F3D", radio=22, grosor=4, parent=None):
        super().__init__(parent)
        self.color = QColor(color)
        self.radio = radio
        self.grosor = grosor
        self.angulo = 0
        self.setFixedSize((radio + grosor + 4) * 2, (radio + grosor + 4) * 2)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._avanzar_angulo)
        self.timer.setInterval(16)  # ~60 FPS

    def iniciar(self):
        self.angulo = 0
        self.timer.start()

    def detener(self):
        self.timer.stop()

    def _avanzar_angulo(self):
        self.angulo = (self.angulo + 8) % 360
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect()
        cx = rect.width() / 2.0
        cy = rect.height() / 2.0

        # Pista de fondo muy tenue
        pen_pista = QPen(QColor(226, 232, 240, 160), self.grosor)
        painter.setPen(pen_pista)
        painter.drawEllipse(QRectF(cx - self.radio, cy - self.radio, self.radio * 2, self.radio * 2))

        # Arco giratorio en color principal
        pen = QPen(self.color, self.grosor)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)

        rect_arco = QRectF(cx - self.radio, cy - self.radio, self.radio * 2, self.radio * 2)
        angulo_inicio = self.angulo * 16
        angulo_span = 270 * 16
        painter.drawArc(rect_arco, angulo_inicio, angulo_span)


class HiloTrabajador(QThread):
    """
    Hilo auxiliar para ejecutar tareas pesadas o de red fuera del hilo GUI de Qt,
    garantizando que el spinner gire fluido a 60 FPS sin congelar la ventana.
    """
    senal_resultado = pyqtSignal(object)
    senal_error = pyqtSignal(str)

    def __init__(self, funcion, *args, **kwargs):
        super().__init__()
        self.funcion = funcion
        self.args = args
        self.kwargs = kwargs

    def run(self):
        try:
            res = self.funcion(*self.args, **self.kwargs)
            self.senal_resultado.emit(res)
        except Exception as e:
            self.senal_error.emit(str(e))


class OverlayCarga(QWidget):
    """
    Capa de bloqueo translúcida que cubre la ventana padre y muestra
    una tarjeta central sobria con el spinner vectorial y un mensaje dinámico.
    """
    def __init__(self, parent=None, color_spinner="#196F3D"):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)

        # Tarjeta central flotante
        self.tarjeta = QFrame(self)
        self.tarjeta.setObjectName("tarjeta_spinner_central")
        self.tarjeta.setStyleSheet("""
            QFrame#tarjeta_spinner_central {
                background-color: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 12px;
            }
        """)

        lay_tarjeta = QVBoxLayout(self.tarjeta)
        lay_tarjeta.setContentsMargins(32, 24, 32, 24)
        lay_tarjeta.setSpacing(14)
        lay_tarjeta.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.spinner = WidgetSpinnerVectorial(color=color_spinner, radio=22, grosor=4, parent=self.tarjeta)
        lay_tarjeta.addWidget(self.spinner, alignment=Qt.AlignmentFlag.AlignCenter)

        self.lbl_mensaje = QLabel("Cargando...", self.tarjeta)
        self.lbl_mensaje.setStyleSheet("font-size: 13px; font-weight: bold; color: #1A252F; font-family: 'Arial', 'Segoe UI', sans-serif;")
        self.lbl_mensaje.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay_tarjeta.addWidget(self.lbl_mensaje, alignment=Qt.AlignmentFlag.AlignCenter)

        self.tarjeta.adjustSize()
        self.hide()
        self.trabajador = None

        if parent:
            parent.installEventFilter(self)
            self._ajustar_a_padre()

    def eventFilter(self, obj, event):
        if obj == self.parent() and event.type() == event.Type.Resize:
            self._ajustar_a_padre()
        return super().eventFilter(obj, event)

    def _ajustar_a_padre(self):
        if self.parent():
            self.setGeometry(0, 0, self.parent().width(), self.parent().height())
            self.tarjeta.adjustSize()
            tx = (self.width() - self.tarjeta.width()) // 2
            ty = (self.height() - self.tarjeta.height()) // 2
            self.tarjeta.move(max(0, tx), max(0, ty))

    def paintEvent(self, event):
        painter = QPainter(self)
        # Velo blanco translúcido sobrio
        painter.fillRect(self.rect(), QColor(255, 255, 255, 185))

    def mostrar(self, mensaje="Cargando..."):
        self.lbl_mensaje.setText(mensaje)
        self._ajustar_a_padre()
        self.spinner.iniciar()
        self.show()
        self.raise_()
        from PyQt6.QtWidgets import QApplication
        QApplication.processEvents()

    def ocultar(self):
        self.spinner.detener()
        self.hide()

    def ejecutar_tarea(self, funcion, callback_exito, callback_error=None, mensaje="Cargando..."):
        """
        Ejecuta 'funcion' en segundo plano sin congelar la interfaz.
        Muestra el spinner mientras corre y llama a callback_exito(resultado) al finalizar.
        """
        self.mostrar(mensaje)
        self.trabajador = HiloTrabajador(funcion)

        def _al_terminar(resultado):
            self.ocultar()
            if callback_exito:
                callback_exito(resultado)

        def _al_fallar(err):
            self.ocultar()
            if callback_error:
                callback_error(err)
            else:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.critical(self.parent(), "Error de Comunicación", f"Ocurrió un problema de red: {err}")

        self.trabajador.senal_resultado.connect(_al_terminar)
        self.trabajador.senal_error.connect(_al_fallar)
        self.trabajador.start()
