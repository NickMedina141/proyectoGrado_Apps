# vista/ventana_principal.py
import os
from PyQt6.QtWidgets import QWidget, QMessageBox
from PyQt6.QtGui import QIcon
from PyQt6 import uic
from utils.gestor_sesion import sesion_actual

from vista.sala_supervision import SalaSupervision
from vista.panel_apelaciones import PanelApelaciones
from vista.detalle_estudiante import DetalleEstudiante
from vista.reporte_ia import ReporteIA
from vista.crear_examen import CrearExamen
from vista.configuracion_examen import ConfiguracionExamen
from vista.panel_carpetas import PanelCarpetas
from vista.panel_admin import PanelAdmin
from vista.reporte_institucional import ReporteInstitucional

class VentanaPrincipal(QWidget):
  def __init__(self):
    super().__init__()
    
    # Cargamos el archivo unificado usando ruta absoluta dinámica
    base_path = os.path.dirname(__file__)
    uic.loadUi(os.path.join(base_path, "ventana_principal.xml"), self)
    
    # Identidad visual e ícono de la ventana
    self.setWindowTitle("UPC Proctor - Portal Docente")
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ruta_ico = os.path.join(base_dir, "recursos", "installer_icon.ico")
    ruta_png = os.path.join(base_path, "recursos", "logo_upc.png")
    ruta_icono = ruta_ico if os.path.exists(ruta_ico) else ruta_png
    if os.path.exists(ruta_icono):
        self.setWindowIcon(QIcon(ruta_icono))
        import sys
        if sys.platform == "win32":
            try:
                import ctypes
                hwnd = int(self.winId())
                if hwnd and ruta_ico and os.path.exists(ruta_ico):
                    WM_SETICON = 0x0080
                    IMAGE_ICON = 1
                    LR_LOADFROMFILE = 0x00000010
                    abs_ico = os.path.abspath(ruta_ico)
                    h_icon_big = ctypes.windll.user32.LoadImageW(0, abs_ico, IMAGE_ICON, 32, 32, LR_LOADFROMFILE)
                    h_icon_small = ctypes.windll.user32.LoadImageW(0, abs_ico, IMAGE_ICON, 16, 16, LR_LOADFROMFILE)
                    if h_icon_big:
                        ctypes.windll.user32.SendMessageW(hwnd, WM_SETICON, 1, h_icon_big)
                    if h_icon_small:
                        ctypes.windll.user32.SendMessageW(hwnd, WM_SETICON, 0, h_icon_small)
            except Exception:
                pass
    
    logo_path = os.path.join(base_path, "recursos", "logo_upc.png").replace("\\", "/")
    if os.path.exists(logo_path):
        self.label_logo_placeholder.setText("")
        self.label_logo_placeholder.setStyleSheet(f"border-image: url('{logo_path}'); border-radius: 50px;")
    
    # Inicialización de referencias a vistas bajo demanda (Lazy Loading)
    self._vista_sala = None
    self._vista_apelaciones = None
    self._vista_detalle_est = None
    self._vista_reporte = None
    self._scroll_reporte = None
    self._vista_crear = None
    self._scroll_crear = None
    self._vista_configuracion = None
    self._scroll_config = None
    self._vista_carpetas = None
    self._vista_admin = None
    self._vista_reporte_admin = None

    # Placeholders en contenedor_vistas para reservar de forma ligera los índices 1 a 9
    from PyQt6.QtWidgets import QWidget
    for _ in range(9):
        self.contenedor_vistas.addWidget(QWidget())

    self.indice_admin = 8
    self.indice_reporte_admin = 9

    self.btn_nav_ayuda.clicked.connect(self.mostrar_ayuda)
    self.btn_nav_salir.clicked.connect(self.cerrar_sesion)
    self.btn_nav_tema.clicked.connect(self.alternar_tema)

    # Conectamos eventos del botón de Crear Examen del Dashboard
    if hasattr(self, 'boton_crear_examen'):
        self.boton_crear_examen.clicked.connect(lambda: self.cambiar_vista(5))
    
    self.modo_oscuro = False
    
    # OVERLAY SPINNER GLOBAL
    from vista.overlay_carga import OverlayCarga
    self.overlay_carga = OverlayCarga(self)
    
    # Segregación de interfaz y vistas según el rol autenticado
    self.configurar_segregacion_roles()
    self.aplicar_tema_claro()
    
    # FIX GEOMETRÍA WINDOWS: Evitar que el ScrollArea o cualquier widget fuerce un tamaño mínimo que colapse al maximizar
    # Calcular minimo dinamico segun resolucion de pantalla
    from PyQt6.QtWidgets import QApplication
    _screen = QApplication.primaryScreen().availableSize()
    self.setMinimumSize(max(800, int(_screen.width() * 0.55)),
                        max(550, int(_screen.height() * 0.65)))
    if hasattr(self, 'area_scroll'):
      self.area_scroll.setMinimumSize(0, 0)
      self.area_scroll.setWidgetResizable(True)
      
    # OVERLAY DE DESCONEXIÓN GLOBAL
    from PyQt6.QtWidgets import QFrame, QVBoxLayout, QLabel
    self.overlay_desconexion = QFrame(self)
    self.overlay_desconexion.setStyleSheet("background-color: rgba(0, 0, 0, 180);")
    self.overlay_desconexion.hide()
    
    lay_overlay = QVBoxLayout(self.overlay_desconexion)
    from PyQt6.QtCore import Qt
    lay_overlay.setAlignment(Qt.AlignmentFlag.AlignCenter)
    
    lbl_aviso = QLabel("⚠️ CONEXIÓN PERDIDA\nIntentando reconectar al servidor...")
    lbl_aviso.setStyleSheet("color: white; font-size: 26px; font-weight: bold; background-color: transparent;")
    lbl_aviso.setAlignment(Qt.AlignmentFlag.AlignCenter)
    lay_overlay.addWidget(lbl_aviso)

  # --------------------------------------------------------------------------
  # Gestores de Carga Diferida (Lazy Loading) de Vistas
  # --------------------------------------------------------------------------
  def _reemplazar_en_stack(self, indice: int, widget_nuevo):
      """Reemplaza limpiamente el placeholder en la posicion correspondiente del stack."""
      widget_antiguo = self.contenedor_vistas.widget(indice)
      self.contenedor_vistas.removeWidget(widget_antiguo)
      if widget_antiguo is not None:
          widget_antiguo.deleteLater()
      self.contenedor_vistas.insertWidget(indice, widget_nuevo)

  def _aplicar_tema_a_widget(self, widget):
      """Aplica el tema CSS actual a un widget recién instanciado bajo demanda."""
      if not widget:
          return
      estilo = getattr(self, '_css_oscuro_cache', '') if getattr(self, 'modo_oscuro', False) else getattr(self, '_css_claro_cache', '')
      if estilo:
          try:
              widget.setStyleSheet(estilo)
          except Exception:
              pass
      if hasattr(widget, 'aplicar_tema'):
          try:
              widget.aplicar_tema(getattr(self, 'modo_oscuro', False))
          except Exception:
              pass

  def obtener_vista_sala(self):
      if self._vista_sala is None:
          from vista.sala_supervision import SalaSupervision
          self._vista_sala = SalaSupervision()
          self._reemplazar_en_stack(1, self._vista_sala)
          self._aplicar_tema_a_widget(self._vista_sala)
      return self._vista_sala

  def obtener_vista_apelaciones(self):
      if self._vista_apelaciones is None:
          from vista.panel_apelaciones import PanelApelaciones
          self._vista_apelaciones = PanelApelaciones()
          self._reemplazar_en_stack(2, self._vista_apelaciones)
          self._aplicar_tema_a_widget(self._vista_apelaciones)
      return self._vista_apelaciones

  def obtener_vista_detalle_est(self):
      if self._vista_detalle_est is None:
          from vista.detalle_estudiante import DetalleEstudiante
          self._vista_detalle_est = DetalleEstudiante(self)
          self._reemplazar_en_stack(3, self._vista_detalle_est)
          self._aplicar_tema_a_widget(self._vista_detalle_est)
      return self._vista_detalle_est

  def obtener_vista_reporte(self):
      if self._vista_reporte is None:
          from vista.reporte_ia import ReporteIA
          from PyQt6.QtWidgets import QScrollArea
          self._vista_reporte = ReporteIA()
          self._scroll_reporte = QScrollArea()
          self._scroll_reporte.setWidgetResizable(True)
          self._scroll_reporte.setFrameShape(QScrollArea.Shape.NoFrame)
          self._scroll_reporte.setWidget(self._vista_reporte)
          self._reemplazar_en_stack(4, self._scroll_reporte)
          self._aplicar_tema_a_widget(self._vista_reporte)
      return self._vista_reporte

  def obtener_vista_crear(self):
      if self._vista_crear is None:
          from vista.crear_examen import CrearExamen
          from PyQt6.QtWidgets import QScrollArea
          self._vista_crear = CrearExamen()
          self._vista_crear.cancelado.connect(lambda: self.cambiar_vista(0))
          self._vista_crear.siguiente.connect(self.ir_a_configuracion_examen)
          self._scroll_crear = QScrollArea()
          self._scroll_crear.setWidgetResizable(True)
          self._scroll_crear.setFrameShape(QScrollArea.Shape.NoFrame)
          self._scroll_crear.setWidget(self._vista_crear)
          self._reemplazar_en_stack(5, self._scroll_crear)
          self._aplicar_tema_a_widget(self._vista_crear)
      return self._vista_crear

  def obtener_vista_configuracion(self):
      if self._vista_configuracion is None:
          from vista.configuracion_examen import ConfiguracionExamen
          from PyQt6.QtWidgets import QScrollArea
          self._vista_configuracion = ConfiguracionExamen()
          self._vista_configuracion.anterior.connect(lambda: self.cambiar_vista(5))
          self._vista_configuracion.finalizado.connect(self.examen_creado_exito)
          self._scroll_config = QScrollArea()
          self._scroll_config.setWidgetResizable(True)
          self._scroll_config.setFrameShape(QScrollArea.Shape.NoFrame)
          self._scroll_config.setWidget(self._vista_configuracion)
          self._reemplazar_en_stack(6, self._scroll_config)
          self._aplicar_tema_a_widget(self._vista_configuracion)
      return self._vista_configuracion

  def obtener_vista_carpetas(self):
      if self._vista_carpetas is None:
          from vista.panel_carpetas import PanelCarpetas
          self._vista_carpetas = PanelCarpetas(self.volver_al_reporte)
          self._reemplazar_en_stack(7, self._vista_carpetas)
          self._aplicar_tema_a_widget(self._vista_carpetas)
      return self._vista_carpetas

  def obtener_vista_admin(self):
      if self._vista_admin is None:
          from vista.panel_admin import PanelAdmin
          self._vista_admin = PanelAdmin()
          self._reemplazar_en_stack(8, self._vista_admin)
          self._aplicar_tema_a_widget(self._vista_admin)
      return self._vista_admin

  def obtener_vista_reporte_admin(self):
      if self._vista_reporte_admin is None:
          from vista.reporte_institucional import ReporteInstitucional
          self._vista_reporte_admin = ReporteInstitucional()
          self._reemplazar_en_stack(9, self._vista_reporte_admin)
          self._aplicar_tema_a_widget(self._vista_reporte_admin)
      return self._vista_reporte_admin

  # Propiedades para compatibilidad transparente hacia atrás
  @property
  def vista_sala(self):
      return self.obtener_vista_sala()

  @property
  def vista_apelaciones(self):
      return self.obtener_vista_apelaciones()

  @property
  def vista_detalle_est(self):
      return self.obtener_vista_detalle_est()

  @property
  def vista_reporte(self):
      return self.obtener_vista_reporte()

  @property
  def vista_crear(self):
      return self.obtener_vista_crear()

  @property
  def vista_configuracion(self):
      return self.obtener_vista_configuracion()

  @property
  def vista_carpetas(self):
      return self.obtener_vista_carpetas()

  @property
  def vista_admin(self):
      return self.obtener_vista_admin()

  @property
  def vista_reporte_admin(self):
      return self.obtener_vista_reporte_admin()

  def configurar_segregacion_roles(self):
    es_adm = sesion_actual.es_admin()

    if es_adm:
        self.setWindowTitle("UPC Proctor - Portal Administrativo (SuperADMIN)")
        # Ocultar botones exclusivos del rol docente
        self.btn_nav_dashboard.setVisible(False)
        self.btn_nav_sala.setVisible(False)
        self.btn_nav_apelaciones.setVisible(False)
        if hasattr(self, 'boton_crear_examen'):
            self.boton_crear_examen.setVisible(False)

        # Configurar botones exclusivos de administración
        if hasattr(self, 'btn_nav_admin'):
            self.btn_nav_admin.setText("Gestión de Usuarios")
            self.btn_nav_admin.setVisible(True)
            try:
                self.btn_nav_admin.clicked.disconnect()
            except (TypeError, RuntimeError):
                pass
            self.btn_nav_admin.clicked.connect(lambda: self.cambiar_vista(self.indice_admin))

        self.btn_nav_reportes.setText("Reportes Institucionales")
        self.btn_nav_reportes.setVisible(True)
        try:
            self.btn_nav_reportes.clicked.disconnect()
        except (TypeError, RuntimeError):
            pass
        self.btn_nav_reportes.clicked.connect(lambda: self.cambiar_vista(self.indice_reporte_admin))

        # La vista inicial para SuperADMIN es el Panel de Administración
        self.cambiar_vista(self.indice_admin)

    else:
        self.setWindowTitle("UPC Proctor - Portal Docente")
        # Mostrar botones correspondientes a docentes
        self.btn_nav_dashboard.setVisible(True)
        self.btn_nav_sala.setVisible(True)
        self.btn_nav_apelaciones.setVisible(True)
        if hasattr(self, 'boton_crear_examen'):
            self.boton_crear_examen.setVisible(True)

        self.btn_nav_reportes.setText("Reportes")
        self.btn_nav_reportes.setVisible(True)
        try:
            self.btn_nav_reportes.clicked.disconnect()
        except (TypeError, RuntimeError):
            pass
        self.btn_nav_reportes.clicked.connect(lambda: self.cambiar_vista(4))

        if hasattr(self, 'btn_nav_admin'):
            self.btn_nav_admin.setVisible(False)

        try:
            self.btn_nav_dashboard.clicked.disconnect()
        except (TypeError, RuntimeError):
            pass
        self.btn_nav_dashboard.clicked.connect(lambda: self.cambiar_vista(0))

        try:
            self.btn_nav_sala.clicked.disconnect()
        except (TypeError, RuntimeError):
            pass
        self.btn_nav_sala.clicked.connect(lambda: self.cambiar_vista(1))

        try:
            self.btn_nav_apelaciones.clicked.disconnect()
        except (TypeError, RuntimeError):
            pass
        self.btn_nav_apelaciones.clicked.connect(lambda: self.cambiar_vista(2))

        # La vista inicial para Docentes es el Dashboard de Exámenes
        self.cambiar_vista(0)

  def mostrar_overlay_reconexion(self, mostrar):
    if not hasattr(self, 'overlay_desconexion'): return
    if mostrar:
        self.overlay_desconexion.resize(self.width(), self.height())
        self.overlay_desconexion.show()
        self.overlay_desconexion.raise_()
    else:
        self.overlay_desconexion.hide()

  def cargar_mis_examenes(self, callback_finalizado=None):
    if sesion_actual.es_admin():
      if callback_finalizado:
          try: callback_finalizado()
          except Exception: pass
      return

    prof_id = sesion_actual.obtener_profesor_id()
    if not prof_id:
      if callback_finalizado:
          try: callback_finalizado()
          except Exception: pass
      return

    from api.cliente_respuesta import cliente_api

    def _tarea_red():
        return cliente_api.obtener_mis_examenes(prof_id)

    def _al_recibir(resultado):
        exito, examenes = resultado
        if not exito:
            print("Error cargando examenes:", examenes)
        elif isinstance(examenes, list):
            self._renderizar_tarjetas_examenes(examenes)
        if callback_finalizado:
            try:
                callback_finalizado()
            except Exception:
                pass

    from vista.overlay_carga import HiloTrabajador
    self._hilo_examenes = HiloTrabajador(_tarea_red)
    self._hilo_examenes.senal_resultado.connect(_al_recibir)
    self._hilo_examenes.start()

  def _renderizar_tarjetas_examenes(self, examenes):
    from PyQt6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
    from PyQt6.QtCore import Qt

    # Limpiar elementos generados dinámicamente si los hay
    if not hasattr(self, 'tarjetas_generadas'):
      self.tarjetas_generadas = []
    for widget in self.tarjetas_generadas:
      widget.setParent(None)
      widget.deleteLater()
    self.tarjetas_generadas.clear()

    # Limpiar completamente el layout_examenes (remover tarjeta_1 y espaciadores previos)
    from PyQt6.sip import delete
    from PyQt6.QtWidgets import QGridLayout
    old_lay = self.contenido_scroll.layout()
    if old_lay is not None:
      while old_lay.count() > 0:
        it = old_lay.takeAt(0)
        if it.widget() and it.widget() not in self.tarjetas_generadas:
          it.widget().deleteLater()
      delete(old_lay)

    self.layout_examenes = QGridLayout(self.contenido_scroll)
    self.layout_examenes.setSpacing(20)
    self.layout_examenes.setContentsMargins(15, 15, 15, 15)

    # Detenemos timer viejo si existe
    if hasattr(self, 'timer_contadores'):
        self.timer_contadores.stop()
    self.etiquetas_tiempo = [] # Para guardar (label, horaFin)
    
    from datetime import datetime
    
    row = 0
    col = 0
    
    for examen in examenes:
      tarjeta = QFrame()
      tarjeta.setFixedSize(280, 260)
      tarjeta.setObjectName("tarjeta_dinamica") # Para que el CSS la pinte como blanca

      lay_v = QVBoxLayout(tarjeta)
      lay_v.setSpacing(10)
      lay_v.setContentsMargins(20, 20, 20, 20)

      # --- TOP ---
      top_lay = QHBoxLayout()
      
      materia = examen.get("materiaCodigo") or "Materia Desconocida"
      
      lbl_titulo_top = QLabel(materia)
      lbl_titulo_top.setObjectName("titulo_dinamico")
      lbl_titulo_top.setStyleSheet("font-weight: bold; font-size: 18px;")
      
      control_acceso = examen.get("controlAcceso") or {}
      estado_pin = control_acceso.get("estadoPin", "FINALIZADO")
        
      # --- AUTOMATIZACIÓN DE TIEMPO ---
      # Si la fecha actual está entre horaInicio y horaFin, forzamos visualmente a que esté ACTIVO (abierto)
      fecha_dict = examen.get("fechaExamen") or {}
      hora_fin_str = fecha_dict.get("horaFin")
      hora_inicio_str = fecha_dict.get("horaInicio")
        
      import datetime
      try:
          if hora_inicio_str and hora_fin_str and estado_pin != "FINALIZADO":
              ahora = datetime.datetime.now().astimezone()
              dt_inicio = datetime.datetime.fromisoformat(hora_inicio_str).astimezone()
              dt_fin = datetime.datetime.fromisoformat(hora_fin_str).astimezone()
              
              if dt_inicio <= ahora <= dt_fin:
                  estado_pin = "ACTIVO"
              elif ahora > dt_fin:
                  estado_pin = "FINALIZADO"
              elif ahora < dt_inicio:
                  estado_pin = "PROGRAMADO"
      except Exception as e:
          pass
        
      texto_badge = "EN CURSO" if estado_pin == "ACTIVO" else ("PROGRAMADO" if estado_pin == "PROGRAMADO" else "FINALIZADO")
      badge = QLabel(texto_badge)
      if estado_pin == "ACTIVO":
        badge.setStyleSheet("background-color: #C1F032; color: #003B13; border-radius: 4px; padding: 4px; font-weight: bold;")
      elif estado_pin == "PROGRAMADO":
        badge.setStyleSheet("background-color: #3498DB; color: #FFFFFF; border-radius: 4px; padding: 4px; font-weight: bold;")
      else:
        badge.setStyleSheet("background-color: #E0E0E0; color: #333333; border-radius: 4px; padding: 4px; font-weight: bold;")

      top_lay.addWidget(lbl_titulo_top)
      top_lay.addStretch()
      top_lay.addWidget(badge)
      lay_v.addLayout(top_lay)

      # --- FECHA ---
      fecha_dict = examen.get("fechaExamen") or {}
      fecha_str = fecha_dict.get("horaInicio", "Sin Fecha")
      if "T" in fecha_str:
        try:
            import datetime
            dt_local = datetime.datetime.fromisoformat(fecha_str).astimezone()
            fecha_str = dt_local.strftime("%Y-%m-%d")
        except:
            fecha_str = fecha_str.split("T")[0]
      lbl_fecha = QLabel(f"Creación: {fecha_str}")
      lbl_fecha.setObjectName("card_lbl_detalle")
      lbl_fecha.setStyleSheet("font-size: 13px; font-weight: bold; padding-left: 5px;")
      lay_v.addWidget(lbl_fecha)
      
      # --- PIN EXAMEN ---
      control = examen.get("controlAcceso") or {}
      pin_acc = control.get("pinSesion") or "Sin PIN"
      lbl_pin = QLabel(f"PIN: {pin_acc}")
      lbl_pin.setObjectName("card_lbl_detalle")
      lbl_pin.setStyleSheet("font-size: 13px; font-weight: bold; padding-left: 5px;")
      lay_v.addWidget(lbl_pin)

      # --- ID EXAMEN ---
      id_ex = examen.get("codigoExamen") or examen.get("id") or "---"
      lbl_id = QLabel(f"ID: {id_ex}")
      lbl_id.setObjectName("card_lbl_detalle")
      lbl_id.setStyleSheet("font-size: 13px; font-weight: bold; padding-left: 5px;")
      lay_v.addWidget(lbl_id)

      # --- CONTADOR DE TIEMPO (NUEVO) ---
      hora_fin = fecha_dict.get("horaFin")
      lbl_tiempo = QLabel()
      lbl_tiempo.setObjectName("card_lbl_tiempo")
      lbl_tiempo.setStyleSheet("font-size: 13px; font-weight: bold; font-family: Consolas; padding-left: 5px;")
      lay_v.addWidget(lbl_tiempo)
      
      if estado_pin == "ACTIVO" and hora_fin_str:
          self.etiquetas_tiempo.append((lbl_tiempo, hora_fin_str, "Cierra en: "))
      elif estado_pin == "PROGRAMADO" and hora_inicio_str:
          self.etiquetas_tiempo.append((lbl_tiempo, hora_inicio_str, "Inicia en: "))
      elif estado_pin == "FINALIZADO":
          lbl_tiempo.setText("Examen Finalizado")
          lbl_tiempo.setObjectName("card_lbl_tiempo_fin")
          lbl_tiempo.setStyleSheet("font-size: 13px; font-weight: bold; padding-left: 5px;")
      else:
          lbl_tiempo.setText("Sin Límite")
          
      # --- SEPARADOR ---
      from PyQt6.QtWidgets import QFrame as QF
      linea = QF()
      linea.setFrameShape(QF.Shape.HLine)
      linea.setFrameShadow(QF.Shadow.Sunken)
      lay_v.addWidget(linea)

      # --- BOTON ENTRAR Y TOGGLE ---
      bot_lay = QHBoxLayout()
      
      btn_configuracion = QPushButton("⚙")
      btn_configuracion.setToolTip("Configurar Examen")
      btn_configuracion.setCursor(Qt.CursorShape.PointingHandCursor)
      btn_configuracion.setStyleSheet("QPushButton { font-size: 16px; border: none; background: transparent; } QPushButton:hover { color: #2980b9; }")
      # El botón se conecta a un modal que implementaré ahora
      btn_configuracion.clicked.connect(lambda checked, ex=examen: self.abrir_configuracion_examen(ex))
      bot_lay.addWidget(btn_configuracion)
      
      bot_lay.addStretch()
      
      btn_toggle = QPushButton(" Abrir" if estado_pin != "ACTIVO" else " Cerrar")
      btn_toggle.setObjectName("btn_toggle_dinamico")
      btn_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
      btn_toggle.clicked.connect(lambda checked, eid=id_ex, st=estado_pin, ex=examen: self.alternar_estado_examen(eid, st, ex))

      btn_entrar = QPushButton("Entrar a Supervisar ")
      btn_entrar.setObjectName("btn_dinamico")
      btn_entrar.setCursor(Qt.CursorShape.PointingHandCursor)
      
      # UX MEJORA: Deshabilitar entrada si está finalizado
      if estado_pin == "FINALIZADO":
          btn_entrar.setEnabled(False)
          btn_entrar.setToolTip("El examen ya finalizó")
          btn_entrar.setStyleSheet("color: #a0a0a0; font-weight: normal;")
      
      # Pasamos el id y la materia por defecto en el lambda
      btn_entrar.clicked.connect(lambda checked, eid=id_ex, mat=materia: self.entrar_supervisar_dinamico(eid, mat))
      
      bot_lay.addWidget(btn_toggle)
      bot_lay.addWidget(btn_entrar)
      lay_v.addLayout(bot_lay)

      # Guardamos la tarjeta generada
      self.tarjetas_generadas.append(tarjeta)

    # Posicionamos las tarjetas en la grilla dinámica
    num_cols = self._calcular_columnas_dinamicas()
    self._ultimas_columnas = num_cols

    for idx, tarjeta in enumerate(self.tarjetas_generadas):
      r = idx // num_cols
      c = idx % num_cols
      self.layout_examenes.addWidget(tarjeta, r, c, alignment=Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)

    self.layout_examenes.setColumnStretch(num_cols, 1)
    if self.tarjetas_generadas:
      self.layout_examenes.setRowStretch((len(self.tarjetas_generadas) // num_cols) + 1, 1)

    # Iniciar Timer de Cuenta Regresiva
    from PyQt6.QtCore import QTimer
    self.timer_contadores = QTimer(self)
    self.timer_contadores.timeout.connect(self._actualizar_contadores_examenes)
    self.timer_contadores.start(1000)
    self._actualizar_contadores_examenes()

  # ---- Responsive Grid -------------------------------------------------
  _CARD_WIDTH   = 280
  _CARD_SPACING = 20

  def _calcular_columnas_dinamicas(self):
      if hasattr(self, 'area_scroll') and self.area_scroll.isVisible():
          ancho = self.area_scroll.viewport().width() - 40
      else:
          ancho = self.width() - 170
      return max(1, (ancho + self._CARD_SPACING) // (self._CARD_WIDTH + self._CARD_SPACING))

  def resizeEvent(self, event):
      super().resizeEvent(event)
      if hasattr(self, 'overlay_desconexion') and self.overlay_desconexion.isVisible():
          self.overlay_desconexion.resize(self.width(), self.height())
      if (hasattr(self, 'tarjetas_generadas') and self.tarjetas_generadas
              and hasattr(self, 'contenedor_vistas')
              and self.contenedor_vistas.currentIndex() == 0):
          self._redistribuir_tarjetas()

  def _redistribuir_tarjetas(self):
      if not hasattr(self, 'tarjetas_generadas') or not self.tarjetas_generadas:
          return
      num_cols = self._calcular_columnas_dinamicas()
      if getattr(self, '_ultimas_columnas', None) == num_cols:
          return
      self._ultimas_columnas = num_cols

      from PyQt6.QtCore import Qt
      from PyQt6.QtWidgets import QGridLayout
      from PyQt6.sip import delete

      old_lay = self.contenido_scroll.layout()
      if old_lay is not None:
          while old_lay.count() > 0:
              old_lay.takeAt(0)
          delete(old_lay)

      self.layout_examenes = QGridLayout(self.contenido_scroll)
      self.layout_examenes.setSpacing(self._CARD_SPACING)
      self.layout_examenes.setContentsMargins(15, 15, 15, 15)

      for idx, tarjeta in enumerate(self.tarjetas_generadas):
          r = idx // num_cols
          c = idx % num_cols
          self.layout_examenes.addWidget(
              tarjeta, r, c,
              alignment=Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop
          )

      self.layout_examenes.setColumnStretch(num_cols, 1)
      self.layout_examenes.setRowStretch((len(self.tarjetas_generadas) // num_cols) + 1, 1)
  # ---- Fin Responsive Grid ---------------------------------------------

  def _actualizar_contadores_examenes(self):
      from datetime import datetime, timezone
      
      ahora_utc = datetime.now(timezone.utc)
      ahora_local = datetime.now()
      
      for lbl, hora_objetivo_str, prefijo in self.etiquetas_tiempo:
          try:
              # '2026-09-30T23:59:59.000Z' o '2026-09-30T23:59:59'
              iso_str = hora_objetivo_str.replace("Z", "+00:00")
              if "." in iso_str and not "+" in iso_str:
                 iso_str = iso_str.split(".")[0]
              
              fin = datetime.fromisoformat(iso_str)
              
              if fin.tzinfo is not None:
                  ahora_comparar = ahora_utc
              else:
                  ahora_comparar = ahora_local
                  
              faltan = (fin - ahora_comparar).total_seconds()
              
              if faltan > 0:
                  dias = int(faltan // 86400)
                  horas = int((faltan % 86400) // 3600)
                  mins = int((faltan % 3600) // 60)
                  segs = int(faltan % 60)
                  
                  if dias > 0:
                      lbl.setText(f" {prefijo}{dias}d {horas:02d}:{mins:02d}:{segs:02d}")
                  else:
                      lbl.setText(f" {prefijo}{horas:02d}:{mins:02d}:{segs:02d}")
              else:
                    lbl.setText(" Actualizando...")
                    if not getattr(lbl, 'ya_actualizo', False):
                        setattr(lbl, 'ya_actualizo', True)
                        from PyQt6.QtCore import QTimer
                        QTimer.singleShot(1000, self.cargar_mis_examenes)
          except Exception as e:
              lbl.setText(" Error de tiempo")

  def alternar_estado_examen(self, id_sesion, estado_actual, examen=None):
    from api.cliente_respuesta import cliente_api
    import datetime
    from PyQt6.QtWidgets import QMessageBox
    
    # Validar que no abra exámenes expirados
    if estado_actual != "ACTIVO" and examen:
        fecha_dict = examen.get("fechaExamen") or {}
        hora_fin_str = fecha_dict.get("horaFin")
        if hora_fin_str:
            try:
                dt_fin = datetime.datetime.fromisoformat(hora_fin_str).astimezone()
                ahora = datetime.datetime.now().astimezone()
                if dt_fin < ahora:
                    QMessageBox.warning(self, "Fechas Expiradas", "Las fechas de este examen ya pasaron. Si desea abrirlo, por favor modifique primero las fechas en la configuración.")
                    return
            except Exception as e:
                print("Error validando fecha_fin:", e)
                
    if hasattr(self, 'overlay_carga') and self.isVisible():
        self.overlay_carga.mostrar("Actualizando estado del examen...")
    try:
        if estado_actual == "ACTIVO":
          exito, mensaje = cliente_api.cerrar_examen(id_sesion)
          if not exito:
              QMessageBox.warning(self, "Error", mensaje)
          else:
              if hasattr(self, 'vista_sala') and getattr(self.vista_sala, 'codigo_examen_actual', None) == id_sesion:
                  self.vista_sala.estado_vacio(True)
                  self.vista_sala.codigo_examen_actual = None
        else:
          exito, mensaje = cliente_api.abrir_examen(id_sesion)
          if not exito: QMessageBox.warning(self, "Error", mensaje)
        
        # Recargar dashboard para ver el cambio
        self.cargar_mis_examenes()
    finally:
        if hasattr(self, 'overlay_carga'):
            self.overlay_carga.ocultar()

  def abrir_detalle_estudiante(self, nombre, id_sesion, estudiante_id=None):
    if hasattr(self, 'overlay_carga') and self.isVisible():
        self.overlay_carga.mostrar("Cargando detalles del estudiante...")
    try:
        self.vista_detalle_est.cargar_datos(nombre, id_sesion, estudiante_id=estudiante_id)
        self.cambiar_vista(3)
    finally:
        if hasattr(self, 'overlay_carga'):
            self.overlay_carga.ocultar()
    
  def abrir_carpetas_forenses(self, nombre, id_sesion):
    if hasattr(self, 'overlay_carga') and self.isVisible():
        self.overlay_carga.mostrar("Cargando evidencias forenses...")
    try:
        self.vista_origen = self.contenedor_vistas.currentIndex()
        
        if self.vista_origen == 2:
            self.vista_carpetas.btn_volver_reporte.setText("Volver a Segunda Revisión")
        elif self.vista_origen == 4:
            self.vista_carpetas.btn_volver_reporte.setText("Volver al Reporte")
        else:
            self.vista_carpetas.btn_volver_reporte.setText("Volver Atrás")
            
        self.vista_carpetas.cargar_datos(nombre, id_sesion)
        self.cambiar_vista(7)
    finally:
        if hasattr(self, 'overlay_carga'):
            self.overlay_carga.ocultar()
    
  def volver_al_reporte(self):
      origen = getattr(self, 'vista_origen', 4)
      self.cambiar_vista(origen)

  def entrar_supervisar_dinamico(self, id_sesion, materia):
    if hasattr(self, 'overlay_carga') and self.isVisible():
        self.overlay_carga.mostrar("Conectando a sala de supervisión...")
    try:
        self.vista_sala.cargar_estudiantes(id_sesion, materia)
        self.cambiar_vista(1)
    finally:
        if hasattr(self, 'overlay_carga'):
            self.overlay_carga.ocultar()

  def abrir_configuracion_examen(self, examen):
    from PyQt6.QtWidgets import QDialog, QMessageBox, QWidget, QVBoxLayout, QStackedWidget, QScrollArea
    from PyQt6 import uic
    from PyQt6.QtCore import Qt, QDate, QTime
    import os
    
    dialogo = QDialog(self)
    dialogo.setWindowTitle("Editar Examen")
    dialogo.resize(800, 550)
    
    # Bug visual arreglado: Windows 11 ignora el color de QDialog. Pintamos el ScrollArea que cubre todo.
    color_fondo = "#0F172A" if hasattr(self, 'modo_oscuro') and self.modo_oscuro else "#F4F6F6"
    
    layout_main = QVBoxLayout(dialogo)
    layout_main.setContentsMargins(0, 0, 0, 0)
    
    scroll = QScrollArea(dialogo)
    scroll.setWidgetResizable(True)
    scroll.setStyleSheet(f"""
        QScrollArea {{ border: none; background-color: {color_fondo}; }}
        QWidget#qt_scrollarea_viewport {{ background-color: {color_fondo}; }}
    """)
    
    stack = QStackedWidget()
    stack.setObjectName("MainConfigStack")
    stack.setStyleSheet(f"QWidget#MainConfigStack {{ background-color: {color_fondo}; }}")
    scroll.setWidget(stack)
    
    layout_main.addWidget(scroll)
    
    base_path = os.path.dirname(__file__)
    
    # --- PASO 1: Información Básica (crear_examen.xml) ---
    widget_paso1 = QWidget()
    uic.loadUi(os.path.join(base_path, "crear_examen.xml"), widget_paso1)
    stack.addWidget(widget_paso1)
    
    # Adaptar textos del paso 1
    if hasattr(widget_paso1, 'titulo_principal'):
        widget_paso1.titulo_principal.setText("Editar Examen")
    
    widget_paso1.entrada_materia.setText(examen.get("materiaCodigo", ""))
    widget_paso1.entrada_materia.setReadOnly(True) # La materia no se debería cambiar fácilmente
    widget_paso1.entrada_materia.setStyleSheet("background-color: #e0e0e0; color: #555;")
    
    # Cargar valores actuales del examen
    config_actual = examen.get("configuracionExamen") or {}
    fecha_examen = examen.get("fechaExamen") or {}
    
    if fecha_examen.get("horaInicio"):
        import datetime
        from PyQt6.QtCore import QDate, QTime
        try:
            # Parsear la cadena ISO (con timezone) y convertir a la zona horaria local
            dt_local = datetime.datetime.fromisoformat(fecha_examen.get("horaInicio")).astimezone()
            
            fecha_obj = QDate(dt_local.year, dt_local.month, dt_local.day)
            hora_obj = QTime(dt_local.hour, dt_local.minute)
            
            if fecha_obj.isValid(): widget_paso1.entrada_fecha.setDate(fecha_obj)
            if hora_obj.isValid():
                  hour12 = hora_obj.hour() % 12
                  if hour12 == 0: hour12 = 12
                  from PyQt6.QtCore import QTime
                  widget_paso1.entrada_hora_texto.setTime(QTime(hour12, hora_obj.minute()))
                  widget_paso1.entrada_hora_ampm.setCurrentText('PM' if hora_obj.hour() >= 12 else 'AM')
            
            if fecha_examen.get("horaFin") and hasattr(widget_paso1, 'entrada_fecha_fin'):
                dt_fin_local = datetime.datetime.fromisoformat(fecha_examen.get("horaFin")).astimezone()
                fecha_fin_obj = QDate(dt_fin_local.year, dt_fin_local.month, dt_fin_local.day)
                if fecha_fin_obj.isValid(): widget_paso1.entrada_fecha_fin.setDate(fecha_fin_obj)
            elif hasattr(widget_paso1, 'entrada_fecha_fin'):
                widget_paso1.entrada_fecha_fin.setDate(fecha_obj)
                
        except Exception as e:
            print("Error procesando fecha:", e)
        
    if hasattr(widget_paso1, 'entrada_duracion'):
        widget_paso1.entrada_duracion.setValue(config_actual.get("duracionExamen", 120))
        
    # Desconectar botones si tienen conexiones previas del UI, y reconectarlos
    try: widget_paso1.btn_cancelar.clicked.disconnect()
    except TypeError: pass
    
    try: widget_paso1.btn_siguiente.clicked.disconnect()
    except TypeError: pass
    
    widget_paso1.btn_cancelar.clicked.connect(dialogo.reject)
    widget_paso1.btn_siguiente.clicked.connect(lambda: stack.setCurrentIndex(1))

    # --- PASO 2: Configuración IA (configuracion_examen.xml) ---
    widget_paso2 = QWidget()
    uic.loadUi(os.path.join(base_path, "configuracion_examen.xml"), widget_paso2)
    stack.addWidget(widget_paso2)
    
    # Ocultar campos de edición básicos inyectados anteriormente (ya que ahora están en el paso 1)
    if hasattr(widget_paso2, 'widget_info_basica'):
        widget_paso2.widget_info_basica.setVisible(False)
        
    # Adaptar textos del paso 2
    widget_paso2.titulo_principal.setText("Ajustes de Supervisión IA")
    widget_paso2.subtitulo_principal.setText("Modifique los parámetros de proctoring automatizado para este examen.")
    widget_paso2.btn_finalizar.setText("Guardar y Actualizar")
    
    # Toggles de IA
    facial_val = config_actual.get("activarReconocimientoFacial")
    widget_paso2.chk_facial.setChecked(True if facial_val is None else bool(facial_val))
    
    objetos_val = config_actual.get("activarDeteccionObjetos")
    widget_paso2.chk_objetos.setChecked(True if objetos_val is None else bool(objetos_val))
    
    audio_val = config_actual.get("activarAnalisisAudio")
    widget_paso2.chk_audio.setChecked(False if audio_val is None else bool(audio_val))
    
    procesos_val = config_actual.get("activarMonitoreoProcesos")
    if hasattr(widget_paso2, "chk_procesos"):
        widget_paso2.chk_procesos.setChecked(True if procesos_val is None else bool(procesos_val))
        
    teclado_val = config_actual.get("activarAnalisisTeclado")
    if hasattr(widget_paso2, "chk_teclado"):
        widget_paso2.chk_teclado.setChecked(True if teclado_val is None else bool(teclado_val))
    
    sensibilidad_actual = config_actual.get("sensibilidadIA", "MEDIA")
    idx = {"BAJA": 0, "MEDIA": 1, "ALTA": 2}.get(sensibilidad_actual, 1)
    widget_paso2.entrada_sensibilidad.setCurrentIndex(idx)
    
    reintentos = config_actual.get("permitirReintentos", 3)
    widget_paso2.entrada_reintentos.setValue(reintentos)
    
    urls = config_actual.get("urlsPermitidas", [])
    widget_paso2.entrada_urls.setText(", ".join(urls))
    
    programas = config_actual.get("procesosPermitidos", [])
    widget_paso2.entrada_programas.setText(", ".join(programas))
    
    try: widget_paso2.btn_anterior.clicked.disconnect()
    except TypeError: pass
    
    try: widget_paso2.btn_finalizar.clicked.disconnect()
    except TypeError: pass
    
    widget_paso2.btn_anterior.clicked.connect(lambda: stack.setCurrentIndex(0))
    
    widget_paso2.estudiantes_csv = []
    def cargar_csv_mod():
        from PyQt6.QtWidgets import QFileDialog, QMessageBox
        import csv
        ruta, _ = QFileDialog.getOpenFileName(widget_paso2, 'Seleccionar CSV', '', 'CSV Files (*.csv)')
        if not ruta: return
        try:
            estudiantes = []
            with open(ruta, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    row_lower = {k.strip().lower() if isinstance(k, str) else k: str(v).strip() if v else '' for k, v in row.items()}
                    nombre = row_lower.get('nombre', '')
                    apellidos = row_lower.get('apellidos', '')
                    cedula = row_lower.get('cedula', '')
                    email = row_lower.get('email', '')
                    
                    if cedula and nombre:
                        estudiantes.append({
                            'nombre': nombre,
                            'apellidos': apellidos,
                            'cedula': str(cedula),
                            'email': email
                        })
                        
            if len(estudiantes) > 0:
                widget_paso2.estudiantes_csv = estudiantes
                widget_paso2.btn_csv.setText(f'Lista Adjunta ({len(estudiantes)} estudiantes)')
                widget_paso2.btn_csv.setStyleSheet('background-color: #27ae60; color: white; border-radius: 4px; padding: 10px 20px; font-weight: bold;')
                QMessageBox.information(widget_paso2, 'Exito', f'Se han cargado {len(estudiantes)} estudiantes correctamente.')
            else:
                QMessageBox.warning(widget_paso2, 'Error', 'El archivo no contiene estudiantes o le faltan las columnas (Cedula, Nombre, Email).')
        except Exception as e:
            QMessageBox.critical(widget_paso2, 'Error', f'No se pudo leer el archivo: {str(e)}')
            
    if hasattr(widget_paso2, 'btn_csv'):
        try: widget_paso2.btn_csv.clicked.disconnect()
        except TypeError: pass
        widget_paso2.btn_csv.clicked.connect(cargar_csv_mod)
    
    def guardar_cambios():
        from api.cliente_respuesta import cliente_api
        
        sensibilidad_map = {0: "BAJA", 1: "MEDIA", 2: "ALTA"}
        sensibilidad = sensibilidad_map.get(widget_paso2.entrada_sensibilidad.currentIndex(), "MEDIA")
        reintentos_nuevos = widget_paso2.entrada_reintentos.value()
        
        urls_raw = widget_paso2.entrada_urls.toPlainText()
        urls_list = [u.strip() for u in urls_raw.split(',') if u.strip()]
        
        prog_raw = widget_paso2.entrada_programas.toPlainText()
        prog_list = [p.strip() for p in prog_raw.split(',') if p.strip()]
                
        payload = {
              "fechaString": widget_paso1.entrada_fecha.date().toString("yyyy-MM-dd"),
              "fechaFinString": widget_paso1.entrada_fecha_fin.date().toString("yyyy-MM-dd") if hasattr(widget_paso1, 'entrada_fecha_fin') else widget_paso1.entrada_fecha.date().toString("yyyy-MM-dd"),
              "horaInicioString": f"{widget_paso1.entrada_hora_texto.time().hour() + (12 if widget_paso1.entrada_hora_ampm.currentText() == 'PM' and widget_paso1.entrada_hora_texto.time().hour() < 12 else (-12 if widget_paso1.entrada_hora_ampm.currentText() == 'AM' and widget_paso1.entrada_hora_texto.time().hour() == 12 else 0)):02d}:{widget_paso1.entrada_hora_texto.time().minute():02d}",
              "activarReconocimientoFacial": widget_paso2.chk_facial.isChecked(),
            "activarDeteccionObjetos": widget_paso2.chk_objetos.isChecked(),
            "activarAnalisisAudio": widget_paso2.chk_audio.isChecked(),
            "activarMonitoreoProcesos": getattr(widget_paso2, "chk_procesos").isChecked() if hasattr(widget_paso2, "chk_procesos") else True,
            "activarAnalisisTeclado": getattr(widget_paso2, "chk_teclado").isChecked() if hasattr(widget_paso2, "chk_teclado") else True,
            "sensibilidadIA": sensibilidad,
            "duracionExamen": widget_paso1.entrada_duracion.value() if hasattr(widget_paso1, 'entrada_duracion') else config_actual.get("duracionExamen", 120),
            "permitirReintentos": reintentos_nuevos,
            "procesosPermitidos": prog_list,
            "urlsPermitidas": urls_list
        }
        
        # Filtrar valores nulos
        payload = {k: v for k, v in payload.items() if v is not None}
        
        exito, msg = cliente_api.configurar_examen(examen.get("codigoExamen"), payload)
        if exito:
            if hasattr(widget_paso2, 'estudiantes_csv') and len(widget_paso2.estudiantes_csv) > 0:
                ex, msg_est = cliente_api.subir_estudiantes_bulk(examen.get("codigoExamen"), widget_paso2.estudiantes_csv)
                if ex:
                    QMessageBox.information(dialogo, "Exito", f"Configuracion actualizada e inscritos {len(widget_paso2.estudiantes_csv)} estudiantes.")
                else:
                    QMessageBox.warning(dialogo, "Advertencia", f"Configuracion actualizada pero fallaron los estudiantes: {msg_est}")
            else:
                QMessageBox.information(dialogo, "Exito", "Configuracion actualizada correctamente.")
            dialogo.accept()
            self.cargar_mis_examenes()
        else:
            QMessageBox.warning(dialogo, "Error", f"No se pudo actualizar: {msg}")
            
    widget_paso2.btn_finalizar.clicked.connect(guardar_cambios)
    
    dialogo.exec()

  def cambiar_vista(self, indice):
    indice_anterior = self.contenedor_vistas.currentIndex()
    # Si salimos de SalaSupervision, cerramos mapa para liberar QWebEngineView y timers
    if indice_anterior == 1 and indice != 1 and self._vista_sala is not None:
        if hasattr(self._vista_sala, 'cerrar_mapa'):
            self._vista_sala.cerrar_mapa()
    # Si salimos de DetalleEstudiante, detenemos stream y timers
    if indice_anterior == 3 and indice != 3 and self._vista_detalle_est is not None:
        if hasattr(self._vista_detalle_est, 'detener_supervision'):
            self._vista_detalle_est.detener_supervision()

    # Carga bajo demanda del widget correspondiente en el índice si aún no fue instanciado
    if indice == 1:
        self.obtener_vista_sala()
    elif indice == 2:
        self.obtener_vista_apelaciones()
    elif indice == 3:
        self.obtener_vista_detalle_est()
    elif indice == 4:
        self.obtener_vista_reporte()
    elif indice == 5:
        self.obtener_vista_crear()
    elif indice == 6:
        self.obtener_vista_configuracion()
    elif indice == 7:
        self.obtener_vista_carpetas()
    elif indice == getattr(self, 'indice_admin', 8):
        self.obtener_vista_admin()
    elif indice == getattr(self, 'indice_reporte_admin', 9):
        self.obtener_vista_reporte_admin()

    self.contenedor_vistas.setCurrentIndex(indice)
    self.actualizar_estilos_sidebar(indice)
    
    # Cargas dinámicas con overlay spinner institucional
    if indice == 0:
      if not sesion_actual.es_admin():
        if hasattr(self, 'overlay_carga') and self.isVisible():
          self.overlay_carga.mostrar("Actualizando dashboard...")
          self.cargar_mis_examenes(callback_finalizado=self.overlay_carga.ocultar)
        else:
          self.cargar_mis_examenes()
    elif indice == 2:
      vista_ap = self.obtener_vista_apelaciones()
      if hasattr(self, 'overlay_carga') and self.isVisible():
        self.overlay_carga.mostrar("Cargando solicitudes de apelación...")
        vista_ap.cargar_apelaciones_reales(callback_finalizado=self.overlay_carga.ocultar)
      else:
        vista_ap.cargar_apelaciones_reales()
    elif indice == 4:
      vista_rep = self.obtener_vista_reporte()
      if hasattr(self, 'overlay_carga') and self.isVisible():
        self.overlay_carga.mostrar("Cargando reportes y exámenes...")
        vista_rep.cargar_examenes(callback_finalizado=self.overlay_carga.ocultar)
      else:
        vista_rep.cargar_examenes()
    elif indice == getattr(self, 'indice_admin', 8):
      if hasattr(self, 'vista_admin'):
        self.vista_admin.cargar_datos()
    elif indice == getattr(self, 'indice_reporte_admin', -1):
      if hasattr(self, 'vista_reporte_admin'):
        self.vista_reporte_admin.cargar_datos()

  def actualizar_estilos_sidebar(self, indice_activo):
    estilo_inactivo = """
      QPushButton { background-color: transparent; border: none; text-align: left; font-weight: bold; font-size: 14px; padding-left: 15px; color: white; border-radius: 6px; } 
      QPushButton:hover { background-color: rgba(255, 255, 255, 0.1); }
    """
    estilo_activo = """
      QPushButton { background-color: #C1F032; border: none; text-align: left; font-weight: bold; font-size: 14px; padding-left: 15px; color: #003B13; border-radius: 6px; } 
    """
    self.btn_nav_dashboard.setStyleSheet(estilo_activo if indice_activo == 0 else estilo_inactivo)
    es_reporte_activo = (indice_activo == 4) or (indice_activo == getattr(self, 'indice_reporte_admin', -1))
    self.btn_nav_reportes.setStyleSheet(estilo_activo if es_reporte_activo else estilo_inactivo)
    self.btn_nav_sala.setStyleSheet(estilo_activo if indice_activo == 1 else estilo_inactivo)
    self.btn_nav_apelaciones.setStyleSheet(estilo_activo if indice_activo == 2 else estilo_inactivo)
    if hasattr(self, 'btn_nav_admin'):
      self.btn_nav_admin.setStyleSheet(estilo_activo if indice_activo == getattr(self, 'indice_admin', 8) else estilo_inactivo)
    self.btn_nav_ayuda.setStyleSheet(estilo_inactivo)
    self.btn_nav_tema.setStyleSheet(estilo_inactivo)
    self.btn_nav_salir.setStyleSheet(estilo_inactivo)

  def mostrar_ayuda(self):
    from vista.modal_chatbot import ModalChatbot
    modal = ModalChatbot(self)
    modal.exec()

  def ir_a_configuracion_examen(self, datos):
    self.vista_configuracion.cargar_datos(datos)
    self.cambiar_vista(6)

  def examen_creado_exito(self):
    # Cuando el examen se crea exitosamente, recargamos el dashboard y volvemos a la vista 0
    from utils.gestor_sesion import sesion_actual
    self.cargar_mis_examenes()
    self.cambiar_vista(0)

  def alternar_tema(self):
    self.modo_oscuro = not self.modo_oscuro
    if self.modo_oscuro:
      self.aplicar_tema_oscuro()
    else:
      self.aplicar_tema_claro()

  def aplicar_tema_claro(self):
    self.modo_oscuro = False
    self.btn_nav_tema.setText("Modo Noche")
    try:
      if not hasattr(self, '_css_claro_cache'):
        base_path = os.path.dirname(__file__)
        with open(os.path.join(base_path, "tema_claro.css"), "r", encoding="utf-8") as f:
          self._css_claro_cache = f.read()
      estilo = self._css_claro_cache
      self.setStyleSheet(estilo)
      for v in [self._vista_sala, self._vista_apelaciones, self._vista_detalle_est, self._vista_reporte, self._vista_carpetas]:
        if v is not None:
          v.setStyleSheet(estilo)
      if self._vista_admin is not None:
        self._vista_admin.setStyleSheet(estilo)
        self._vista_admin.aplicar_tema(False)
      if self._vista_reporte_admin is not None:
        self._vista_reporte_admin.setStyleSheet(estilo)
        self._vista_reporte_admin.aplicar_tema(False)
    except Exception as e:
      print(f"Error cargando CSS Claro: {e}")
    self.actualizar_estilos_sidebar(self.contenedor_vistas.currentIndex())

  def aplicar_tema_oscuro(self):
    self.modo_oscuro = True
    self.btn_nav_tema.setText("Modo Día")
    try:
      if not hasattr(self, '_css_oscuro_cache'):
        base_path = os.path.dirname(__file__)
        with open(os.path.join(base_path, "tema_oscuro.css"), "r", encoding="utf-8") as f:
          self._css_oscuro_cache = f.read()
      estilo = self._css_oscuro_cache
      self.setStyleSheet(estilo)
      for v in [self._vista_sala, self._vista_apelaciones, self._vista_detalle_est, self._vista_reporte, self._vista_carpetas]:
        if v is not None:
          v.setStyleSheet(estilo)
      if self._vista_admin is not None:
        self._vista_admin.setStyleSheet(estilo)
        self._vista_admin.aplicar_tema(True)
      if self._vista_reporte_admin is not None:
        self._vista_reporte_admin.setStyleSheet(estilo)
        self._vista_reporte_admin.aplicar_tema(True)
    except Exception as e:
      print(f"Error cargando CSS Oscuro: {e}")
    self.actualizar_estilos_sidebar(self.contenedor_vistas.currentIndex())

  def cerrar_sesion(self):
    resp = QMessageBox.question(self, "Cerrar Sesión", "¿Está seguro de cerrar sesión?", 
                  QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
    if resp == QMessageBox.StandardButton.Yes:
      sesion_actual.cerrar_sesion()
      self.close()
