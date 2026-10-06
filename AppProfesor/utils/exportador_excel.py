# utils/exportador_excel.py
"""
Módulo de Exportación Institucional a Microsoft Excel (.xlsx) para SuperADMIN.
Genera libros y reportes con tipografía limpia, paleta institucional UPC
y autoajuste de columnas sin truncamiento.
Carga diferida y segura de openpyxl (no interrumpe el arranque de la app).
Universidad Popular del Cesar.
"""

import os
import sys
import csv
from datetime import datetime

from utils.gestor_sesion import sesion_actual


# Paleta Institucional UPC
COLOR_VERDE_HEADER_TOP = "004D1E"   # Verde UPC institucional principal
COLOR_VERDE_TABLA      = "0B5324"   # Verde bosque encabezado tabla
COLOR_ZEBRA            = "F4F9F5"   # Verde tenue para filas pares
COLOR_TEXTO_BLANCO     = "FFFFFF"
COLOR_TEXTO_OSCURO     = "2C3E50"
COLOR_BORDE            = "DCE2E0"


def _cargar_openpyxl():
    """
    Importa openpyxl bajo demanda para evitar que la falta de la librería
    impida el inicio de sesión o la carga de la interfaz.
    Si no está instalada, intenta instalarla automáticamente en el entorno actual.
    """
    try:
        import openpyxl
        from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
        from openpyxl.utils import get_column_letter
        return openpyxl, Font, PatternFill, Alignment, Border, Side, get_column_letter
    except ImportError:
        # Intento de autoinstalación en el entorno activo
        import subprocess
        try:
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", "openpyxl"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            import openpyxl
            from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
            from openpyxl.utils import get_column_letter
            return openpyxl, Font, PatternFill, Alignment, Border, Side, get_column_letter
        except Exception:
            return None, None, None, None, None, None, None


def _crear_estilos(Font, PatternFill, Alignment, Border, Side):
    """Genera las instancias de estilos de openpyxl."""
    fuente_titulo = Font(name="Segoe UI", size=13, bold=True, color=COLOR_TEXTO_BLANCO)
    fuente_subtitulo = Font(name="Segoe UI", size=10, bold=False, color="E8F5E9")
    fuente_meta = Font(name="Segoe UI", size=9, italic=True, color="C8E6C9")
    fuente_header_tabla = Font(name="Segoe UI", size=10, bold=True, color=COLOR_TEXTO_BLANCO)
    fuente_datos = Font(name="Segoe UI", size=10, color=COLOR_TEXTO_OSCURO)
    fuente_datos_bold = Font(name="Segoe UI", size=10, bold=True, color=COLOR_TEXTO_OSCURO)
    fuente_estado_activo = Font(name="Segoe UI", size=9, bold=True, color="1E7B3A")
    fuente_estado_susp = Font(name="Segoe UI", size=9, bold=True, color="B42318")

    fill_top = PatternFill(start_color=COLOR_VERDE_HEADER_TOP, end_color=COLOR_VERDE_HEADER_TOP, fill_type="solid")
    fill_header_tabla = PatternFill(start_color=COLOR_VERDE_TABLA, end_color=COLOR_VERDE_TABLA, fill_type="solid")
    fill_zebra = PatternFill(start_color=COLOR_ZEBRA, end_color=COLOR_ZEBRA, fill_type="solid")
    fill_blanco = PatternFill(start_color="FFFFFF", end_color="FFFFFF", fill_type="solid")
    fill_badge_activo = PatternFill(start_color="E8F5E9", end_color="E8F5E9", fill_type="solid")
    fill_badge_susp = PatternFill(start_color="FCE8E6", end_color="FCE8E6", fill_type="solid")

    borde_fino = Border(
        left=Side(style="thin", color=COLOR_BORDE),
        right=Side(style="thin", color=COLOR_BORDE),
        top=Side(style="thin", color=COLOR_BORDE),
        bottom=Side(style="thin", color=COLOR_BORDE)
    )

    align_centro = Alignment(horizontal="center", vertical="center")
    align_izq = Alignment(horizontal="left", vertical="center")
    align_der = Alignment(horizontal="right", vertical="center")

    return {
        "fuente_titulo": fuente_titulo,
        "fuente_subtitulo": fuente_subtitulo,
        "fuente_meta": fuente_meta,
        "fuente_header_tabla": fuente_header_tabla,
        "fuente_datos": fuente_datos,
        "fuente_datos_bold": fuente_datos_bold,
        "fuente_estado_activo": fuente_estado_activo,
        "fuente_estado_susp": fuente_estado_susp,
        "fill_top": fill_top,
        "fill_header_tabla": fill_header_tabla,
        "fill_zebra": fill_zebra,
        "fill_blanco": fill_blanco,
        "fill_badge_activo": fill_badge_activo,
        "fill_badge_susp": fill_badge_susp,
        "borde_fino": borde_fino,
        "align_centro": align_centro,
        "align_izq": align_izq,
        "align_der": align_der,
    }


