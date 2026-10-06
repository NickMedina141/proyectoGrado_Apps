# vista/panel_admin.py
"""
Administración de usuarios (SuperADMIN).
Gestión de cuentas de docentes y estudiantes: consulta, edición, creación,
restablecimiento de contraseña, suspensión y baja.
Universidad Popular del Cesar - UPC Proctor.
"""

import os
import re
import csv
from datetime import datetime

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton,
    QLineEdit, QTableWidget, QTableWidgetItem, QHeaderView, QTabWidget,
    QFrame, QMessageBox, QApplication, QComboBox, QDialog, QToolButton,
    QMenu, QAbstractItemView, QProgressBar, QFileDialog
)
from PyQt6.QtCore import Qt, QThread, QTimer, pyqtSignal, QRegularExpression
from PyQt6.QtGui import QColor, QFont, QRegularExpressionValidator
from api.cliente_respuesta import cliente_api
from utils.gestor_sesion import sesion_actual


# ----------------------------------------------------------------------------
# Gestión centralizada de estilos externos (tema_claro.css y tema_oscuro.css)
# ----------------------------------------------------------------------------
def cargar_estilo(oscuro: bool = False) -> str:
    """Carga la hoja de estilo CSS centralizada desde los archivos oficiales."""
    archivo = "tema_oscuro.css" if oscuro else "tema_claro.css"
    ruta = os.path.join(os.path.dirname(__file__), archivo)
    try:
        with open(ruta, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        print(f"Error cargando {archivo}: {e}")
        return ""


def color_estado(estado: str, oscuro: bool = False) -> str:
    """Retorna el color del indicador de estado respetando el modo activo."""
    if oscuro:
        return "#4ADE80" if estado == "ACTIVO" else ("#F87171" if estado == "SUSPENDIDO" else "#FBBF24")
    return "#1E7B3A" if estado == "ACTIVO" else ("#B42318" if estado == "SUSPENDIDO" else "#9A5B00")


def color_codigo(oscuro: bool = False) -> str:
    """Retorna el color tenue institucional para el identificador o código."""
    return "#94A3B8" if oscuro else "#68757A"


# Mapeo de conveniencia para scripts de prueba o compatibilidad retroactiva
PALETA_CLARA = {
    "ok": "#1E7B3A", "danger_text": "#B42318", "warn": "#9A5B00",
    "muted": "#68757A", "text": "#2C3E50", "bg": "#F4F6F6"
}
PALETA_OSCURA = {
    "ok": "#4ADE80", "danger_text": "#F87171", "warn": "#FBBF24",
    "muted": "#94A3B8", "text": "#F8FAFC", "bg": "#0F172A"
}


# ----------------------------------------------------------------------------
# Utilidades
# ----------------------------------------------------------------------------
def formatear_fecha(valor):
    """Convierte la fecha devuelta por la API (ISO o arreglo) a dd/mm/aaaa hh:mm."""
    if not valor:
        return "Sin registro"
    try:
        if isinstance(valor, (list, tuple)) and len(valor) >= 5:
            a, m, d, h, mi = (int(x) for x in valor[:5])
            return f"{d:02d}/{m:02d}/{a} {h:02d}:{mi:02d}"
        texto = str(valor).replace("T", " ")[:19]
        return datetime.fromisoformat(texto).strftime("%d/%m/%Y %H:%M")
    except Exception:
        return str(valor)


def texto_estado(estado):
    return {"ACTIVO": "Activo", "SUSPENDIDO": "Suspendido"}.get(estado, str(estado).title())


def es_superadmin(usuario):
    return str(usuario.get("rol", "")).upper() == "SUPERADMIN"


def normalizar_profesor(p):
    rol = (p.get("rol") or "PROFESOR").upper()
    nombre = (p.get("nombre") or "").strip()
    apellidos = (p.get("apellidos") or "").strip()
    return {
        "tipo": "docente",
        "id": p.get("codigoProfesor") or "",
        "nombre_pila": nombre,
        "apellidos": apellidos,
        "nombre": f"{nombre} {apellidos}".strip(),
        "cedula": p.get("cedula") or "",
        "email": p.get("emailInstitucional") or "",
        "rol": rol,
        "rol_texto": "SuperADMIN" if rol == "SUPERADMIN" else "Docente",
        "estado": (p.get("estado") or "ACTIVO").upper(),
        "auditoria": p.get("auditoria") or {},
        "materias": len(p.get("materias") or []),
    }


def normalizar_estudiante(e):
    nombre = (e.get("nombre") or "").strip()
    apellidos = (e.get("apellidos") or "").strip()
    return {
        "tipo": "estudiante",
        "id": e.get("estudianteId") or "",
        "nombre_pila": nombre,
        "apellidos": apellidos,
        "nombre": f"{nombre} {apellidos}".strip(),
        "cedula": e.get("cedula") or "",
        "email": e.get("email") or "",
        "rol": "ESTUDIANTE",
        "rol_texto": "Estudiante",
        "estado": (e.get("estadoUsuario") or "ACTIVO").upper(),
        "auditoria": e.get("auditoria") or {},
        "materias": len(e.get("materiasInscritas") or []),
    }


# ----------------------------------------------------------------------------
# Hilos
# ----------------------------------------------------------------------------
class HiloAdmin(QThread):
    datos_cargados = pyqtSignal(bool, dict)

    def run(self):
        try:
            ex_res, datos_res = cliente_api.admin_obtener_resumen()
            ex_prof, datos_prof = cliente_api.admin_listar_profesores()
            ex_est, datos_est = cliente_api.admin_listar_estudiantes()

            resultado = {
                "resumen": datos_res if ex_res and isinstance(datos_res, dict) else {},
                "profesores": datos_prof if ex_prof and isinstance(datos_prof, list) else [],
                "estudiantes": datos_est if ex_est and isinstance(datos_est, list) else [],
                "exito": ex_res or ex_prof or ex_est,
                "parcial": not (ex_res and ex_prof and ex_est),
                "detalle": next((m for ok, m in ((ex_res, datos_res), (ex_prof, datos_prof), (ex_est, datos_est))
                                 if not ok and isinstance(m, str)), ""),
            }
            self.datos_cargados.emit(True, resultado)
        except Exception as e:
            self.datos_cargados.emit(False, {"error": str(e)})


class HiloAccion(QThread):
    """Ejecuta una operación de la API fuera del hilo de la interfaz."""
    terminado = pyqtSignal(bool, object)

    def __init__(self, funcion, parent=None):
        super().__init__(parent)
        self._funcion = funcion

    def run(self):
        try:
            exito, datos = self._funcion()
            self.terminado.emit(bool(exito), datos)
        except Exception as e:
            self.terminado.emit(False, f"Error inesperado: {e}")


# ----------------------------------------------------------------------------
# Diálogos Modales de SuperADMIN
# ----------------------------------------------------------------------------
class DialogoBase(QDialog):
    def __init__(self, parent=None, titulo="Diálogo", ancho=480):
        super().__init__(parent)
        self.setWindowTitle(titulo)
        self.setModal(True)
        self.setMinimumWidth(ancho)
        self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)
        self._aplicar_estilo()

    def _es_modo_oscuro(self) -> bool:
        padre = self.parent()
        if hasattr(padre, "modo_oscuro"):
            return bool(padre.modo_oscuro)
        win = self.window()
        if hasattr(win, "modo_oscuro"):
            return bool(win.modo_oscuro)
        return False

    def _aplicar_estilo(self):
        estilo = cargar_estilo(self._es_modo_oscuro())
        if estilo:
            self.setStyleSheet(estilo)


