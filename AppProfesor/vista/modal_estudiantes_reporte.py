# vista/modal_estudiantes_reporte.py
# --------------------------------------------------------------------
# Modal del Directorio Completo de Estudiantes y Evidencias
# Permite al profesor buscar, filtrar y auditar las evidencias de
# CUALQUIER estudiante del examen (no solo del Top 3).
# Compatible con temas claro y oscuro mediante hojas de estilo.
# --------------------------------------------------------------------

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QLineEdit, QTableWidget, QTableWidgetItem,
    QHeaderView, QWidget, QFrame, QSizePolicy, QApplication
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QFont, QIcon, QColor


class ModalEstudiantesReporte(QDialog):
    """
    Directorio navegable con búsqueda en tiempo real de todos los estudiantes
    evaluados en un examen, con acceso directo a sus carpetas forenses.
    """
    def __init__(self, lista_estudiantes: list, codigo_examen: str, callback_ver_detalle, parent=None):
        super().__init__(parent)
        self.setObjectName("ModalEstudiantesReporte")
        self.setWindowTitle(f"Directorio de Estudiantes — Examen {codigo_examen}")
        self.setModal(True)

        self.lista_estudiantes = lista_estudiantes
        self.codigo_examen = codigo_examen
        self.callback_ver_detalle = callback_ver_detalle
        self.filtro_actual = "TODOS"

        # Dimensiones dinámicas basadas en la pantalla
        _screen = QApplication.primaryScreen().availableSize()
        _w = max(720, min(920, int(_screen.width() * 0.58)))
        _h = max(480, min(650, int(_screen.height() * 0.70)))
        self.setMinimumSize(680, 450)
        self.resize(_w, _h)

        # Cargar icono vectorial nítido para carpetas de evidencias
        import os
        ruta_icono = os.path.join(os.path.dirname(__file__), "recursos", "icono_carpeta.svg")
        self._icono_carpeta = QIcon(ruta_icono) if os.path.exists(ruta_icono) else QIcon()

        self._construir_ui()
        self._cargar_tabla()

    def _es_modo_oscuro(self) -> bool:
        """Determina con precisión si el tema activo es oscuro o claro."""
        win = self.window()
        if hasattr(win, "modo_oscuro"):
            return bool(win.modo_oscuro)
        widget = self
        while widget:
            st = widget.styleSheet() or ""
            if "#1E293B" in st or "#0F172A" in st or "DARK MODE" in st:
                return True
            if "#F4F6F6" in st or "tema_claro" in st:
                return False
            widget = widget.parentWidget()
        return False

    def _construir_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(14)

        # ── Cabecera ──────────────────────────────────────────────────
        lay_header = QHBoxLayout()
        lay_titulos = QVBoxLayout()
        lay_titulos.setSpacing(4)

        lbl_titulo = QLabel("📋 Directorio Completo de Estudiantes")
        lbl_titulo.setObjectName("titulo_directorio")
        lbl_titulo.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))

        total_est = len(self.lista_estudiantes)
        lbl_sub = QLabel(f"Examen: <b>{self.codigo_examen}</b>  |  Total evaluados: <b>{total_est} estudiantes</b>")
        lbl_sub.setObjectName("subtitulo_directorio")
        lbl_sub.setFont(QFont("Segoe UI", 10))

        lay_titulos.addWidget(lbl_titulo)
        lay_titulos.addWidget(lbl_sub)
        lay_header.addLayout(lay_titulos)
        lay_header.addStretch()

        # Nota: La 'X' de cierre es la nativa de la barra de título de la ventana modal
        root.addLayout(lay_header)

        # ── Barra de herramientas: Búsqueda y Chips de filtro ────────
        lay_tools = QHBoxLayout()
        lay_tools.setSpacing(10)

        self.input_buscar = QLineEdit()
        self.input_buscar.setObjectName("input_buscar_directorio")
        self.input_buscar.setPlaceholderText("🔍 Buscar por nombre o cédula de estudiante...")
        self.input_buscar.setClearButtonEnabled(True)
        self.input_buscar.setFixedHeight(36)
        self.input_buscar.textChanged.connect(self._aplicar_filtros)
        lay_tools.addWidget(self.input_buscar, 2)

        # Chips de filtro (texto limpio sin círculos de colores)
        self.btn_f_todos = QPushButton(f"Todos ({len(self.lista_estudiantes)})")
        self.btn_f_rojo = QPushButton(f"Críticos ({self._contar_riesgo('ROJO')})")
        self.btn_f_naranja = QPushButton(f"Sospechosos ({self._contar_riesgo('NARANJA')})")
        self.btn_f_verde = QPushButton(f"Limpios ({self._contar_riesgo('VERDE')})")

        self.botones_filtro = {
            "TODOS": self.btn_f_todos,
            "ROJO": self.btn_f_rojo,
            "NARANJA": self.btn_f_naranja,
            "VERDE": self.btn_f_verde
        }

        for clave, btn in self.botones_filtro.items():
            btn.setFixedHeight(36)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setObjectName("chip_filtro")
            btn.clicked.connect(lambda checked, c=clave: self._cambiar_filtro(c))
            lay_tools.addWidget(btn)

        self._actualizar_estilo_chips()
        root.addLayout(lay_tools)

        # ── Tabla de Estudiantes ─────────────────────────────────────
        self.tabla = QTableWidget()
        self.tabla.setObjectName("tabla_directorio_estudiantes")
        self.tabla.setColumnCount(6)
        self.tabla.setHorizontalHeaderLabels([
            "N°", "Estudiante", "Cédula", "Nivel de Riesgo", "Alertas", "Acción"
        ])
        self.tabla.verticalHeader().setVisible(False)
        self.tabla.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tabla.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tabla.setShowGrid(False)

        header = self.tabla.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        self.tabla.setColumnWidth(5, 155)

        root.addWidget(self.tabla, 1)

    def _contar_riesgo(self, categoria: str) -> int:
        return sum(1 for e in self.lista_estudiantes if e.get("categoria_riesgo") == categoria)

    def _cambiar_filtro(self, categoria: str):
        self.filtro_actual = categoria
        self._actualizar_estilo_chips()
        self._aplicar_filtros()

    def _actualizar_estilo_chips(self):
        for clave, btn in self.botones_filtro.items():
            if clave == self.filtro_actual:
                btn.setProperty("activo", "true")
            else:
                btn.setProperty("activo", "false")
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def _aplicar_filtros(self):
        texto_busqueda = self.input_buscar.text().strip().lower()
        estudiantes_filtrados = []

        for e in self.lista_estudiantes:
            # Filtro por categoría
            if self.filtro_actual != "TODOS" and e.get("categoria_riesgo") != self.filtro_actual:
                continue

            # Filtro por texto (nombre, cédula o id)
            nombre = str(e.get("nombre", "")).lower()
            cedula = str(e.get("cedula", "")).lower()
            if not cedula:
                try:
                    from utils.gestor_estudiantes import gestor_estudiantes
                    cedula = gestor_estudiantes.obtener_cedula(
                        nombre=e.get("nombre", ""),
                        estudiante_id=e.get("estudiante_id", "")
                    ).lower()
                except Exception:
                    pass
            eid = str(e.get("estudiante_id", "")).lower()
            if texto_busqueda and (texto_busqueda not in nombre and texto_busqueda not in cedula and texto_busqueda not in eid):
                continue

            estudiantes_filtrados.append(e)

        self._llenar_tabla(estudiantes_filtrados)

    def _cargar_tabla(self):
        self._llenar_tabla(self.lista_estudiantes)

    def _llenar_tabla(self, estudiantes: list):
        self.tabla.setRowCount(0)
        self.tabla.setRowCount(len(estudiantes))

        es_oscuro = self._es_modo_oscuro()
        color_texto_principal = QColor("#F8FAFC") if es_oscuro else QColor("#2C3E50")
        color_texto_secundario = QColor("#94A3B8") if es_oscuro else QColor("#7F8C8D")

        for fila, est in enumerate(estudiantes):
            # 1. N°
            item_num = QTableWidgetItem(str(fila + 1))
            item_num.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item_num.setForeground(color_texto_secundario)
            self.tabla.setItem(fila, 0, item_num)

            # 2. Nombre
            nombre = est.get("nombre", "Desconocido")
            item_nom = QTableWidgetItem(nombre)
            item_nom.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            item_nom.setForeground(color_texto_principal)
            self.tabla.setItem(fila, 1, item_nom)

            # 3. Cédula Real (Nunca usar el ID del estudiante ej: EST-2000)
            cedula_val = str(est.get("cedula", "")).strip()
            if not cedula_val:
                cedula_val = str(est.get("documento", "") or est.get("numeroDocumento", "") or est.get("identificacion", "")).strip()

            # Resolver mediante gestor_estudiantes si aún no vino en el objeto de sesión
            if not cedula_val:
                try:
                    from utils.gestor_estudiantes import gestor_estudiantes
                    cedula_val = gestor_estudiantes.obtener_cedula(
                        nombre=est.get("nombre", ""),
                        estudiante_id=est.get("estudiante_id", "")
                    )
                except Exception:
                    pass

            # Mostramos la cédula real del estudiante
            texto_cedula = cedula_val if cedula_val else "—"

            item_id = QTableWidgetItem(texto_cedula)
            item_id.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item_id.setForeground(color_texto_secundario)
            self.tabla.setItem(fila, 2, item_id)

            # 4. Nivel de Riesgo (Texto limpio sin fondos ni iconos de colores: Alto / Medio / Bajo)
            categoria = est.get("categoria_riesgo", "VERDE")
            if categoria == "ROJO":
                texto_riesgo = "Alto"
            elif categoria == "NARANJA":
                texto_riesgo = "Medio"
            else:
                texto_riesgo = "Bajo"

            item_riesgo = QTableWidgetItem(texto_riesgo)
            item_riesgo.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item_riesgo.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            item_riesgo.setForeground(color_texto_principal)
            self.tabla.setItem(fila, 3, item_riesgo)

            # 5. Cantidad de Alertas
            alertas = est.get("total_alertas", 0)
            item_al = QTableWidgetItem(f"{alertas} alerta{'s' if alertas != 1 else ''}")
            item_al.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if alertas >= 3:
                item_al.setForeground(QColor("#C0392B"))
                item_al.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            elif alertas > 0:
                item_al.setForeground(QColor("#D35400"))
            else:
                item_al.setForeground(color_texto_secundario)
            self.tabla.setItem(fila, 4, item_al)

            # 6. Botón de Acción con icono vectorial nítido y tamaño seguro sin recortes
            btn_ver = QPushButton("Ver Evidencia")
            btn_ver.setObjectName("btn_ver_evidencias_modal")
            if hasattr(self, '_icono_carpeta') and not self._icono_carpeta.isNull():
                btn_ver.setIcon(self._icono_carpeta)
                btn_ver.setIconSize(QSize(16, 16))
            btn_ver.setFixedHeight(28)
            btn_ver.setMinimumWidth(130)
            btn_ver.setCursor(Qt.CursorShape.PointingHandCursor)
            sesion_id = est.get("sesion_id", "")
            btn_ver.clicked.connect(lambda checked, n=nombre, sid=sesion_id: self._abrir_evidencias_y_cerrar(n, sid))

            contenedor_btn = QWidget()
            lay_btn = QHBoxLayout(contenedor_btn)
            lay_btn.setContentsMargins(6, 2, 6, 2)
            lay_btn.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lay_btn.addWidget(btn_ver)
            self.tabla.setCellWidget(fila, 5, contenedor_btn)

            self.tabla.setRowHeight(fila, 42)

    def _abrir_evidencias_y_cerrar(self, nombre: str, sesion_id: str):
        """Ejecuta el callback para abrir las carpetas forenses y cierra el modal."""
        self.close()
        if self.callback_ver_detalle:
            self.callback_ver_detalle(nombre, sesion_id)
