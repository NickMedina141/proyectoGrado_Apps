# vista/sala_supervision.py
import os
from PyQt6.QtWidgets import QWidget, QMessageBox, QFrame, QVBoxLayout, QHBoxLayout, QLabel, QDialog, QPushButton
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtCore import Qt, QTimer, QUrl
import json
from PyQt6 import uic

from api.cliente_ws import HiloWebSocket
from utils.formato_tiempo import formatear_hora_local_12h


class SalaSupervision(QWidget):
    def __init__(self, id_sesion=""):
        super().__init__()

        base_path = os.path.dirname(__file__)
        uic.loadUi(os.path.join(base_path, "sala_supervision.xml"), self)

        self.boton_finalizar.clicked.connect(self.finalizar_examen)
        if hasattr(self, 'boton_mapa'):
            self.boton_mapa.clicked.connect(self.mostrar_mapa)

        # Crear contenedor principal del mapa in-app
        self.frame_mapa_contenedor = QFrame()
        self.frame_mapa_contenedor.setVisible(False)
        self.layout_mapa = QVBoxLayout()
        self.layout_mapa.setContentsMargins(0, 0, 0, 0)
        self.layout_mapa.setSpacing(0)
        self.frame_mapa_contenedor.setLayout(self.layout_mapa)
        self.layout_global.addWidget(self.frame_mapa_contenedor)

        self.timer_mapa = QTimer(self)
        self.timer_mapa.timeout.connect(self.actualizar_pines_mapa)

        # Evitar que el badge "EN VIVO" se estire ocupando todo el ancho disponible
        from PyQt6.QtWidgets import QSizePolicy
        self.badge_envivo.setSizePolicy(
            QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Maximum)

        self.tarjetas_estudiantes = {}
        self.estado_vacio(True)
        self.codigo_examen_actual = None
        self.estado_estudiantes = {}
        self.sesiones_activas_ids = set()
        self._max_intentos_cache = None

    def _calcular_distancia_haversine(self, lat1, lon1, lat2, lon2):
        import math
        try:
            r = 6371.0  # Radio de la Tierra en km
            dlat = math.radians(float(lat2) - float(lat1))
            dlon = math.radians(float(lon2) - float(lon1))
            a = math.sin(dlat / 2)**2 + math.cos(math.radians(float(lat1))) * math.cos(math.radians(float(lat2))) * math.sin(dlon / 2)**2
            c = 2 * math.asin(math.sqrt(a))
            return round(r * c, 2)
        except Exception:
            return 0.0

    def _obtener_max_intentos_examen(self):
        try:
            if hasattr(self, '_max_intentos_cache') and self._max_intentos_cache is not None:
                return self._max_intentos_cache
            if not getattr(self, 'codigo_examen_actual', None):
                return None
            from utils.gestor_sesion import sesion_actual
            from api.cliente_respuesta import cliente_api
            prof_id = sesion_actual.obtener_profesor_id()
            if prof_id:
                exito, examenes = cliente_api.obtener_mis_examenes(prof_id)
                if exito and isinstance(examenes, list):
                    for ex in examenes:
                        cod = ex.get("codigoExamen") or ex.get("id")
                        if cod == self.codigo_examen_actual:
                            conf = ex.get("configuracionExamen") or {}
                            if "intentosMaximos" in conf:
                                self._max_intentos_cache = int(conf["intentosMaximos"])
                                return self._max_intentos_cache
                            if "maxIntentos" in conf:
                                self._max_intentos_cache = int(conf["maxIntentos"])
                                return self._max_intentos_cache
                            if "permitirReintentos" in conf:
                                r = int(conf.get("permitirReintentos", 0))
                                self._max_intentos_cache = r if r > 0 else 1
                                return self._max_intentos_cache
        except Exception as e:
            print("Error al obtener intentos maximos del examen:", e)
        return None

    def _procesar_datos_mapa(self, datos):
        if not datos or not isinstance(datos, list):
            return {"pines": []}

        max_permitidos = self._obtener_max_intentos_examen()

        # 1. Agrupar sesiones validas por estudiante
        estudiantes_sesiones = {}
        for s in datos:
            nom = s.get("nombreEstudiante") or "Desconocido"
            est_id = str(s.get("estudianteId") or nom)
            conexion = s.get("conexion") or {}
            if not isinstance(conexion, dict):
                continue
            lat = conexion.get("latitud")
            lon = conexion.get("longitud")

            if lat is None or lon is None:
                continue
            try:
                lat = float(lat)
                lon = float(lon)
            except (ValueError, TypeError):
                continue

            if lat == 0.0 and lon == 0.0:
                continue

            if est_id not in estudiantes_sesiones:
                estudiantes_sesiones[est_id] = []

            estudiantes_sesiones[est_id].append({
                "sesionId": s.get("sesionId") or s.get("id", ""),
                "nombre": nom,
                "estudianteId": est_id,
                "estadoSesion": s.get("estadoSesion", "EN_CURSO"),
                "ip": conexion.get("ipEstudiante", "N/A"),
                "lat": lat,
                "lon": lon,
                "inicio": str(s.get("inicioSesion") or s.get("horaInicio") or s.get("fechaCreacion") or "")
            })

        # 2. Orden cronológico de intentos y cálculo de trazabilidad por estudiante
        todos_los_intentos = []
        for est_id, s_list in estudiantes_sesiones.items():
            s_list.sort(key=lambda x: x.get("inicio", ""))
            total_realizados = len(s_list)
            # El total mostrado refleja el maximo permitido del examen si esta configurado
            total_intentos = max(total_realizados, max_permitidos) if max_permitidos else total_realizados

            trayectoria = []
            for i, ses in enumerate(s_list):
                trayectoria.append({
                    "intento": i + 1,
                    "lat": ses["lat"],
                    "lon": ses["lon"],
                    "ip": ses["ip"],
                    "estado": ses["estadoSesion"],
                    "fecha": ses["inicio"]
                })

            distancia_total = 0.0
            if total_realizados > 1:
                distancia_total = self._calcular_distancia_haversine(
                    s_list[0]["lat"], s_list[0]["lon"],
                    s_list[-1]["lat"], s_list[-1]["lon"]
                )

            for i, ses in enumerate(s_list):
                intento_num = i + 1
                es_actual = (i == total_realizados - 1)
                todos_los_intentos.append({
                    "sesionId": ses["sesionId"],
                    "estudianteId": est_id,
                    "nombre": ses["nombre"],
                    "intento": intento_num,
                    "totalIntentos": total_intentos,
                    "esActual": es_actual,
                    "estado": ses["estadoSesion"],
                    "ip": ses["ip"],
                    "lat": ses["lat"],
                    "lon": ses["lon"],
                    "distanciaDesplazamientoKm": distancia_total,
                    "trayectoria": trayectoria if total_realizados > 1 else []
                })

        # 3. Agrupación por proximidad geográfica (Clusters <= 50 metros)
        clusters = []
        for item in todos_los_intentos:
            asignado = False
            for cl in clusters:
                d = self._calcular_distancia_haversine(
                    item["lat"], item["lon"], cl["lat_centro"], cl["lon_centro"]
                )
                if d <= 0.05:  # Menor o igual a 50 metros
                    cl["items"].append(item)
                    asignado = True
                    break
            if not asignado:
                clusters.append({
                    "lat_centro": item["lat"],
                    "lon_centro": item["lon"],
                    "items": [item]
                })

        # 4. Clasificación de categorías para pines
        pines = []
        for cl in clusters:
            items = cl["items"]
            alumnos_unicos = set(it["estudianteId"] for it in items)
            cant_alumnos = len(alumnos_unicos)

            # Comprobar si al menos una sesión en este cluster sigue en curso
            tiene_en_curso = any(str(it.get("estado", "")).upper() in ["EN_CURSO", "INICIADA", "ACTIVA"] for it in items)

            if cant_alumnos >= 10:
                categoria = "AULA_PRESENCIAL"
                color = "morado"
            elif cant_alumnos >= 2:
                categoria = "UBICACION_COMPARTIDA"
                color = "rojo" if tiene_en_curso else "morado"
            else:
                if tiene_en_curso:
                    categoria = "ACTUAL"
                    color = "verde"
                else:
                    categoria = "HISTORICO"
                    color = "azul"

            pines.append({
                "lat": cl["lat_centro"],
                "lon": cl["lon_centro"],
                "categoria": categoria,
                "color": color,
                "cantidadAlumnos": cant_alumnos,
                "tieneEnCurso": tiene_en_curso,
                "items": items
            })

        return {"pines": pines}

    def actualizar_pines_mapa(self):
        if not self.codigo_examen_actual or not hasattr(self, 'vista_mapa'):
            return
        from api.cliente_respuesta import cliente_api
        exito, datos = cliente_api.obtener_sesiones_examen(
            self.codigo_examen_actual, todas=True)
        if exito and isinstance(datos, list):
            datos_mapa = self._procesar_datos_mapa(datos)
            import json
            json_pines = json.dumps(datos_mapa)
            self.vista_mapa.page().runJavaScript(f"cargarPines({json_pines});")

    def cerrar_mapa(self):
        self.timer_mapa.stop()
        self.frame_mapa_contenedor.setVisible(False)
        self.frame_central.setVisible(True)
        self.frame_feed_alertas.setVisible(True)
        while self.layout_mapa.count():
            item = self.layout_mapa.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def mostrar_mapa(self):
        if not self.codigo_examen_actual:
            return
        from api.cliente_respuesta import cliente_api
        exito, datos = cliente_api.obtener_sesiones_examen(
            self.codigo_examen_actual, todas=True)
        datos_mapa = self._procesar_datos_mapa(datos) if (exito and isinstance(datos, list)) else {"pines": []}

        self.cerrar_mapa()

        barra = QFrame()
        barra.setFixedHeight(50)
        barra.setStyleSheet("QFrame { background-color: #2C3E50; }")
        lay_barra = QHBoxLayout()
        lay_barra.setContentsMargins(15, 0, 15, 0)

        btn_cerrar = QPushButton("← Regresar a la supervisión")
        btn_cerrar.setStyleSheet(
            "QPushButton { background-color: transparent; color: #E74C3C; font-weight: bold; font-size: 14px; border: none; } QPushButton:hover { color: #ff6b6b; }")
        from PyQt6.QtCore import Qt
        btn_cerrar.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cerrar.clicked.connect(self.cerrar_mapa)
        lay_barra.addWidget(btn_cerrar)

        titulo = QLabel("Mapa Histórico de Supervisión GPS (Trazabilidad e Intentos)")
        titulo.setStyleSheet(
            "QLabel { color: white; font-size: 16px; font-weight: bold; background-color: transparent; }")
        titulo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay_barra.addWidget(titulo)
        lay_barra.addStretch()

        barra.setLayout(lay_barra)
        self.layout_mapa.addWidget(barra)

        self.vista_mapa = QWebEngineView()
        self.vista_mapa.settings().setAttribute(
            self.vista_mapa.settings().WebAttribute.LocalContentCanAccessRemoteUrls, True)
        import os
        ruta_html = os.path.abspath(os.path.join(
            os.path.dirname(__file__), "recursos", "mapa_leaflet.html"))
        with open(ruta_html, "r", encoding="utf-8") as f_html:
            html_str = f_html.read()
        self.vista_mapa.setHtml(html_str, QUrl("http://localhost"))
        self.layout_mapa.addWidget(self.vista_mapa)

        import json
        json_pines = json.dumps(datos_mapa)
        self.vista_mapa.loadFinished.connect(
            lambda: self.vista_mapa.page().runJavaScript(f"cargarPines({json_pines});"))

        self.frame_central.setVisible(False)
        self.frame_feed_alertas.setVisible(False)
        self.frame_mapa_contenedor.setVisible(True)
        self.timer_mapa.start(5000)

    def estado_vacio(self, vacio, texto="Actualmente no se esta supervisando nada"):
        self.etiqueta_vacia.setVisible(vacio)
        self.etiqueta_vacia.setText(texto)
        self.area_scroll_grupos.setVisible(not vacio)
        self.badge_envivo.setVisible(not vacio)
        self.etiqueta_titulo.setVisible(not vacio)
        self.boton_finalizar.setVisible(not vacio)
        if hasattr(self, 'boton_mapa'):
            self.boton_mapa.setVisible(not vacio)
        self.frame_feed_alertas.setVisible(not vacio)
        if vacio:
            self.limpiar_sala()

    def limpiar_sala(self):
        # Eliminar tarjetas de estudiantes
        for i in reversed(range(self.layout_grupos.count())):
            item = self.layout_grupos.itemAt(i)
            if item.widget() and item.widget() != self.etiqueta_vacia:
                item.widget().setParent(None)

        # Eliminar alertas del feed
        for i in reversed(range(self.layout_feed.count())):
            item = self.layout_feed.itemAt(i)
            if item.widget():
                item.widget().setParent(None)

        self.tarjetas_estudiantes.clear()
        if hasattr(self, 'hilo_ws') and self.hilo_ws.corriendo:
            self.hilo_ws.detener()

    def cargar_estudiantes(self, codigo_examen, nombre_materia=""):
        self.limpiar_sala()
        self.codigo_examen_actual = codigo_examen
        self._max_intentos_cache = None
        self.estado_vacio(False)
        self.estado_estudiantes = {}  # Diccionario para rastrear estados

        titulo = nombre_materia if nombre_materia else codigo_examen
        self.etiqueta_titulo.setText(f"Monitoreo de Examen: {titulo}")

        from api.cliente_respuesta import cliente_api
        exito, datos = cliente_api.obtener_sesiones_examen(codigo_examen)

        self.sesiones_activas_ids = set()
        if exito and isinstance(datos, list) and len(datos) >0:
            for sesion in datos:
                nombre = sesion.get("nombreEstudiante", "")
                sesion_id = sesion.get("id") or sesion.get("sesionId")
                if nombre:
                    self.estado_estudiantes[nombre] = sesion.get(
                        "estadoSesion", "PENDIENTE")
                if sesion_id:
                    self.sesiones_activas_ids.add(sesion_id)
                self.crear_tarjeta_estudiante(sesion)
            self.area_scroll_grupos.setVisible(True)
            self.etiqueta_vacia.setVisible(False)
        else:
            self.area_scroll_grupos.setVisible(False)
            self.etiqueta_vacia.setVisible(True)
            self.etiqueta_vacia.setText(
                "No hay estudiantes aun presentando el examen")

        self.iniciar_conexion_en_vivo(codigo_examen)

        # Cargar el historial global de alertas de este examen
        exito_alertas, alertas = cliente_api.obtener_alertas_examen(
            codigo_examen)
        if exito_alertas and isinstance(alertas, list):
            from datetime import datetime
            fecha_hoy = datetime.now().strftime("%Y-%m-%d")

            for alerta in reversed(alertas):  # reversed para que las mas recientes queden arriba
                hora_completa = alerta.get(
                    "horaCaptura", alerta.get("hora", ""))

                # FILTRO 1: No revivir alertas de dias anteriores en la vista "En Vivo"
                if "T" in hora_completa:
                    fecha_alerta = hora_completa.split("T")[0]
                    if fecha_alerta != fecha_hoy:
                        continue

                # FILTRO 2: No revivir alertas de sesiones pasadas
                sesion_id = alerta.get("sesionId")
                if sesion_id not in getattr(self, "sesiones_activas_ids", set()):
                    continue

                nombre_est = alerta.get(
                    "nombreEstudiante", alerta.get("estudiante", "Desconocido"))

                self.agregar_tarjeta_alerta(alerta)

    def crear_tarjeta_estudiante(self, sesion):
        from PyQt6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QSpacerItem, QSizePolicy

        estudiante_id = sesion.get("estudianteId", "Desconocido")
        nombre = sesion.get("nombreEstudiante", f"Estudiante {estudiante_id[:5]}")

        tarjeta = QFrame()
        tarjeta.setObjectName("tarjeta_e1")
        tarjeta.setMinimumWidth(200)
        tarjeta.setMaximumWidth(300)
        tarjeta.setMinimumHeight(260)

        lay_t = QVBoxLayout(tarjeta)
        lay_t.setSpacing(10)
        lay_t.setContentsMargins(20, 20, 20, 20)

        # TOP ROW
        top_row = QHBoxLayout()
        lbl_titulo = QLabel(nombre)
        lbl_titulo.setObjectName("titulo_e1")
        lbl_titulo.setStyleSheet("font-weight: bold; font-size: 16px;")
        lbl_titulo.setWordWrap(True)

        lbl_badge = QLabel("En Vivo")
        lbl_badge.setObjectName("badge_verde_1")

        top_row.addWidget(lbl_titulo)
        top_row.addWidget(lbl_badge)
        lay_t.addLayout(top_row)

        lay_t.addSpacerItem(QSpacerItem(
            20, 10, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed))

        # INTEGRIDAD
        row_int = QHBoxLayout()
        lbl_i1 = QLabel("Integridad IA")
        lbl_i1.setObjectName("label_est_1")

        integridad = sesion.get("porcentajeIntegridad", 100)
        lbl_val_int = QLabel(f"{integridad}%")
        lbl_val_int.setObjectName("val_norm_1")

        if integridad >= 80:
            lbl_val_int.setStyleSheet("font-weight: bold; color: #003B13;")
        elif integridad >= 50:
            lbl_val_int.setStyleSheet("font-weight: bold; color: #d35400;")
        else:
            lbl_val_int.setStyleSheet("font-weight: bold; color: #c0392b;")

        row_int.addWidget(lbl_i1)
        row_int.addStretch()
        row_int.addWidget(lbl_val_int)
        lay_t.addLayout(row_int)

        # ALERTAS
        row_al = QHBoxLayout()
        lbl_a1 = QLabel("Alertas")
        lbl_a1.setObjectName("label_al_1")

        alertas = sesion.get("cantidadAlertas", 0)
        lbl_val_al = QLabel(str(alertas))
        lbl_val_al.setObjectName("val_norm_2")

        if alertas == 0:
            lbl_val_al.setStyleSheet("font-weight: bold; color: #003B13;")
        elif alertas <= 3:
            lbl_val_al.setStyleSheet("font-weight: bold; color: #d35400;")
        else:
            lbl_val_al.setStyleSheet("font-weight: bold; color: #c0392b;")

        row_al.addWidget(lbl_a1)
        row_al.addStretch()
        row_al.addWidget(lbl_val_al)
        lay_t.addLayout(row_al)

        # CONEXION
        row_cx = QHBoxLayout()
        lbl_c1 = QLabel("Estado de Conexión")
        lbl_c1.setObjectName("label_cx_1")
        lbl_c1.setWordWrap(True)

        estado_db = str(sesion.get("estadoSesion", "")).upper()
        if estado_db in ["INICIADA", "EN_CURSO", "ACTIVA"]:
            texto_conexion = "Buena"
            color_cx = "#27AE60"
        elif estado_db in ["FINALIZADA", "ANULADA"]:
            texto_conexion = "Offline"
            color_cx = "#7F8C8D"
        else:
            texto_conexion = "Inestable"
            color_cx = "#E74C3C"

        lbl_val_cx = QLabel(texto_conexion)
        lbl_val_cx.setObjectName("val_green_1")
        lbl_val_cx.setStyleSheet(f"font-weight: bold; color: {color_cx};")
        row_cx.addWidget(lbl_c1)
        row_cx.addWidget(lbl_val_cx)
        lay_t.addLayout(row_cx)

        lay_t.addSpacerItem(QSpacerItem(
            20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

        btn_cam = QPushButton("Ver Cámara")
        btn_cam.setObjectName("btn_e1")
        btn_cam.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cam.setMinimumHeight(35)
        sesion_id = sesion.get("sesionId") or sesion.get("id") or ""
        btn_cam.clicked.connect(lambda checked, n=nombre,
                                sid=sesion_id, eid=estudiante_id: self.abrir_estudiante(n, sid, eid))
        lay_t.addWidget(btn_cam)

        self.layout_grupos.addWidget(tarjeta)

        self.tarjetas_estudiantes[sesion_id] = {
            "widget": tarjeta,
            "lbl_alertas": lbl_val_al,
            "lbl_integridad": lbl_val_int,
            "lbl_conexion": lbl_val_cx,
            "badge": lbl_badge,
            "alertas_count": alertas,
            "integridad": integridad,
            "estudiante_id": estudiante_id,
            "estado": estado_db
        }

    def abrir_estudiante(self, nombre, sesion_id, estudiante_id=None):
        parent = self.window()
        if hasattr(parent, "abrir_detalle_estudiante"):
            parent.abrir_detalle_estudiante(nombre, sesion_id, estudiante_id)

    def iniciar_conexion_en_vivo(self, id_sesion):
        ruta_especifica = f"/{id_sesion}" if id_sesion else ""
        self.hilo_ws = HiloWebSocket(ruta_especifica)

        self.hilo_ws.alerta_recibida.connect(self.mostrar_nueva_alerta)
        self.hilo_ws.conexion_perdida.connect(self.notificar_desconexion)

        def en_conexion():
            self.badge_envivo.setText(" EN VIVO")
            self.badge_envivo.setStyleSheet(
                "background-color: #E74C3C; color: white; border-radius: 4px; padding: 4px; font-weight: bold;")
            if hasattr(self.window(), 'mostrar_overlay_reconexion'):
                self.window().mostrar_overlay_reconexion(False)
        self.hilo_ws.conectado.connect(en_conexion)

        self.hilo_ws.start()

    def mostrar_nueva_alerta(self, datos_alerta):
        if datos_alerta.get("tipoEvento") == "ESTUDIANTE_UNIDO":
            self.cargar_estudiantes(self.codigo_examen_actual)
            
            # Auto-sincronizar si el profesor está viendo a este mismo estudiante en la vista de detalle
            parent = self.window()
            if hasattr(parent, 'vista_detalle_est') and hasattr(parent, 'contenedor_vistas'):
                if parent.contenedor_vistas.currentIndex() == 3:  # Vista 3 es detalle estudiante
                    vista_det = parent.vista_detalle_est
                    est_id_evento = datos_alerta.get("estudianteId")
                    nueva_ses_id = datos_alerta.get("sesionId")
                    if est_id_evento and nueva_ses_id and getattr(vista_det, 'estudiante_id', None) == est_id_evento:
                        print(f"[AUTO-SYNC] Estudiante {est_id_evento} activo con nueva sesión {nueva_ses_id}. Auto-actualizando vista detalle...")
                        vista_det.cargar_datos(vista_det.lbl_nombre_estudiante.text(), nueva_ses_id, est_id_evento)
            return

        if datos_alerta.get("tipoEvento") == "SESION_DUPLICADA_BLOQUEADA":
            mac = datos_alerta.get("macIntruso", "Desconocida")
            ip = datos_alerta.get("ipIntruso", "Desconocida")
            datos_alerta["claseAlerta"] = "SESION_DUPLICADA"
            datos_alerta["nivelRiesgo"] = "CRITICO"
            datos_alerta["nombreProceso"] = f"Intento en segundo equipo (MAC: {mac})"
            datos_alerta["categoriaProceso"] = f"IP: {ip}"
            datos_alerta["objetoDetectado"] = f"Intento de acceso simultáneo bloqueado"

        # Cuando entra por websocket
        datos_alerta["nueva_alerta_ws"] = True
        
        # BYPASS E2EE: Guardar la evidencia localmente!
        import os
        import json
        cod_ex = str(self.codigo_examen_actual or "general")
        base_dir = os.path.join(os.path.expanduser("~"), "Documents", "DataSupervision", "Examenes", cod_ex, datos_alerta.get("nombreEstudiante", "Desconocido").replace(" ", "_"), datos_alerta.get("sesionId", "unknown"))
        for cat in ['audio', 'proceso', 'webcam', 'teclado']:
            os.makedirs(os.path.join(base_dir, cat), exist_ok=True)
            
        from utils.formato_evidencia import generar_nombre_evidencia

        meta_json_path = os.path.join(base_dir, "meta_archivos.json")
        meta_archivos = {}
        if os.path.exists(meta_json_path):
            try:
                with open(meta_json_path, "r", encoding="utf-8") as f_meta:
                    meta_archivos = json.load(f_meta)
            except Exception:
                meta_archivos = {}

        id_alerta = str(datos_alerta.get("idAlerta", ""))
        if id_alerta and id_alerta not in meta_archivos:
            meta_archivos[id_alerta] = {}

        def guardar_b64(b64, subcarpeta, clave_meta="", sufijo_extra="", ext_archivo=".webp"):
            if b64:
                import base64
                if "," in b64: b64 = b64.split(",")[1]
                nombre_archivo = generar_nombre_evidencia(base_dir, subcarpeta, datos_alerta, sufijo_extra=sufijo_extra, ext_archivo=ext_archivo)
                path = os.path.join(base_dir, subcarpeta, nombre_archivo)
                with open(path, "wb") as f_out:
                    if b64.startswith("gAAAAA"): f_out.write(b64.encode('utf-8'))
                    else: f_out.write(base64.b64decode(b64))
                if id_alerta and clave_meta:
                    meta_archivos[id_alerta][clave_meta] = os.path.join(subcarpeta, nombre_archivo).replace("\\", "/")

        guardar_b64(datos_alerta.get("base64WebcamTransient"), "webcam", clave_meta="webcam", sufijo_extra="", ext_archivo=".webp")
        
        clase = datos_alerta.get("claseAlerta", "").upper()
        if clase in ["SISTEMA", "PROCESO", "PROCESOS"]:
            guardar_b64(datos_alerta.get("base64PantallaTransient"), "proceso", clave_meta="pantalla", sufijo_extra="", ext_archivo=".webp")
        elif clase == "TECLADO":
            guardar_b64(datos_alerta.get("base64PantallaTransient"), "teclado", clave_meta="pantalla", sufijo_extra="", ext_archivo=".webp")
        else:
            guardar_b64(datos_alerta.get("base64PantallaTransient"), "webcam", clave_meta="pantalla", sufijo_extra="_pantalla", ext_archivo=".webp")
            
        guardar_b64(datos_alerta.get("base64AudioTransient"), "audio", clave_meta="audio", sufijo_extra="", ext_archivo=".wav")
        
        if id_alerta:
            try:
                with open(meta_json_path, "w", encoding="utf-8") as f_meta:
                    json.dump(meta_archivos, f_meta, indent=2, ensure_ascii=False)
            except Exception as e:
                print(f"[SalaSupervision] Error guardando meta_archivos.json: {e}")
        
        self.agregar_tarjeta_alerta(datos_alerta)

    def agregar_tarjeta_alerta(self, alerta):
        from PyQt6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
        from PyQt6.QtCore import Qt

        # Extraer datos basicos
        clase_alerta = alerta.get(
            "claseAlerta", alerta.get("tipo", "DESCONOCIDO")).upper()
        nombre_est = alerta.get(
            "nombreEstudiante", alerta.get("estudiante", "Desconocido"))

        # OPClON 2: Averiguar si la sesion de este estudiante esta FINALIZADA
        estado_sesion = getattr(self, "estado_estudiantes", {}).get(
            nombre_est, "PENDIENTE")
        es_finalizada = (estado_sesion == "FINALIZADA")

        bg_color = "#f9f9f9" if es_finalizada else "#ffffff"
        border_color = "#e8e8e8" if es_finalizada else "#dcdde1"

        tarjeta = QFrame()
        tarjeta.setObjectName("tarjeta_alerta_limpia")
        tarjeta.setStyleSheet(f"""
        QFrame#tarjeta_alerta_limpia {{ 
            border: 1px solid {border_color}; 
            border-radius: 6px;
            background-color: {bg_color};
            margin-bottom: 8px; 
        }}
    """)

        layout = QVBoxLayout(tarjeta)
        layout.setSpacing(6)
        layout.setContentsMargins(12, 10, 12, 12)

        # Hora de captura en formato local 12H (AM/PM)
        hora_str = formatear_hora_local_12h(alerta.get("horaCaptura", alerta.get("hora", "")))

        nivel_riesgo = alerta.get("nivelRiesgo", "MEDIO").upper()

        # Colores segun estado
        if es_finalizada:
            color_riesgo = "#aaaaaa"
            color_nombre = "#999999"
            color_desc = "#bbbbbb"
            clase_alerta += " [Finalizado]"
        else:
            color_riesgo = "#2c3e50"
            if nivel_riesgo in ["ALTO", "CRITICO"]:
                color_riesgo = "#c0392b"
            elif nivel_riesgo == "MEDIO":
                color_riesgo = "#d35400"
            elif nivel_riesgo == "BAJO":
                color_riesgo = "#27ae60"
            color_nombre = "#2c3e50"
            color_desc = "#7f8c8d"

        top_row = QHBoxLayout()

        # Texto de tipo de alerta sin recuadro (fondo transparente)
        lbl_tipo = QLabel(clase_alerta)
        lbl_tipo.setStyleSheet(f"""
        color: {color_riesgo}; 
        background-color: transparent;
        font-weight: bold; 
        font-size: 13px;
    """)

        lbl_hora = QLabel(hora_str)
        lbl_hora.setStyleSheet("color: #95a5a6; font-size: 11px;")

        top_row.addWidget(lbl_tipo)
        top_row.addStretch()
        top_row.addWidget(lbl_hora)
        layout.addLayout(top_row)

        lbl_nombre = QLabel(nombre_est)
        lbl_nombre.setStyleSheet(
            f"font-weight: bold; font-size: 14px; color: {color_nombre};")
        layout.addWidget(lbl_nombre)

        # Extraer descripcion dinamica
        desc = alerta.get("descripcion", alerta.get("mensaje", ""))
        if not desc or str(desc).strip().lower() in ["none", "null"]:
            obj = alerta.get("objetoDetectado", "")
            if obj:
                desc = f"Objeto: {obj}"
            elif alerta.get("combinacionTeclas"):
                teclas_str = str(alerta.get("combinacionTeclas"))
                if "_" in teclas_str and (teclas_str.isupper() or "_BLOQUEAD" in teclas_str):
                    teclas_str = teclas_str.replace("_BLOQUEADO", "").replace("_BLOQUEADA", "").replace("_", " ").title()
                desc = f"Atajo bloqueado: {teclas_str}"
            elif alerta.get("nombreProceso"):
                proc_str = str(alerta.get("nombreProceso"))
                if "_" in proc_str and proc_str.isupper():
                    proc_str = proc_str.replace("_", " ").title()
                desc = f"Proceso: {proc_str}"

        if desc:
            lbl_desc = QLabel(desc)
            lbl_desc.setWordWrap(True)
            lbl_desc.setStyleSheet(f"color: {color_desc}; font-size: 12px;")
            layout.addWidget(lbl_desc)

        # Boton Ver Evidencia
        est_id = alerta.get("estudianteId", alerta.get("sesionId", ""))
        btn_link = QPushButton("Ver Evidencia")
        btn_link.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_link.setStyleSheet(f"""
        QPushButton {{
            color: {color_riesgo}; 
            background-color: transparent;
            text-align: left;

            border: none;
            text-decoration: underline;
            font-size: 12px;
            font-weight: bold;
        }}
        QPushButton:hover {{
            color: #2980b9;
        }}
    """)
        btn_link.clicked.connect(
            lambda checked, n=nombre_est, sid=est_id: self.abrir_estudiante(n, sid))
        layout.addWidget(btn_link)

        self.layout_feed.insertWidget(0, tarjeta)

        # Actualizar tarjeta del estudiante si existe
        sid = alerta.get("sesionId") or ""
        eid = alerta.get("estudianteId") or ""
        tarjeta_est = self.tarjetas_estudiantes.get(sid) or self.tarjetas_estudiantes.get(eid)
        if not tarjeta_est and eid:
            for t in self.tarjetas_estudiantes.values():
                if t.get("estudiante_id") == eid:
                    tarjeta_est = t
                    break

        if tarjeta_est:
            # Confirmar conexion activa al recibir telemetria/alerta en vivo
            if "lbl_conexion" in tarjeta_est and tarjeta_est["lbl_conexion"]:
                tarjeta_est["lbl_conexion"].setText("Buena")
                tarjeta_est["lbl_conexion"].setStyleSheet("font-weight: bold; color: #27AE60;")

            # Actualizar el numero de alertas sumando 1 si es una nueva alerta (vía WebSocket)
            # Las alertas del historial REST ya vienen contabilizadas en la carga inicial
            if alerta.get("nueva_alerta_ws", False):
                lbl_al = tarjeta_est["widget"].findChild(QLabel, "val_norm_2")
                if lbl_al:
                    try:
                        actual = int(lbl_al.text())
                        lbl_al.setText(str(actual + 1))
                        lbl_al.setStyleSheet(
                            "font-weight: bold; color: #c0392b;")
                    except:
                        pass

            tipo = alerta.get("claseAlerta", alerta.get("tipo", ""))
            if "VISION" in tipo.upper() or "AUDIO" in tipo.upper() or "PROCESO" in tipo.upper():

                # Bajar integridad dinámicamente si llega por websocket
                if alerta.get("nueva_alerta_ws", False):
                    try:
                        texto_int = tarjeta_est["lbl_integridad"].text().replace(
                            "%", "")
                        integridad_actual = int(texto_int)
                        nivel = alerta.get("nivelRiesgo", "MEDIO").upper()
                        descuento = 15
                        if nivel == "ALTO":
                            descuento = 30
                        elif nivel == "BAJO": descuento = 5

                        nueva_int = max(0, integridad_actual - descuento)
                        tarjeta_est["lbl_integridad"].setText(f"{nueva_int}%")

                        if nueva_int < 50:
                            tarjeta_est["lbl_integridad"].setStyleSheet(
                                "font-weight: bold; color: #c0392b;")
                        elif nueva_int < 80:
                            tarjeta_est["lbl_integridad"].setStyleSheet(
                                "font-weight: bold; color: #d35400;")
                    except Exception as e:
                        pass

                # Cambiar badge a Alerta
                tarjeta_est["badge"].setText("Alerta")
                tarjeta_est["badge"].setObjectName("badge_rojo_1")
                tarjeta_est["widget"].setStyleSheet(
                    tarjeta_est["widget"].styleSheet())

    def notificar_desconexion(self, mensaje):
        self.badge_envivo.setText(" RECONECTANDO...")
        self.badge_envivo.setStyleSheet(
            "background-color: #F39C12; color: white; border-radius: 4px; padding: 4px; font-weight: bold;")
        if hasattr(self.window(), 'mostrar_overlay_reconexion'):
            self.window().mostrar_overlay_reconexion(True)
        # La reconexion ahora es automatica e interna en HiloWebSocket.

    def finalizar_examen(self):
        respuesta = QMessageBox.question(self, "Cerrar Sala", "¿Seguro que desea finalizar el monitoreo?",
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if respuesta == QMessageBox.StandardButton.Yes:
            from api.cliente_respuesta import cliente_api
            exito, mensaje = cliente_api.cerrar_examen(
                self.codigo_examen_actual)

            if exito:
                self.estado_vacio(True)
                QMessageBox.information(
                    self, "Examen Finalizado", "El examen ha sido cerrado en el servidor.")
                # Avisar al parent (ventana principal) que recargue el dashboard
                parent = self.window()
                if hasattr(parent, "cargar_mis_examenes"):
                    parent.cargar_mis_examenes()
            else:
                QMessageBox.warning(self, "Error", mensaje)