class DialogoFicha(DialogoBase):
    def __init__(self, parent=None, usuario=None):
        usuario = usuario or {}
        super().__init__(parent, "Ficha de usuario", 500)
        self.setObjectName("DialogoFicha")

        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(28, 24, 28, 22)
        raiz.setSpacing(16)

        titulo = QLabel(usuario.get("nombre") or "Sin nombre")
        titulo.setObjectName("dlg_titulo")
        sub = QLabel(f"{usuario.get('rol_texto', '')}  ·  {usuario.get('id', '')}")
        sub.setObjectName("dlg_subtitulo")
        raiz.addWidget(titulo)
        raiz.addWidget(sub)

        aud = usuario.get("auditoria") or {}
        filas = [
            ("Cédula", usuario.get("cedula") or "Sin registro"),
            ("Correo institucional", usuario.get("email") or "Sin registro"),
            ("Estado de la cuenta", texto_estado(usuario.get("estado", "ACTIVO"))),
            ("Materias" if usuario.get("tipo") == "docente" else "Materias inscritas", str(usuario.get("materias", 0))),
            ("Fecha de registro", formatear_fecha(aud.get("fechaRegistro"))),
            ("Última actualización", formatear_fecha(aud.get("fechaActualizacion"))),
            ("Último acceso", formatear_fecha(aud.get("ultimoAcceso"))),
        ]
        cuadricula = QGridLayout()
        cuadricula.setHorizontalSpacing(24)
        cuadricula.setVerticalSpacing(12)
        for i, (etiqueta, valor) in enumerate(filas):
            lbl_e = QLabel(etiqueta.upper())
            lbl_e.setObjectName("dlg_campo")
            lbl_v = QLabel(valor)
            lbl_v.setObjectName("dlg_valor")
            lbl_v.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            cuadricula.addWidget(lbl_e, i, 0, Qt.AlignmentFlag.AlignTop)
            cuadricula.addWidget(lbl_v, i, 1)
        cuadricula.setColumnStretch(1, 1)
        raiz.addLayout(cuadricula)

        fila_btn = QHBoxLayout()
        self.btn_exportar_pdf = QPushButton("Exportar Ficha (PDF)")
        self.btn_exportar_pdf.setObjectName("btn_admin_secundario")
        self.btn_exportar_pdf.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_exportar_pdf.clicked.connect(lambda: self._exportar_pdf(usuario))
        fila_btn.addWidget(self.btn_exportar_pdf)
        fila_btn.addStretch()
        cerrar = QPushButton("Cerrar")
        cerrar.setObjectName("btn_admin_secundario")
        cerrar.setCursor(Qt.CursorShape.PointingHandCursor)
        cerrar.clicked.connect(self.accept)
        fila_btn.addWidget(cerrar)
        raiz.addLayout(fila_btn)

    def _exportar_pdf(self, usuario):
        sugerido = f"Ficha_{usuario.get('id', 'usuario')}.pdf"
        ruta, _ = QFileDialog.getSaveFileName(self, "Exportar Ficha a PDF", sugerido, "Archivos PDF (*.pdf)")
        if not ruta:
            return
        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.lib import colors
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

            doc = SimpleDocTemplate(ruta, pagesize=letter, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
            styles = getSampleStyleSheet()
            verde_upc = colors.HexColor("#004D1E")
            gris_borde = colors.HexColor("#DCE2E0")
            texto_oscuro = colors.HexColor("#2C3E50")

            titulo_style = ParagraphStyle('Tit', parent=styles['Heading1'], fontName='Helvetica-Bold', fontSize=16, leading=20, textColor=verde_upc)
            sub_style = ParagraphStyle('Sub', parent=styles['Normal'], fontName='Helvetica', fontSize=10, leading=14, textColor=colors.HexColor("#7F8C8D"), spaceAfter=15)
            norm_style = ParagraphStyle('Norm', parent=styles['Normal'], fontName='Helvetica', fontSize=9, leading=12, textColor=texto_oscuro)

            elementos = [
                Paragraph("UNIVERSIDAD POPULAR DEL CESAR", titulo_style),
                Paragraph("CONSTANCIA OFICIAL DE USUARIO · SISTEMA UPC PROCTOR", sub_style),
                Paragraph(f"Fecha de emisión: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}", norm_style),
                Spacer(1, 15)
            ]

            aud = usuario.get("auditoria") or {}
            filas = [
                ["CAMPO", "INFORMACIÓN REGISTRADA"],
                ["Identificador / Código", str(usuario.get("id", ""))],
                ["Nombre Completo", str(usuario.get("nombre", ""))],
                ["Documento / Cédula", str(usuario.get("cedula", ""))],
                ["Correo Institucional", str(usuario.get("email", ""))],
                ["Rol en el Sistema", str(usuario.get("rol_texto", ""))],
                ["Estado de la Cuenta", str(usuario.get("estado", "ACTIVO"))],
                ["Fecha de Registro", formatear_fecha(aud.get("fechaRegistro"))],
                ["Última Actualización", formatear_fecha(aud.get("fechaActualizacion"))],
                ["Último Acceso Registrado", formatear_fecha(aud.get("ultimoAcceso"))]
            ]
            t = Table(filas, colWidths=[180, 320])
            t.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), verde_upc),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 9),
                ('GRID', (0, 0), (-1, -1), 0.5, gris_borde),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#F9FBF9")]),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
            ]))
            elementos.append(t)
            elementos.append(Spacer(1, 40))

            firma_data = [
                ["____________________________________________"],
                ["Dirección de Tecnologías de la Información"],
                ["Universidad Popular del Cesar"]
            ]
            t_firma = Table(firma_data, colWidths=[500])
            t_firma.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor("#7F8C8D")),
            ]))
            elementos.append(t_firma)

            doc.build(elementos)
            QMessageBox.information(self, "Ficha Exportada", f"La ficha oficial se guardó correctamente en:\n\n{ruta}")
        except Exception as e:
            QMessageBox.critical(self, "Error al Exportar", f"No se pudo generar la ficha en PDF:\n{e}")


