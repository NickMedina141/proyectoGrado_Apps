# utils/actualizador.py
import os
import sys
import json
import zipfile
import urllib.request
import urllib.error
import tempfile

REPO_NAME = "NickMedina141/proyectoGrado_Apps"
API_URL = f"https://api.github.com/repos/{REPO_NAME}/releases/latest"

def _leer_config_local(base_path):
    ruta = os.path.join(base_path, "config", "version.json")
    if os.path.exists(ruta):
        try:
            with open(ruta, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"app": "PanelDocente_UPC", "version": "1.0", "tag": "v1.0.0"}

def _guardar_config_local(base_path, datos):
    ruta = os.path.join(base_path, "config", "version.json")
    try:
        with open(ruta, "w", encoding="utf-8") as f:
            json.dump(datos, f, indent=2)
    except Exception:
        pass

def sincronizar_parches(nombre_app, base_path):
    """
    Verifica de forma silenciosa si existe un parche de estabilidad en GitHub Releases.
    Retorna True si se aplicó un parche (requiere reiniciar), False en caso contrario.
    """
    try:
        peticion = urllib.request.Request(
            API_URL, 
            headers={"User-Agent": "UPC-Desktop-Client", "Accept": "application/vnd.github.v3+json"}
        )
        # Timeout corto (2.0s): si no hay internet o GitHub no responde, la app abre al instante
        with urllib.request.urlopen(peticion, timeout=2.0) as respuesta:
            if respuesta.status != 200:
                return False
            datos_release = json.loads(respuesta.read().decode("utf-8"))

        tag_remoto = datos_release.get("tag_name", "")
        if not tag_remoto:
            return False

        config_local = _leer_config_local(base_path)
        tag_local = config_local.get("tag", "v1.0.0")

        # Si ya tenemos instalado este parche, continuar normalmente
        if tag_remoto == tag_local:
            return False

        # Buscar el archivo ZIP correspondiente a esta app
        assets = datos_release.get("assets", [])
        asset_encontrado = None
        claves = ["appprofesor", "paneldocente", "profesor"] if any(k in nombre_app.lower() for k in ["profesor", "panel", "docente"]) else ["appsupervision", "supervisionupc", "estudiante"]
        for asset in assets:
            nombre_asset = asset.get("name", "").lower()
            if any(c in nombre_asset for c in claves) and nombre_asset.endswith(".zip"):
                asset_encontrado = asset
                break

        if not asset_encontrado:
            return False

        url_descarga = asset_encontrado.get("browser_download_url")
        if not url_descarga:
            return False

        print(f"[ACTUALIZADOR] Sincronizando parche del sistema ({tag_remoto})...")

        # Descargar el archivo comprimido a una carpeta temporal
        with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as archivo_temp:
            ruta_temporal = archivo_temp.name

        urllib.request.urlretrieve(url_descarga, ruta_temporal)

        # Descomprimir los archivos actualizados en la raíz de la app
        with zipfile.ZipFile(ruta_temporal, "r") as zip_ref:
            carpetas_permitidas = ("api", "config", "utils", "vista", "recursos", "main.py", "requerimientos.txt", "requirements.txt")
            for miembro in zip_ref.namelist():
                if any(miembro.startswith(c) for c in carpetas_permitidas):
                    zip_ref.extract(miembro, base_path)

        try:
            os.remove(ruta_temporal)
        except Exception:
            pass

        # Instalar silenciosamente si hay nuevas librerías en requerimientos
        req_arch = "requerimientos.txt" if any(k in nombre_app.lower() for k in ["profesor", "panel", "docente"]) else "requirements.txt"
        req_path = os.path.join(base_path, req_arch)
        if os.path.exists(req_path):
            try:
                import subprocess
                subprocess.run(
                    [sys.executable, "-m", "pip", "install", "--prefer-binary", "-r", req_path, "--quiet"],
                    cwd=base_path,
                    timeout=90
                )
            except Exception as e:
                print(f"[ACTUALIZADOR] Error actualizando librerías: {e}")

        # Actualizar el registro del tag local
        config_local["tag"] = tag_remoto
        config_local["version"] = tag_remoto.lstrip("v")
        _guardar_config_local(base_path, config_local)

        print("[ACTUALIZADOR] Parche aplicado exitosamente.")
        return True

    except Exception as e:
        # Fail-Safe total: cualquier caída de red o error abre la app normal
        return False