def _aplicar_cabecera_institucional(ws, titulo, subtitulo, total_registros, num_cols, estilos, get_column_letter):
    """Crea el banner institucional membretado en las filas 1-3."""
    letra_fin = get_column_letter(num_cols)
    ws.views.sheetView[0].showGridLines = True
    
    ws.merge_cells(f"A1:{letra_fin}1")
    ws["A1"] = "UNIVERSIDAD POPULAR DEL CESAR"
    ws["A1"].font = estilos["fuente_titulo"]
    ws["A1"].alignment = estilos["align_centro"]
    
    ws.merge_cells(f"A2:{letra_fin}2")
    ws["A2"] = subtitulo
    ws["A2"].font = estilos["fuente_subtitulo"]
    ws["A2"].alignment = estilos["align_centro"]
    
    ws.merge_cells(f"A3:{letra_fin}3")
    emisor = sesion_actual.obtener_nombre() or "SuperADMIN"
    ws["A3"] = (
        f"Fecha de emisión: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}  |  "
        f"Registros: {total_registros}  |  Emitido por: {emisor}"
    )
    ws["A3"].font = estilos["fuente_meta"]
    ws["A3"].alignment = estilos["align_centro"]
    
    for r in range(1, 4):
        ws.row_dimensions[r].height = 22
        for col_idx in range(1, num_cols + 1):
            cell = ws.cell(row=r, column=col_idx)
            cell.fill = estilos["fill_top"]
            
    ws.row_dimensions[4].height = 10  # Separador


def _autoajustar_columnas(ws, columnas_def, fila_inicio_datos, fila_fin_datos, get_column_letter):
    """Ajusta anchos de columnas para asegurar que ningún dato salga truncado."""
    for c_idx, (_, ancho_min) in enumerate(columnas_def, start=1):
        letra = get_column_letter(c_idx)
        max_len = 0
        for r in range(fila_inicio_datos, fila_fin_datos + 1):
            val = ws.cell(row=r, column=c_idx).value
            if val is not None:
                max_len = max(max_len, len(str(val)))
        ws.column_dimensions[letra].width = max(max_len + 4, ancho_min)