class DialogoUsuario(DialogoBase):
    """Alta o edición de una cuenta. El código y la contraseña los genera el sistema."""

    def __init__(self, parent=None, modo="crear", usuario=None, tipo_inicial="docente"):
        titulo = "Nuevo usuario" if modo == "crear" else "Editar datos"
        super().__init__(parent, titulo, 480)
        self.setObjectName("DialogoUsuario")
        self.modo = modo
        self.usuario = usuario or {}

        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(28, 24, 28, 22)
        raiz.setSpacing(12)

        encabezado = QLabel(titulo)
        encabezado.setObjectName("dlg_titulo")
        raiz.addWidget(encabezado)
        ayuda = QLabel(
            "El código institucional y una contraseña temporal se generan automáticamente."
            if modo == "crear" else
            f"Cuenta {self.usuario.get('id', '')}. El código institucional no se puede modificar."
        )
        ayuda.setObjectName("dlg_subtitulo")
        ayuda.setWordWrap(True)
        raiz.addWidget(ayuda)
        raiz.addSpacing(4)

        self.combo_tipo = QComboBox()
        self.combo_tipo.setObjectName("dlg_combo")
        self.combo_tipo.addItem("Docente", "docente")
        self.combo_tipo.addItem("Estudiante", "estudiante")
        if modo == "crear":
            raiz.addWidget(self._etiqueta("Tipo de cuenta"))
            raiz.addWidget(self.combo_tipo)
            self.combo_tipo.setCurrentIndex(0 if tipo_inicial == "docente" else 1)

        self.in_nombre = QLineEdit(self.usuario.get("nombre_pila", ""))
        self.in_nombre.setObjectName("dlg_input")
        self.in_apellidos = QLineEdit(self.usuario.get("apellidos", ""))
        self.in_apellidos.setObjectName("dlg_input")
        self.in_cedula = QLineEdit(self.usuario.get("cedula", ""))
        self.in_cedula.setObjectName("dlg_input")
        self.in_cedula.setValidator(QRegularExpressionValidator(QRegularExpression(r"^[0-9]{0,15}$"), self.in_cedula))
        self.in_correo = QLineEdit(self.usuario.get("email", ""))
        self.in_correo.setObjectName("dlg_input")

        for etiqueta, campo in (("Nombres", self.in_nombre), ("Apellidos", self.in_apellidos),
                                ("Cédula", self.in_cedula), ("Correo institucional", self.in_correo)):
            raiz.addWidget(self._etiqueta(etiqueta))
            raiz.addWidget(campo)

        self.lbl_codigo = QLabel("")
        self.lbl_codigo.setObjectName("dlg_subtitulo")
        raiz.addWidget(self.lbl_codigo)
        self.lbl_error = QLabel("")
        self.lbl_error.setObjectName("dlg_error")
        self.lbl_error.setWordWrap(True)
        raiz.addWidget(self.lbl_error)

        fila_btn = QHBoxLayout()
        fila_btn.addStretch()
        cancelar = QPushButton("Cancelar")
        cancelar.setObjectName("btn_admin_secundario")
        cancelar.setCursor(Qt.CursorShape.PointingHandCursor)
        cancelar.clicked.connect(self.reject)
        self.btn_guardar = QPushButton("Crear cuenta" if modo == "crear" else "Guardar cambios")
        self.btn_guardar.setObjectName("btn_admin_nuevo")
        self.btn_guardar.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_guardar.setDefault(True)
        self.btn_guardar.clicked.connect(self._validar)
        fila_btn.addWidget(cancelar)
        fila_btn.addWidget(self.btn_guardar)
        raiz.addLayout(fila_btn)

        def _filtrar_cedula(texto):
            solo_dig = re.sub(r"[^0-9]", "", texto)[:15]
            if solo_dig != texto:
                self.in_cedula.setText(solo_dig)
            self._actualizar_codigo()

        self.in_cedula.textChanged.connect(_filtrar_cedula)
        self.combo_tipo.currentIndexChanged.connect(self._actualizar_codigo)
        self._actualizar_codigo()

    def _etiqueta(self, texto):
        lbl = QLabel(texto.upper())
        lbl.setObjectName("dlg_campo")
        return lbl

    def tipo(self):
        return self.combo_tipo.currentData() if self.modo == "crear" else self.usuario.get("tipo", "docente")

    def _actualizar_codigo(self):
        if self.modo != "crear":
            self.lbl_codigo.setText("")
            return
        cedula = self.in_cedula.text().strip()
        prefijo = "PROF" if self.tipo() == "docente" else "EST"
        self.lbl_codigo.setText(f"Código que se asignará: {prefijo}-{cedula}" if cedula else "El código se asigna a partir de la cédula.")

    def _validar(self):
        if not all(c.text().strip() for c in (self.in_nombre, self.in_apellidos, self.in_cedula, self.in_correo)):
            self.lbl_error.setText("Complete todos los campos.")
            return
        if len(self.in_cedula.text().strip()) < 5:
            self.lbl_error.setText("La cédula debe tener al menos 5 dígitos.")
            return
        if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", self.in_correo.text().strip()):
            self.lbl_error.setText("El correo electrónico no tiene un formato válido.")
            return
        self.accept()

    def datos(self):
        return {
            "nombre": self.in_nombre.text().strip(),
            "apellidos": self.in_apellidos.text().strip(),
            "cedula": self.in_cedula.text().strip(),
            "email": self.in_correo.text().strip().lower(),
        }


class DialogoClaveTemporal(DialogoBase):
    def __init__(self, parent=None, titulo="Contraseña Temporal", nombre="", clave="", codigo=None):
        super().__init__(parent, titulo, 460)
        self.setObjectName("DialogoClaveTemporal")
        self.clave = clave
        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(28, 24, 28, 22)
        raiz.setSpacing(12)

        t = QLabel(titulo)
        t.setObjectName("dlg_titulo")
        raiz.addWidget(t)
        detalle = f"{nombre}" + (f"  ·  Código {codigo}" if codigo else "")
        d = QLabel(detalle)
        d.setObjectName("dlg_subtitulo")
        raiz.addWidget(d)
        raiz.addSpacing(6)

        etiqueta = QLabel("CONTRASEÑA TEMPORAL")
        etiqueta.setObjectName("dlg_campo")
        raiz.addWidget(etiqueta)
        self.lbl_clave = QLabel(clave)
        self.lbl_clave.setObjectName("dlg_clave")
        self.lbl_clave.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        raiz.addWidget(self.lbl_clave)

        nota = QLabel("Entréguela al usuario por un medio seguro. Solo se muestra en esta ventana; "
                      "si se pierde, deberá restablecerse nuevamente.")
        nota.setObjectName("dlg_subtitulo")
        nota.setWordWrap(True)
        raiz.addWidget(nota)

        fila_btn = QHBoxLayout()
        self.lbl_copiado = QLabel("")
        self.lbl_copiado.setObjectName("aviso_admin")
        fila_btn.addWidget(self.lbl_copiado)
        fila_btn.addStretch()
        copiar = QPushButton("Copiar")
        copiar.setObjectName("btn_admin_secundario")
        copiar.setCursor(Qt.CursorShape.PointingHandCursor)
        copiar.clicked.connect(self._copiar)
        cerrar = QPushButton("Cerrar")
        cerrar.setObjectName("btn_admin_nuevo")
        cerrar.setCursor(Qt.CursorShape.PointingHandCursor)
        cerrar.clicked.connect(self.accept)
        fila_btn.addWidget(copiar)
        fila_btn.addWidget(cerrar)
        raiz.addLayout(fila_btn)

    def _copiar(self):
        QApplication.clipboard().setText(self.clave)
        self.lbl_copiado.setText("Copiada al portapapeles")


class DialogoEliminar(DialogoBase):
    PALABRA = "ELIMINAR"

    def __init__(self, parent=None, usuario=None):
        usuario = usuario or {}
        super().__init__(parent, "Eliminar cuenta", 460)
        self.setObjectName("DialogoEliminar")
        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(28, 24, 28, 22)
        raiz.setSpacing(12)

        t = QLabel("Eliminar cuenta")
        t.setObjectName("dlg_titulo")
        raiz.addWidget(t)
        msg = QLabel(
            f"Se eliminará de forma permanente la cuenta de {usuario.get('nombre', '')} ({usuario.get('id', '')}). "
            "Esta acción no se puede deshacer. Si solo desea impedir el acceso, utilice Suspender cuenta."
        )
        msg.setObjectName("dlg_valor")
        msg.setWordWrap(True)
        raiz.addWidget(msg)
        raiz.addSpacing(4)

        etiqueta = QLabel(f"ESCRIBA {self.PALABRA} PARA CONFIRMAR")
        etiqueta.setObjectName("dlg_campo")
        raiz.addWidget(etiqueta)
        self.entrada = QLineEdit()
        self.entrada.setObjectName("dlg_input")
        self.entrada.textChanged.connect(self._revisar)
        raiz.addWidget(self.entrada)

        fila_btn = QHBoxLayout()
        fila_btn.addStretch()
        cancelar = QPushButton("Cancelar")
        cancelar.setObjectName("btn_admin_secundario")
        cancelar.setCursor(Qt.CursorShape.PointingHandCursor)
        cancelar.clicked.connect(self.reject)
        self.btn_eliminar = QPushButton("Eliminar cuenta")
        self.btn_eliminar.setObjectName("btn_admin_peligro")
        self.btn_eliminar.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_eliminar.setEnabled(False)
        self.btn_eliminar.clicked.connect(self.accept)
        fila_btn.addWidget(cancelar)
        fila_btn.addWidget(self.btn_eliminar)
        raiz.addLayout(fila_btn)

    def _revisar(self, texto):
        self.btn_eliminar.setEnabled(texto.strip().upper() == self.PALABRA)


