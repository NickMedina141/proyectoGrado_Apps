
import os
from PyQt6.QtWidgets import QApplication

class GestorTemas:
  """
  Administra el cambio entre el Tema Claro y el Tema Oscuro.
  """
  def __init__(self, aplicacion: QApplication):
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

  def aplicar_tema_oscuro(self):
    self.tema_actual = "oscuro"
    ruta = os.path.join(self.ruta_base, "tema_oscuro.css")
    self._cargar_css(ruta)

  def _cargar_css(self, ruta_archivo):
    try:
      with open(ruta_archivo, "r", encoding="utf-8") as f:
        self.app.setStyleSheet(f.read())
    except Exception as e:
      print(f"Error al cargar el tema {ruta_archivo}: {e}")
