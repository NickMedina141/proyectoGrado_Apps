# vista/reporte_institucional.py
"""
Reportes y Métricas Institucionales (SuperADMIN).
Consolidado administrativo y analítica ejecutiva del sistema de supervisión UPC Proctor.
Universidad Popular del Cesar.
"""

import os
import csv
from datetime import datetime

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton,
    QFrame, QMessageBox, QApplication, QTableWidget, QTableWidgetItem,
    QHeaderView, QFileDialog, QScrollArea
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QColor, QFont

from api.cliente_respuesta import cliente_api
from utils.gestor_sesion import sesion_actual
from utils.exportador_excel import generar_excel_directorio, generar_excel_consolidado

# Gestión de estilos externos compartidos
from vista.panel_admin import cargar_estilo, HiloAdmin, formatear_fecha

# Gráficos y analítica ejecutiva
from vista.componentes.graficos_reporte import (
    TarjetaGrafico,
    GraficoAlertasProctoring,
    GraficoDispersionIngresos,
    GraficoIntegridadCripto,
    GraficoEstadoCuentas,
    GraficoCrecimientoUsuarios,
    GraficoRatioCarga
)


class HiloGenerarPDF(QThread):
    terminado = pyqtSignal(bool, str)

    def __init__(self, ruta_archivo, datos_resumen, lista_profesores, lista_estudiantes, parent=None):
        super().__init__(parent)
        self.ruta_archivo = ruta_archivo
        self.datos_resumen = datos_resumen
        self.lista_profesores = lista_profesores
        self.lista_estudiantes = lista_estudiantes

    def run(self):
        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.lib import colors
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

            doc = SimpleDocTemplate(
                self.ruta_archivo,
                pagesize=letter,
                rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40
            )

            styles = getSampleStyleSheet()
            verde_upc = colors.HexColor("#004D1E")
            verde_claro = colors.HexColor("#E8F5E9")
            gris_borde = colors.HexColor("#DCE2E0")
            texto_oscuro = colors.HexColor("#2C3E50")

            titulo_style = ParagraphStyle(
                'TituloUPC', parent=styles['Heading1'],
                fontName='Helvetica-Bold', fontSize=18, leading=22,
                textColor=verde_upc, spaceAfter=4
            )
            subtitulo_style = ParagraphStyle(
                'SubtituloUPC', parent=styles['Normal'],
                fontName='Helvetica', fontSize=10, leading=14,
                textColor=colors.HexColor("#7F8C8D"), spaceAfter=15
            )
            seccion_style = ParagraphStyle(
                'SeccionUPC', parent=styles['Heading2'],
                fontName='Helvetica-Bold', fontSize=12, leading=16,
                textColor=verde_upc, spaceBefore=14, spaceAfter=8
            )
            normal_style = ParagraphStyle(
                'NormalUPC', parent=styles['Normal'],
                fontName='Helvetica', fontSize=9, leading=12,
                textColor=texto_oscuro
            )

            r = self.datos_resumen or {}
            tp = r.get("totalProfesores", len(self.lista_profesores))
            ap = r.get("profesoresActivos", sum(1 for p in self.lista_profesores if str(p.get("estado", "")).upper() == "ACTIVO"))
            sp = max(tp - ap, 0)

            te = r.get("totalEstudiantes", len(self.lista_estudiantes))
            ae = r.get("estudiantesActivos", sum(1 for e in self.lista_estudiantes if str(e.get("estadoUsuario", "")).upper() == "ACTIVO"))
            se = max(te - ae, 0)

            tex = r.get("totalExamenes", 0)

            tasa_p = (ap / tp * 100) if tp > 0 else 100.0
            tasa_e = (ae / te * 100) if te > 0 else 100.0

            elementos = []
            elementos.append(Paragraph("UNIVERSIDAD POPULAR DEL CESAR", titulo_style))
            elementos.append(Paragraph("SISTEMA INSTITUCIONAL UPC PROCTOR · INFORME OFICIAL DE AUDITORÍA Y USUARIOS", subtitulo_style))
            elementos.append(Paragraph(
                f"Fecha de emisión: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}  |  "
                f"Emitido por: {sesion_actual.obtener_nombre() or 'SuperADMIN'}",
                normal_style
            ))
            elementos.append(Spacer(1, 15))

            # Tabla 1: Métricas
            elementos.append(Paragraph("1. Resumen Consolidado del Sistema", seccion_style))
            datos_tabla1 = [
                ["Categoría", "Total Registrado", "Cuentas Activas", "Cuentas Suspendidas", "Tasa de Actividad"],
                ["Docentes", str(tp), str(ap), str(sp), f"{tasa_p:.1f}%"],
                ["Estudiantes", str(te), str(ae), str(se), f"{tasa_e:.1f}%"],
                ["Evaluaciones Globales", str(tex), "—", "—", "100.0%"],
            ]
            t1 = Table(datos_tabla1, colWidths=[130, 95, 95, 110, 100])
            t1.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), verde_upc),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 9),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
                ('TOPPADDING', (0, 0), (-1, 0), 6),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('ALIGN', (0, 1), (0, -1), 'LEFT'),
                ('GRID', (0, 0), (-1, -1), 0.5, gris_borde),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, verde_claro]),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
                ('TOPPADDING', (0, 1), (-1, -1), 5),
                ('BOTTOMPADDING', (0, 1), (-1, -1), 5),
            ]))
            elementos.append(t1)
            elementos.append(Spacer(1, 20))

            # Muestra de docentes
            elementos.append(Paragraph("2. Directorio Institucional de Docentes (Consolidado)", seccion_style))
            filas_doc = [["Código", "Nombre Completo", "Cédula", "Correo Institucional", "Estado"]]
            for p in self.lista_profesores[:20]:
                cod = str(p.get("codigoProfesor") or p.get("id") or "")
                nom = f"{p.get('nombre', '')} {p.get('apellidos', '')}".strip()
                ced = str(p.get("cedula") or "")
                em = str(p.get("emailInstitucional") or p.get("email") or "")
                est = str(p.get("estado") or "ACTIVO").upper()
                filas_doc.append([cod, nom, ced, em, est])
            if len(self.lista_profesores) > 20:
                filas_doc.append(["...", f"Y {len(self.lista_profesores) - 20} docentes adicionales en sistema", "...", "...", "..."])

            t_doc = Table(filas_doc, colWidths=[80, 140, 80, 160, 70])
            t_doc.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#2C3E50")),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 8),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('ALIGN', (1, 1), (1, -1), 'LEFT'),
                ('ALIGN', (3, 1), (3, -1), 'LEFT'),
                ('GRID', (0, 0), (-1, -1), 0.5, gris_borde),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#F9FBF9")]),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ]))
            elementos.append(t_doc)
            elementos.append(Spacer(1, 25))

            # Pie y firmas institucionales
            elementos.append(Paragraph("3. Dictamen y Certificación Administrativa", seccion_style))
            elementos.append(Paragraph(
                "El presente reporte constituye una constancia administrativa del estado de las cuentas del sistema UPC Proctor. "
                "Documento emitido con propósitos exclusivos de gobernanza, auditoría técnica y gestión universitaria.",
                normal_style
            ))
            elementos.append(Spacer(1, 30))

            firma_data = [
                ["____________________________________________", "____________________________________________"],
                ["Dirección de Tecnologías y Sistemas", "Comité de Auditoría Académica"],
                ["Universidad Popular del Cesar", "Universidad Popular del Cesar"]
            ]
            t_firma = Table(firma_data, colWidths=[260, 260])
            t_firma.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor("#7F8C8D")),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
            ]))
            elementos.append(t_firma)

            doc.build(elementos)
            self.terminado.emit(True, self.ruta_archivo)
        except Exception as e:
            self.terminado.emit(False, str(e))