class HiloImportarCSV(QThread):
    progreso = pyqtSignal(int, int)
    item_procesado = pyqtSignal(dict)
    terminado = pyqtSignal(list)

    def __init__(self, registros, tipo, parent=None):
        super().__init__(parent)
        self.registros = registros
        self.tipo = tipo

    def run(self):
        resultados = []
        total = len(self.registros)
        funcion = cliente_api.admin_crear_profesor if self.tipo == "docente" else cliente_api.admin_crear_estudiante

        for idx, reg in enumerate(self.registros):
            datos = {
                "nombre": reg["nombre"],
                "apellidos": reg["apellidos"],
                "cedula": reg["cedula"],
                "email": reg["email"]
            }
            try:
                exito, res = funcion(datos)
                if exito:
                    item = {
                        "nombre": f"{reg['nombre']} {reg['apellidos']}",
                        "cedula": reg["cedula"],
                        "email": reg["email"],
                        "codigo": res.get("codigo", ""),
                        "claveTemporal": res.get("claveTemporal", ""),
                        "exito": True,
                        "mensaje": "Creado con éxito"
                    }
                else:
                    item = {
                        "nombre": f"{reg['nombre']} {reg['apellidos']}",
                        "cedula": reg["cedula"],
                        "email": reg["email"],
                        "codigo": "",
                        "claveTemporal": "",
                        "exito": False,
                        "mensaje": str(res)
                    }
            except Exception as e:
                item = {
                    "nombre": f"{reg['nombre']} {reg['apellidos']}",
                    "cedula": reg["cedula"],
                    "email": reg["email"],
                    "codigo": "",
                    "claveTemporal": "",
                    "exito": False,
                    "mensaje": f"Error: {e}"
                }
            resultados.append(item)
            self.item_procesado.emit(item)
            self.progreso.emit(idx + 1, total)

        self.terminado.emit(resultados)


class DialogoCredencialesImportadas(DialogoBase):
    def __init__(self, parent=None, resultados=None, tipo="docente"):
        super().__init__(parent, "Credenciales Temporales de Cuentas Creadas", 620)
        self.setObjectName("DialogoCredencialesImportadas")
        self.resultados = resultados or []
        self.tipo = tipo

        exitosos = [r for r in self.resultados if r.get("exito")]
        fallidos = [r for r in self.resultados if not r.get("exito")]

        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(28, 24, 28, 22)
        raiz.setSpacing(12)

        t = QLabel("Resultado de Importación Masiva")
        t.setObjectName("dlg_titulo")
        raiz.addWidget(t)

        sub = QLabel(f"Se crearon correctamente {len(exitosos)} cuentas. {len(fallidos)} presentaron errores.")
        sub.setObjectName("dlg_subtitulo")
        raiz.addWidget(sub)

        tabla = QTableWidget()
        tabla.setObjectName("tabla_admin_usuarios")
        tabla.setColumnCount(5)
        tabla.setHorizontalHeaderLabels(["NOMBRE", "CÉDULA", "CÓDIGO ASIGNADO", "CLAVE TEMPORAL", "ESTADO"])
        tabla.verticalHeader().setVisible(False)
        tabla.setRowCount(len(self.resultados))
        tabla.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        tabla.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)

        for f, r in enumerate(self.resultados):
            it_nom = QTableWidgetItem(r.get("nombre", ""))
            it_ced = QTableWidgetItem(r.get("cedula", ""))
            it_cod = QTableWidgetItem(r.get("codigo", "—"))
            it_cla = QTableWidgetItem(r.get("claveTemporal", "—"))
            it_est = QTableWidgetItem("● Creado" if r.get("exito") else f"● Error: {r.get('mensaje', '')}")
            it_est.setForeground(QColor("#1E7B3A" if r.get("exito") else "#B42318"))

            for c, it in enumerate([it_nom, it_ced, it_cod, it_cla, it_est]):
                it.setTextAlignment(int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter if c in (0, 4) else Qt.AlignmentFlag.AlignCenter))
                tabla.setItem(f, c, it)

        raiz.addWidget(tabla, 1)

        fila_btn = QHBoxLayout()
        self.btn_copiar = QPushButton("Copiar al Portapapeles")
        self.btn_copiar.setObjectName("btn_admin_secundario")
        self.btn_copiar.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_copiar.clicked.connect(self._copiar)

        self.btn_guardar_txt = QPushButton("Guardar Archivo (TXT)")
        self.btn_guardar_txt.setObjectName("btn_admin_secundario")
        self.btn_guardar_txt.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_guardar_txt.clicked.connect(self._guardar_archivo)

        cerrar = QPushButton("Cerrar")
        cerrar.setObjectName("btn_admin_nuevo")
        cerrar.setCursor(Qt.CursorShape.PointingHandCursor)
        cerrar.clicked.connect(self.accept)

        fila_btn.addWidget(self.btn_copiar)
        fila_btn.addWidget(self.btn_guardar_txt)
        fila_btn.addStretch()
        fila_btn.addWidget(cerrar)
        raiz.addLayout(fila_btn)

    def _generar_texto(self):
        lineas = ["=== UNIVERSIDAD POPULAR DEL CESAR - CREDENCIALES TEMPORALES GENERADAS ==="]
        lineas.append(f"Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n")
        for r in self.resultados:
            if r.get("exito"):
                lineas.append(f"Usuario: {r.get('nombre')} | Cédula: {r.get('cedula')} | Código: {r.get('codigo')} | Clave: {r.get('claveTemporal')}")
            else:
                lineas.append(f"FALLIDO: {r.get('nombre')} | Cédula: {r.get('cedula')} | Razón: {r.get('mensaje')}")
        return "\n".join(lineas)

    def _copiar(self):
        QApplication.clipboard().setText(self._generar_texto())
        QMessageBox.information(self, "Copiado", "Credenciales copiadas al portapapeles exitosamente.")

    def _guardar_archivo(self):
        sugerido = f"Credenciales_{self.tipo.title()}s_{datetime.now().strftime('%Y%m%d_%H%M')}.txt"
        ruta, _ = QFileDialog.getSaveFileName(self, "Guardar Credenciales Temporales", sugerido, "Archivos de Texto (*.txt)")
        if not ruta:
            return
        try:
            with open(ruta, "w", encoding="utf-8") as f:
                f.write(self._generar_texto())
            QMessageBox.information(self, "Guardado", f"Archivo guardado exitosamente en:\n{ruta}")
        except Exception as e:
            QMessageBox.critical(self, "Error al Guardar", f"No se pudo guardar el archivo:\n{e}")


