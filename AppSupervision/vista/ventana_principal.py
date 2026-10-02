from PyQt6.QtWidgets import QWidget, QMessageBox
from PyQt6.uic import loadUi
from api.cliente_respuesta import cliente_api
from utils.gestor_sesion import sesion_actual
import os
from PyQt6.QtCore import Qt, pyqtSignal

class VentanaPrincipal(QWidget):
  senal_apelacion_terminada = pyqtSignal(bool, str)

  def __init__(self, app_principal=None):
    super().__init__()
    self.app_principal = app_principal
    self.senal_apelacion_terminada.connect(self._finalizar_apelacion)
    
    # Cargar UI
    ruta_ui = os.path.join(os.path.dirname(__file__), "ventana_principal.xml")
    loadUi(ruta_ui, self)
    
    # Pantalla de bloqueo de red (Fault Tolerance)
    from PyQt6.QtWidgets import QLabel
    self.pantalla_bloqueo = QLabel(self)
    self.pantalla_bloqueo.setStyleSheet("background-color: rgba(0, 0, 0, 230); color: white; font-size: 30px; font-weight: bold;")
    self.pantalla_bloqueo.setAlignment(Qt.AlignmentFlag.AlignCenter)
    self.pantalla_bloqueo.setText(" CONEXION A INTERNET PERDIDA\n\nEl examen esta pausado pero la supervision IA sigue ACTIVA.\nPor favor restablezca su conexion.")
    self.pantalla_bloqueo.hide()
    
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

      navegador = NavegadorSeguro()
      settings = navegador.settings()
      settings.setAttribute(QWebEngineSettings.WebAttribute.PluginsEnabled, False)
      settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptCanOpenWindows, True)
      settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, False)
        
      profile = navegador.page().profile()
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
      
      # 2. Arrancamos la Cámara Local
      self.hilo_camara = HiloCamara()
      def _actualizar_frame_seguro(img):
          if not getattr(self, "examen_anulado", False):
              self.lbl_camara.setPixmap(QPixmap.fromImage(img))
      self.hilo_camara.senal_frame.connect(_actualizar_frame_seguro)
      self.hilo_camara.senal_advertencia.connect(self.actualizar_indicador_buho)
      
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

  def procesar_pin(self):
    pin = self.entrada_pin.text().strip()
    
    if not pin:
      QMessageBox.warning(self, "PIN Inválido", "Por favor ingresa el PIN del examen.")
      return
      
    self.btn_ingresar_pin.setEnabled(False)
    self.btn_ingresar_pin.setText("Validando...")
    
    estudiante_id = sesion_actual.obtener_estudiante_id()
    
    # 1. Llamar a la API para validar PIN
    exito, respuesta = cliente_api.iniciar_sesion_examen(estudiante_id, pin)
    
    if exito:
      sesion_id = respuesta.get("sesionId", "")
      
      # 2. Descargar Reglas del Examen (Lista Blanca de Apps)
      exito_reglas, reglas = cliente_api.obtener_reglas_examen(sesion_id)
      
      # Inyectar URLs dinámicas
      urls = reglas.get("urls_permitidas", []) if exito_reglas else []
      self.cargar_urls_permitidas(urls)
      
      # Configurar Temporizador Visual
      if exito_reglas and reglas.get("duracion_examen"):
         self.tiempo_restante = reglas.get("duracion_examen") * 60
         self._configurar_temporizador()
      
      # Inyectar reglas a módulos IA
      from motor_ia.sistema import monitor_sys
      monitor_sys.funcion_alerta = lambda evidencia: cliente_api.enviar_alerta(sesion_id, evidencia)
      
      if exito_reglas and "procesos_permitidos" in reglas:
        monitor_sys.actualizar_lista_blanca(reglas["procesos_permitidos"])
      else:
        # Si falla, la lista de permitidos queda vacía de forma estricta y real
        monitor_sys.actualizar_lista_blanca([])
        
      monitor_sys.iniciar()
        
      sensibilidad = "MEDIA"
      if exito_reglas:
        sensibilidad = reglas.get("sensibilidad_ia") or reglas.get("sensibilidadIA") or "MEDIA"

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
      # Aplicar colores institucionales (Verde UPC)
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
    else:
      QMessageBox.critical(self, "Error de Acceso", respuesta)
      
    self.btn_ingresar_pin.setEnabled(True)
    self.btn_ingresar_pin.setText("Validar Código y Entrar")
    
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
      
      # Avisar al backend que se finaliza la sesion
      sesion_id = sesion_actual.obtener_sesion_id()
      if sesion_id:
        cliente_api.finalizar_sesion_examen(sesion_id)
      sesion_actual.cerrar_sesion()
      if self.app_principal:
        self.app_principal.mostrar_ventana_login()

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
    """Detecta si el usuario minimiza la ventana o cambia el foco a otra aplicacion."""
    from PyQt6.QtCore import QEvent
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
    if conectado:
      if hasattr(self, 'pantalla_bloqueo'):
        self.pantalla_bloqueo.hide()
    else:
      if hasattr(self, 'pantalla_bloqueo'):
        self.pantalla_bloqueo.resize(self.size())
        self.pantalla_bloqueo.show()
        self.pantalla_bloqueo.raise_()

  def resizeEvent(self, event):
    super().resizeEvent(event)
    if hasattr(self, 'pantalla_bloqueo') and not self.pantalla_bloqueo.isHidden():
      self.pantalla_bloqueo.resize(self.size())

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


