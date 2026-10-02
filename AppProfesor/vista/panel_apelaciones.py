import os
import math
from PyQt6.QtWidgets import QComboBox, QWidget, QMessageBox, QTableWidgetItem, QHBoxLayout, QLabel, QPushButton, QInputDialog, QHeaderView
from PyQt6.QtCore import Qt
from PyQt6 import uic
from utils.gestor_sesion import sesion_actual
from api.cliente_respuesta import cliente_api

class PanelApelaciones(QWidget):
  def __init__(self):
    super().__init__()
    base_path = os.path.dirname(__file__)
    uic.loadUi(os.path.join(base_path, "panel_apelaciones.xml"), self)
    
    self.todas_las_apelaciones = []
    self.apelaciones_filtradas = []
    self.pagina_actual = 1
    
    # Crear filtro combo
    self.combo_filtro = QComboBox()
    self.combo_filtro.addItems(["Todos", "Pendientes", "Aprobados", "Rechazados"])
    self.combo_filtro.setObjectName("combo_filtro")
    self.combo_filtro.currentIndexChanged.connect(self.aplicar_filtro)
    
    # Add to layout_cuerpo if exists
    if hasattr(self, 'layout_cuerpo'):
        top_h_lay = QHBoxLayout()
        title_item = self.layout_cuerpo.takeAt(0)
        top_h_lay.addItem(title_item)
        top_h_lay.addStretch()
        
        lbl = QLabel("Filtrar:")
        lbl.setObjectName("lbl_filtrar_apelaciones")
        top_h_lay.addWidget(lbl)
        
        self.combo_filtro.setMinimumHeight(35)
        self.combo_filtro.setStyleSheet("QComboBox { padding: 5px; border: 1px solid #BDC3C7; border-radius: 4px; font-size: 13px; }")
        top_h_lay.addWidget(self.combo_filtro)
        
        self.layout_cuerpo.insertLayout(0, top_h_lay)
    
    self.elementos_por_pagina = 6
    
    self.btn_pag_prev.clicked.connect(self.pagina_anterior)
    self.btn_pag_next.clicked.connect(self.pagina_siguiente)
    
    self.cargar_apelaciones_reales()



  def cargar_apelaciones_reales(self):
    self.todas_las_apelaciones = []
    profesor_id = sesion_actual.obtener_profesor_id()
    if not profesor_id:
      return
      
    exito, datos = cliente_api.obtener_apelaciones_pendientes(profesor_id)
    
    if exito and isinstance(datos, list):
      self.todas_las_apelaciones = datos
      
    self.aplicar_filtro()

  def aplicar_filtro(self):
    filtro = self.combo_filtro.currentText()
    if filtro == "Todos":
        self.apelaciones_filtradas = self.todas_las_apelaciones
    elif filtro == "Pendientes":
        self.apelaciones_filtradas = [a for a in self.todas_las_apelaciones if a.get("apelacion", {}).get("estadoApelacion", "EN_REVISION") in ("PENDIENTE", "EN_REVISION")]
    elif filtro == "Aprobados":
        self.apelaciones_filtradas = [a for a in self.todas_las_apelaciones if a.get("apelacion", {}).get("estadoApelacion") == "APROBADA"]
    elif filtro == "Rechazados":
        self.apelaciones_filtradas = [a for a in self.todas_las_apelaciones if a.get("apelacion", {}).get("estadoApelacion") == "RECHAZADA"]
    self.pagina_actual = 1
    self.renderizar_pagina()

  def renderizar_pagina(self):
    self.tabla_apelaciones.setColumnWidth(0, 180) 
    self.tabla_apelaciones.setColumnWidth(1, 180)
    self.tabla_apelaciones.setColumnWidth(2, 110)
    self.tabla_apelaciones.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
    self.tabla_apelaciones.setColumnWidth(4, 110)
    self.tabla_apelaciones.setColumnWidth(5, 260)
    
    self.tabla_apelaciones.verticalHeader().setVisible(False)
    self.tabla_apelaciones.verticalHeader().setDefaultSectionSize(65)
    self.tabla_apelaciones.setFocusPolicy(Qt.FocusPolicy.NoFocus)
    
    total_elementos = len(self.apelaciones_filtradas)
    
    self.tabla_apelaciones.setVisible(True)
    self.frame_paginacion.setVisible(total_elementos>0)
    self.etiqueta_vacia.setVisible(False)
    
    if total_elementos == 0:
      self.tabla_apelaciones.setRowCount(0)
      self.tabla_apelaciones.setRowCount(1)
      self.tabla_apelaciones.setColumnCount(6)
      self.tabla_apelaciones.clearSpans()
      self.tabla_apelaciones.setSpan(0, 0, 1, 6)
      
      texto_vacio = "No existen segundas revisiones "
      filtro_actual = self.combo_filtro.currentText()
      if filtro_actual == "Pendientes":
          texto_vacio += "pendientes"
      elif filtro_actual == "Aprobados":
          texto_vacio += "aprobadas"
      elif filtro_actual == "Rechazados":
          texto_vacio += "rechazadas"
      else:
          texto_vacio = "No existen segundas revisiones registradas"
      item_vacio = QTableWidgetItem(texto_vacio)
      item_vacio.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
      # Aplicamos estilo gris claro cursiva simulando la etiqueta_vacia
      font = item_vacio.font()
      font.setItalic(True)
      font.setPointSize(12)
      item_vacio.setFont(font)
      
      from PyQt6.QtGui import QColor, QBrush
      item_vacio.setForeground(QBrush(QColor("#7F8C8D")))
      
      self.tabla_apelaciones.setItem(0, 0, item_vacio)
      return
      
    self.tabla_apelaciones.clearSpans()
    
    total_paginas = max(1, math.ceil(total_elementos / self.elementos_por_pagina))
    self.lbl_paginacion.setText(f"{self.pagina_actual} / {total_paginas}")
    
    self.btn_pag_prev.setEnabled(self.pagina_actual>1)
    self.btn_pag_next.setEnabled(self.pagina_actual < total_paginas)
    
    inicio = (self.pagina_actual - 1) * self.elementos_por_pagina
    fin = inicio + self.elementos_por_pagina
    apelaciones_pagina = self.apelaciones_filtradas[inicio:fin]
    
    self.tabla_apelaciones.setRowCount(0)
    self.tabla_apelaciones.setRowCount(len(apelaciones_pagina))
    
    for fila, sesion in enumerate(apelaciones_pagina):
      id_apelacion = sesion.get("sesionId") or sesion.get("id") or "---"
      estudiante_id = sesion.get("estudianteId", "Desconocido")
      estudiante_nombre = sesion.get("nombreEstudiante") or estudiante_id
      examen = sesion.get("examenId", "---")
      
      apelacion_obj = sesion.get("apelacion", {})
      motivo = apelacion_obj.get("argumentoEstudiante", "Sin argumento")
      estado = apelacion_obj.get("estadoApelacion", "EN_REVISION")

      # Mostrar el ID del estudiante en la columna ID, y el nombre real en la columna Estudiante
      item_id = QTableWidgetItem(estudiante_id)
      item_id.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
      self.tabla_apelaciones.setItem(fila, 0, item_id)
      
      item_est = QTableWidgetItem(estudiante_nombre)
      item_est.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
      self.tabla_apelaciones.setItem(fila, 1, item_est)
      
      item_exa = QTableWidgetItem(examen)
      item_exa.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
      self.tabla_apelaciones.setItem(fila, 2, item_exa)
      
      item_mot = QTableWidgetItem(motivo[:30] + "..." if len(motivo)>30 else motivo)
      item_mot.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
      self.tabla_apelaciones.setItem(fila, 3, item_mot)
      
      widget_estado = QWidget()
      layout_estado = QHBoxLayout(widget_estado)
      layout_estado.setContentsMargins(0, 0, 0, 0)
      
      lbl_pendiente = QLabel()
      lbl_pendiente.setAlignment(Qt.AlignmentFlag.AlignCenter)
      if estado == "APROBADA_A_FAVOR":
          lbl_pendiente.setText("Aprobada")
          lbl_pendiente.setStyleSheet("color: #27AE60; font-weight: bold; font-size: 14px;")
      elif estado == "RECHAZADA_FRAUDE_MANTENIDO":
          lbl_pendiente.setText("Rechazada")
          lbl_pendiente.setStyleSheet("color: #E74C3C; font-weight: bold; font-size: 14px;")
      else:
          lbl_pendiente.setText("Pendiente")
          lbl_pendiente.setStyleSheet("color: #F39C12; font-weight: bold; font-size: 14px;")
      
      layout_estado.addWidget(lbl_pendiente)
      layout_estado.setAlignment(Qt.AlignmentFlag.AlignCenter)
      self.tabla_apelaciones.setCellWidget(fila, 4, widget_estado)
      
      widget_acciones = QWidget()
      layout_acc = QHBoxLayout(widget_acciones)
      layout_acc.setContentsMargins(0, 0, 0, 0)
      layout_acc.setSpacing(10)
      layout_acc.setAlignment(Qt.AlignmentFlag.AlignCenter)
      
      btn_ver = QPushButton("Ver Evidencia")
      btn_ver.setCursor(Qt.CursorShape.PointingHandCursor)
      btn_ver.setStyleSheet("""
        QPushButton { color: #2C3E50; border: none; font-weight: bold; padding: 6px 12px; font-size: 13px; text-decoration: underline; }
        QPushButton:hover { color: #1A252F; }
      """)
      btn_ver.clicked.connect(lambda checked, m=motivo, n=estudiante_nombre, s=id_apelacion: self.ver_evidencia(m, n, s))
      
      btn_rechazar = QPushButton("Rechazar")
      btn_rechazar.setCursor(Qt.CursorShape.PointingHandCursor)
      btn_rechazar.setStyleSheet("""
        QPushButton { color: #C0392B; border: none; font-weight: bold; padding: 6px 12px; font-size: 13px; }
        QPushButton:hover { color: #922B21; text-decoration: underline; }
      """)
      btn_rechazar.clicked.connect(lambda checked, s=id_apelacion: self.rechazar_apelacion(s))
      
      btn_aprobar = QPushButton("Aprobar")
      btn_aprobar.setCursor(Qt.CursorShape.PointingHandCursor)
      btn_aprobar.setStyleSheet("""
        QPushButton { color: #1E8449; border: none; font-weight: bold; padding: 6px 12px; font-size: 13px; }
        QPushButton:hover { color: #145A32; text-decoration: underline; }
      """)
      btn_aprobar.clicked.connect(lambda checked, s=id_apelacion: self.aprobar_apelacion(s))
      
      layout_acc.addWidget(btn_ver)
      if estado == "EN_REVISION" or estado == "PENDIENTE":
          layout_acc.addWidget(btn_rechazar)
          layout_acc.addWidget(btn_aprobar)
      else:
          lbl_resuelta = QLabel("Ya Resuelta")
          lbl_resuelta.setStyleSheet("color: #7F8C8D; font-size: 12px; font-style: italic;")
          layout_acc.addWidget(lbl_resuelta)
      
      self.tabla_apelaciones.setCellWidget(fila, 5, widget_acciones)
      


  def pagina_anterior(self):
    if self.pagina_actual>1:
      self.pagina_actual -= 1
      self.renderizar_pagina()

  def pagina_siguiente(self):
    total_paginas = max(1, math.ceil(len(self.apelaciones_filtradas) / self.elementos_por_pagina))
    if self.pagina_actual < total_paginas:
      self.pagina_actual += 1
      self.renderizar_pagina()

  def ver_evidencia(self, motivo_completo, nombre, sesion_id):
    parent = self.window()
    if hasattr(parent, "abrir_carpetas_forenses"):
      parent.abrir_carpetas_forenses(nombre, sesion_id)

  def aprobar_apelacion(self, sesion_id):
    motivo, ok = QInputDialog.getText(self, "Aprobar Segunda Revisión", "Motivo de la aprobación:")
    if ok and motivo:
      exito, msg = cliente_api.resolver_apelacion(sesion_id, motivo, "APROBADA_A_FAVOR")
      if exito:
        QMessageBox.information(self, "Éxito", "Apelación aprobada y estado actualizado.")
        self.cargar_apelaciones_reales()
      else:
        QMessageBox.warning(self, "Error", msg)
        
  def rechazar_apelacion(self, sesion_id):
    motivo, ok = QInputDialog.getText(self, "Rechazar Segunda Revisión", "Motivo para mantener la decisión:")
    if ok and motivo:
      exito, msg = cliente_api.resolver_apelacion(sesion_id, motivo, "RECHAZADA_FRAUDE_MANTENIDO")
      if exito:
        QMessageBox.information(self, "Éxito", "Apelación rechazada y estado actualizado.")
        self.cargar_apelaciones_reales()
      else:
        QMessageBox.warning(self, "Error", msg)