def generar_excel_directorio(ruta_archivo: str, tipo: str, usuarios: list):
    """
    Exporta el directorio de docentes o estudiantes en un archivo Excel .xlsx profesional.
    Si openpyxl no está disponible y no se puede instalar, genera un CSV compatible con Excel.
    """
    openpyxl, Font, PatternFill, Alignment, Border, Side, get_column_letter = _cargar_openpyxl()
    if openpyxl is None:
        # Fallback de seguridad a CSV si openpyxl no se encuentra
        ruta_csv = ruta_archivo if ruta_archivo.lower().endswith(".csv") else f"{os.path.splitext(ruta_archivo)[0]}.csv"
        es_doc = (tipo == "docente" or tipo == "docentes")
        with open(ruta_csv, mode='w', encoding='utf-8-sig', newline='') as f:
            escritor = csv.writer(f, delimiter=';')
            if es_doc:
                escritor.writerow(["CODIGO_DOCENTE", "NOMBRE", "APELLIDOS", "CEDULA", "CORREO_INSTITUCIONAL", "ESTADO", "ROL"])
                for u in usuarios:
                    escritor.writerow([
                        u.get("codigoProfesor", "") or u.get("id", ""),
                        u.get("nombre", ""), u.get("apellidos", ""),
                        u.get("cedula", ""), u.get("emailInstitucional", "") or u.get("email", ""),
                        u.get("estado", "ACTIVO"), u.get("rol", "PROFESOR")
                    ])
            else:
                escritor.writerow(["IDENTIFICADOR_ESTUDIANTE", "NOMBRE", "APELLIDOS", "CEDULA", "CORREO_INSTITUCIONAL", "ESTADO"])
                for u in usuarios:
                    escritor.writerow([
                        u.get("estudianteId", "") or u.get("id", ""),
                        u.get("nombre", ""), u.get("apellidos", ""),
                        u.get("cedula", ""), u.get("email", ""),
                        u.get("estadoUsuario", "ACTIVO")
                    ])
        return True

    estilos = _crear_estilos(Font, PatternFill, Alignment, Border, Side)
    wb = openpyxl.Workbook()
    ws = wb.active
    es_docente = (tipo == "docente" or tipo == "docentes")
    ws.title = "Docentes" if es_docente else "Estudiantes"
    
    subtitulo = (
        "SISTEMA INSTITUCIONAL UPC PROCTOR · DIRECTORIO OFICIAL DE DOCENTES"
        if es_docente else
        "SISTEMA INSTITUCIONAL UPC PROCTOR · DIRECTORIO OFICIAL DE ESTUDIANTES"
    )
    
    columnas = [
        ("N°", 6),
        ("CÓDIGO INSTITUCIONAL", 24),
        ("NOMBRE COMPLETO", 30),
        ("N° DOCUMENTO / CÉDULA", 22),
        ("CORREO INSTITUCIONAL", 35),
        ("ESTADO DE CUENTA", 18),
        ("ROL EN SISTEMA" if es_docente else "MATERIAS", 18)
    ]
    
    _aplicar_cabecera_institucional(ws, "UNIVERSIDAD POPULAR DEL CESAR", subtitulo, len(usuarios or []), len(columnas), estilos, get_column_letter)
    
    # Encabezados de tabla en fila 5
    fila_header = 5
    ws.row_dimensions[fila_header].height = 26
    for c_idx, (tit, _) in enumerate(columnas, start=1):
        c = ws.cell(row=fila_header, column=c_idx, value=tit)
        c.font = estilos["fuente_header_tabla"]
        c.fill = estilos["fill_header_tabla"]
        c.alignment = estilos["align_centro"]
        c.border = estilos["borde_fino"]
        
    fila_actual = 6
    for idx, u in enumerate(usuarios or [], start=1):
        ws.row_dimensions[fila_actual].height = 20
        fill_fila = estilos["fill_zebra"] if idx % 2 == 0 else estilos["fill_blanco"]
        
        cod = str(u.get("codigoProfesor") or u.get("id") or u.get("estudianteId") or "")
        nombre_completo = u.get("nombre_completo") or f"{u.get('nombre', '')} {u.get('apellidos', '')}".strip()
        cedula = str(u.get("cedula") or "")
        email = str(u.get("emailInstitucional") or u.get("email") or "")
        estado = str(u.get("estado") or u.get("estadoUsuario") or "ACTIVO").upper()
        extra = str(u.get("rol") or ("DOCENTE" if es_docente else len(u.get("materiasInscritas") or []))).upper()
        
        datos_fila = [
            (idx, estilos["align_centro"], estilos["fuente_datos"], fill_fila),
            (cod, estilos["align_centro"], estilos["fuente_datos"], fill_fila),
            (nombre_completo, estilos["align_izq"], estilos["fuente_datos"], fill_fila),
            (cedula, estilos["align_centro"], estilos["fuente_datos"], fill_fila),
            (email, estilos["align_izq"], estilos["fuente_datos"], fill_fila),
            (f"● {estado}", estilos["align_centro"],
             estilos["fuente_estado_activo"] if estado == "ACTIVO" else estilos["fuente_estado_susp"],
             estilos["fill_badge_activo"] if estado == "ACTIVO" else estilos["fill_badge_susp"]),
            (extra, estilos["align_centro"], estilos["fuente_datos"], fill_fila),
        ]
        
        for c_idx, (val, alig, fnt, fll) in enumerate(datos_fila, start=1):
            cell = ws.cell(row=fila_actual, column=c_idx, value=val)
            cell.alignment = alig
            cell.font = fnt
            cell.fill = fll
            cell.border = estilos["borde_fino"]
            
        fila_actual += 1
        
    fin = max(fila_actual - 1, 5)
    _autoajustar_columnas(ws, columnas, 5, fin, get_column_letter)
    ws.auto_filter.ref = f"A5:G{fin}"
    
    wb.save(ruta_archivo)
    return True


