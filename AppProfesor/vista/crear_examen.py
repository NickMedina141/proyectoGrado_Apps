import os
from PyQt6.QtWidgets import QWidget, QMessageBox
from PyQt6.QtCore import pyqtSignal, QDate, QTime
from PyQt6 import uic

class CrearExamen(QWidget):
  cancelado = pyqtSignal()
  siguiente = pyqtSignal(dict)

  def __init__(self):
    super().__init__()
    
    base_path = os.path.dirname(__file__)
    uic.loadUi(os.path.join(base_path, "crear_examen.xml"), self)
    
    # Conectar botones
    self.btn_cancelar.clicked.connect(self.emitir_cancelar)
    self.btn_siguiente.clicked.connect(self.procesar_siguiente)
    
    # Valores por defecto
    self.entrada_fecha.setDate(QDate.currentDate())
    if hasattr(self, 'entrada_fecha_fin'):
        self.entrada_fecha_fin.setDate(QDate.currentDate())
    self._set_hora(QTime.currentTime())
    
  def limpiar_formulario(self):
    self.entrada_materia.clear()
    self.entrada_fecha.setDate(QDate.currentDate())
    if hasattr(self, 'entrada_fecha_fin'):
        self.entrada_fecha_fin.setDate(QDate.currentDate())
    self._set_hora(QTime.currentTime())
    self.entrada_duracion.setValue(60)

  def emitir_cancelar(self):
    # Limpiar formulario
    self.limpiar_formulario()
    self.cancelado.emit()

  def _set_hora(self, qtime):
    # Convertir a 12 horas y AM/PM
    hour12 = qtime.hour() % 12
    if hour12 == 0: hour12 = 12
    self.entrada_hora_texto.setTime(QTime(hour12, qtime.minute()))
    self.entrada_hora_ampm.setCurrentText("PM" if qtime.hour() >= 12 else "AM")

  def _get_hora_string(self):
    hora = self.entrada_hora_texto.time()
    is_pm = self.entrada_hora_ampm.currentText() == "PM"
    h = hora.hour()
    if is_pm and h < 12: h += 12
    elif not is_pm and h == 12: h = 0
    return f"{h:02d}:{hora.minute():02d}"

  def procesar_siguiente(self):
    materia = self.entrada_materia.text().strip()
    fecha = self.entrada_fecha.date().toString("yyyy-MM-dd")
    fecha_fin = self.entrada_fecha_fin.date().toString("yyyy-MM-dd") if hasattr(self, 'entrada_fecha_fin') else fecha
    hora = self._get_hora_string()
    duracion = self.entrada_duracion.value()
    
    if not materia:
      QMessageBox.warning(self, "Campos Incompletos", "Por favor, ingrese el nombre de la materia.")
      return
      
    # Agrupar los datos en un diccionario para mandarlos al Paso 2
    datos_examen = {
      "materia": materia,
      "fecha": fecha,
      "fecha_fin": fecha_fin,
      "hora": hora,
      "duracion": duracion
    }
    
    # Emitimos la señal con los datos para ir al paso 2
    self.siguiente.emit(datos_examen)
