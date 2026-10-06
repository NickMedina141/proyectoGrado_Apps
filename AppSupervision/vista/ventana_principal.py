from PyQt6.QtWidgets import QWidget, QMessageBox
from PyQt6.QtGui import QIcon, QRegularExpressionValidator
from PyQt6.QtCore import Qt, pyqtSignal, QRegularExpression, QThread, QTimer
from PyQt6.uic import loadUi
from api.cliente_respuesta import cliente_api
from utils.gestor_sesion import sesion_actual
import os
import time

from vista.modal_diagnostico_hardware import ModalDiagnosticoHardware, HiloPruebaAudio


class VentanaPrincipal(QWidget):
  senal_apelacion_terminada = pyqtSignal(bool, str)

  def __init__(self, app_principal=None):
    super().__init__()
    self.app_principal = app_principal
    self.senal_apelacion_terminada.connect(self._finalizar_apelacion)
    
    # Cargar UI
    ruta_ui = os.path.join(os.path.dirname(__file__), "ventana_principal.xml")
    loadUi(ruta_ui, self)
    
    # Identidad visual e ícono de la ventana
    self.setWindowTitle("UPC SecureExam - Entorno de Evaluación")
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ruta_ico = os.path.join(base_dir, "recursos", "installer_icon.ico")
    ruta_png = os.path.join(os.path.dirname(__file__), "recursos", "logo_upc.png")
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

    # Variables de diagnóstico previo de hardware
    self.hardware_ok = False
    self.camara_ok = False
    self.microfono_ok = False
    self.red_ok = True
    self.hilo_audio_test = None
    self.segundos_gracia_camara = 10
    self.timer_gracia_camara = None

    # Seguridad de Kiosko, Watchdog y Heartbeat
    self.proceso_watchdog = None
    self.timer_heartbeat = None
    dir_sup = os.path.join(os.getenv("LOCALAPPDATA", os.path.expanduser("~")), "SupervisionUPC")
    os.makedirs(dir_sup, exist_ok=True)
    self.ruta_bandera_limpia = os.path.join(dir_sup, "salida_limpia.flag")

    # Conectar botón para volver a comprobar hardware si se desea
    if hasattr(self, 'btn_reabrir_diagnostico'):
        self.btn_reabrir_diagnostico.clicked.connect(self._ejecutar_diagnostico_hardware)

    # Validación estricta en tiempo real para el PIN: solo alfanumérico
    validador_pin = QRegularExpressionValidator(QRegularExpression(r"^[A-Za-z0-9]{0,20}$"), self.entrada_pin)
    self.entrada_pin.setValidator(validador_pin)
    self.entrada_pin.textChanged.connect(self._formatear_pin_mayusculas)
    self.entrada_pin.textChanged.connect(self._actualizar_estado_boton_ingreso)
    self.entrada_pin.returnPressed.connect(self.procesar_pin)
    
    # Overlay de Bloqueo Inmediato por Desconexión de Red (30 min de gracia y max 3 cortes)
    from vista.overlay_desconexion import OverlayBloqueoDesconexion
    self.overlay_desconexion = OverlayBloqueoDesconexion(self)
    self.overlay_desconexion.tiempo_expirado.connect(
        lambda: self.finalizar_examen_por_desconexion("TIEMPO_DESCONEXION_EXCEDIDO")
    )
    self.overlay_desconexion.limite_desconexiones_superado.connect(
        lambda: self.finalizar_examen_por_desconexion("DESCONEXION_REINCIDENTE")
    )
    if hasattr(self, 'app_principal') and self.app_principal and hasattr(self.app_principal, 'gestor_temas'):
        self.app_principal.gestor_temas.tema_cambiado.connect(self.overlay_desconexion.aplicar_tema)
    
    logo_path = os.path.join(os.path.dirname(__file__), "recursos", "logo_upc.png").replace("\\", "/")
    if os.path.exists(logo_path) and hasattr(self, 'etiqueta_logo_pin'):
        self.etiqueta_logo_pin.setText("")
        self.etiqueta_logo_pin.setStyleSheet(f"border-image: url('{logo_path}'); border-radius: 30px;")
    
    # Conectar botones
    self.btn_ingresar_pin.clicked.connect(self.procesar_pin)
    self.btn_salir_examen.clicked.connect(self.salir_examen)
    self.btn_cambiar_tema.clicked.connect(self._cambiar_tema)
    self.btn_apelacion_examen.clicked.connect(self.ir_a_apelacion)
    self.btn_enviar_apelacion.clicked.connect(self.enviar_apelacion)
    self.btn_volver_login.clicked.connect(self.volver_al_login_desde_apelacion)
    self.btn_adjuntar_evidencia.clicked.connect(self.abrir_dialogo_evidencia)
    
    # Asegurarse de mostrar la pagina del PIN al iniciar
    self.stack_vistas.setCurrentIndex(0)
    
    # Configurar el Navegador Real
    self._configurar_navegador()
    
    # Variables de cámara
    self.hilo_camara = None
    
    # Activar Pantalla Maximizada (Devuelve los controles de ventana)
    self.showMaximized()
    
    # Overlay Spinner para transiciones y operaciones de red
    from vista.overlay_carga import OverlayCarga
    self.overlay_carga = OverlayCarga(self)
    
  def _configurar_navegador(self):
    """Configura el contenedor de pestañas para el motor web."""
    try:
      from PyQt6.QtWidgets import QTabWidget
      
      # 1. Crear el TabWidget
      self.tabs_navegador = QTabWidget()
      self.tabs_navegador.setDocumentMode(True)
      self.tabs_navegador.setTabsClosable(False)
      self.vl_contenedor_navegador.addWidget(self.tabs_navegador)
      
      # Lista para rastrear las urls maestras
      self.urls_maestras = []
      
    except ImportError as e:
      print(f"Error real al intentar cargar PyQt6: {e}")
      print("Puede que falten dependencias o haya conflicto de versiones.")

  def cargar_urls_permitidas(self, urls):
    """Carga las URLs permitidas en pestañas separadas y bloquea navegación externa."""
    from PyQt6.QtWebEngineWidgets import QWebEngineView
    from PyQt6.QtWebEngineCore import QWebEngineSettings
    from PyQt6.QtCore import QUrl
    
    # AulaWeb como primera pestaña fija
    aulaweb_url = "https://aulaweb.unicesar.edu.co/login/index.php"
    self.urls_maestras = [aulaweb_url]
    if urls:
        self.urls_maestras.extend(urls)
        
    self.tabs_navegador.clear()
    
    for idx, url_str in enumerate(self.urls_maestras):
      if not url_str.startswith("http"):
          url_str = "https://" + url_str
          
      from PyQt6.QtWebEngineCore import QWebEnginePage
      class PaginaSilenciosa(QWebEnginePage):
          def javaScriptConsoleMessage(self, level, message, lineNumber, sourceID):
              pass # Ignorar JS logs
      class NavegadorSeguro(QWebEngineView):
          def __init__(self):
              super().__init__()
              self.setPage(PaginaSilenciosa(self))
          def createWindow(self, _type):
              return self
          def contextMenuEvent(self, event):
              # Bloquea el menú contextual de clic derecho (evita inspeccionar elemento, copiar y pegar)
              event.ignore()

      navegador = NavegadorSeguro()
      settings = navegador.settings()
      settings.setAttribute(QWebEngineSettings.WebAttribute.PluginsEnabled, False)
      settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptCanOpenWindows, True)
      settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, False)
        
      profile = navegador.page().profile()
      profile.downloadRequested.connect(lambda item: item.cancel())
      profile.setHttpUserAgent("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
      dominios_sso = [
          "login.microsoftonline.com",
          "microsoftonline.com",
          "login.live.com",
          "accounts.google.com",
          "google.com"
      ]
        
      def url_changed_handler(nueva_url, nav=navegador, master=url_str):
        if getattr(self, 'examen_anulado', False):
            return
        host_nuevo = nueva_url.host()
        host_maestro = QUrl(master).host()
        permitido = (host_maestro in host_nuevo) or any(sso in host_nuevo for sso in dominios_sso)
        if not permitido:
           nav.setUrl(QUrl(master))
             
      navegador.urlChanged.connect(url_changed_handler)
      
      navegador.setUrl(QUrl(url_str))
      
      # Nombre corto para la pestaña
      host = QUrl(url_str).host().replace("www.", "")
      if idx == 0:
          self.tabs_navegador.addTab(navegador, "AulaWeb UPC")
      else:
          self.tabs_navegador.addTab(navegador, host)
      
  def _configurar_temporizador(self):
    """Configura el temporizador visual del examen."""
    from PyQt6.QtCore import QTimer
    self.timer_examen = QTimer(self)
    self.timer_examen.timeout.connect(self._actualizar_temporizador)
    self.timer_examen.start(1000) # Cada segundo
    self._actualizar_temporizador()
    
  def _actualizar_temporizador(self):
    if self.tiempo_restante > 0:
        self.tiempo_restante -= 1
        horas = self.tiempo_restante // 3600
        minutos = (self.tiempo_restante % 3600) // 60
        segundos = self.tiempo_restante % 60
        texto = f"Tiempo Restante: {horas:02d}:{minutos:02d}:{segundos:02d}"
        if hasattr(self, 'lbl_temporizador'):
            self.lbl_temporizador.setText(texto)
    else:
        self.timer_examen.stop()
        if hasattr(self, 'lbl_temporizador'):
            self.lbl_temporizador.setText("TIEMPO AGOTADO")
        # Auto finalizar
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.warning(self, "Tiempo Agotado", "El tiempo del examen ha concluido. La sesión se cerrará automáticamente.")
        self.finalizar_examen_forzado()
        
  def finalizar_examen_forzado(self):
      """Finaliza la sesión del examen abruptamente sin preguntar (por tiempo agotado)."""
      # Apagar módulos
      if self.hilo_camara:
        self.hilo_camara.detener()
        self.hilo_camara = None
        
      if hasattr(self, 'hilo_stream') and self.hilo_stream:
        self.hilo_stream.detener()
        self.hilo_stream = None
        
      try:
        from motor_ia.perifericos import monitor_perifericos
        monitor_perifericos.detener()
      except ImportError:
        pass
        
      from motor_ia.sistema import monitor_sys
      monitor_sys.detener()
      
      try:
        from motor_ia.audio import monitor_audio
        monitor_audio.detener()
      except Exception:
        pass

      # Detener el Centinela de Red
      if hasattr(self, 'monitor_red') and self.monitor_red:
        try:
          self.monitor_red.detener()
          self.monitor_red = None
        except Exception:
          pass

      # Desactivar Modo Kiosko Seguro y Vigilancia Remota
      try:
        from utils.modo_kiosko import gestor_kiosko
        gestor_kiosko.desactivar_kiosko()
      except Exception:
        pass

      try:
        from motor_ia.anti_remoto import blindaje_remoto
        blindaje_remoto.detener_vigilancia()
      except Exception:
        pass

      if getattr(self, 'wts_registrado', False):
        try:
          import ctypes
          ctypes.windll.wtsapi32.WTSUnRegisterSessionNotification(int(self.winId()))
          self.wts_registrado = False
        except Exception:
          pass

      if hasattr(self, 'timer_heartbeat') and self.timer_heartbeat:
        self.timer_heartbeat.stop()

      # Marcar salida limpia para que el watchdog no alerte
      try:
        with open(self.ruta_bandera_limpia, "w") as f:
          f.write("CLEAN_EXIT")
      except Exception:
        pass

      if getattr(self, 'proceso_watchdog', None):
        try:
          self.proceso_watchdog.terminate()
        except Exception:
          pass
        self.proceso_watchdog = None
        
      # Limpiar vista y enviar API
      sesion_id = sesion_actual.obtener_sesion_id()
      if sesion_id:
        cliente_api.finalizar_sesion_examen(sesion_id)
        
      sesion_actual.cerrar_sesion()
      self.entrada_pin.clear()
      self.tabs_navegador.clear()
      if self.app_principal:
        self.app_principal.mostrar_ventana_login()
    
  def iniciar_camara(self):
    # [PREPARATIVO] Biometría Facial y Liveness Detection
    # Listo para usarse cuando se active:
    # from motor_ia.biometria_facial import BiometriaFacial
    # self.biometria = BiometriaFacial()

    from vista.hilo_camara import HiloCamara
    from PyQt6.QtGui import QPixmap
    from api.cliente_respuesta import HiloStreamEstudiante
    from PyQt6.QtWidgets import QLabel
    from PyQt6.QtCore import Qt
    
    # --- NUEVO: Crear los ojos en la barra lateral (Animado) ---
    if not hasattr(self, "lbl_ojos"):
      from vista.faro_animado import FaroAnimado
      self.lbl_ojos = FaroAnimado(self)
      # Insertar en la posicion 2 (debajo de estado_monitoreo), centrado para que NO empuje ni estire nada
      self.frame_supervision.layout().insertWidget(2, self.lbl_ojos, 0, Qt.AlignmentFlag.AlignCenter)
      
      # Fijar texto (con un espacio inicial para que no se corte el emoji) adaptado al tema actual
      self.estado_monitoreo.setText(" Tu actividad está siendo supervisada")
      self.estado_monitoreo.setStyleSheet("font-weight: bold; font-size: 13px;")

    if self.hilo_camara is None:
      # 1. Arrancamos el Túnel WebSocket STOMP
      sesion_id = sesion_actual.obtener_sesion_id()
      self.hilo_stream = HiloStreamEstudiante(sesion_id)
      self.hilo_stream.comando_recibido.connect(self._al_recibir_comando_ws)
      self.hilo_stream.estado_conexion.connect(self.manejar_estado_red)
      self.hilo_stream.start()
      
      # 1.5. Arrancamos el Centinela Activo de Red (Sondeo rápido de socket cada 1.5s)
      from utils.monitor_red import MonitorRed
      self.monitor_red = MonitorRed()
      self.monitor_red.senal_estado_red.connect(self.manejar_estado_red)
      self.monitor_red.start()
      
      # 2. Arrancamos la Cámara Local
      self.hilo_camara = HiloCamara()
      def _actualizar_frame_seguro(img):
          if not getattr(self, "examen_anulado", False):
              self.lbl_camara.setPixmap(QPixmap.fromImage(img))
      self.hilo_camara.senal_frame.connect(_actualizar_frame_seguro)
      self.hilo_camara.senal_advertencia.connect(self.actualizar_indicador_buho)
      self.hilo_camara.senal_camara_obstruida.connect(self._manejar_camara_obstruida)
      self.hilo_camara.senal_error.connect(self._manejar_error_camara)
      
      # 3. Conectamos la IA con el Túnel
      self.hilo_camara.senal_frame_anotado.connect(self.hilo_stream.enviar_frame_stream)
      self.hilo_camara.start()
      
      # 4. Iniciar Monitor de Perifericos (Teclado/Mouse silencioso)
      try:
        from motor_ia.perifericos import monitor_perifericos
        # Le pasamos la alerta al cliente_api para que lo mande al profe (como el de sistema)
        monitor_perifericos.funcion_alerta = lambda evidencia: cliente_api.enviar_alerta(sesion_id, evidencia)
        monitor_perifericos.iniciar()
      except ImportError:
        print("ADVERTENCIA: La librería 'pynput' no está instalada. El monitor de teclado está inactivo.")
      
  def actualizar_indicador_buho(self, riesgo):
    """Actualiza el indicador visual de distraccion progresiva"""
    if getattr(self, "examen_anulado", False):
        return
    if not hasattr(self, "lbl_ojos"):
      return
    
    # Notificamos al widget de ojos animados sobre el nuevo nivel de riesgo
    self.lbl_ojos.set_riesgo(riesgo)
    
    # Cambiamos unicamente el texto explicativo y su color
    if riesgo <= 0:
      self.estado_monitoreo.setText(" Tu actividad está siendo supervisada")
      self.estado_monitoreo.setStyleSheet("font-weight: bold; font-size: 13px; color: #196F3D;")
    elif riesgo == 1:
      self.estado_monitoreo.setText(" Tu actividad está siendo supervisada")
      self.estado_monitoreo.setStyleSheet("font-weight: bold; font-size: 13px;")
    elif riesgo == 2:
      self.estado_monitoreo.setText(" Estás desviando la mirada")
      self.estado_monitoreo.setStyleSheet("font-weight: bold; font-size: 13px; color: #D4AC0D;")
    elif riesgo == 3:
      self.estado_monitoreo.setText(" Vuelve a mirar a la pantalla")
      self.estado_monitoreo.setStyleSheet("font-weight: bold; font-size: 13px; color: #D35400;")
    elif riesgo == 4:
      self.estado_monitoreo.setText(" Mira a la pantalla AHORA")
      self.estado_monitoreo.setStyleSheet("font-weight: bold; font-size: 13px; color: #E67E22;")
    elif riesgo >= 5:
      self.estado_monitoreo.setText(" Mirad a la camara inmediatamente esta en problemas")
      self.estado_monitoreo.setStyleSheet("font-weight: bold; font-size: 13px; color: #C0392B;")

  def _ejecutar_diagnostico_hardware(self):
    """Abre el modal de verificación de hardware y audio."""
    from vista.modal_diagnostico_hardware import ModalDiagnosticoHardware
    from PyQt6.QtWidgets import QDialog
    modal = ModalDiagnosticoHardware(self)
    resultado = modal.exec()
    if resultado == QDialog.DialogCode.Accepted:
        self.hardware_ok = True
        self.camara_ok = True
        self.microfono_ok = True
        self.red_ok = True
        if hasattr(self, 'lbl_estado_hardware'):
            self.lbl_estado_hardware.setText("✓ Dispositivos y audio comprobados")
            self.lbl_estado_hardware.setStyleSheet("color: #196F3D; font-weight: bold;")
    else:
        self.hardware_ok = False
        self.camara_ok = False
        self.microfono_ok = False
        if hasattr(self, 'lbl_estado_hardware'):
            self.lbl_estado_hardware.setText("⚠️ Hardware no verificado")
            self.lbl_estado_hardware.setStyleSheet("color: #C0392B; font-weight: bold;")
    self._actualizar_estado_boton_ingreso()

  def _actualizar_estado_boton_ingreso(self):
    pin = self.entrada_pin.text().strip() if hasattr(self, 'entrada_pin') else ""
    hw_listo = getattr(self, 'hardware_ok', False)
    if hasattr(self, 'btn_ingresar_pin'):
        self.btn_ingresar_pin.setEnabled(bool(pin and hw_listo))

  def _manejar_camara_obstruida(self, obstruida: bool, frame_b64: str = ""):
    if getattr(self, "examen_anulado", False):
        return

    if obstruida:
        if frame_b64:
            cliente_api.enviar_evidencia_silenciosa(["CAMARA_OBSTRUIDA"], frame_base64=frame_b64)

        if not hasattr(self, "overlay_camara_obstruida"):
            from PyQt6.QtWidgets import QFrame, QLabel, QVBoxLayout
            self.overlay_camara_obstruida = QFrame(self)
            self.overlay_camara_obstruida.setStyleSheet("""
                QFrame {
                    background-color: rgba(15, 23, 42, 242);
                    color: white;
                }
                QLabel#titulo_obs {
                    color: #E74C3C;
                    font-size: 24px;
                    font-weight: bold;
                }
                QLabel#desc_obs {
                    color: #ECEFF1;
                    font-size: 14px;
                }
                QLabel#timer_obs {
                    color: #F39C12;
                    font-size: 28px;
                    font-weight: bold;
                    padding: 8px;
                }
            """)
            lay = QVBoxLayout(self.overlay_camara_obstruida)
            lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lay.setSpacing(14)
            
            lbl_tit = QLabel("⚠️ CÁMARA WEB TAPADA U OBSTRUIDA", self.overlay_camara_obstruida)
            lbl_tit.setObjectName("titulo_obs")
            lbl_tit.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lay.addWidget(lbl_tit)

            lbl_desc = QLabel(
                "Se ha detectado la lente de la cámara completamente cubierta o la tapa cerrada.\n"
                "Por favor, abre la cubierta de la cámara web inmediatamente.\n\n"
                "El examen se encuentra pausado para garantizar la integridad académica.",
                self.overlay_camara_obstruida
            )
            lbl_desc.setObjectName("desc_obs")
            lbl_desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lay.addWidget(lbl_desc)

            self.lbl_timer_obs = QLabel("Anulación definitiva en: 10 s", self.overlay_camara_obstruida)
            self.lbl_timer_obs.setObjectName("timer_obs")
            self.lbl_timer_obs.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lay.addWidget(self.lbl_timer_obs)

        self.overlay_camara_obstruida.setGeometry(0, 0, self.width(), self.height())
        self.overlay_camara_obstruida.show()
        self.overlay_camara_obstruida.raise_()

        self.segundos_gracia_camara = 10
        self.lbl_timer_obs.setText(f"Anulación definitiva en: {self.segundos_gracia_camara} s")
        
        if not hasattr(self, "timer_gracia_camara") or self.timer_gracia_camara is None:
            self.timer_gracia_camara = QTimer(self)
            self.timer_gracia_camara.setInterval(1000)
            self.timer_gracia_camara.timeout.connect(self._tick_gracia_camara)
        
        if not self.timer_gracia_camara.isActive():
            self.timer_gracia_camara.start()

    else:
        if hasattr(self, "timer_gracia_camara") and self.timer_gracia_camara and self.timer_gracia_camara.isActive():
            self.timer_gracia_camara.stop()
        if hasattr(self, "overlay_camara_obstruida"):
            self.overlay_camara_obstruida.hide()

  def _tick_gracia_camara(self):
    self.segundos_gracia_camara -= 1
    if hasattr(self, "lbl_timer_obs"):
        self.lbl_timer_obs.setText(f"Anulación definitiva en: {self.segundos_gracia_camara} s")

    if self.segundos_gracia_camara <= 0:
        if hasattr(self, "timer_gracia_camara") and self.timer_gracia_camara:
            self.timer_gracia_camara.stop()
        self._anular_examen_por_obstruccion()

  def _anular_examen_por_obstruccion(self):
    self.examen_anulado = True
    if hasattr(self, "overlay_camara_obstruida"):
        self.overlay_camara_obstruida.hide()
    
    QMessageBox.critical(
        self,
        "Examen Anulado",
        "Tu sesión de examen ha sido anulada debido a que la cámara web permaneció tapada u obstruida durante más de 10 segundos continuos.\n\n"
        "Se ha registrado la evidencia en el sistema institucional. Si consideras que se trató de un fallo técnico, puedes presentar una solicitud de segunda revisión."
    )
    self.ir_a_apelacion()

  def _manejar_error_camara(self, error_str):
    if getattr(self, "examen_anulado", False):
        return
    self._manejar_camara_obstruida(True, "")

  def _formatear_pin_mayusculas(self, texto):
    texto_mayus = texto.upper()
    if texto != texto_mayus:
      pos = self.entrada_pin.cursorPosition()
      self.entrada_pin.setText(texto_mayus)
      self.entrada_pin.setCursorPosition(pos)

  def procesar_pin(self):
    pin = self.entrada_pin.text().strip().upper()
    
    if not pin:
      QMessageBox.warning(self, "PIN Requerido", "Por favor ingresa el PIN del examen.")
      return

    if not pin.isalnum():
      QMessageBox.warning(self, "PIN Inválido", "El PIN debe contener únicamente caracteres alfanuméricos (números y letras).")
      return

    # Verificación estricta de Hardware obligatorio
    if not getattr(self, 'hardware_ok', False) or not getattr(self, 'camara_ok', False) or not getattr(self, 'microfono_ok', False):
      self._ejecutar_diagnostico_hardware()
      if not getattr(self, 'hardware_ok', False):
        QMessageBox.warning(
          self,
          "Requisitos de Hardware no Cumplidos",
          "Para iniciar la evaluación es obligatorio disponer de una cámara web y un micrófono funcionales.\n\n"
          "Si tu equipo presenta fallas físicas o de controlador, por favor acude a las salas de cómputo de la UPC para presentar tu examen de manera presencial."
        )
        return
      
    self.btn_ingresar_pin.setEnabled(False)
    self.btn_ingresar_pin.setText("Validando...")
    
    estudiante_id = sesion_actual.obtener_estudiante_id()

    def _tarea_verificar_pin():
        # Verificación estricta previa de entorno de seguridad (VM, cámaras virtuales, RDP, monitores)
        from motor_ia.anti_remoto import blindaje_remoto
        ok_entorno, motivo_entorno = blindaje_remoto.verificar_entorno_previo()
        if not ok_entorno:
            return False, motivo_entorno, False, {}

        # 1. Llamar a la API para validar PIN (incluye GPS y detección de VPN)
        exito_api, resp_api = cliente_api.iniciar_sesion_examen(estudiante_id, pin)
        if not exito_api:
            return False, resp_api, False, {}
        s_id = resp_api.get("sesionId", "")
        # 2. Descargar Reglas del Examen
        ex_reglas, datos_reglas = cliente_api.obtener_reglas_examen(s_id)
        return True, resp_api, ex_reglas, datos_reglas

    def _al_terminar_pin(resultado):
        self.btn_ingresar_pin.setEnabled(True)
        self.btn_ingresar_pin.setText("Ingresar")
        
        exito, respuesta, exito_reglas, reglas = resultado
        
        if not exito:
            QMessageBox.critical(self, "Acceso al Examen", str(respuesta))
            return
            
        sesion_id = respuesta.get("sesionId", "")
        
        # Detener hilo de prueba de audio para liberar el micrófono para el monitor del examen
        if getattr(self, 'hilo_audio_test', None):
            self.hilo_audio_test.detener()
        
        # Inyectar URLs dinámicas
        urls = reglas.get("urls_permitidas", []) if exito_reglas else []
        self.cargar_urls_permitidas(urls)
        
        # Configurar Temporizador Visual
        if exito_reglas and reglas.get("duracion_examen"):
           self.tiempo_restante = reglas.get("duracion_examen") * 60
           self._configurar_temporizador()
        
        # Inyectar reglas a módulos IA y Kiosko Adaptativo
        from motor_ia.sistema import monitor_sys
        from utils.modo_kiosko import gestor_kiosko
        
        monitor_sys.funcion_alerta = lambda evidencia: cliente_api.enviar_alerta(sesion_id, evidencia)
        
        procesos_examen = reglas.get("procesos_permitidos", []) if (exito_reglas and "procesos_permitidos" in reglas) else []
        monitor_sys.actualizar_lista_blanca(procesos_examen)
        gestor_kiosko.actualizar_procesos_permitidos(procesos_examen)
          
        monitor_sys.iniciar()
          
        sensibilidad = "MEDIA"
        if exito_reglas:
          sensibilidad = reglas.get("sensibilidad_ia") or reglas.get("sensibilidadIA") or "MEDIA"

        # Detener la prueba de audio preliminar para liberar el hardware del micrófono
        if hasattr(self, 'hilo_audio_test') and self.hilo_audio_test:
          self.hilo_audio_test.detener()
          self.hilo_audio_test = None

        try:
          from motor_ia.audio import monitor_audio
          monitor_audio.funcion_alerta = lambda evidencia: cliente_api.enviar_alerta(sesion_id, evidencia)
          monitor_audio.configurar_sensibilidad(sensibilidad)
          monitor_audio.iniciar()
        except Exception:
          pass
          
        try:
          import requests
          requests.post("http://127.0.0.1:8005/configurar_sensibilidad", json={"nivel": sensibilidad}, timeout=1.0)
        except Exception:
          pass
          
        # Cambiar a la vista del examen
        self.stack_vistas.setCurrentIndex(1)
        self.iniciar_camara()

        # 1. Activar Modo Kiosko Seguro (Pantalla completa fija, hook de teclado, taskmgr off)
        try:
          gestor_kiosko.funcion_alerta = lambda ev: cliente_api.enviar_alerta(sesion_id, ev)
          gestor_kiosko.activar_kiosko(self)
        except Exception as e:
          print(f"[KIOSKO] Error al activar modo kiosko: {e}")

        # 1.1 Ejecutar Barrido Forense Inicial (inspecciona procesos, fotografía evidencia y cierra no autorizados)
        try:
          monitor_sys.ejecutar_barrido_inicial(procesos_examen)
        except Exception as e:
          print(f"[BARRIDO INICIAL] Error durante el barrido forense: {e}")

        # 2. Registrar Notificaciones de Bloqueo de Sesión y Cambio de Usuario (Wtsapi32)
        try:
          import ctypes
          hwnd = int(self.winId())
          ctypes.windll.wtsapi32.WTSRegisterSessionNotification(hwnd, 0)
          self.wts_registrado = True
          print("[SESION WINDOWS] WTSRegisterSessionNotification activo contra bloqueo y cambio de usuario.")
        except Exception as e:
          print(f"[SESION WINDOWS] Error registrando WTS: {e}")

        # 3. Iniciar Vigilancia y Blindaje Anti-Control Remoto
        try:
          from motor_ia.anti_remoto import blindaje_remoto
          blindaje_remoto.funcion_alerta = lambda ev: cliente_api.enviar_alerta(sesion_id, ev)
          blindaje_remoto.iniciar_vigilancia()
        except Exception as e:
          print(f"[ANTI-REMOTO] Error al iniciar vigilancia: {e}")

        # 3. Iniciar Heartbeat periódico hacia el backend
        self._iniciar_heartbeat(sesion_id)

        # 4. Iniciar Proceso Watchdog Supervisor
        self._iniciar_watchdog(sesion_id)
        
        # Ventana de advertencia al estudiante (Dentro de la supervisión)
        msg = QMessageBox(self)
        msg.setWindowTitle("Términos de Supervisión Activa")
        msg.setText("<h3>Tu sesión de examen está siendo monitoreada.</h3>")
        msg.setInformativeText(
          "Ten en cuenta las siguientes reglas de seguridad:\n\n"
          " Tu cámara y micrófono están siendo grabados por IA.\n"
          " Se registra el uso de aplicaciones, teclado y pantalla completa.\n"
          " Intentar minimizar la ventana, cerrarla o usar atajos prohibidos generará evidencia de fraude al instante.\n\n"
          "Mucho éxito en tu prueba."
        )
        msg.setStyleSheet("""
          QMessageBox {
            background-color: #ffffff;
          }
          QLabel {
            color: #2c3e50;
            font-size: 13px;
          }
          QPushButton {
            background-color: #27AE60;
            color: white;
            font-weight: bold;
            padding: 8px 20px;
            border-radius: 4px;
            min-width: 100px;
          }
          QPushButton:hover {
            background-color: #219653;
          }
        """)
        msg.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg.button(QMessageBox.StandardButton.Ok).setText("Entendido")
        msg.exec()

    self.overlay_carga.ejecutar_tarea(
        _tarea_verificar_pin,
        _al_terminar_pin,
        mensaje="Validando PIN y verificando entorno..."
    )
    
  def salir_examen(self):
    respuesta = QMessageBox.question(self, "Salir del Examen", "¿Estás seguro que deseas finalizar y salir del sistema de supervisión?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
    
    if respuesta == QMessageBox.StandardButton.Yes:
      # Apagar módulos
      if self.hilo_camara:
        self.hilo_camara.detener()
        self.hilo_camara = None
        
      if hasattr(self, 'hilo_stream') and self.hilo_stream:
        self.hilo_stream.detener()
        self.hilo_stream = None
        
      try:
        from motor_ia.perifericos import monitor_perifericos
        monitor_perifericos.detener()
      except ImportError:
        pass # Si no estaba instalada la libreria pynput, no hacemos nada
        
      from motor_ia.sistema import monitor_sys
      monitor_sys.detener()
      
      try:
        from motor_ia.audio import monitor_audio
        monitor_audio.detener()
      except Exception:
        pass

      if hasattr(self, 'hilo_audio_test') and self.hilo_audio_test:
        self.hilo_audio_test.detener()
        self.hilo_audio_test = None
      if hasattr(self, 'timer_gracia_camara') and self.timer_gracia_camara:
        self.timer_gracia_camara.stop()
      if hasattr(self, 'overlay_camara_obstruida'):
        self.overlay_camara_obstruida.hide()

      # Desactivar Modo Kiosko Seguro y Vigilancia Remota
      try:
        from utils.modo_kiosko import gestor_kiosko
        gestor_kiosko.desactivar_kiosko()
      except Exception:
        pass

      try:
        from motor_ia.anti_remoto import blindaje_remoto
        blindaje_remoto.detener_vigilancia()
      except Exception:
        pass

      if getattr(self, 'wts_registrado', False):
        try:
          import ctypes
          ctypes.windll.wtsapi32.WTSUnRegisterSessionNotification(int(self.winId()))
          self.wts_registrado = False
        except Exception:
          pass

      if hasattr(self, 'timer_heartbeat') and self.timer_heartbeat:
        self.timer_heartbeat.stop()

      # Marcar salida limpia para que el watchdog no alerte
      try:
        with open(self.ruta_bandera_limpia, "w") as f:
          f.write("CLEAN_EXIT")
      except Exception:
        pass

      if getattr(self, 'proceso_watchdog', None):
        try:
          self.proceso_watchdog.terminate()
        except Exception:
          pass
        self.proceso_watchdog = None
      
      # Avisar al backend que se finaliza la sesion
      sesion_id = sesion_actual.obtener_sesion_id()
      if sesion_id:
        cliente_api.finalizar_sesion_examen(sesion_id)
      sesion_actual.cerrar_sesion()
      if self.app_principal:
        self.app_principal.mostrar_ventana_login()

  def _iniciar_heartbeat(self, sesion_id):
    if hasattr(self, 'timer_heartbeat') and self.timer_heartbeat:
      self.timer_heartbeat.stop()
    self.timer_heartbeat = QTimer(self)
    self.timer_heartbeat.setInterval(6000)
    def _tick():
      dev_id = sesion_actual.obtener_device_id()
      ok, resp = cliente_api.enviar_heartbeat(sesion_id, dev_id)
      if ok and isinstance(resp, dict):
        if resp.get("estadoSesion") == "ANULADA":
          self.timer_heartbeat.stop()
          self.recibir_anulacion_servidor()
      elif not ok and resp == "DISPOSITIVO_NO_AUTORIZADO":
        self.timer_heartbeat.stop()
        QMessageBox.critical(self, "Dispositivo no Autorizado", "Tu sesión ha sido suspendida porque no coincide el identificador del equipo autorizado.")
        self.finalizar_examen_forzado()
    self.timer_heartbeat.timeout.connect(_tick)
    self.timer_heartbeat.start()

  def _iniciar_watchdog(self, sesion_id):
    try:
      import subprocess
      if os.path.exists(self.ruta_bandera_limpia):
        os.remove(self.ruta_bandera_limpia)
      base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
      watchdog_py = os.path.join(base_dir, "utils", "watchdog.py")
      token = sesion_actual.obtener_token() or ""
      self.proceso_watchdog = subprocess.Popen(
        [sys.executable, watchdog_py, str(os.getpid()), sesion_id, self.ruta_bandera_limpia, token],
        creationflags=0x08000000
      )
      print(f"[WATCHDOG] Proceso supervisor lanzado con PID: {self.proceso_watchdog.pid}")
    except Exception as e:
      print(f"[WATCHDOG] No se pudo lanzar proceso supervisor: {e}")

  def _cambiar_tema(self):
    if self.app_principal:
      self.app_principal.gestor_temas.alternar_tema()

  def recibir_anulacion_servidor(self):
    self.examen_anulado = True
    self.estado_monitoreo.setText(" EXAMEN ANULADO POR FRAUDE")
    self.estado_monitoreo.setStyleSheet("color: #C0392B; font-weight: bold;")
    
    if hasattr(self, 'timer_examen'):
        self.timer_examen.stop()
    if hasattr(self, 'lbl_ojos'):
        self.lbl_ojos.set_riesgo(5)
        self.lbl_ojos.timer_animacion.stop()
        self.lbl_ojos.timer_parpadeo.stop()
        
    html_bloqueo = "<div style='display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100vh; font-family: Georgia, serif; background: #F5F5F5;'><div style='border: 1px solid #CCCCCC; padding: 50px 70px; text-align: center; background: white;'><h1 style='color: #2C3E50; font-size: 36px; font-weight: normal; letter-spacing: 2px; margin-bottom: 16px;'>Acceso Suspendido</h1><hr style='border: none; border-top: 1px solid #CCCCCC; margin: 20px auto; width: 60px;'><p style='font-size: 15px; color: #555555; line-height: 1.7; font-family: Arial, sans-serif;'>Su sesión de evaluación ha sido suspendida por disposición del docente supervisor.<br>Si considera que esto es un error, utilice el botón de apelación disponible en la aplicación.</p></div></div>"
    if hasattr(self, 'tabs_navegador'):
        for i in range(self.tabs_navegador.count()):
            nav = self.tabs_navegador.widget(i)
            if hasattr(nav, 'setHtml'):
                nav.setHtml(html_bloqueo)
    elif hasattr(self, 'navegador') and self.navegador:
        self.navegador.setHtml(html_bloqueo)
        
    self.btn_apelacion_examen.setEnabled(True)
    self.btn_salir_examen.setEnabled(False)
    
    QMessageBox.warning(self, "Anulación de Examen", "Su examen fue anulado por fraude. Si desea solicitar una segunda revisión de su caso, complete el formulario a continuación.")

  def ir_a_apelacion(self):
    """Cambia a la vista de apelación."""
    self.stack_vistas.setCurrentIndex(2)
    
  def volver_al_login_desde_apelacion(self, finalizar_backend=True):
    """Vuelve a la pantalla de login después de apelar o ser bloqueado."""
    sesion_id = sesion_actual.obtener_sesion_id()
    if sesion_id and finalizar_backend:
      cliente_api.finalizar_sesion_examen(sesion_id)
    sesion_actual.cerrar_sesion()
    if self.app_principal:
      self.app_principal.mostrar_ventana_login()

  def abrir_dialogo_evidencia(self):
    """Abre un diálogo para seleccionar una imagen como evidencia."""
    from PyQt6.QtWidgets import QFileDialog
    import os
    archivo, _ = QFileDialog.getOpenFileName(
      self, 
      "Seleccionar Captura de Pantalla o Evidencia", 
      "", 
      "Imágenes (*.png *.jpg *.jpeg)"
    )
    if archivo:
      nombre_archivo = os.path.basename(archivo)
      self.btn_adjuntar_evidencia.setText(f"Evidencia Adjunta: {nombre_archivo}")
      self.btn_adjuntar_evidencia.setStyleSheet("color: #147B2C; border: 1px solid #147B2C; background-color: #E8F5E9;")

  def changeEvent(self, event):
    """Detecta si el usuario minimiza la ventana o cambia el foco a otra aplicacion durante el examen."""
    from PyQt6.QtCore import QEvent
    if hasattr(self, 'stack_vistas') and self.isVisible() and self.stack_vistas.currentIndex() == 1:
      if event.type() == QEvent.Type.WindowStateChange:
        if self.isMinimized():
          self._reportar_trampa_ventana("El estudiante minimizó la aplicación (falsa esperanza).")
      elif event.type() == QEvent.Type.ActivationChange:
        if not self.isActiveWindow():
          self._reportar_trampa_ventana("La aplicación perdió el foco (posible trampa).")
    super().changeEvent(event)

  def closeEvent(self, event):
    """Detecta intento de cierre mediante la X y reporta trampa antes de salir completamente."""
    from PyQt6.QtWidgets import QMessageBox
    respuesta = QMessageBox.question(self, "Cerrar Aplicación", "¿Estás seguro que deseas cerrar la aplicación? Si estás en un examen, esto se reportará como abandono forzado.", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
    
    if respuesta == QMessageBox.StandardButton.Yes:
      self._reportar_trampa_ventana("Intento de cierre forzado de la aplicación (Botón X).")
      # Apagar módulos
      if self.hilo_camara:
        self.hilo_camara.detener()
        self.hilo_camara = None
        
      if hasattr(self, 'hilo_stream') and self.hilo_stream:
        self.hilo_stream.detener()
        
      from api.cliente_respuesta import cliente_api
      from utils.gestor_sesion import sesion_actual
      sesion_id = sesion_actual.obtener_sesion_id()
      if sesion_id:
        cliente_api.finalizar_sesion_examen(sesion_id)
      
      try:
        from motor_ia.sistema import monitor_sys
        monitor_sys.detener()
      except Exception:
        pass
        
      try:
        from motor_ia.audio import monitor_audio
        monitor_audio.detener()
      except Exception:
        pass

      if hasattr(self, 'hilo_audio_test') and self.hilo_audio_test:
        self.hilo_audio_test.detener()
        self.hilo_audio_test = None
      if hasattr(self, 'timer_gracia_camara') and self.timer_gracia_camara:
        self.timer_gracia_camara.stop()
        
      event.accept() # Permite el cierre de la ventana
      import sys
      sys.exit(0) # Cierra completamente toda la app
    else:
      event.ignore() # Cancela el cierre

  def _reportar_trampa_ventana(self, detalle):
    try:
      from api.cliente_respuesta import cliente_api
      from motor_ia.sistema import monitor_sys
      # Reutilizamos la captura de pantalla que ya implementamos
      img_b64 = monitor_sys._capturar_pantalla_b64()
      evidencia = {
        "tipo_alerta": "INTENTO_EVASION_INTERFAZ",
        "detalle": detalle,
        "evidencia_grafica": img_b64
      }
      cliente_api.enviar_evidencia_silenciosa([evidencia])
    except Exception:
      pass

  def _al_recibir_comando_ws(self, datos):
    comando = datos.get("comando")
    if comando == "VOZ_PROFESOR":
      self.procesar_voz_profesor(datos)
    elif comando == "ADVERTENCIA":
      mensaje = datos.get("mensaje", "Por favor revisa tu comportamiento en el examen.")
      QMessageBox.warning(self, "Advertencia del Profesor", mensaje)
      
    elif comando == "FRAUDE":
      motivo = datos.get("mensaje", "Violación grave de seguridad.")
      QMessageBox.critical(self, " EXAMEN ANULADO", f"Tu examen ha sido cancelado por fraude.\nMotivo: {motivo}\n\nLos procesos de supervisión han sido detenidos.")
      
      # Detener todos los hilos de IA y WebSockets
      if self.hilo_camara:
        self.hilo_camara.detener()
        self.hilo_camara = None
        
      if hasattr(self, 'hilo_stream') and self.hilo_stream:
        self.hilo_stream.detener()
        self.hilo_stream = None
        
      try:
        from motor_ia.perifericos import monitor_perifericos
        monitor_perifericos.detener()
      except ImportError:
        pass
        
      try:
        from motor_ia.sistema import monitor_sys
        monitor_sys.detener()
      except ImportError:
        pass
        
      try:
        from motor_ia.audio import monitor_audio
        monitor_audio.detener()
      except ImportError:
        pass
      
      # Quitar la cámara de la interfaz visualmente
      self.lbl_camara.clear()
      self.lbl_camara.setStyleSheet("background-color: black; color: white;")
      self.lbl_camara.setText("Cámara apagada por anulación.")
      
      # Disparar la interfaz de anulación/apelación
      self.recibir_anulacion_servidor()
  def enviar_apelacion(self):
    argumento = self.entrada_apelacion.toPlainText().strip()
    if not argumento:
      from PyQt6.QtWidgets import QMessageBox
      QMessageBox.warning(self, "Atención", "Por favor, escribe el motivo de tu apelación.")
      return
      
    self.btn_enviar_apelacion.setEnabled(False)
    self.btn_enviar_apelacion.setText("Enviando...")
    self.overlay_carga.mostrar("Enviando apelación al profesor...")
    
    from utils.gestor_sesion import sesion_actual
    sesion_id = sesion_actual.obtener_sesion_id()
    
    import threading
    def tarea_enviar():
      try:
        from api.cliente_respuesta import cliente_api
        exito, mensaje = cliente_api.solicitar_apelacion(sesion_id, argumento)
        self.senal_apelacion_terminada.emit(exito, mensaje)
      except Exception as e:
        self.senal_apelacion_terminada.emit(False, str(e))
      
    threading.Thread(target=tarea_enviar, daemon=True).start()

  def _finalizar_apelacion(self, exito, mensaje):
    self.overlay_carga.ocultar()
    from PyQt6.QtWidgets import QMessageBox
    self.btn_enviar_apelacion.setEnabled(True)
    self.btn_enviar_apelacion.setText("Solicitar Segunda Revisión al Profesor")
    if exito:
      QMessageBox.information(self, "Apelación Enviada", "Su solicitud ha sido enviada exitosamente al profesor.")
      self.entrada_apelacion.clear()
      self.volver_al_login_desde_apelacion(finalizar_backend=False)
    else:
      QMessageBox.warning(self, "Error", f"No se pudo enviar la apelación: {mensaje}")


  def manejar_estado_red(self, conectado):
    from api.cliente_respuesta import cliente_api
    cliente_api.conectado = conectado

    if conectado:
      if hasattr(self, 'overlay_desconexion'):
        self.overlay_desconexion.restablecer_conexion()
      if hasattr(self, 'tabs_navegador') and self.tabs_navegador:
        self.tabs_navegador.show()
    else:
      # Ocultar inmediatamente las preguntas del examen para que no puedan fotografiarla offline
      if hasattr(self, 'tabs_navegador') and self.tabs_navegador:
        self.tabs_navegador.hide()
      if hasattr(self, 'overlay_desconexion'):
        self.overlay_desconexion.resize(self.size())
        self.overlay_desconexion.iniciar_bloqueo()

  def finalizar_examen_por_desconexion(self, motivo):
    """Finaliza el examen de manera definitiva si se supera el tiempo offline (30m) o reincidencias (>3)."""
    sesion_id = sesion_actual.obtener_sesion_id()
    print(f"[SEGURIDAD RED] Finalizando examen por motivo de red: {motivo}")

    if motivo == "TIEMPO_DESCONEXION_EXCEDIDO":
      titulo = "Tiempo de Reconexión Expirado"
      mensaje = (
          "El tiempo límite de espera sin conexión a internet (30 minutos) ha expirado.\n\n"
          "Por motivos de integridad académica y seguridad del examen, "
          "la sesión ha sido finalizada automáticamente."
      )
      clase = "DESCONEXION_PROLONGADA"
    else:
      titulo = "Límite de Desconexiones Superado"
      mensaje = (
          "Se ha detectado una reincidencia de desconexiones que excede el límite permitido "
          "(más de 3 interrupciones de red durante la sesión).\n\n"
          "Por protocolos de seguridad, el examen ha sido finalizado automáticamente."
      )
      clase = "DESCONEXION_REINCIDENTE"

    if sesion_id:
      from api.cliente_respuesta import cliente_api
      carga_util = {
          "claseAlerta": clase,
          "nivelRiesgo": "CRITICO",
          "tipoEvidenciaVision": "ENTORNO",
          "objetoDetectado": f"Cierre forzado: {motivo}",
          "confianzaIa": 1.0,
          "urlFotoWebcam": None,
          "urlCapturaPantalla": None
      }
      cliente_api.enviar_alerta(sesion_id, carga_util)

    from PyQt6.QtWidgets import QMessageBox
    QMessageBox.critical(self, titulo, mensaje)
    self.finalizar_examen_forzado()

  def resizeEvent(self, event):
    super().resizeEvent(event)
    if hasattr(self, 'overlay_desconexion') and not self.overlay_desconexion.isHidden():
      self.overlay_desconexion.resize(self.size())
    if hasattr(self, 'overlay_camara_obstruida') and not self.overlay_camara_obstruida.isHidden():
      self.overlay_camara_obstruida.resize(self.size())

  def procesar_voz_profesor(self, datos):
    if not hasattr(self, 'hilo_reproduccion_voz') or not self.hilo_reproduccion_voz:
      import threading, queue
      self.cola_audio = queue.Queue()
      self.hilo_reproduccion_voz = threading.Thread(target=self._reproducir_voz, daemon=True)
      self.hilo_reproduccion_voz.start()
      
    try:
      import base64
      from cryptography.fernet import Fernet
      from config.configuracion import AES_SECRET_KEY
      f_crypto = Fernet(AES_SECRET_KEY)
      
      b64_str = datos.get('audio_b64', '')
      data_descifrada = f_crypto.decrypt(b64_str.encode('utf-8'))
      self.cola_audio.put(data_descifrada)
    except Exception as e:
      print(f'Error procesando voz del profe: {e}')

  def _reproducir_voz(self):
    try:
      import pyaudio
      p = pyaudio.PyAudio()
      stream = p.open(format=pyaudio.paInt16, channels=1, rate=16000, output=True)
      while True:
        data = self.cola_audio.get()
        if data is None: break
        stream.write(data)
    except Exception as e:
      print(f'Error reproduciendo voz: {e}')


  def _procesar_evento_sesion_windows(self, event_code):
    """Procesa los eventos de sesión emitidos por Wtsapi32"""
    WTS_CONSOLE_CONNECT = 0x1
    WTS_CONSOLE_DISCONNECT = 0x2
    WTS_SESSION_LOCK = 0x7
    WTS_SESSION_UNLOCK = 0x8

    print(f"[SESION WINDOWS] Notificación de sesión recibida (Código: {event_code})")
    sesion_id = None
    try:
      from utils.gestor_sesion import sesion_actual
      sesion_id = sesion_actual.obtener_sesion_id()
    except Exception:
      pass

    if event_code in (WTS_SESSION_LOCK, WTS_CONSOLE_DISCONNECT):
      tipo_str = "BLOQUEO_PANTALLA_WIN_L" if event_code == WTS_SESSION_LOCK else "CAMBIO_USUARIO_WINDOWS"
      detalle = "El estudiante bloqueó la pantalla (Win+L) durante el examen." if event_code == WTS_SESSION_LOCK else "El estudiante desconectó la sesión para conmutar a otra cuenta de usuario."

      if sesion_id:
        from api.cliente_respuesta import cliente_api
        evidencia = {
            "claseAlerta": "ENTORNO",
            "nivelRiesgo": "CRITICO",
            "pidProceso": 0,
            "nombreProceso": tipo_str,
            "categoriaProceso": "CONTROL_REMOTO",
            "accionTomada": "BLOQUEADO",
            "detalle": detalle
        }
        cliente_api.enviar_alerta(sesion_id, evidencia)

      # Iniciar temporizador de tolerancia máxima (15 segundos)
      if not hasattr(self, 'timer_abandono_sesion'):
        from PyQt6.QtCore import QTimer
        self.timer_abandono_sesion = QTimer(self)
        self.timer_abandono_sesion.setSingleShot(True)
        self.timer_abandono_sesion.timeout.connect(self._anular_examen_por_abandono_sesion)
      if not self.timer_abandono_sesion.isActive():
        self.timer_abandono_sesion.start(15000)

    elif event_code in (WTS_SESSION_UNLOCK, WTS_CONSOLE_CONNECT):
      if hasattr(self, 'timer_abandono_sesion') and self.timer_abandono_sesion.isActive():
        self.timer_abandono_sesion.stop()
      if sesion_id:
        from api.cliente_respuesta import cliente_api
        evidencia = {
            "claseAlerta": "ENTORNO",
            "nivelRiesgo": "ALTO",
            "pidProceso": 0,
            "nombreProceso": "RETORNO_A_SESION",
            "categoriaProceso": "CONTROL_REMOTO",
            "accionTomada": "REGISTRADO",
            "detalle": "El estudiante desbloqueó la pantalla y retornó a la sesión del examen."
        }
        cliente_api.enviar_alerta(sesion_id, evidencia)

  def _anular_examen_por_abandono_sesion(self):
    print("[SESION WINDOWS] Examen anulado: La sesión permaneció bloqueada o conmutada por más de 15 segundos.")
    sesion_id = None
    try:
      from utils.gestor_sesion import sesion_actual
      sesion_id = sesion_actual.obtener_sesion_id()
    except Exception:
      pass
    if sesion_id:
      from api.cliente_respuesta import cliente_api
      evidencia = {
          "claseAlerta": "ENTORNO",
          "nivelRiesgo": "CRITICO",
          "pidProceso": 0,
          "nombreProceso": "EXAMEN_ANULADO_ABANDONO_SESION",
          "categoriaProceso": "CONTROL_REMOTO",
          "accionTomada": "BLOQUEADO",
          "detalle": "Sesión de Windows bloqueada o en otra cuenta por más de 15 segundos continuos."
      }
      cliente_api.enviar_alerta(sesion_id, evidencia)
    from PyQt6.QtWidgets import QMessageBox
    QMessageBox.critical(
        self,
        "Examen Anulado por Abandono de Sesión",
        "Tu sesión de examen ha sido anulada debido a que el sistema operativo permaneció bloqueado o en otra cuenta de usuario por más de 15 segundos continuos.\n\n"
        "Esta acción infringe las políticas de integridad institucional. Puedes presentar una apelación si consideras que se debió a un fallo técnico ajeno."
    )
    self.ir_a_apelacion()

  def nativeEvent(self, eventType, message):
    """Captura los mensajes nativos de sesión de Windows emitidos por Wtsapi32 (Win+L / Switch User)"""
    if eventType in (b"windows_generic_MSG", "windows_generic_MSG"):
      try:
        import ctypes
        from ctypes import wintypes
        msg = wintypes.MSG.from_address(int(message))
        WM_WTSSESSION_CHANGE = 0x02B1
        if msg.message == WM_WTSSESSION_CHANGE:
          self._procesar_evento_sesion_windows(msg.wParam)
          return True, 0
      except Exception:
        pass
    return False, 0