class DialogoImportarCSV(DialogoBase):
    def __init__(self, parent=None, tipo_inicial="docente"):
        super().__init__(parent, "Importación Masiva de Usuarios (CSV)", 720)
        self.setObjectName("DialogoImportarCSV")
        self.registros_leidos = []
        self._hilo_importar = None

        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(28, 24, 28, 22)
        raiz.setSpacing(12)

        t = QLabel("Importación Masiva de Cuentas")
        t.setObjectName("dlg_titulo")
        raiz.addWidget(t)

        sub = QLabel(
            "Seleccione un archivo CSV con las columnas: Nombre, Apellidos, Cédula y Correo Institucional. "
            "El sistema validará el formato antes de crear las cuentas y generar las contraseñas temporales."
        )
        sub.setObjectName("dlg_subtitulo")
        sub.setWordWrap(True)
        raiz.addWidget(sub)

        # Barra de selección
        fila_sel = QHBoxLayout()
        fila_sel.setSpacing(10)

        lbl_tipo = QLabel("TIPO:")
        lbl_tipo.setObjectName("dlg_campo")
        self.combo_tipo = QComboBox()
        self.combo_tipo.setObjectName("dlg_combo")
        self.combo_tipo.addItem("Docentes", "docente")
        self.combo_tipo.addItem("Estudiantes", "estudiante")
        self.combo_tipo.setCurrentIndex(0 if tipo_inicial == "docente" else 1)
        self.combo_tipo.setFixedWidth(140)

        self.btn_examinar = QPushButton("Seleccionar archivo CSV...")
        self.btn_examinar.setObjectName("btn_admin_secundario")
        self.btn_examinar.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_examinar.clicked.connect(self._abrir_csv)

        self.lbl_archivo = QLabel("Ningún archivo seleccionado")
        self.lbl_archivo.setObjectName("dlg_subtitulo")

        fila_sel.addWidget(lbl_tipo)
        fila_sel.addWidget(self.combo_tipo)
        fila_sel.addWidget(self.btn_examinar)
        fila_sel.addWidget(self.lbl_archivo, 1)
        raiz.addLayout(fila_sel)

        # Tabla de previsualización
        self.tabla_prev = QTableWidget()
        self.tabla_prev.setObjectName("tabla_admin_usuarios")
        self.tabla_prev.setColumnCount(6)
        self.tabla_prev.setHorizontalHeaderLabels(["FILA", "NOMBRE", "APELLIDOS", "CÉDULA", "CORREO INSTITUCIONAL", "ESTADO"])
        self.tabla_prev.verticalHeader().setVisible(False)
        self.tabla_prev.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.tabla_prev.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.tabla_prev.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        raiz.addWidget(self.tabla_prev, 1)

        # Resumen y barra de progreso
        self.lbl_resumen = QLabel("")
        self.lbl_resumen.setObjectName("dlg_subtitulo")
        raiz.addWidget(self.lbl_resumen)

        self.barra_progreso = QProgressBar()
        self.barra_progreso.setObjectName("barra_progreso_admin")
        self.barra_progreso.setVisible(False)
        raiz.addWidget(self.barra_progreso)

        # Botones inferiores
        fila_btn = QHBoxLayout()
        fila_btn.addStretch()

        cancelar = QPushButton("Cancelar")
        cancelar.setObjectName("btn_admin_secundario")
        cancelar.setCursor(Qt.CursorShape.PointingHandCursor)
        cancelar.clicked.connect(self.reject)

        self.btn_importar = QPushButton("Iniciar Importación")
        self.btn_importar.setObjectName("btn_admin_nuevo")
        self.btn_importar.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_importar.setEnabled(False)
        self.btn_importar.clicked.connect(self._iniciar_importacion)

        fila_btn.addWidget(cancelar)
        fila_btn.addWidget(self.btn_importar)
        raiz.addLayout(fila_btn)

    def _abrir_csv(self, ruta_archivo=None):
        import io
        if ruta_archivo:
            ruta = ruta_archivo
        else:
            ruta, _ = QFileDialog.getOpenFileName(self, "Seleccionar archivo CSV", "", "Archivos CSV (*.csv);;Todos los archivos (*.*)")
        if not ruta:
            return

        self.lbl_archivo.setText(os.path.basename(ruta))
        try:
            with open(ruta, "rb") as f:
                contenido_bytes = f.read()

            texto = None
            for encoding in ['utf-8-sig', 'utf-8', 'latin-1', 'cp1252']:
                try:
                    texto = contenido_bytes.decode(encoding)
                    break
                except Exception:
                    continue
            if texto is None:
                QMessageBox.warning(self, "Error al Leer", "No se pudo detectar la codificación del archivo.")
                return

            primera_linea = texto.splitlines()[0] if texto.splitlines() else ""
            delimitador = ';' if primera_linea.count(';') > primera_linea.count(',') else ','

            lector = csv.DictReader(io.StringIO(texto), delimiter=delimitador)
            if not lector.fieldnames:
                QMessageBox.warning(self, "Archivo Vacío", "El archivo CSV no contiene registros.")
                return

            import unicodedata
            mapa_cols = {}
            for col in lector.fieldnames:
                cn = ''.join(c for c in unicodedata.normalize('NFD', col.strip().lower()) if unicodedata.category(c) != 'Mn')
                if cn in ['nombre', 'nombres', 'primer nombre']:
                    mapa_cols['nombre'] = col
                elif cn in ['apellido', 'apellidos', 'primer apellido']:
                    mapa_cols['apellidos'] = col
                elif cn in ['cedula', 'documento', 'identificacion', 'numero documento']:
                    mapa_cols['cedula'] = col
                elif cn in ['email', 'correo', 'correo institucional', 'emailinstitucional']:
                    mapa_cols['email'] = col

            faltantes = [c for c in ['nombre', 'apellidos', 'cedula', 'email'] if c not in mapa_cols]
            if faltantes:
                QMessageBox.warning(self, "Columnas Faltantes", f"Faltan columnas requeridas en el CSV:\n\n{', '.join(faltantes)}")
                return

            import re
            regex_email = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
            cedulas_vistas = set()
            registros = []

            for idx, fila in enumerate(lector, start=2):
                nombre = (fila.get(mapa_cols['nombre']) or "").strip()
                apellidos = (fila.get(mapa_cols['apellidos']) or "").strip()
                cedula_raw = (fila.get(mapa_cols['cedula']) or "").strip()
                email = (fila.get(mapa_cols['email']) or "").strip().lower()
                solo_dig = re.sub(r"[^0-9]", "", cedula_raw)

                errores = []
                if not nombre:
                    errores.append("Nombre requerido")
                if not apellidos:
                    errores.append("Apellidos requeridos")
                if len(solo_dig) < 5:
                    errores.append("Cédula < 5 dígitos")
                elif solo_dig in cedulas_vistas:
                    errores.append("Cédula duplicada en archivo")
                else:
                    cedulas_vistas.add(solo_dig)

                if not regex_email.match(email):
                    errores.append("Correo no válido")

                registros.append({
                    "fila": idx,
                    "nombre": nombre,
                    "apellidos": apellidos,
                    "cedula": solo_dig,
                    "email": email,
                    "valido": len(errores) == 0,
                    "error": " | ".join(errores) if errores else "Válido"
                })

            self.registros_leidos = registros
            self._pintar_preview()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo procesar el archivo CSV:\n{e}")

    def _pintar_preview(self):
        self.tabla_prev.setRowCount(len(self.registros_leidos))
        validos = sum(1 for r in self.registros_leidos if r["valido"])
        invalidos = len(self.registros_leidos) - validos

        for f, r in enumerate(self.registros_leidos):
            it_fila = QTableWidgetItem(str(r["fila"]))
            it_nom = QTableWidgetItem(r["nombre"])
            it_ape = QTableWidgetItem(r["apellidos"])
            it_ced = QTableWidgetItem(r["cedula"])
            it_ema = QTableWidgetItem(r["email"])
            it_est = QTableWidgetItem(f"● {r['error']}")
            it_est.setForeground(QColor("#1E7B3A" if r["valido"] else "#B42318"))

            for c, it in enumerate([it_fila, it_nom, it_ape, it_ced, it_ema, it_est]):
                it.setTextAlignment(int(Qt.AlignmentFlag.AlignCenter if c in (0, 3) else Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter))
                self.tabla_prev.setItem(f, c, it)

        self.lbl_resumen.setText(f"Registros válidos: {validos}  ·  Con observaciones o errores: {invalidos}")
        self.btn_importar.setEnabled(validos > 0)
        self.btn_importar.setText(f"Importar {validos} Cuentas Válidas")

    def _iniciar_importacion(self):
        validos = [r for r in self.registros_leidos if r["valido"]]
        if not validos:
            return

        tipo = self.combo_tipo.currentData()
        self.btn_importar.setEnabled(False)
        self.btn_examinar.setEnabled(False)
        self.combo_tipo.setEnabled(False)

        self.barra_progreso.setVisible(True)
        self.barra_progreso.setMaximum(len(validos))
        self.barra_progreso.setValue(0)

        self._hilo_importar = HiloImportarCSV(validos, tipo, self)
        self._hilo_importar.progreso.connect(self._actualizar_progreso)
        self._hilo_importar.terminado.connect(self._finalizar_importacion)
        self._hilo_importar.start()

    def _actualizar_progreso(self, actual, total):
        self.barra_progreso.setValue(actual)
        self.lbl_resumen.setText(f"Creando cuentas: {actual} de {total} procesadas…")

    def _finalizar_importacion(self, resultados):
        self.accept()
        dlg_cred = DialogoCredencialesImportadas(self.parent(), resultados, tipo=self.combo_tipo.currentData())
        dlg_cred.exec()