class ReporteInstitucional(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("ReporteInstitucional")
        self.modo_oscuro = False
        self.datos_resumen = {}
        self.lista_profesores = []
        self.lista_estudiantes = []
        self._hilos = []
        self._tarjetas_graficos = []

        self._construir_ui()
        self.aplicar_tema(False)

    def _construir_ui(self):
        # Disposición general con scroll fluido
        layout_exterior = QVBoxLayout(self)
        layout_exterior.setContentsMargins(0, 0, 0, 0)
        layout_exterior.setSpacing(0)

        self.area_scroll = QScrollArea()
        self.area_scroll.setObjectName("area_scroll_reporte")
        self.area_scroll.setWidgetResizable(True)
        self.area_scroll.setFrameShape(QScrollArea.Shape.NoFrame)

        contenedor_scroll = QWidget()
        contenedor_scroll.setObjectName("contenedor_reporte_interior")
        raiz = QVBoxLayout(contenedor_scroll)
        raiz.setContentsMargins(34, 28, 34, 30)
        raiz.setSpacing(22)

        # 1. Cabecera institucional sobria
        cabecera = QHBoxLayout()
        bloque_tit = QVBoxLayout()
        bloque_tit.setSpacing(2)

        titulo = QLabel("Reportes y Métricas Institucionales")
        titulo.setObjectName("titulo_admin")
        subtitulo = QLabel("Universidad Popular del Cesar · Consolidado General del Sistema de Supervisión")
        subtitulo.setObjectName("subtitulo_admin")
        bloque_tit.addWidget(titulo)
        bloque_tit.addWidget(subtitulo)
        cabecera.addLayout(bloque_tit)
        cabecera.addStretch()

        self.lbl_aviso = QLabel("")
        self.lbl_aviso.setObjectName("aviso_admin")
        cabecera.addWidget(self.lbl_aviso)
        cabecera.addSpacing(8)

        self.btn_actualizar = QPushButton("Actualizar Métricas")
        self.btn_actualizar.setObjectName("btn_admin_secundario")
        self.btn_actualizar.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_actualizar.clicked.connect(lambda: self.cargar_datos(forzar=True))

        self.btn_exportar_pdf = QPushButton("Exportar Informe Oficial (PDF)")
        self.btn_exportar_pdf.setObjectName("btn_admin_nuevo")
        self.btn_exportar_pdf.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_exportar_pdf.clicked.connect(self._exportar_pdf_institucional)

        cabecera.addWidget(self.btn_actualizar)
        cabecera.addWidget(self.btn_exportar_pdf)
        raiz.addLayout(cabecera)

        # 2. Franja de Indicadores Clave (KPIs)
        franja = QFrame()
        franja.setObjectName("franja_admin")
        lay_f = QHBoxLayout(franja)
        lay_f.setContentsMargins(0, 0, 0, 0)
        lay_f.setSpacing(0)

        self.kpi_docentes = self._crear_kpi("DOCENTES REGISTRADOS", "0", "0 activos · 0 suspendidos")
        self.kpi_estudiantes = self._crear_kpi("ESTUDIANTES REGISTRADOS", "0", "0 activos · 0 suspendidos")
        self.kpi_examenes = self._crear_kpi("EVALUACIONES EN PLATAFORMA", "0", "Exámenes registrados")
        self.kpi_operatividad = self._crear_kpi("TASA DE OPERATIVIDAD", "100%", "Cuentas institucionales activas")

        kpis = [self.kpi_docentes, self.kpi_estudiantes, self.kpi_examenes, self.kpi_operatividad]
        for i, k in enumerate(kpis):
            if i > 0:
                divisor = QFrame()
                divisor.setObjectName("divisor_admin")
                divisor.setFixedWidth(1)
                lay_f.addWidget(divisor)
            lay_f.addWidget(k["widget"], 1)
        raiz.addWidget(franja)

        # 3. Sección de Indicadores y Analítica Ejecutiva (Gráficos para Alta Gerencia)
        bloque_analitica = QVBoxLayout()
        bloque_analitica.setSpacing(10)

        lbl_tit_graficos = QLabel("INDICADORES Y ANALÍTICA EJECUTIVA (ALTA GERENCIA)")
        lbl_tit_graficos.setObjectName("metrica_etiqueta")
        lbl_desc_graficos = QLabel(
            "Métricas consolidadas para sustentar decisiones estratégicas ante Rectoría, Decanatura y Dirección de TI."
        )
        lbl_desc_graficos.setObjectName("metrica_detalle")

        bloque_analitica.addWidget(lbl_tit_graficos)
        bloque_analitica.addWidget(lbl_desc_graficos)
        raiz.addLayout(bloque_analitica)

        # Cuadrícula 2 columnas x 3 filas con los 6 gráficos ejecutivos
        cuadricula_graficos = QGridLayout()
        cuadricula_graficos.setHorizontalSpacing(16)
        cuadricula_graficos.setVerticalSpacing(16)

        # Gráfico 1: Alertas
        self.graf_alertas = GraficoAlertasProctoring()
        self.card_alertas = TarjetaGrafico(
            "INCIDENCIAS Y ALERTAS DE PROCTORING",
            "Distribución de sospechas de fraude por tipología y recurrencia",
            "Tendencia Semestral", self.graf_alertas
        )

        # Gráfico 2: Dispersión real de accesos
        self.graf_dispersion = GraficoDispersionIngresos()
        self.card_dispersion = TarjetaGrafico(
            "DISPERSIÓN Y CONCURRENCIA DE ACCESOS",
            "Patrón horario de ingresos estudiantiles (24h)",
            "Dispersión X/Y", self.graf_dispersion
        )

        # Gráfico 3: Integridad Criptográfica E2EE
        self.graf_cripto = GraficoIntegridadCripto()
        self.card_cripto = TarjetaGrafico(
            "SALUD CRIPTOGRÁFICA E2EE (AES-256)",
            "Telemetría de paquetes válidos vs fallas de integridad",
            "Seguridad y Auditoría", self.graf_cripto
        )

        # Gráfico 4: Estado del Padrón
        self.graf_estado = GraficoEstadoCuentas()
        self.card_estado = TarjetaGrafico(
            "ESTADO DEL PADRÓN INSTITUCIONAL",
            "Relación de cuentas activas vs suspendidas por estamento",
            "Gobernanza", self.graf_estado
        )

        # Gráfico 5: Crecimiento y Altas de Usuarios (Línea con Nodos - Datos Reales)
        self.graf_crecimiento = GraficoCrecimientoUsuarios()
        self.card_crecimiento = TarjetaGrafico(
            "CRECIMIENTO Y ALTAS DE USUARIOS",
            "Evolución real de incorporación al sistema en el semestre",
            "Crecimiento 2026", self.graf_crecimiento
        )

        # Gráfico 6: Balance de Carga Operativa
        self.graf_ratio = GraficoRatioCarga()
        self.card_ratio = TarjetaGrafico(
            "BALANCE DE CARGA OPERATIVA",
            "Ratio promedio de estudiantes supervisados por docente activo",
            "Capacidad", self.graf_ratio
        )

        self._tarjetas_graficos = [
            self.card_alertas, self.card_dispersion, self.card_cripto,
            self.card_estado, self.card_crecimiento, self.card_ratio
        ]

        cuadricula_graficos.addWidget(self.card_alertas, 0, 0)
        cuadricula_graficos.addWidget(self.card_dispersion, 0, 1)
        cuadricula_graficos.addWidget(self.card_cripto, 1, 0)
        cuadricula_graficos.addWidget(self.card_estado, 1, 1)
        cuadricula_graficos.addWidget(self.card_crecimiento, 2, 0)
        cuadricula_graficos.addWidget(self.card_ratio, 2, 1)

        raiz.addLayout(cuadricula_graficos)

        # 4. Resumen Ejecutivo de Cuentas
        zona_resumen = QFrame()
        zona_resumen.setObjectName("franja_admin")
        lay_zr = QVBoxLayout(zona_resumen)
        lay_zr.setContentsMargins(24, 20, 24, 20)
        lay_zr.setSpacing(14)

        lbl_tit_resumen = QLabel("CONSOLIDADO DE CUENTAS INSTITUCIONALES")
        lbl_tit_resumen.setObjectName("metrica_etiqueta")
        lay_zr.addWidget(lbl_tit_resumen)

        self.tabla_resumen = QTableWidget()
        self.tabla_resumen.setObjectName("tabla_admin_usuarios")
        self.tabla_resumen.setColumnCount(5)
        self.tabla_resumen.setHorizontalHeaderLabels([
            "ESTAMENTO", "TOTAL REGISTRADOS", "CUENTAS ACTIVAS", "CUENTAS SUSPENDIDAS", "TASA DE ACTIVIDAD"
        ])
        self.tabla_resumen.verticalHeader().setVisible(False)
        self.tabla_resumen.setShowGrid(False)
        self.tabla_resumen.setAlternatingRowColors(True)
        self.tabla_resumen.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tabla_resumen.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tabla_resumen.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tabla_resumen.setFixedHeight(115)
        lay_zr.addWidget(self.tabla_resumen)

        raiz.addWidget(zona_resumen)

        # 5. Registro de Actividad y Auditoría Reciente
        zona_auditoria = QFrame()
        zona_auditoria.setObjectName("franja_admin")
        lay_za = QVBoxLayout(zona_auditoria)
        lay_za.setContentsMargins(24, 20, 24, 20)
        lay_za.setSpacing(12)

        lbl_tit_aud = QLabel("REGISTRO DE ACTIVIDAD Y AUDITORÍA RECIENTE")
        lbl_tit_aud.setObjectName("metrica_etiqueta")
        lbl_sub_aud = QLabel("Monitoreo en tiempo real del último acceso y estado operacional de usuarios en el sistema.")
        lbl_sub_aud.setObjectName("dlg_subtitulo")
        lay_za.addWidget(lbl_tit_aud)
        lay_za.addWidget(lbl_sub_aud)

        self.tabla_auditoria = QTableWidget()
        self.tabla_auditoria.setObjectName("tabla_admin_usuarios")
        self.tabla_auditoria.setColumnCount(6)
        self.tabla_auditoria.setHorizontalHeaderLabels([
            "CÓDIGO", "NOMBRE COMPLETO", "CÉDULA", "ROL", "ÚLTIMO ACCESO", "ESTADO"
        ])
        self.tabla_auditoria.verticalHeader().setVisible(False)
        self.tabla_auditoria.setShowGrid(False)
        self.tabla_auditoria.setAlternatingRowColors(True)
        self.tabla_auditoria.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tabla_auditoria.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tabla_auditoria.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tabla_auditoria.setFixedHeight(220)
        lay_za.addWidget(self.tabla_auditoria)

        raiz.addWidget(zona_auditoria)

        # 6. Sección de Exportación y Descargas Oficiales
        zona_export = QFrame()
        zona_export.setObjectName("franja_admin")
        lay_exp = QVBoxLayout(zona_export)
        lay_exp.setContentsMargins(24, 20, 24, 20)
        lay_exp.setSpacing(12)

        lbl_tit_exp = QLabel("EXPORTACIONES OFICIALES Y DESCARGAS DE AUDITORÍA")
        lbl_tit_exp.setObjectName("metrica_etiqueta")
        lay_exp.addWidget(lbl_tit_exp)

        lbl_desc_exp = QLabel(
            "Descargue los directorios en libros profesionales Microsoft Excel (.xlsx) con estilos institucionales "
            "o genere el informe membretado oficial en PDF para trámites de decanatura, vicerrectoría y auditorías técnicas."
        )
        lbl_desc_exp.setObjectName("dlg_subtitulo")
        lbl_desc_exp.setWordWrap(True)
        lay_exp.addWidget(lbl_desc_exp)

        fila_botones_exp = QHBoxLayout()
        fila_botones_exp.setSpacing(10)

        self.btn_excel_consolidado = QPushButton("Descargar Libro Consolidado (.xlsx)")
        self.btn_excel_consolidado.setObjectName("btn_admin_nuevo")
        self.btn_excel_consolidado.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_excel_consolidado.clicked.connect(self._exportar_excel_consolidado)

        self.btn_excel_docentes = QPushButton("Directorio Docente (.xlsx)")
        self.btn_excel_docentes.setObjectName("btn_admin_secundario")
        self.btn_excel_docentes.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_excel_docentes.clicked.connect(lambda: self._exportar_excel_directorio("docente"))

        self.btn_excel_estudiantes = QPushButton("Directorio Estudiantil (.xlsx)")
        self.btn_excel_estudiantes.setObjectName("btn_admin_secundario")
        self.btn_excel_estudiantes.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_excel_estudiantes.clicked.connect(lambda: self._exportar_excel_directorio("estudiante"))

        self.btn_csv_compatible = QPushButton("Exportar CSV (Compatibilidad)")
        self.btn_csv_compatible.setObjectName("btn_admin_secundario")
        self.btn_csv_compatible.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_csv_compatible.clicked.connect(lambda: self._exportar_csv("docentes"))

        fila_botones_exp.addWidget(self.btn_excel_consolidado)
        fila_botones_exp.addWidget(self.btn_excel_docentes)
        fila_botones_exp.addWidget(self.btn_excel_estudiantes)
        fila_botones_exp.addWidget(self.btn_csv_compatible)
        fila_botones_exp.addStretch()
        lay_exp.addLayout(fila_botones_exp)

        raiz.addWidget(zona_export)

        self.area_scroll.setWidget(contenedor_scroll)
        layout_exterior.addWidget(self.area_scroll)

    def _crear_kpi(self, etiqueta, valor_ini, detalle_ini):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(24, 16, 24, 16)
        lay.setSpacing(2)

        e = QLabel(etiqueta)
        e.setObjectName("metrica_etiqueta")
        v = QLabel(valor_ini)
        v.setObjectName("metrica_valor")
        d = QLabel(detalle_ini)
        d.setObjectName("metrica_detalle")

        lay.addWidget(e)
        lay.addWidget(v)
        lay.addWidget(d)
        return {"widget": w, "valor": v, "detalle": d}

    # -- Métodos de carga y datos -----------------------------------------------
    def cargar_datos(self, forzar: bool = False):
        if hasattr(self, 'hilo') and self.hilo is not None and self.hilo.isRunning():
            return
        self.btn_actualizar.setEnabled(False)
        self.btn_actualizar.setText("Cargando…")
        self.hilo = HiloAdmin(forzar=forzar)
        self.hilo.datos_cargados.connect(self._al_cargar_datos)
        self.hilo.start()

    def _al_cargar_datos(self, exito, resultado):
        self.btn_actualizar.setEnabled(True)
        self.btn_actualizar.setText("Actualizar Métricas")

        if not exito or not resultado.get("exito", True):
            QMessageBox.warning(self, "Reporte Institucional", "No se pudieron obtener las métricas del servidor.")
            return

        self.datos_resumen = resultado.get("resumen", {})
        self.lista_profesores = resultado.get("profesores", [])
        self.lista_estudiantes = resultado.get("estudiantes", [])

        r = self.datos_resumen
        tp = r.get("totalProfesores", len(self.lista_profesores))
        ap = r.get("profesoresActivos", sum(1 for p in self.lista_profesores if str(p.get("estado", "")).upper() == "ACTIVO"))
        sp = max(tp - ap, 0)

        te = r.get("totalEstudiantes", len(self.lista_estudiantes))
        ae = r.get("estudiantesActivos", sum(1 for e in self.lista_estudiantes if str(e.get("estadoUsuario", "")).upper() == "ACTIVO"))
        se = max(te - ae, 0)

        tex = r.get("totalExamenes", 0)

        total_cuentas = tp + te
        activas_cuentas = ap + ae
        tasa_global = (activas_cuentas / total_cuentas * 100) if total_cuentas > 0 else 100.0

        self.kpi_docentes["valor"].setText(str(tp))
        self.kpi_docentes["detalle"].setText(f"{ap} activos · {sp} suspendidos")

        self.kpi_estudiantes["valor"].setText(str(te))
        self.kpi_estudiantes["detalle"].setText(f"{ae} activos · {se} suspendidos")

        self.kpi_examenes["valor"].setText(str(tex))
        self.kpi_examenes["detalle"].setText("Evaluaciones institucionales")

        self.kpi_operatividad["valor"].setText(f"{tasa_global:.1f}%")
        self.kpi_operatividad["detalle"].setText(f"{activas_cuentas} activas de {total_cuentas} cuentas")

        # Actualizar datos de gráficos ejecutivos dinámicos
        self.graf_estado.actualizar_datos(ap, sp, ae, se)
        self.graf_ratio.actualizar_ratio(ae, ap)
        self.graf_crecimiento.actualizar_datos_reales(tp, te, ap, ae)

        # Rellenar tablas
        self._pintar_tabla_resumen(tp, ap, sp, te, ae, se)
        self._pintar_tabla_auditoria()

    def _pintar_tabla_resumen(self, tp, ap, sp, te, ae, se):
        self.tabla_resumen.setRowCount(2)
        datos = [
            ("Personal Docente", tp, ap, sp, (ap / tp * 100) if tp > 0 else 100.0),
            ("Estudiantes de Pregrado", te, ae, se, (ae / te * 100) if te > 0 else 100.0)
        ]
        for fila, (estamento, total, activos, susp, tasa) in enumerate(datos):
            item_est = QTableWidgetItem(estamento)
            item_tot = QTableWidgetItem(str(total))
            item_act = QTableWidgetItem(f"● {activos}")
            item_act.setForeground(QColor("#1E7B3A" if not self.modo_oscuro else "#4ADE80"))
            item_sus = QTableWidgetItem(f"● {susp}")
            item_sus.setForeground(QColor("#B42318" if not self.modo_oscuro else "#F87171"))
            item_tas = QTableWidgetItem(f"{tasa:.1f}%")

            for col, item in enumerate([item_est, item_tot, item_act, item_sus, item_tas]):
                item.setTextAlignment(int(Qt.AlignmentFlag.AlignCenter if col > 0 else Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter))
                self.tabla_resumen.setItem(fila, col, item)

    def _pintar_tabla_auditoria(self):
        """Llena el registro de auditoría reciente con los últimos accesos."""
        usuarios_aud = []
        for p in self.lista_profesores:
            aud = p.get("auditoria") or {}
            usuarios_aud.append({
                "codigo": p.get("codigoProfesor") or p.get("id") or "",
                "nombre": f"{p.get('nombre', '')} {p.get('apellidos', '')}".strip(),
                "cedula": p.get("cedula") or "",
                "rol": "Docente" if str(p.get("rol", "")).upper() != "SUPERADMIN" else "SuperADMIN",
                "ultimo_acceso": aud.get("ultimoAcceso") or aud.get("fechaActualizacion") or aud.get("fechaRegistro"),
                "estado": (p.get("estado") or "ACTIVO").upper()
            })
        for e in self.lista_estudiantes:
            aud = e.get("auditoria") or {}
            usuarios_aud.append({
                "codigo": e.get("estudianteId") or e.get("id") or "",
                "nombre": f"{e.get('nombre', '')} {e.get('apellidos', '')}".strip(),
                "cedula": e.get("cedula") or "",
                "rol": "Estudiante",
                "ultimo_acceso": aud.get("ultimoAcceso") or aud.get("fechaActualizacion") or aud.get("fechaRegistro"),
                "estado": (e.get("estadoUsuario") or "ACTIVO").upper()
            })

        # Mostrar hasta los 15 registros más relevantes
        usuarios_aud = usuarios_aud[:15]
        self.tabla_auditoria.setRowCount(len(usuarios_aud))

        for fila, u in enumerate(usuarios_aud):
            it_cod = QTableWidgetItem(u["codigo"])
            it_nom = QTableWidgetItem(u["nombre"])
            it_ced = QTableWidgetItem(u["cedula"])
            it_rol = QTableWidgetItem(u["rol"])
            it_acc = QTableWidgetItem(formatear_fecha(u["ultimo_acceso"]))
            it_est = QTableWidgetItem(f"● {u['estado']}")
            it_est.setForeground(QColor("#1E7B3A" if u["estado"] == "ACTIVO" else "#B42318"))

            for col, item in enumerate([it_cod, it_nom, it_ced, it_rol, it_acc, it_est]):
                alig = Qt.AlignmentFlag.AlignCenter if col in (0, 2, 3, 4, 5) else (Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
                item.setTextAlignment(int(alig))
                self.tabla_auditoria.setItem(fila, col, item)

    # -- Exportación Excel (.xlsx) -----------------------------------------------
    def _exportar_excel_consolidado(self):
        sugerido = f"Libro_Consolidado_UPC_Proctor_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
        ruta, _ = QFileDialog.getSaveFileName(self, "Exportar Libro Consolidado Excel", sugerido, "Archivos Excel (*.xlsx)")
        if not ruta:
            return
        try:
            generar_excel_consolidado(ruta, self.lista_profesores, self.lista_estudiantes, self.datos_resumen)
            QMessageBox.information(
                self, "Exportación Exitosa",
                f"El libro consolidado oficial se generó exitosamente con hojas de Resumen, Docentes y Estudiantes en:\n\n{ruta}"
            )
        except Exception as ex:
            QMessageBox.critical(self, "Error de Exportación", f"No se pudo guardar el archivo Excel:\n{ex}")

    def _exportar_excel_directorio(self, tipo: str):
        es_doc = (tipo == "docente")
        sugerido = f"Directorio_{'Docentes' if es_doc else 'Estudiantes'}_UPC_{datetime.now().strftime('%Y%m%d')}.xlsx"
        ruta, _ = QFileDialog.getSaveFileName(self, f"Exportar Directorio de {'Docentes' if es_doc else 'Estudiantes'}", sugerido, "Archivos Excel (*.xlsx)")
        if not ruta:
            return
        try:
            lista = self.lista_profesores if es_doc else self.lista_estudiantes
            generar_excel_directorio(ruta, tipo, lista)
            QMessageBox.information(
                self, "Exportación Exitosa",
                f"El directorio oficial en Excel se ha guardado exitosamente con {len(lista)} registros en:\n\n{ruta}"
            )
        except Exception as ex:
            QMessageBox.critical(self, "Error de Exportación", f"No se pudo guardar el archivo Excel:\n{ex}")

    # -- Exportación PDF --------------------------------------------------------
    def _exportar_pdf_institucional(self):
        sugerido = f"Reporte_Institucional_UPC_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
        ruta, _ = QFileDialog.getSaveFileName(self, "Guardar Informe Oficial PDF", sugerido, "Archivos PDF (*.pdf)")
        if not ruta:
            return

        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        self.btn_exportar_pdf.setEnabled(False)

        hilo_pdf = HiloGenerarPDF(ruta, self.datos_resumen, self.lista_profesores, self.lista_estudiantes, self)
        self._hilos.append(hilo_pdf)

        def terminar(exito, res):
            QApplication.restoreOverrideCursor()
            self.btn_exportar_pdf.setEnabled(True)
            if hilo_pdf in self._hilos:
                self._hilos.remove(hilo_pdf)
            if exito:
                QMessageBox.information(
                    self, "Informe Generado",
                    f"El informe institucional oficial se ha guardado exitosamente en:\n\n{res}"
                )
            else:
                QMessageBox.critical(self, "Error al Exportar", f"No se pudo generar el informe:\n{res}")

        hilo_pdf.terminado.connect(terminar)
        hilo_pdf.start()

    # -- Exportación CSV --------------------------------------------------------
    def _exportar_csv(self, tipo):
        es_docente = tipo == "docente" or tipo == "docentes"
        sugerido = f"Directorio_{'Docentes' if es_docente else 'Estudiantes'}_UPC_{datetime.now().strftime('%Y%m%d')}.csv"
        ruta, _ = QFileDialog.getSaveFileName(self, "Exportar Directorio a CSV", sugerido, "Archivos CSV (*.csv)")
        if not ruta:
            return

        try:
            lista = self.lista_profesores if es_docente else self.lista_estudiantes
            with open(ruta, mode='w', encoding='utf-8-sig', newline='') as f:
                escritor = csv.writer(f, delimiter=';')
                if es_docente:
                    escritor.writerow(["CODIGO_DOCENTE", "NOMBRE", "APELLIDOS", "CEDULA", "CORREO_INSTITUCIONAL", "ESTADO", "ROL"])
                    for p in lista:
                        escritor.writerow([
                            p.get("codigoProfesor", ""),
                            p.get("nombre", ""),
                            p.get("apellidos", ""),
                            p.get("cedula", ""),
                            p.get("emailInstitucional", ""),
                            p.get("estado", "ACTIVO"),
                            p.get("rol", "PROFESOR")
                        ])
                else:
                    escritor.writerow(["IDENTIFICADOR_ESTUDIANTE", "NOMBRE", "APELLIDOS", "CEDULA", "CORREO_INSTITUCIONAL", "ESTADO"])
                    for e in lista:
                        escritor.writerow([
                            e.get("estudianteId", ""),
                            e.get("nombre", ""),
                            e.get("apellidos", ""),
                            e.get("cedula", ""),
                            e.get("email", ""),
                            e.get("estadoUsuario", "ACTIVO")
                        ])

            QMessageBox.information(
                self, "Exportación Exitosa",
                f"Se han exportado {len(lista)} registros correctamente a:\n\n{ruta}"
            )
        except Exception as ex:
            QMessageBox.critical(self, "Error de Exportación", f"No se pudo guardar el archivo CSV:\n{ex}")

    # -- Tema visual ------------------------------------------------------------
    def aplicar_tema(self, oscuro: bool):
        self.modo_oscuro = oscuro
        bg = "#0F172A" if oscuro else "#F4F6F6"
        estilo = cargar_estilo(oscuro)
        css_extra = f"""
            QWidget#ReporteInstitucional {{ background-color: {bg}; }}
            QScrollArea#area_scroll_reporte {{ background-color: {bg}; border: none; }}
            QScrollArea#area_scroll_reporte > QWidget {{ background-color: {bg}; }}
            QWidget#contenedor_reporte_interior {{ background-color: {bg}; }}
        """
        self.setStyleSheet((estilo or "") + css_extra)
        for t in self._tarjetas_graficos:
            t.aplicar_tema(oscuro)