def generar_excel_consolidado(ruta_archivo: str, lista_profesores: list, lista_estudiantes: list, datos_resumen: dict):
    """
    Genera un libro consolidado oficial (.xlsx) multi-hoja con:
    1. Hoja 'Resumen y Métricas': KPIs institucionales y tasas de actividad.
    2. Hoja 'Directorio Docentes': Todo el cuerpo docente registrado.
    3. Hoja 'Directorio Estudiantes': Toda la población estudiantil registrada.
    """
    openpyxl, Font, PatternFill, Alignment, Border, Side, get_column_letter = _cargar_openpyxl()
    if openpyxl is None:
        # Fallback de seguridad si openpyxl no está disponible
        return generar_excel_directorio(ruta_archivo, "docentes", lista_profesores)

    estilos = _crear_estilos(Font, PatternFill, Alignment, Border, Side)
    wb = openpyxl.Workbook()
    
    # -------------------------------------------------------------
    # HOJA 1: RESUMEN INSTITUCIONAL
    # -------------------------------------------------------------
    ws_res = wb.active
    ws_res.title = "Resumen Institucional"
    ws_res.views.sheetView[0].showGridLines = True
    
    r = datos_resumen or {}
    tp = r.get("totalProfesores", len(lista_profesores))
    ap = r.get("profesoresActivos", sum(1 for p in lista_profesores if str(p.get("estado", "")).upper() == "ACTIVO"))
    sp = max(tp - ap, 0)
    
    te = r.get("totalEstudiantes", len(lista_estudiantes))
    ae = r.get("estudiantesActivos", sum(1 for e in lista_estudiantes if str(e.get("estadoUsuario", "")).upper() == "ACTIVO"))
    se = max(te - ae, 0)
    
    tex = r.get("totalExamenes", 0)
    tasa_p = (ap / tp * 100) if tp > 0 else 100.0
    tasa_e = (ae / te * 100) if te > 0 else 100.0
    total_cuentas = tp + te
    activas_cuentas = ap + ae
    tasa_global = (activas_cuentas / total_cuentas * 100) if total_cuentas > 0 else 100.0
    
    _aplicar_cabecera_institucional(
        ws_res, "UNIVERSIDAD POPULAR DEL CESAR",
        "SISTEMA INSTITUCIONAL UPC PROCTOR · INFORME CONSOLIDADO DE GOBERNANZA",
        total_cuentas, 5, estilos, get_column_letter
    )
    
    # Tabla Resumen
    cols_res = [
        ("ESTAMENTO INSTITUCIONAL", 30),
        ("TOTAL REGISTRADOS", 20),
        ("CUENTAS ACTIVAS", 20),
        ("CUENTAS SUSPENDIDAS", 22),
        ("TASA DE ACTIVIDAD", 20)
    ]
    
    ws_res.row_dimensions[5].height = 26
    for c_idx, (tit, _) in enumerate(cols_res, start=1):
        c = ws_res.cell(row=5, column=c_idx, value=tit)
        c.font = estilos["fuente_header_tabla"]
        c.fill = estilos["fill_header_tabla"]
        c.alignment = estilos["align_centro"]
        c.border = estilos["borde_fino"]
        
    filas_res = [
        ("Personal Docente", tp, ap, sp, f"{tasa_p:.1f}%"),
        ("Estudiantes de Pregrado", te, ae, se, f"{tasa_e:.1f}%"),
        ("TOTAL INSTITUCIONAL", total_cuentas, activas_cuentas, sp + se, f"{tasa_global:.1f}%")
    ]
    
    for idx, (estam, tot, act, susp, tasa) in enumerate(filas_res, start=1):
        f = 5 + idx
        ws_res.row_dimensions[f].height = 22
        es_total = (idx == len(filas_res))
        fll = estilos["fill_zebra"] if idx % 2 == 0 and not es_total else estilos["fill_blanco"]
        fnt = estilos["fuente_datos_bold"] if es_total else estilos["fuente_datos"]
        
        datos = [
            (estam, estilos["align_izq"], fnt, fll),
            (tot, estilos["align_centro"], fnt, fll),
            (f"● {act}", estilos["align_centro"], estilos["fuente_estado_activo"], estilos["fill_badge_activo"] if not es_total else fll),
            (f"● {susp}", estilos["align_centro"], estilos["fuente_estado_susp"], estilos["fill_badge_susp"] if not es_total else fll),
            (tasa, estilos["align_centro"], fnt, fll),
        ]
        for c_idx, (val, alig, font_c, fill_c) in enumerate(datos, start=1):
            cell = ws_res.cell(row=f, column=c_idx, value=val)
            cell.alignment = alig
            cell.font = font_c
            cell.fill = fill_c
            cell.border = estilos["borde_fino"]
            
    # Sección Dictamen
    f_nota = 10
    ws_res.cell(row=f_nota, column=1, value="EVALUACIONES EN PLATAFORMA:").font = estilos["fuente_datos_bold"]
    ws_res.cell(row=f_nota, column=2, value=tex).font = estilos["fuente_datos"]
    
    ws_res.cell(row=f_nota + 2, column=1, value="DICTAMEN DE AUDITORÍA Y SEGURIDAD:").font = estilos["fuente_datos_bold"]
    ws_res.merge_cells(f"A{f_nota+3}:E{f_nota+3}")
    ws_res[f"A{f_nota+3}"] = (
        "Documento oficial de control y gobernanza emitido por la Dirección de Tecnologías de la Información. "
        "Constancia válida para control de decanatura, vicerrectoría y auditorías técnicas."
    )
    ws_res[f"A{f_nota+3}"].font = estilos["fuente_meta"]
    ws_res[f"A{f_nota+3}"].alignment = estilos["align_izq"]
    
    _autoajustar_columnas(ws_res, cols_res, 5, 8, get_column_letter)
    
    # -------------------------------------------------------------
    # HOJA 2: DIRECTORIO DOCENTES
    # -------------------------------------------------------------
    ws_doc = wb.create_sheet(title="Directorio Docentes")
    ws_doc.views.sheetView[0].showGridLines = True
    
    cols_doc = [
        ("N°", 6),
        ("CÓDIGO DOCENTE", 24),
        ("NOMBRE COMPLETO", 30),
        ("CÉDULA", 20),
        ("CORREO INSTITUCIONAL", 35),
        ("ESTADO", 18),
        ("ROL", 16)
    ]
    _aplicar_cabecera_institucional(
        ws_doc, "UNIVERSIDAD POPULAR DEL CESAR",
        "SISTEMA INSTITUCIONAL UPC PROCTOR · PADRÓN DOCENTE",
        len(lista_profesores), len(cols_doc), estilos, get_column_letter
    )
    ws_doc.row_dimensions[5].height = 26
    for c_idx, (tit, _) in enumerate(cols_doc, start=1):
        c = ws_doc.cell(row=5, column=c_idx, value=tit)
        c.font = estilos["fuente_header_tabla"]
        c.fill = estilos["fill_header_tabla"]
        c.alignment = estilos["align_centro"]
        c.border = estilos["borde_fino"]
        
    f_doc = 6
    for idx, p in enumerate(lista_profesores, start=1):
        ws_doc.row_dimensions[f_doc].height = 20
        fill_fila = estilos["fill_zebra"] if idx % 2 == 0 else estilos["fill_blanco"]
        cod = str(p.get("codigoProfesor") or p.get("id") or "")
        nom = f"{p.get('nombre', '')} {p.get('apellidos', '')}".strip()
        ced = str(p.get("cedula") or "")
        em = str(p.get("emailInstitucional") or p.get("email") or "")
        est = str(p.get("estado") or "ACTIVO").upper()
        rol = str(p.get("rol") or "PROFESOR").upper()
        
        datos = [
            (idx, estilos["align_centro"], estilos["fuente_datos"], fill_fila),
            (cod, estilos["align_centro"], estilos["fuente_datos"], fill_fila),
            (nom, estilos["align_izq"], estilos["fuente_datos"], fill_fila),
            (ced, estilos["align_centro"], estilos["fuente_datos"], fill_fila),
            (em, estilos["align_izq"], estilos["fuente_datos"], fill_fila),
            (f"● {est}", estilos["align_centro"],
             estilos["fuente_estado_activo"] if est == "ACTIVO" else estilos["fuente_estado_susp"],
             estilos["fill_badge_activo"] if est == "ACTIVO" else estilos["fill_badge_susp"]),
            (rol, estilos["align_centro"], estilos["fuente_datos"], fill_fila)
        ]
        for c_idx, (val, alig, fnt, fll) in enumerate(datos, start=1):
            cell = ws_doc.cell(row=f_doc, column=c_idx, value=val)
            cell.alignment = alig
            cell.font = fnt
            cell.fill = fll
            cell.border = estilos["borde_fino"]
        f_doc += 1
        
    fin_doc = max(f_doc - 1, 5)
    _autoajustar_columnas(ws_doc, cols_doc, 5, fin_doc, get_column_letter)
    ws_doc.auto_filter.ref = f"A5:G{fin_doc}"
    
    # -------------------------------------------------------------
    # HOJA 3: DIRECTORIO ESTUDIANTES
    # -------------------------------------------------------------
    ws_est = wb.create_sheet(title="Directorio Estudiantes")
    ws_est.views.sheetView[0].showGridLines = True
    
    cols_est = [
        ("N°", 6),
        ("CÓDIGO ESTUDIANTE", 24),
        ("NOMBRE COMPLETO", 30),
        ("CÉDULA", 20),
        ("CORREO INSTITUCIONAL", 35),
        ("ESTADO", 18),
        ("MATERIAS INSCRITAS", 20)
    ]
    _aplicar_cabecera_institucional(
        ws_est, "UNIVERSIDAD POPULAR DEL CESAR",
        "SISTEMA INSTITUCIONAL UPC PROCTOR · PADRÓN ESTUDIANTIL",
        len(lista_estudiantes), len(cols_est), estilos, get_column_letter
    )
    ws_est.row_dimensions[5].height = 26
    for c_idx, (tit, _) in enumerate(cols_est, start=1):
        c = ws_est.cell(row=5, column=c_idx, value=tit)
        c.font = estilos["fuente_header_tabla"]
        c.fill = estilos["fill_header_tabla"]
        c.alignment = estilos["align_centro"]
        c.border = estilos["borde_fino"]
        
    f_est = 6
    for idx, e in enumerate(lista_estudiantes, start=1):
        ws_est.row_dimensions[f_est].height = 20
        fill_fila = estilos["fill_zebra"] if idx % 2 == 0 else estilos["fill_blanco"]
        cod = str(e.get("estudianteId") or e.get("id") or "")
        nom = f"{e.get('nombre', '')} {e.get('apellidos', '')}".strip()
        ced = str(e.get("cedula") or "")
        em = str(e.get("email") or "")
        est = str(e.get("estadoUsuario") or "ACTIVO").upper()
        mat = len(e.get("materiasInscritas") or [])
        
        datos = [
            (idx, estilos["align_centro"], estilos["fuente_datos"], fill_fila),
            (cod, estilos["align_centro"], estilos["fuente_datos"], fill_fila),
            (nom, estilos["align_izq"], estilos["fuente_datos"], fill_fila),
            (ced, estilos["align_centro"], estilos["fuente_datos"], fill_fila),
            (em, estilos["align_izq"], estilos["fuente_datos"], fill_fila),
            (f"● {est}", estilos["align_centro"],
             estilos["fuente_estado_activo"] if est == "ACTIVO" else estilos["fuente_estado_susp"],
             estilos["fill_badge_activo"] if est == "ACTIVO" else estilos["fill_badge_susp"]),
            (mat, estilos["align_centro"], estilos["fuente_datos"], fill_fila)
        ]
        for c_idx, (val, alig, fnt, fll) in enumerate(datos, start=1):
            cell = ws_est.cell(row=f_est, column=c_idx, value=val)
            cell.alignment = alig
            cell.font = fnt
            cell.fill = fll
            cell.border = estilos["borde_fino"]
        f_est += 1
        
    fin_est = max(f_est - 1, 5)
    _autoajustar_columnas(ws_est, cols_est, 5, fin_est, get_column_letter)
    ws_est.auto_filter.ref = f"A5:G{fin_est}"
    
    wb.save(ruta_archivo)
    return True