# ----------------------------------------------------------------------------
# Tabla de usuarios (reutilizada para docentes y estudiantes)
# ----------------------------------------------------------------------------
class TablaUsuarios(QWidget):
    accion = pyqtSignal(str, dict)

    def __init__(self, tipo: str):
        super().__init__()
        self.setObjectName("TablaUsuarios")
        self.tipo = tipo
        self.modo_oscuro = False
        self.usuarios = []
        self.visibles = []
        self.orden_col = 1
        self.orden_asc = True

        if tipo == "docente":
            self.columnas = [("id", "CÓDIGO"), ("nombre", "NOMBRE COMPLETO"), ("cedula", "CÉDULA"),
                             ("email", "CORREO INSTITUCIONAL"), ("rol_texto", "ROL"), ("estado", "ESTADO")]
            marcador = "Buscar por nombre, cédula, código o correo"
        else:
            self.columnas = [("id", "IDENTIFICADOR"), ("nombre", "NOMBRE COMPLETO"), ("cedula", "CÉDULA"),
                             ("email", "CORREO INSTITUCIONAL"), ("estado", "ESTADO")]
            marcador = "Buscar por nombre, cédula, identificador o correo"
        self.col_acciones = len(self.columnas)

        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(0, 16, 0, 0)
        raiz.setSpacing(12)

        barra = QHBoxLayout()
        barra.setSpacing(10)
        self.buscador = QLineEdit()
        self.buscador.setObjectName("buscador_admin")
        self.buscador.setPlaceholderText(marcador)
        self.buscador.setClearButtonEnabled(True)
        self.buscador.textChanged.connect(self.refrescar)
        self.filtro_estado = QComboBox()
        self.filtro_estado.setObjectName("filtro_estado_admin")
        self.filtro_estado.addItem("Todos los estados", "")
        self.filtro_estado.addItem("Activos", "ACTIVO")
        self.filtro_estado.addItem("Suspendidos", "SUSPENDIDO")
        self.filtro_estado.setFixedWidth(170)
        self.filtro_estado.currentIndexChanged.connect(self.refrescar)
        self.lbl_conteo = QLabel("")
        self.btn_exportar = QPushButton("Exportar Excel")
        self.btn_exportar.setObjectName("btn_admin_secundario")
        self.btn_exportar.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_exportar.setToolTip("Exportar registros a archivo Excel (.xlsx) o CSV")
        self.btn_exportar.clicked.connect(self._exportar_tabla)
        barra.addWidget(self.buscador, 1)
        barra.addWidget(self.filtro_estado)
        barra.addWidget(self.btn_exportar)
        barra.addWidget(self.lbl_conteo)
        raiz.addLayout(barra)

        zona = QFrame()
        zona.setObjectName("zona_tabla_admin")
        lay_zona = QVBoxLayout(zona)
        lay_zona.setContentsMargins(0, 0, 0, 0)
        lay_zona.setSpacing(0)

        self.tabla = QTableWidget()
        self.tabla.setObjectName("tabla_admin_usuarios")
        self.tabla.setColumnCount(len(self.columnas) + 1)
        self.tabla.setHorizontalHeaderLabels([t for _, t in self.columnas] + ["ACCIONES"])
        self.tabla.verticalHeader().setVisible(False)
        self.tabla.verticalHeader().setDefaultSectionSize(46)
        self.tabla.setShowGrid(False)
        self.tabla.setAlternatingRowColors(True)
        self.tabla.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tabla.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tabla.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tabla.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.tabla.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.tabla.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tabla.customContextMenuRequested.connect(self._menu_contextual)
        self.tabla.cellDoubleClicked.connect(lambda fila, _c: self._emitir_fila("ficha", fila))

        self.alineaciones = {
            "id": Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            "nombre": Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            "cedula": Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            "email": Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            "rol_texto": Qt.AlignmentFlag.AlignCenter,
            "estado": Qt.AlignmentFlag.AlignCenter,
        }

        cab = self.tabla.horizontalHeader()
        cab.setHighlightSections(False)
        cab.setSectionsClickable(True)
        cab.setSortIndicatorShown(True)
        cab.setMinimumSectionSize(90)
        cab.sectionClicked.connect(self._ordenar_por)
        cab.setStretchLastSection(False)
        for i, (clave, _) in enumerate(self.columnas):
            modo = QHeaderView.ResizeMode.Stretch if clave in ("nombre", "email") else QHeaderView.ResizeMode.ResizeToContents
            cab.setSectionResizeMode(i, modo)
            alig = self.alineaciones.get(clave, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            self.tabla.horizontalHeaderItem(i).setTextAlignment(int(alig))

        # La columna de acciones tiene ancho fijo suficiente para evitar truncamiento
        cab.setSectionResizeMode(self.col_acciones, QHeaderView.ResizeMode.Fixed)
        self.tabla.setColumnWidth(self.col_acciones, 130)
        self.tabla.horizontalHeaderItem(self.col_acciones).setTextAlignment(int(Qt.AlignmentFlag.AlignCenter))
        cab.setSortIndicator(self.orden_col, Qt.SortOrder.AscendingOrder)

        # Widget de esquina para continuar el encabezado sobre el scrollbar sin dejar huecos
        self.corner = QWidget()
        self.corner.setObjectName("tabla_header_corner")
        self.tabla.setCornerWidget(self.corner)

        self.lbl_vacio = QLabel("No hay registros que coincidan con la búsqueda.")
        self.lbl_vacio.setObjectName("vacio_admin")
        self.lbl_vacio.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_vacio.setMinimumHeight(120)
        self.lbl_vacio.hide()

        lay_zona.addWidget(self.tabla)
        lay_zona.addWidget(self.lbl_vacio)
        raiz.addWidget(zona, 1)

    # -- datos ---------------------------------------------------------------
    def cargar(self, usuarios):
        self.usuarios = list(usuarios)
        self.refrescar()

    def set_modo_oscuro(self, oscuro: bool):
        self.modo_oscuro = oscuro
        self.refrescar()

    # Compatibilidad con pruebas previas
    def set_paleta(self, paleta):
        self.modo_oscuro = paleta is PALETA_OSCURA
        self.refrescar()

    def _ordenar_por(self, col):
        if col >= self.col_acciones:
            return
        self.orden_asc = (not self.orden_asc) if col == self.orden_col else True
        self.orden_col = col
        self.tabla.horizontalHeader().setSortIndicator(
            col, Qt.SortOrder.AscendingOrder if self.orden_asc else Qt.SortOrder.DescendingOrder)
        self.refrescar()

    def refrescar(self, *_):
        q = self.buscador.text().strip().lower()
        estado = self.filtro_estado.currentData()
        clave_orden = self.columnas[self.orden_col][0]

        filtrados = [
            u for u in self.usuarios
            if (not estado or u["estado"] == estado)
            and (not q or any(q in str(u[c]).lower() for c in ("id", "nombre", "cedula", "email")))
        ]
        filtrados.sort(key=lambda u: str(u[clave_orden]).lower(), reverse=not self.orden_asc)
        self.visibles = filtrados
        self._pintar()
        self.lbl_conteo.setText(f"{len(filtrados)} de {len(self.usuarios)}")

    def _pintar(self):
        self.tabla.setUpdatesEnabled(False)
        self.tabla.clearContents()
        self.tabla.setRowCount(len(self.visibles))
        for fila, u in enumerate(self.visibles):
            for col, (clave, _) in enumerate(self.columnas):
                alig = self.alineaciones.get(clave, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
                if clave == "estado":
                    item = QTableWidgetItem(f"●  {texto_estado(u['estado'])}")
                    item.setForeground(QColor(color_estado(u["estado"], self.modo_oscuro)))
                    fuente = QFont(item.font())
                    fuente.setWeight(QFont.Weight.DemiBold)
                    item.setFont(fuente)
                else:
                    item = QTableWidgetItem(str(u[clave]))
                    if clave == "id":
                        item.setForeground(QColor(color_codigo(self.modo_oscuro)))
                item.setTextAlignment(int(alig))
                self.tabla.setItem(fila, col, item)
            self.tabla.setCellWidget(fila, self.col_acciones, self._boton_gestion(u))
        self.tabla.setUpdatesEnabled(True)
        hay = bool(self.visibles)
        self.tabla.setVisible(hay)
        self.lbl_vacio.setVisible(not hay)

    def _exportar_tabla(self):
        sugerido = f"Directorio_{self.tipo.title()}s_UPC_{datetime.now().strftime('%Y%m%d')}.xlsx"
        ruta, filtro = QFileDialog.getSaveFileName(
            self, "Exportar Listado de Usuarios", sugerido,
            "Archivos Excel (*.xlsx);;Archivos CSV (*.csv)"
        )
        if not ruta:
            return
        try:
            if ruta.lower().endswith(".csv") or ("CSV" in filtro and not ruta.lower().endswith(".xlsx")):
                with open(ruta, mode='w', encoding='utf-8-sig', newline='') as f:
                    escritor = csv.writer(f, delimiter=';')
                    encabezados = [tit for _, tit in self.columnas]
                    escritor.writerow(encabezados)
                    for u in self.visibles:
                        fila = [str(u.get(clave, '')) for clave, _ in self.columnas]
                        escritor.writerow(fila)
            else:
                from utils.exportador_excel import generar_excel_directorio
                generar_excel_directorio(ruta, self.tipo, self.visibles)

            QMessageBox.information(
                self, "Exportación Exitosa",
                f"Se exportaron {len(self.visibles)} registros correctamente a:\n\n{ruta}"
            )
        except Exception as e:
            QMessageBox.critical(self, "Error al Exportar", f"No se pudo guardar el archivo:\n{e}")

    # -- acciones --------------------------------------------------------------
    def _crear_menu(self, usuario, padre):
        menu = QMenu(padre)
        menu.setObjectName("menu_gestion_admin")
        protegido = es_superadmin(usuario)
        suspendido = usuario["estado"] == "SUSPENDIDO"
        definicion = [
            ("ficha", "Ver ficha", True),
            ("editar", "Editar datos", True),
            ("clave", "Restablecer contraseña", True),
            None,
            ("estado", "Reactivar cuenta" if suspendido else "Suspender cuenta", not protegido),
            ("eliminar", "Eliminar cuenta…", not protegido),
        ]
        for entrada in definicion:
            if entrada is None:
                menu.addSeparator()
                continue
            nombre, texto, habilitada = entrada
            a = menu.addAction(texto)
            a.setEnabled(habilitada)
            a.triggered.connect(lambda _=False, n=nombre, u=usuario: self.accion.emit(n, u))
        return menu

    def _boton_gestion(self, usuario):
        contenedor = QWidget()
        lay = QHBoxLayout(contenedor)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        boton = QToolButton()
        boton.setObjectName("gestionar")
        boton.setText("Gestionar")
        boton.setFixedSize(84, 26)
        boton.setCursor(Qt.CursorShape.PointingHandCursor)
        boton.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        boton.setMenu(self._crear_menu(usuario, boton))
        lay.addWidget(boton)
        return contenedor

    def _menu_contextual(self, pos):
        fila = self.tabla.rowAt(pos.y())
        if 0 <= fila < len(self.visibles):
            self.tabla.selectRow(fila)
            self._crear_menu(self.visibles[fila], self.tabla).exec(self.tabla.viewport().mapToGlobal(pos))

    def _emitir_fila(self, nombre, fila):
        if 0 <= fila < len(self.visibles):
            self.accion.emit(nombre, self.visibles[fila])


# ----------------------------------------------------------------------------
# Panel principal
# ----------------------------------------------------------------------------
class PanelAdmin(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("PanelAdmin")
        self.modo_oscuro = False
        self._hilos = []
        self._construir_ui()
        self.aplicar_tema(False)
        if sesion_actual.es_admin():
            self.cargar_datos()

    # -- construcción -----------------------------------------------------------
    def _construir_ui(self):
        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(34, 28, 34, 24)
        raiz.setSpacing(20)

        cabecera = QHBoxLayout()
        bloque = QVBoxLayout()
        bloque.setSpacing(2)
        titulo = QLabel("Administración de usuarios")
        titulo.setObjectName("titulo_admin")
        sub = QLabel("Gestión de las cuentas de docentes y estudiantes de la Universidad Popular del Cesar")
        sub.setObjectName("subtitulo_admin")
        bloque.addWidget(titulo)
        bloque.addWidget(sub)
        cabecera.addLayout(bloque)
        cabecera.addStretch()

        self.lbl_aviso = QLabel("")
        self.lbl_aviso.setObjectName("aviso_admin")
        cabecera.addWidget(self.lbl_aviso)
        cabecera.addSpacing(8)

        self.btn_recargar = QPushButton("Actualizar")
        self.btn_recargar.setObjectName("btn_admin_secundario")
        self.btn_recargar.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_recargar.clicked.connect(self.cargar_datos)
        self.btn_importar = QPushButton("Importar CSV")
        self.btn_importar.setObjectName("btn_admin_secundario")
        self.btn_importar.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_importar.clicked.connect(self._importar_csv)
        self.btn_nuevo = QPushButton("Nuevo usuario")
        self.btn_nuevo.setObjectName("btn_admin_nuevo")
        self.btn_nuevo.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_nuevo.clicked.connect(self._nuevo_usuario)
        cabecera.addWidget(self.btn_recargar)
        cabecera.addWidget(self.btn_importar)
        cabecera.addWidget(self.btn_nuevo)
        raiz.addLayout(cabecera)

        # Franja de indicadores
        franja = QFrame()
        franja.setObjectName("franja_admin")
        lay_f = QHBoxLayout(franja)
        lay_f.setContentsMargins(0, 0, 0, 0)
        lay_f.setSpacing(0)
        self.m_docentes = self._metrica("DOCENTES REGISTRADOS", "Cuentas de docentes")
        self.m_estudiantes = self._metrica("ESTUDIANTES REGISTRADOS", "Cuentas de estudiantes")
        self.m_examenes = self._metrica("EXÁMENES EN EL SISTEMA", "Evaluaciones creadas")
        for i, m in enumerate((self.m_docentes, self.m_estudiantes, self.m_examenes)):
            if i:
                divisor = QFrame()
                divisor.setObjectName("divisor_admin")
                divisor.setFixedWidth(1)
                lay_f.addWidget(divisor)
            lay_f.addWidget(m["widget"], 1)
        raiz.addWidget(franja)

        # Pestañas
        self.tabs = QTabWidget()
        self.tabs.setObjectName("tabs_admin")
        self.tabs.setDocumentMode(True)
        self.tabla_docentes = TablaUsuarios("docente")
        self.tabla_estudiantes = TablaUsuarios("estudiante")
        self.tabla_docentes.accion.connect(self._manejar_accion)
        self.tabla_estudiantes.accion.connect(self._manejar_accion)
        self.tabs.addTab(self.tabla_docentes, "Docentes")
        self.tabs.addTab(self.tabla_estudiantes, "Estudiantes")
        raiz.addWidget(self.tabs, 1)

    def _metrica(self, etiqueta, detalle):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(24, 16, 24, 16)
        lay.setSpacing(2)
        e = QLabel(etiqueta)
        e.setObjectName("metrica_etiqueta")
        v = QLabel("0")
        v.setObjectName("metrica_valor")
        d = QLabel(detalle)
        d.setObjectName("metrica_detalle")
        lay.addWidget(e)
        lay.addWidget(v)
        lay.addWidget(d)
        return {"widget": w, "valor": v, "detalle": d}

    # -- tema -------------------------------------------------------------------
    def aplicar_tema(self, oscuro: bool):
        self.modo_oscuro = oscuro
        estilo = cargar_estilo(oscuro)
        if estilo:
            self.setStyleSheet(estilo)
        self.tabla_docentes.set_modo_oscuro(oscuro)
        self.tabla_estudiantes.set_modo_oscuro(oscuro)

    @property
    def paleta(self):
        """Propiedad para compatibilidad con verificaciones externas."""
        return PALETA_OSCURA if self.modo_oscuro else PALETA_CLARA

    # -- carga de datos ---------------------------------------------------------
    def cargar_datos(self):
        self.btn_recargar.setEnabled(False)
        self.btn_recargar.setText("Cargando…")
        self.hilo = HiloAdmin()
        self.hilo.datos_cargados.connect(self._al_cargar_datos)
        self.hilo.start()

    def _al_cargar_datos(self, exito, resultado):
        self.btn_recargar.setEnabled(True)
        self.btn_recargar.setText("Actualizar")

        if not exito or not resultado.get("exito", True):
            detalle = resultado.get("error") or resultado.get("detalle") or "Sin respuesta del servidor."
            QMessageBox.warning(self, "Administración de usuarios", f"No se pudieron cargar los datos.\n\n{detalle}")
            return
        if resultado.get("parcial"):
            self._avisar("Algunos datos no se pudieron cargar")

        r = resultado.get("resumen", {})
        tp, ap = r.get("totalProfesores", 0), r.get("profesoresActivos", 0)
        te, ae = r.get("totalEstudiantes", 0), r.get("estudiantesActivos", 0)
        self.m_docentes["valor"].setText(str(tp))
        self.m_docentes["detalle"].setText(f"{ap} activos  ·  {max(tp - ap, 0)} suspendidos")
        self.m_estudiantes["valor"].setText(str(te))
        self.m_estudiantes["detalle"].setText(f"{ae} activos  ·  {max(te - ae, 0)} suspendidos")
        self.m_examenes["valor"].setText(str(r.get("totalExamenes", 0)))

        self.tabla_docentes.cargar([normalizar_profesor(p) for p in resultado.get("profesores", [])])
        self.tabla_estudiantes.cargar([normalizar_estudiante(e) for e in resultado.get("estudiantes", [])])

    def _avisar(self, texto, ms=5000):
        self.lbl_aviso.setText(texto)
        QTimer.singleShot(ms, lambda: self.lbl_aviso.setText("") if self.lbl_aviso.text() == texto else None)

    # -- ejecución de operaciones ---------------------------------------------------
    def _ejecutar(self, funcion, al_exito):
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        self.setEnabled(False)
        hilo = HiloAccion(funcion, self)
        self._hilos.append(hilo)

        def terminar(exito, datos):
            QApplication.restoreOverrideCursor()
            self.setEnabled(True)
            if exito:
                al_exito(datos if isinstance(datos, dict) else {})
            else:
                QMessageBox.warning(self, "No se pudo completar la acción", str(datos))

        hilo.terminado.connect(terminar)
        hilo.finished.connect(lambda: self._hilos.remove(hilo) if hilo in self._hilos else None)
        hilo.start()

    def _manejar_accion(self, nombre, usuario):
        docente = usuario["tipo"] == "docente"
        if nombre == "ficha":
            DialogoFicha(self, usuario).exec()

        elif nombre == "editar":
            dlg = DialogoUsuario(self, "editar", usuario)
            if dlg.exec() == QDialog.DialogCode.Accepted:
                datos = dlg.datos()
                f = cliente_api.admin_editar_profesor if docente else cliente_api.admin_editar_estudiante
                self._ejecutar(lambda: f(usuario["id"], datos),
                               lambda _d: (self._avisar("Datos actualizados"), self.cargar_datos()))

        elif nombre == "clave":
            resp = QMessageBox.question(
                self, "Restablecer contraseña",
                f"Se generará una contraseña temporal para {usuario['nombre']}.\n"
                "La contraseña actual dejará de funcionar. ¿Desea continuar?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
            if resp != QMessageBox.StandardButton.Yes:
                return
            f = cliente_api.admin_restablecer_clave_profesor if docente else cliente_api.admin_restablecer_clave_estudiante
            self._ejecutar(lambda: f(usuario["id"]), lambda d: DialogoClaveTemporal(
                self, "Contraseña restablecida", usuario["nombre"],
                d.get("claveTemporal", ""), usuario["id"]).exec())

        elif nombre == "estado":
            nuevo = "ACTIVO" if usuario["estado"] == "SUSPENDIDO" else "SUSPENDIDO"
            accion = "reactivar" if nuevo == "ACTIVO" else "suspender"
            resp = QMessageBox.question(
                self, "Confirmar",
                f"¿Desea {accion} la cuenta de {usuario['nombre']}?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
            if resp != QMessageBox.StandardButton.Yes:
                return
            f = cliente_api.admin_cambiar_estado_profesor if docente else cliente_api.admin_cambiar_estado_estudiante
            self._ejecutar(lambda: f(usuario["id"], nuevo),
                           lambda _d: (self._avisar("Cuenta reactivada" if nuevo == "ACTIVO" else "Cuenta suspendida"),
                                       self.cargar_datos()))

        elif nombre == "eliminar":
            if DialogoEliminar(self, usuario).exec() != QDialog.DialogCode.Accepted:
                return
            f = cliente_api.admin_eliminar_profesor if docente else cliente_api.admin_eliminar_estudiante
            self._ejecutar(lambda: f(usuario["id"]),
                           lambda _d: (self._avisar("Cuenta eliminada"), self.cargar_datos()))

    def _nuevo_usuario(self):
        tipo = "docente" if self.tabs.currentIndex() == 0 else "estudiante"
        dlg = DialogoUsuario(self, "crear", tipo_inicial=tipo)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        datos, tipo_final = dlg.datos(), dlg.tipo()
        f = cliente_api.admin_crear_profesor if tipo_final == "docente" else cliente_api.admin_crear_estudiante
        nombre = f"{datos['nombre']} {datos['apellidos']}"

        def exito(d):
            self.cargar_datos()
            self.tabs.setCurrentIndex(0 if tipo_final == "docente" else 1)
            DialogoClaveTemporal(self, "Cuenta creada", nombre,
                                 d.get("claveTemporal", ""), d.get("codigo")).exec()

        self._ejecutar(lambda: f(datos), exito)

    def _importar_csv(self):
        tipo_actual = "docente" if self.tabs.currentIndex() == 0 else "estudiante"
        dlg = DialogoImportarCSV(self, tipo_inicial=tipo_actual)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.cargar_datos()

