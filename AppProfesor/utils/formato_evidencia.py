import os
import re

def sanitizar_texto_evidencia(texto: str) -> str:
    """
    Convierte una descripción o motivo en un texto limpio,
    legible y seguro para nombres de archivo en Windows.
    Ej: "cell phone" -> "Objeto_Sospechoso_Celular"
        "DESATENCION" -> "Desatencion_Constante"
        "Discord.exe (4521)" -> "Discord"
    """
    if not texto:
        return "sospechoso"
    
    texto_str = str(texto).strip()
    texto_lower = texto_str.lower()
    
    # Mapeo de términos frecuentes de IA a descripciones en español claras
    if "cell phone" in texto_lower or "celular" in texto_lower or "telefono" in texto_lower:
        return "Objeto_Sospechoso_Celular"
    elif "laptop" in texto_lower or "portatil" in texto_lower:
        return "Objeto_Sospechoso_Laptop"
    elif "multiple" in texto_lower and "rostro" in texto_lower:
        return "Multiples_Rostros"
    elif "camara_obstruida" in texto_lower or "obstruida" in texto_lower or "tapada" in texto_lower:
        return "Camara_Obstruida"
    elif "desatencion" in texto_lower:
        return "Desatencion_Constante"
    elif "mirada" in texto_lower:
        return "Desatencion_Mirada"
    elif "cabeza_inclinada" in texto_lower or "inclinada" in texto_lower:
        return "Desatencion_Inclinacion"
    elif "manos_no_visibles" in texto_lower:
        return "Manos_No_Visibles"
    elif "suplantacion" in texto_lower:
        return "Suplantacion_Identidad"
    elif "alt_tab" in texto_lower:
        return "Atajo_Alt_Tab"
    elif "ctrl_c" in texto_lower or "copiar" in texto_lower:
        return "Atajo_Ctrl_C"
    elif "ctrl_v" in texto_lower or "pegar" in texto_lower:
        return "Atajo_Ctrl_V"
    elif "remoto" in texto_lower or "anydesk" in texto_lower or "teamviewer" in texto_lower:
        return "Software_Control_Remoto"
    elif "admin" in texto_lower or "taskmgr" in texto_lower or "administrador" in texto_lower:
        return "Administrador_Tareas"
    elif "sesion_duplicada" in texto_lower:
        return "Sesion_Duplicada"
        
    # Limpieza estándar para nombres de proceso o textos libres
    limpio = re.sub(r'[\(\)\[\]\{\}\\\/\:\*\?\"\<\>\|]', '', texto_str)
    limpio = re.sub(r'\s+', '_', limpio.strip())
    # Remover extensiones comunes si vienen en el nombre del proceso (.exe)
    if limpio.lower().endswith(".exe"):
        limpio = limpio[:-4]
    
    # Capitalizar fragmentos para formato PascalCase / CamelCase legible
    partes = [p.capitalize() for p in limpio.split('_') if p]
    resultado = "_".join(partes)
    
    return resultado[:40] if resultado else "sospechoso"


def generar_nombre_evidencia(base_dir: str, subcarpeta: str, datos_alerta: dict, sufijo_extra: str = "", ext_archivo: str = ".webp") -> str:
    """
    Genera un nombre descriptivo y secuencial para los archivos de evidencia.
    Ejemplos:
      - 'evidenciaVision1_Desatencion_Mirada.webp'
      - 'evidenciaVision2_Objeto_Sospechoso_Celular.webp'
      - 'evidenciaVision2_Objeto_Sospechoso_Celular_pantalla.webp'
      - 'evidenciaAudio1_Voces_Multiples.wav'
      - 'evidenciaProceso1_Discord.webp'
      - 'evidenciaTeclado1_Atajo_Alt_Tab.webp'
    """
    ruta_cat = os.path.join(base_dir, subcarpeta)
    os.makedirs(ruta_cat, exist_ok=True)
    
    prefijo_map = {
        'webcam': 'Vision',
        'audio': 'Audio',
        'proceso': 'Proceso',
        'teclado': 'Teclado'
    }
    prefijo = prefijo_map.get(subcarpeta, 'General')
    
    # Extraer el motivo descriptivo
    if subcarpeta == 'webcam':
        motivo_raw = datos_alerta.get("objetoDetectado") or datos_alerta.get("tipoEvidenciaVision") or datos_alerta.get("claseAlerta") or "Vision"
    elif subcarpeta == 'audio':
        voces = datos_alerta.get("vocesDetectadas")
        if voces and int(voces) > 1:
            motivo_raw = "Voces_Multiples"
        else:
            motivo_raw = "Audio_Sospechoso"
    elif subcarpeta == 'proceso':
        motivo_raw = datos_alerta.get("nombreProceso") or datos_alerta.get("categoriaProceso") or "Proceso_No_Autorizado"
    elif subcarpeta == 'teclado':
        motivo_raw = datos_alerta.get("combinacionTeclas") or datos_alerta.get("patronSospechoso") or "Teclas_No_Permitidas"
    else:
        motivo_raw = datos_alerta.get("claseAlerta") or "Alerta"
        
    motivo_slug = sanitizar_texto_evidencia(motivo_raw)
    
    # Calcular el número secuencial dentro de esta carpeta
    # Contamos cuántos archivos de esta categoría ya existen para esta sesión
    archivos_existentes = []
    try:
        archivos_existentes = [f for f in os.listdir(ruta_cat) if os.path.isfile(os.path.join(ruta_cat, f))]
    except Exception:
        pass
        
    # Filtrar solo archivos base (excluyendo los _pantalla para no doble-contar la misma evidencia de visión)
    archivos_base = [f for f in archivos_existentes if not f.endswith("_pantalla.webp")]
    
    # Si esta alerta ya generó un archivo webcam en esta misma ronda (ej. está guardando el par webcam_pantalla),
    # debemos reutilizar el mismo número de secuencia para relacionar la webcam y la pantalla
    id_alerta = str(datos_alerta.get("idAlerta", ""))
    secuencia = len(archivos_base) + 1
    
    # Si viene con sufijo _pantalla, buscamos si hay un archivo webcam recién creado para emparejar
    if sufijo_extra == "_pantalla" and archivos_base:
        # Emparejar con el último archivo base creado
        secuencia = max(1, len(archivos_base))
        
    nombre_final = f"evidencia{prefijo}{secuencia}_{motivo_slug}{sufijo_extra}{ext_archivo}"
    return nombre_final
