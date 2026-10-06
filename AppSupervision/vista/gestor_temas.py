import os
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QObject, pyqtSignal

class GestorTemas(QObject):
    """
    Administra el cambio dinámico entre el Tema Claro y el Tema Oscuro,
    notificando a los componentes suscritos mediante señales de PyQt6.
    """
    tema_cambiado = pyqtSignal(str) # Emite 'claro' u 'oscuro'

    def __init__(self, aplicacion: QApplication):
        super().__init__()
        self.app = aplicacion
        self.tema_actual = "claro"
        self.ruta_base = os.path.dirname(__file__)
        self.aplicar_tema_claro()

    def alternar_tema(self):
        if self.tema_actual == "claro":
            self.aplicar_tema_oscuro()
        else:
            self.aplicar_tema_claro()

    def aplicar_tema_claro(self):
        self.tema_actual = "claro"
        ruta = os.path.join(self.ruta_base, "tema_claro.css")
        self._cargar_css(ruta)
        self.tema_cambiado.emit("claro")

    def aplicar_tema_oscuro(self):
        self.tema_actual = "oscuro"
        ruta = os.path.join(self.ruta_base, "tema_oscuro.css")
        self._cargar_css(ruta)
        self.tema_cambiado.emit("oscuro")

    def _cargar_css(self, ruta_archivo):
        try:
            with open(ruta_archivo, "r", encoding="utf-8") as f:
                self.app.setStyleSheet(f.read())
        except Exception as e:
            print(f"Error al cargar el tema {ruta_archivo}: {e}")
