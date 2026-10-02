import os
import datetime
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QFrame, QGridLayout, QScrollArea, QSizePolicy, QComboBox)
from PyQt6.QtCore import Qt, QUrl, QSize, QRectF
from PyQt6.QtGui import QFont, QColor, QPixmap, QDesktopServices, QPainter, QPen, QBrush

class LineaDeTiempoWidget(QWidget):
    def __init__(self, fn_abrir_categoria):
        super().__init__()
        self.fn_abrir_categoria = fn_abrir_categoria
        # Altura aún mayor para que se vea espectacular sin aplastar (el scroll lo maneja)
        self.setMinimumHeight(500)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.eventos = []
        self.t_min = 0
        self.t_max = 0
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
    def cargar_eventos(self, ruta_evidencias):
        self.eventos.clear()
        if not ruta_evidencias:
            self.update()
            return
            
        mapa_carpetas = {
            'audio': ('audio', 'Audio'),
            'proceso': ('proceso', 'Procesos y Sistema'),
            'webcam': ('webcam', 'Visión'), # Cambiado de Webcam a Visión
            'teclado': ('teclado', 'Teclado')
        }
            
        for carpeta_id, info in mapa_carpetas.items():
            ruta_cat = os.path.join(ruta_evidencias, carpeta_id)
            if os.path.exists(ruta_cat):
                for arch in os.listdir(ruta_cat):
                    ruta_comp = os.path.join(ruta_cat, arch)
                    if os.path.isfile(ruta_comp):
                        ts = os.path.getmtime(ruta_comp)
                        
                        # Solo el tipo de alerta para que se vea limpio
                        motivo = info[1].upper()
                        
                        # Excepcion especial para objetos sospechosos en la categoria webcam
                        if carpeta_id == 'webcam':
                            arch_lower = arch.lower()
                            if 'objeto' in arch_lower or 'celular' in arch_lower or 'telefono' in arch_lower or 'dispositivo' in arch_lower:
                                motivo = "OBJETO"
                            
                        self.eventos.append({
                            'time': ts,
                            'tipo': carpeta_id,
                            'titulo_cat': info[1],
                            'motivo': motivo,
                            'rect': None
                        })
                        
        if not self.eventos:
            self.update()
            return
            
        self.eventos.sort(key=lambda x: x['time'])
        
        # Calcular duracion real de los eventos para dar un espaciado dinamico y perfecto
        duracion_real = self.eventos[-1]['time'] - self.eventos[0]['time']
        
        # Darle un "padding" o margen del 10% a los lados (con un minimo de 60 segundos)
        # Esto asegura que los eventos abarquen todo el ancho de la pantalla de manera uniforme
        padding = max(60, duracion_real * 0.1)
        self.t_min = self.eventos[0]['time'] - padding
        self.t_max = self.eventos[-1]['time'] + padding
            
        # Al no establecer MinimumWidth, el widget toma el 100% del ancho de la pantalla sin scroll
        self.setMinimumHeight(650)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        w = self.width()
        h = self.height()
        
        margen_x = 80
        # Linea base centrada con espacio perfecto
        y_linea = h // 2
        
        # --- Título Superior Centrado ---
        painter.setPen(self.palette().windowText().color())
        font = painter.font()
        font.setFamily("Segoe UI")
        font.setBold(True)
        font.setPointSize(24)
        painter.setFont(font)
        titulo = "Línea de Tiempo Analítica"
        fm_titulo = painter.fontMetrics()
        x_titulo = int((w - fm_titulo.horizontalAdvance(titulo)) / 2)
        painter.drawText(x_titulo, 50, titulo)
        
        # Eliminado el subtítulo para que no choque con los nodos superiores
        
        if not self.eventos:
            font.setPointSize(10)
            painter.setFont(font)
            painter.setPen(QColor("#BDC3C7"))
            fm = painter.fontMetrics()
            painter.drawText(int((w - fm.horizontalAdvance("No hay evidencias registradas.")) / 2), y_linea - 30, "No hay evidencias registradas.")
            return

        # --- Track Base (Efecto "Glow" y grosor extra) ---
        ancho_linea = w - (margen_x * 2)
        grosor_linea = 12
        
        # Sombra suave / Glow exterior
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor(46, 204, 113, 50))) # Verde semi-transparente
        painter.drawRoundedRect(margen_x - 2, y_linea - (grosor_linea//2) - 2, ancho_linea + 4, grosor_linea + 4, (grosor_linea+4)//2, (grosor_linea+4)//2)
        
        # Línea central sólida
        painter.setBrush(QBrush(QColor("#2ECC71")))  
        painter.drawRoundedRect(margen_x, y_linea - (grosor_linea//2), ancho_linea, grosor_linea, grosor_linea//2, grosor_linea//2)
        
        # --- Banderas de Inicio y Fin ---
        dt_inicio = datetime.datetime.fromtimestamp(self.t_min).strftime("%H:%M")
        dt_fin = datetime.datetime.fromtimestamp(self.t_max).strftime("%H:%M")
        font.setPointSize(9)
        
        def dibujar_bandera_extremo(x, y, titulo, hora):
            from PyQt6.QtGui import QPolygonF
            from PyQt6.QtCore import QPointF
            color_base = QColor("#27AE60")
            
            # Punto en la linea
            painter.setPen(QPen(color_base, 2))
            painter.setBrush(QBrush(QColor("white")))
            painter.drawEllipse(QRectF(x - 6, y - 6, 12, 12))
            
            # Hora en el track principal
            painter.setPen(self.palette().windowText().color())
            font.setBold(True)
            painter.setFont(font)
            painter.drawText(int(x) - 15, int(y) + 30, hora)
            painter.setPen(QColor("#7F8C8D"))
            font.setBold(False)
            painter.setFont(font)
            painter.drawText(int(x) - 15, int(y) + 45, titulo)
            
            # Mástil hacia arriba (como la imagen de Gemini)
            painter.setPen(QPen(color_base, 2))
            painter.drawLine(int(x), int(y - 6), int(x), int(y - 35))
            
            # Bandera
            poly = QPolygonF([
                QPointF(x, y - 35),
                QPointF(x + 16, y - 27),
                QPointF(x, y - 19)
            ])
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(color_base))
            painter.drawPolygon(poly)

        dibujar_bandera_extremo(margen_x, y_linea, "Inicio del Examen", dt_inicio)
        dibujar_bandera_extremo(w - margen_x, y_linea, "Fin del Examen", dt_fin)
        
        # --- Eventos (Diseño Gemini: Icono en mástil, Texto al lado, Hora en Track) ---
        duracion_total = self.t_max - self.t_min
        
        # Pre-calcular posiciones X para esparcirlas si están muy pegadas
        for ev in self.eventos:
            pct = (ev['time'] - self.t_min) / duracion_total
            ev['x_pos'] = margen_x + int(pct * ancho_linea)
            
        
        colores = {
            'audio': QColor("#F1C40F"),   
            'proceso': QColor("#3498DB"), 
            'webcam': QColor("#E74C3C"),  
            'teclado': QColor("#9B59B6")  
        }
        
        iconos = {
            'audio': '🎙',   
            'proceso': '💻', 
            'webcam': '👁',  
            'teclado': '⌨'  
        }
        
        # Algoritmo de asignación de niveles (Arriba / Abajo) con mástiles mucho más altos
        
        niveles = []
        for ev in self.eventos:
            x_pos = ev['x_pos']
            color = colores.get(ev['tipo'], QColor("#E74C3C"))
            # Fallback a un icono genérico
            icono_char = '•'
            if ev['tipo'] == 'audio': icono_char = '🎙️'
            elif ev['tipo'] == 'proceso': icono_char = '⚙️'
            elif ev['tipo'] == 'webcam': icono_char = '👁️'
            elif ev['tipo'] == 'teclado': icono_char = '⌨️'
            
            elegido = None
            for niv in niveles:
                if x_pos > niv['last_x'] + 60:
                    elegido = niv
                    break
            if elegido is None:
                new_idx = len(niveles)
                dir_ = -1 if new_idx % 2 == 0 else 1
                alto = 50 + (new_idx // 2) * 45
                elegido = {'dir': dir_, 'last_x': -1000, 'alto': alto}
                niveles.append(elegido)
            elegido['last_x'] = x_pos
            
            direccion = elegido['dir']
            alto_mastil = elegido['alto']
            y_end = y_linea + (alto_mastil * direccion)
            
            # 1. Dibujar Mástil
            painter.setPen(QPen(color, 2))
            painter.drawLine(x_pos, y_linea, x_pos, y_end)
            
            # 2. Nodo en el Track (Un punto con borde blanco y centro de color)
            radio = 6
            rect_nodo = QRectF(x_pos - radio, y_linea - radio, radio * 2, radio * 2)
            painter.setPen(QPen(QColor("white"), 2))
            painter.setBrush(QBrush(color))
            painter.drawEllipse(rect_nodo)
            
            # 3. Nodo en el extremo del mástil (Icono)
            radio_extremo = 12
            rect_icono = QRectF(x_pos - radio_extremo, y_end - radio_extremo, radio_extremo * 2, radio_extremo * 2)
            painter.setPen(QPen(color, 2))
            painter.setBrush(QBrush(QColor("white")))
            painter.drawEllipse(rect_icono)
            
            # Dibujar icono simplificado (Letra) en el extremo
            painter.setPen(color)
            font.setPointSize(10)
            font.setBold(True)
            painter.setFont(font)
            painter.drawText(rect_icono, Qt.AlignmentFlag.AlignCenter, icono_char)
            
            # 4. Texto (Etiqueta arriba o abajo del icono) CON LA HORA!
            str_hora = datetime.datetime.fromtimestamp(ev['time']).strftime("%H:%M:%S")
            texto_completo = f"{ev['motivo']}\n{str_hora}"
            
            if direccion == -1: # Hacia arriba (texto debe ir mas arriba que el circulo)
                y_texto = y_end - 45
            else: # Hacia abajo (texto debe ir mas abajo que el circulo)
                y_texto = y_end + 15
                
            rect_texto = QRectF(x_pos - 50, y_texto, 100, 30)
            painter.setPen(self.palette().windowText().color())
            font.setPointSize(8)
            painter.setFont(font)
            painter.drawText(rect_texto, Qt.AlignmentFlag.AlignCenter, texto_completo)
            
            # (Se eliminó el texto en la línea base para que no se superpongan entre sí cuando hay muchos eventos)
            
            # Hitbox para hacer clic
            ev['rect'] = rect_icono.united(rect_texto).united(rect_nodo)



    def mousePressEvent(self, event):
        pos = event.position()
        for ev in self.eventos:
            if ev['rect'] and ev['rect'].contains(pos):
                self.fn_abrir_categoria(ev['tipo'], ev['titulo_cat'])
                return


class PanelCarpetas(QWidget):
    def __init__(self, fn_volver):
        super().__init__()
        self.fn_volver = fn_volver
        self.sesion_id = ""
        self.nombre = ""
        self.ruta_evidencias_local = ""
        
        self.setObjectName("panel_carpetas_main")
        self.lay_main = QVBoxLayout(self)
        self.lay_main.setContentsMargins(40, 40, 40, 40)
        self.lay_main.setSpacing(20)
        
        # --- HEADER PRINCIPAL ---
        self.lbl_titulo = QLabel("Apartado de evidencias del estudiante")
        self.lbl_titulo.setObjectName("pc_lbl_main_titulo")
        
        head_lay = QHBoxLayout()
        head_lay.addWidget(self.lbl_titulo)
        head_lay.addStretch()
        
        self.btn_volver_reporte = QPushButton("Volver al Reporte")
        self.btn_volver_reporte.setStyleSheet("background-color: #005928; color: white; border-radius: 4px; padding: 10px 20px; font-weight: bold;")
        self.btn_volver_reporte.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_volver_reporte.clicked.connect(self.fn_volver)
        
        self.btn_auditoria_forense = QPushButton("🛡 Auditoría Forense")
        self.btn_auditoria_forense.setStyleSheet("background-color: #2c3e50; color: white; border-radius: 4px; padding: 10px 20px; font-weight: bold; border: 2px solid #34495e;")
        self.btn_auditoria_forense.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_auditoria_forense.clicked.connect(self.ejecutar_auditoria)
        
        self.btn_volver_carpetas = QPushButton("Volver a Carpetas")
        self.btn_volver_carpetas.setStyleSheet("background-color: #555555; color: white; border-radius: 4px; padding: 10px 20px; font-weight: bold;")
        self.btn_volver_carpetas.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_volver_carpetas.clicked.connect(self.mostrar_vista_carpetas)
        self.btn_volver_carpetas.setVisible(False)
        
        head_lay.addWidget(self.btn_auditoria_forense)
        head_lay.addWidget(self.btn_volver_carpetas)
        head_lay.addWidget(self.btn_volver_reporte)
        self.lay_main.addLayout(head_lay)
        
        # --- SELECTOR DE REINTENTOS (Idéntico visualmente a ReporteIA) ---
        self.widget_selector_intentos = QWidget()
        self.widget_selector_intentos.setObjectName("widget_selector_intentos")
        lay_sel = QHBoxLayout(self.widget_selector_intentos)
        lay_sel.setContentsMargins(0, 4, 0, 10)
        lay_sel.setSpacing(12)
        
        self.lbl_seleccionar_intento = QLabel("Seleccionar Intento:")
        self.lbl_seleccionar_intento.setObjectName("lbl_seleccionar_intento")
        
        self.combo_intentos = QComboBox()
        self.combo_intentos.setObjectName("combo_intentos")
        self.combo_intentos.setMinimumHeight(35)
        self.combo_intentos.setMinimumWidth(350)
        self.combo_intentos.setCursor(Qt.CursorShape.PointingHandCursor)
        self.combo_intentos.currentIndexChanged.connect(self._al_cambiar_intento)
        
        lay_sel.addWidget(self.lbl_seleccionar_intento)
        lay_sel.addWidget(self.combo_intentos)
        lay_sel.addStretch()
        
        self.widget_selector_intentos.setVisible(False)
        self.lay_main.addWidget(self.widget_selector_intentos)
        
        # --- CONTENEDOR DINAMICO ---
        # Agregamos todo a un ScrollArea para evitar squishing en pantallas pequeñas
        self.scroll_principal = QScrollArea()
        self.scroll_principal.setWidgetResizable(True)
        # Hacemos que la barra de scroll sea invisible visualmente pero que siga funcionando
        self.scroll_principal.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_principal.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        self.lay_main.addWidget(self.scroll_principal)
        
        self.contenedor_dinamico = QWidget()
        self.contenedor_dinamico.setStyleSheet("background: transparent;")
        self.scroll_principal.setWidget(self.contenedor_dinamico)
        
        self.lay_dinamico = QVBoxLayout(self.contenedor_dinamico)
        self.lay_dinamico.setContentsMargins(0,0,0,0)
        
        self.cards = {}
        self.crear_vista_carpetas()
        
        # --- VISTA DE EVIDENCIAS ---
        self.widget_evidencias = QWidget()
        self.widget_evidencias.setObjectName("panel_carpetas_evidencias")
        self.lay_evidencias = QVBoxLayout(self.widget_evidencias)
        self.lay_evidencias.setSpacing(20)
        self.lay_evidencias.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        self.lay_dinamico.addWidget(self.widget_evidencias)
        self.widget_evidencias.setVisible(False)

    def crear_vista_carpetas(self):
        self.widget_carpetas = QWidget()
        self.widget_carpetas.setStyleSheet("background: transparent;")
        
        self.lay_carpetas_main = QVBoxLayout(self.widget_carpetas)
        self.lay_carpetas_main.setContentsMargins(0,0,0,0)
        self.lay_carpetas_main.setSpacing(30)
        
        widget_grid = QWidget()
        self.grid_carpetas = QGridLayout(widget_grid)
        self.grid_carpetas.setSpacing(25)
        self.grid_carpetas.setContentsMargins(0,0,0,0)
        
        self.cards['audio'] = self._crear_tarjeta(
            "VECTOR 01", "Audio", 
            "Archivos de sonido y grabaciones de voz del entorno.", 
            self.abrir_audio
        )
        self.cards['proceso'] = self._crear_tarjeta(
            "VECTOR 02", "Procesos y Sistema", 
            "Capturas de pantalla de aplicaciones no permitidas y alertas de sistema.", 
            self.abrir_procesos
        )
        self.cards['webcam'] = self._crear_tarjeta(
            "VECTOR 03", "Webcam", 
            "Capturas fotográficas de rostros no reconocidos, uso de celular o desatención.", 
            self.abrir_webcam
        )
        self.cards['teclado'] = self._crear_tarjeta(
            "VECTOR 04", "Teclado", 
            "Registro de comandos prohibidos como Alt+Tab o uso del portapapeles.", 
            self.abrir_teclado
        )
        
        for i, key in enumerate(['audio', 'proceso', 'webcam', 'teclado']):
            self.grid_carpetas.setColumnStretch(i % 2, 1)
        
        self.grid_carpetas.addWidget(self.cards['audio'][0], 0, 0)
        self.grid_carpetas.addWidget(self.cards['proceso'][0], 0, 1)
        self.grid_carpetas.addWidget(self.cards['webcam'][0], 1, 0)
        self.grid_carpetas.addWidget(self.cards['teclado'][0], 1, 1)
        
        self.lay_carpetas_main.addWidget(widget_grid)
        self.lay_carpetas_main.addSpacing(80) # Extra separación masiva entre carpetas y línea de tiempo
        
        self.timeline = LineaDeTiempoWidget(self.abrir_categoria)
        
        # Envolvemos la línea de tiempo en su propio ScrollArea para que su ancho dinámico no rompa el diseño general
        self.scroll_timeline = QScrollArea()
        self.scroll_timeline.setWidgetResizable(True)
        self.scroll_timeline.setWidget(self.timeline)
        self.scroll_timeline.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        self.scroll_timeline.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_timeline.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll_timeline.setMinimumHeight(670)
        
        self.lay_carpetas_main.addWidget(self.scroll_timeline)
        
        self.lay_dinamico.addWidget(self.widget_carpetas)

    def _crear_tarjeta(self, vector, titulo, desc, fn_abrir):
        frame = QFrame()
        frame.setFixedHeight(260) # Aún más grandes a petición del usuario (tamaño mediano-grande)
        frame.setObjectName("pc_tarjeta_folder")
        lay = QVBoxLayout(frame)
        lay.setContentsMargins(20, 20, 20, 20)
        
        l1 = QLabel(vector)
        l1.setObjectName("pc_lbl_vector")
        l2 = QLabel(titulo)
        l2.setObjectName("pc_lbl_titulo")
        
        lbl_desc = QLabel(desc)
        lbl_desc.setWordWrap(True)
        lbl_desc.setObjectName("pc_lbl_desc")
        
        lbl_cantidad = QLabel("Calculando evidencias...")
        lbl_cantidad.setObjectName("pc_lbl_cantidad")
        
        btn_abrir = QPushButton("Abrir Carpeta →")
        btn_abrir.setObjectName("pc_btn_abrir")
        btn_abrir.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_abrir.clicked.connect(fn_abrir)
        
        lay.addWidget(l1)
        lay.addWidget(l2)
        lay.addWidget(lbl_desc)
        lay.addWidget(lbl_cantidad)
        lay.addStretch()
        lay.addWidget(btn_abrir, alignment=Qt.AlignmentFlag.AlignRight)
        
        return (frame, lbl_cantidad)

    def _buscar_ruta_sesion(self, sesion_id):
        base_dir = os.path.join(os.path.expanduser("~"), "Documents", "DataSupervision", "Examenes")
        if not os.path.exists(base_dir): return None
        for root, dirs, files in os.walk(base_dir):
            if sesion_id in dirs: return os.path.join(root, sesion_id)
        return None

    def cargar_datos(self, nombre, sesion_id):
        self.nombre = nombre
        self.sesion_id = sesion_id
        nombre_puro = nombre.split('(')[0].strip()
        self.lbl_titulo.setText(f"Apartado de evidencias del estudiante {nombre_puro}")
        
        # Determinar el código del examen de forma robusta
        codigo_examen = "Desconocido"
        parent = self.window()
        if hasattr(parent, "vista_sala") and getattr(parent.vista_sala, "codigo_examen_actual", None):
            codigo_examen = parent.vista_sala.codigo_examen_actual
            
        if codigo_examen == "Desconocido" and hasattr(parent, "vista_reporte") and hasattr(parent.vista_reporte, "combo_examenes"):
            idx = parent.vista_reporte.combo_examenes.currentIndex()
            if 0 <= idx < len(getattr(parent.vista_reporte, "examenes_ids", [])):
                codigo_examen = parent.vista_reporte.examenes_ids[idx]
                
        if codigo_examen == "Desconocido":
            ruta_ses = self._buscar_ruta_sesion(sesion_id)
            if ruta_ses:
                partes = os.path.normpath(ruta_ses).split(os.sep)
                if len(partes) >= 3 and partes[-3] not in ["Examenes", "DataSupervision"]:
                    codigo_examen = partes[-3]

        if codigo_examen == "Desconocido":
            from api.cliente_respuesta import cliente_api
            exito_sesion, sesion_info = cliente_api.obtener_sesion(sesion_id)
            if exito_sesion and isinstance(sesion_info, dict):
                ex = sesion_info.get("examen", {})
                if isinstance(ex, dict):
                    codigo_examen = ex.get("codigoExamen", ex.get("codigo", sesion_info.get("codigoExamen", "Desconocido")))
                else:
                    codigo_examen = sesion_info.get("codigoExamen", "Desconocido")

        self.codigo_examen_actual = codigo_examen
        
        # 1. Detectar si existen reintentos y configurar el combo selector
        self._detectar_intentos(codigo_examen, nombre_puro, sesion_id)
        
        # 2. Cargar y renderizar las evidencias de la sesión seleccionada
        self._aplicar_sesion(sesion_id)

    def _detectar_intentos(self, codigo_examen, nombre_puro, sesion_id_actual):
        """
        Escanea las sesiones de la base de datos (API) como fuente de verdad
        para detectar todos los intentos válidos del estudiante en el examen actual.
        Si la API no está disponible, utiliza el almacenamiento forense local como respaldo.
        Si hay más de 1 intento (> 0 reintentos), activa y llena el selector dinámico.
        """
        from api.cliente_respuesta import cliente_api
        import unicodedata
        import datetime
        
        def norm_str(s):
            if not s: return ""
            return "".join(c for c in unicodedata.normalize('NFD', str(s).lower()) if unicodedata.category(c) != 'Mn').replace("_", " ").strip()
            
        nom_norm = norm_str(nombre_puro)
        
        # 1. Consultar a la API para obtener las sesiones registradas en la Base de Datos
        sesiones_api = None
        if codigo_examen and codigo_examen != "Desconocido":
            try:
                exito, resp_api = cliente_api.obtener_sesiones_examen(codigo_examen, todas=True)
                if exito and isinstance(resp_api, list):
                    sesiones_api = resp_api
            except Exception as e:
                print(f"[PanelCarpetas] Error consultando API para sesiones: {e}")
                
        # Si la llamada a la API no devolvió lista pero la ventana padre tiene sesiones en memoria (ReporteIA)
        if sesiones_api is None:
            parent = self.window()
            if hasattr(parent, "vista_reporte") and getattr(parent.vista_reporte, "sesiones_actuales", None):
                sesiones_api = parent.vista_reporte.sesiones_actuales
                
        intentos_map = {}
        
        def calcular_timestamp(sid):
            ts = 0
            if len(sid) == 24:
                try:
                    ts_mongo = int(sid[:8], 16)
                    if 1577836800 <= ts_mongo <= 2208988800:
                        ts = ts_mongo
                except Exception:
                    pass
            if ts == 0:
                ruta_sid = self._buscar_ruta_sesion(sid)
                if ruta_sid and os.path.exists(ruta_sid):
                    try:
                        ts = min(os.path.getctime(ruta_sid), os.path.getmtime(ruta_sid))
                    except Exception:
                        pass
            return ts

        if sesiones_api is not None:
            # --- CASO PRINCIPAL: La API / Base de Datos es la fuente de verdad ---
            # Identificar el estudianteId correspondiente a la sesión actual
            target_estudiante_id = None
            for s in sesiones_api:
                if str(s.get("sesionId", "")).strip() == str(sesion_id_actual).strip():
                    target_estudiante_id = s.get("estudianteId")
                    break
                    
            if not target_estudiante_id:
                try:
                    ex, s_info = cliente_api.obtener_sesion(sesion_id_actual)
                    if ex and isinstance(s_info, dict):
                        target_estudiante_id = s_info.get("estudianteId")
                except Exception:
                    pass

            # Filtrar estrictamente las sesiones activas en la BD para este estudiante en este examen
            for s in sesiones_api:
                sid = str(s.get("sesionId", "")).strip()
                if not sid:
                    continue
                pertenece = False
                if target_estudiante_id and s.get("estudianteId") == target_estudiante_id:
                    pertenece = True
                elif not target_estudiante_id and s.get("nombreEstudiante"):
                    if norm_str(s.get("nombreEstudiante")) == nom_norm:
                        pertenece = True
                        
                if pertenece:
                    intentos_map[sid] = {
                        "sesion_id": sid,
                        "timestamp": calcular_timestamp(sid)
                    }
                    
            # Asegurar que al menos la sesión actual seleccionada esté presente
            if sesion_id_actual and sesion_id_actual not in intentos_map:
                intentos_map[sesion_id_actual] = {
                    "sesion_id": sesion_id_actual,
                    "timestamp": calcular_timestamp(sesion_id_actual)
                }

        else:
            # --- CASO SECUNDARIO (OFFLINE / FALLBACK): Escanear disco local ---
            intentos_map[sesion_id_actual] = {
                "sesion_id": sesion_id_actual,
                "timestamp": calcular_timestamp(sesion_id_actual)
            }
            ruta_actual = self._buscar_ruta_sesion(sesion_id_actual)
            carpeta_estudiante_disco = None
            if ruta_actual and os.path.exists(ruta_actual):
                carpeta_estudiante_disco = os.path.dirname(ruta_actual)
                
            if not carpeta_estudiante_disco and codigo_examen and codigo_examen != "Desconocido":
                nombre_limpio = nombre_puro.replace(" ", "_").strip("_")
                base_cand = os.path.join(os.path.expanduser("~"), "Documents", "DataSupervision", "Examenes", codigo_examen, nombre_limpio)
                if os.path.exists(base_cand):
                    carpeta_estudiante_disco = base_cand

            if carpeta_estudiante_disco and os.path.isdir(carpeta_estudiante_disco):
                try:
                    for entrada in os.listdir(carpeta_estudiante_disco):
                        ruta_sub = os.path.join(carpeta_estudiante_disco, entrada)
                        if os.path.isdir(ruta_sub):
                            es_sesion = any(os.path.exists(os.path.join(ruta_sub, cat)) for cat in ['audio', 'proceso', 'webcam', 'teclado'])
                            if es_sesion or len(entrada) == 24:
                                intentos_map[entrada] = {
                                    "sesion_id": entrada,
                                    "timestamp": calcular_timestamp(entrada)
                                }
                except Exception as e:
                    print(f"[PanelCarpetas] Error en fallback de disco: {e}")

        lista_intentos = list(intentos_map.values())
        lista_intentos.sort(key=lambda x: x["timestamp"])

        self.combo_intentos.blockSignals(True)
        self.combo_intentos.clear()

        if len(lista_intentos) > 1:
            total = len(lista_intentos)
            for idx, item in enumerate(lista_intentos, 1):
                sid = item["sesion_id"]
                ts = item["timestamp"]
                if ts > 0:
                    dt = datetime.datetime.fromtimestamp(ts)
                    fecha_str = dt.strftime("%d/%m/%Y %I:%M %p")
                else:
                    fecha_str = "Fecha no registrada"
                
                if idx == total:
                    texto = f"Intento {idx} (Más reciente) — {fecha_str}"
                else:
                    texto = f"Intento {idx} — {fecha_str}"
                    
                self.combo_intentos.addItem(texto, sid)
                
            idx_sel = -1
            for i in range(self.combo_intentos.count()):
                if self.combo_intentos.itemData(i) == sesion_id_actual:
                    idx_sel = i
                    break
            if idx_sel >= 0:
                self.combo_intentos.setCurrentIndex(idx_sel)
            else:
                self.combo_intentos.setCurrentIndex(self.combo_intentos.count() - 1)
                
            self.widget_selector_intentos.setVisible(True)
        else:
            self.widget_selector_intentos.setVisible(False)

        self.combo_intentos.blockSignals(False)


    def _al_cambiar_intento(self, index):
        """Manejador del evento de selección de un intento previo o reciente."""
        if index < 0:
            return
        nueva_sesion_id = self.combo_intentos.itemData(index)
        if not nueva_sesion_id or nueva_sesion_id == self.sesion_id:
            return
        self._aplicar_sesion(nueva_sesion_id)

    def _aplicar_sesion(self, sesion_id):
        """Aplica la sesión seleccionada, actualizando contadores, línea de tiempo y evidencias."""
        from api.cliente_respuesta import cliente_api
        
        self.sesion_id = sesion_id
        
        # Buscar la ruta real en el disco usando el sesion_id
        base_dir = self._buscar_ruta_sesion(sesion_id)

        if not base_dir:
            # Si no existe, crear la ruta por defecto
            nombre_real = self.nombre.split('(')[0].strip()
            nombre_limpio = nombre_real.replace(" ", "_").strip("_")
            codigo_ex = getattr(self, "codigo_examen_actual", "Desconocido")
            base_dir = os.path.join(os.path.expanduser("~"), "Documents", "DataSupervision", "Examenes", codigo_ex, nombre_limpio, sesion_id)
            for cat in ['audio', 'proceso', 'webcam', 'teclado']:
                os.makedirs(os.path.join(base_dir, cat), exist_ok=True)
            
        # Llamar a la API para traer la metadata con los hashes
        try:
            exito, alertas = cliente_api.obtener_alertas(sesion_id)
            self.alertas_metadata = alertas if exito else []
        except Exception as e:
            print(f"[PanelCarpetas] Error obteniendo alertas para sesion {sesion_id}: {e}")
            self.alertas_metadata = []
        
        self.ruta_evidencias_local = base_dir
        
        # Contar archivos en cada vector
        for carpeta in ['audio', 'proceso', 'webcam', 'teclado']:
            cantidad = 0
            if self.ruta_evidencias_local:
                ruta_cat = os.path.join(self.ruta_evidencias_local, carpeta)
                if os.path.exists(ruta_cat):
                    archivos = [a for a in os.listdir(ruta_cat) if os.path.isfile(os.path.join(ruta_cat, a))]
                    cantidad = len(archivos)
            lbl = self.cards[carpeta][1]
            if cantidad > 0:
                lbl.setText(f"📂 {cantidad} archivos de evidencia recopilados.")
                lbl.setStyleSheet("")
            else:
                lbl.setText("📁 Carpeta sin evidencias (0 archivos).")
                lbl.setStyleSheet("color: #777777; font-size: 13px; font-weight: bold; margin-top: 5px; border: none; background: transparent;")
                
        if self.ruta_evidencias_local:
            self.timeline.cargar_eventos(self.ruta_evidencias_local)
        else:
            self.timeline.cargar_eventos(None)
            
        self.mostrar_vista_carpetas()


    def mostrar_vista_carpetas(self):
        self.widget_evidencias.setVisible(False)
        self.widget_carpetas.setVisible(True)
        self.btn_volver_carpetas.setVisible(False)
        self.btn_volver_reporte.setVisible(True)

    def _abrir_archivo(self, ruta_archivo):
        # --- DESCIFRADO E2EE AES-256 PARA VISUALIZACION LOCAL ---
        import tempfile
        import os
        from cryptography.fernet import Fernet
        from config.configuracion import AES_SECRET_KEY
        import base64

        try:
            with open(ruta_archivo, 'rb') as f:
                contenido_cifrado = f.read()
            
            f_crypto = Fernet(AES_SECRET_KEY)
            base64_descifrado = f_crypto.decrypt(contenido_cifrado).decode('utf-8')
            contenido_final = base64.b64decode(base64_descifrado)
            
            # Crear archivo temporal descifrado
            ext = os.path.splitext(ruta_archivo)[1]
            if not ext: ext = ".png" # fallback
            
            fd, temp_path = tempfile.mkstemp(suffix=ext)
            with os.fdopen(fd, 'wb') as f_temp:
                f_temp.write(contenido_final)
                
            # Abrir el archivo temporal con el visor de Windows
            QDesktopServices.openUrl(QUrl.fromLocalFile(temp_path))
            print(f"[E2EE] Archivo abierto con exito (descifrado en {temp_path})")
            
        except Exception as e:
            print(f"[E2EE] El archivo no estaba cifrado o hubo un error al descifrar: {e}")
            # Fallback: abrir original por si no es cifrado (ej. fotos viejas antes del parche E2EE)
            QDesktopServices.openUrl(QUrl.fromLocalFile(ruta_archivo))

    def abrir_categoria(self, nombre_carpeta, titulo_cat):
        self.widget_carpetas.setVisible(False)
        self.btn_volver_reporte.setVisible(False)
        self.btn_volver_carpetas.setVisible(True)
        self.widget_evidencias.setVisible(True)
        
        while self.lay_evidencias.count():
            child = self.lay_evidencias.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
            elif child.layout():
                inner = child.layout()
                while inner.count():
                    item = inner.takeAt(0)
                    if item.widget():
                        item.widget().deleteLater()
                inner.deleteLater()
                
        lbl_cat = QLabel(f"Evidencias Locales de {titulo_cat}")
        lbl_cat.setObjectName("pc_lbl_cat")
        self.lay_evidencias.addWidget(lbl_cat)
        
        if not self.ruta_evidencias_local:
            lbl_vacio = QLabel("No se encontro el directorio local de DataSupervision.")
            self.lay_evidencias.addWidget(lbl_vacio)
            self.lay_evidencias.addStretch()
            return
            
        ruta_carpeta = os.path.join(self.ruta_evidencias_local, nombre_carpeta)
        
        if not os.path.exists(ruta_carpeta):
            lbl_vacio = QLabel(f"La carpeta '{nombre_carpeta}' esta vacia.")
            self.lay_evidencias.addWidget(lbl_vacio)
            self.lay_evidencias.addStretch()
            return
            
        archivos = os.listdir(ruta_carpeta)
        archivos = [a for a in archivos if os.path.isfile(os.path.join(ruta_carpeta, a))]
        
        if not archivos:
            lbl_vacio = QLabel("No hay archivos guardados.")
            self.lay_evidencias.addWidget(lbl_vacio)
            self.lay_evidencias.addStretch()
            return
            
        grid = QGridLayout()
        grid.setSpacing(20)
        self.lay_evidencias.addLayout(grid)
        
        fila = 0
        col = 0
        max_cols = 4 
        
        for c in range(max_cols):
            grid.setColumnStretch(c, 1)
            
        for i, archivo in enumerate(archivos):
            ruta_completa = os.path.join(ruta_carpeta, archivo)
            
            frame_card = QFrame()
            frame_card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            frame_card.setMinimumHeight(240)
            frame_card.setObjectName("pc_frame_card")
            lay_c = QVBoxLayout(frame_card)
            lay_c.setContentsMargins(15, 15, 15, 15)
            
            num = str(i+1).zfill(2)
            nombre_corto = f"EV_{nombre_carpeta}_{num}"
            
            lbl_info = QLabel(f"<b>{nombre_corto}</b>")
            lbl_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl_info.setObjectName("pc_lbl_info")
            lay_c.addWidget(lbl_info)
            
            lbl_img = QLabel()
            lbl_img.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl_img.setStyleSheet("border: none; background: transparent;")
            lbl_img.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            
            es_imagen = archivo.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))
            
            if es_imagen:
                try:
                    from cryptography.fernet import Fernet
                    from config.configuracion import AES_SECRET_KEY
                    f = Fernet(AES_SECRET_KEY)
                    with open(ruta_completa, 'rb') as file_obj:
                        datos = file_obj.read()
                    try:
                        datos = f.decrypt(datos)
                    except:
                        pass
                    pixmap = QPixmap()
                    pixmap.loadFromData(datos)
                    if not pixmap.isNull():
                        pix_scaled = pixmap.scaled(200, 150, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                        lbl_img.setPixmap(pix_scaled)
                    else:
                        lbl_img.setText("📷")
                        lbl_img.setStyleSheet("font-size: 40px; border: none; background: transparent;")
                except:
                    lbl_img.setText("📷")
                    lbl_img.setStyleSheet("font-size: 40px; border: none; background: transparent;")
            else:
                lbl_img.setText("🎵" if archivo.lower().endswith('.wav') else "📄")
                lbl_img.setStyleSheet("font-size: 60px; border: none; background: transparent;")
                
            lay_c.addWidget(lbl_img)
            lay_c.addStretch()
            
            btn_play = QPushButton("Ver" if es_imagen else "Reproducir")
            btn_play.setStyleSheet("QPushButton { background-color: #005928; color: white; border-radius: 4px; padding: 10px; font-weight: bold; } QPushButton:hover { background-color: #00451f; }")
            btn_play.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_play.clicked.connect(lambda checked, ruta=ruta_completa: self._abrir_archivo(ruta))
            
            lay_c.addWidget(btn_play)
            grid.addWidget(frame_card, fila, col)
            
            col += 1
            if col >= max_cols:
                col = 0
                fila += 1
                
        self.lay_evidencias.addStretch()

    def abrir_audio(self): self.abrir_categoria("audio", "Audio")
    def abrir_procesos(self): self.abrir_categoria("proceso", "Procesos y Sistema")
    def abrir_webcam(self): self.abrir_categoria("webcam", "Webcam")
    def abrir_teclado(self): self.abrir_categoria("teclado", "Teclado")


    def ejecutar_auditoria(self):
        import hashlib
        import os
        from PyQt6.QtWidgets import QMessageBox, QProgressDialog
        from PyQt6.QtCore import Qt
        
        if not hasattr(self, 'alertas_metadata') or not self.alertas_metadata:
            QMessageBox.information(self, "Auditoria", "No hay evidencias para auditar.")
            return
            
        total_archivos_esperados = 0
        for al in self.alertas_metadata:
            if al.get('hashWebcam'): total_archivos_esperados += 1
            if al.get('hashPantalla'): total_archivos_esperados += 1
            if al.get('hashAudio'): total_archivos_esperados += 1
            
        if total_archivos_esperados == 0:
            box = QMessageBox(self)
            box.setIcon(QMessageBox.Icon.Information)
            box.setWindowTitle("Auditoria")
            box.setText("No se encontraron archivos en el disco con un hash valido.\n\nNota: Las evidencias capturadas ANTES de implementar el Sello Forense no tienen firma matematica en la base de datos.\n\nPor favor, realiza un nuevo examen de prueba para verificar esta funcion.")
            box.exec()
            return
            
        progress = QProgressDialog("Analizando firma Hash de las evidencias...", "Cancelar", 0, total_archivos_esperados, self)
        progress.setWindowTitle("Sello Forense")
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(0) # Forzar que se muestre de inmediato
        progress.show()
        
        archivos_analizados = 0
        archivos_validos = 0
        archivos_manipulados = []
        
        for al in self.alertas_metadata:
            if progress.wasCanceled():
                break
                
            id_alerta = al.get('idAlerta', 'ws')
            
            # Revisar Webcam
            hash_webcam = al.get('hashWebcam')
            path_webcam = os.path.join(self.ruta_evidencias_local, "webcam", f"evidencia_{id_alerta}.webp")
            if hash_webcam and os.path.exists(path_webcam):
                archivos_analizados += 1
                progress.setLabelText(f"Analizando firma Hash de las evidencias {archivos_analizados}/{total_archivos_esperados}...")
                progress.setValue(archivos_analizados)
                import time
                time.sleep(0.8)
                from PyQt6.QtWidgets import QApplication
                QApplication.processEvents()
                with open(path_webcam, "rb") as f:
                    from cryptography.fernet import Fernet
                    from config.configuracion import AES_SECRET_KEY
                    f_crypto = Fernet(AES_SECRET_KEY)
                    try:
                        bytes_enc = f.read()
                        bytes_dec = f_crypto.decrypt(bytes_enc)
                        hash_calc = hashlib.sha256(bytes_dec).hexdigest()
                        if hash_calc == hash_webcam: archivos_validos += 1
                        else: archivos_manipulados.append(path_webcam)
                    except:
                        archivos_manipulados.append(path_webcam)
            
            # Revisar Proceso/Pantalla
            hash_pantalla = al.get('hashPantalla')
            clase = al.get('claseAlerta', '').upper()
            subc = "proceso" if clase in ["SISTEMA", "PROCESO", "PROCESOS"] else ("teclado" if clase == "TECLADO" else "webcam")
            suf = ".webp" if clase in ["SISTEMA", "PROCESO", "PROCESOS", "TECLADO"] else "_pantalla.webp"
            path_pantalla = os.path.join(self.ruta_evidencias_local, subc, f"evidencia_{id_alerta}{suf}")
            
            if hash_pantalla and os.path.exists(path_pantalla):
                archivos_analizados += 1
                progress.setLabelText(f"Analizando firma Hash de las evidencias {archivos_analizados}/{total_archivos_esperados}...")
                progress.setValue(archivos_analizados)
                import time
                time.sleep(0.8)
                from PyQt6.QtWidgets import QApplication
                QApplication.processEvents()
                with open(path_pantalla, "rb") as f:
                    from cryptography.fernet import Fernet
                    from config.configuracion import AES_SECRET_KEY
                    f_crypto = Fernet(AES_SECRET_KEY)
                    try:
                        bytes_enc = f.read()
                        bytes_dec = f_crypto.decrypt(bytes_enc)
                        hash_calc = hashlib.sha256(bytes_dec).hexdigest()
                        if hash_calc == hash_pantalla: archivos_validos += 1
                        else: archivos_manipulados.append(path_pantalla)
                    except:
                        archivos_manipulados.append(path_pantalla)
                        
            # Revisar Audio
            hash_audio = al.get('hashAudio')
            path_audio = os.path.join(self.ruta_evidencias_local, "audio", f"evidencia_{id_alerta}.wav")
            if hash_audio and os.path.exists(path_audio):
                archivos_analizados += 1
                progress.setLabelText(f"Analizando firma Hash de las evidencias {archivos_analizados}/{total_archivos_esperados}...")
                progress.setValue(archivos_analizados)
                import time
                time.sleep(0.8)
                from PyQt6.QtWidgets import QApplication
                QApplication.processEvents()
                with open(path_audio, "rb") as f:
                    from cryptography.fernet import Fernet
                    from config.configuracion import AES_SECRET_KEY
                    f_crypto = Fernet(AES_SECRET_KEY)
                    try:
                        bytes_enc = f.read()
                        bytes_dec = f_crypto.decrypt(bytes_enc)
                        hash_calc = hashlib.sha256(bytes_dec).hexdigest()
                        if hash_calc == hash_audio: archivos_validos += 1
                        else: archivos_manipulados.append(path_audio)
                    except:
                        archivos_manipulados.append(path_audio)
                        
        progress.setValue(total_archivos_esperados)
            
        if archivos_manipulados:
            msg = "PELIGRO DE SEGURIDAD\n\nSe auditaron " + str(archivos_analizados) + " archivos.\nArchivos Validos: " + str(archivos_validos) + "\nArchivos MANIPULADOS O CORRUPTOS: " + str(len(archivos_manipulados)) + "\n\nArchivos alterados:\n"
            msg += "\n".join([os.path.basename(p) for p in archivos_manipulados[:5]])
            if len(archivos_manipulados) > 5: msg += "..."
            
            box = QMessageBox(self)
            box.setIcon(QMessageBox.Icon.Critical)
            box.setWindowTitle("Sello Forense Roto")
            box.setText(msg)
            box.exec()
        else:
            box = QMessageBox(self)
            box.setIcon(QMessageBox.Icon.Information)
            box.setWindowTitle("Auditoria Forense Exitosa")
            msg2 = "INTEGRIDAD CONFIRMADA\n\nSe verificaron matematicamente " + str(archivos_analizados) + " archivos de evidencia con SHA-256.\n\nNingun archivo ha sido manipulado, editado ni corrompido desde que salio del PC del estudiante."
            box.setText(msg2)
            box.exec()
