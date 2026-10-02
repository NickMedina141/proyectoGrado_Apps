# publicar_parche.py
"""
Script utilitario para empaquetar parches de estabilidad de AppProfesor y AppSupervision.
Genera archivos .zip livianos (2-3 MB) listos para subir a GitHub Releases sin tocar instaladores pesados.
"""
import os
import sys
import zipfile
import subprocess
import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "actualizaciones")

def crear_zip(nombre_zip, ruta_origen, carpetas_incluir, archivos_incluir):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    ruta_zip = os.path.join(OUTPUT_DIR, nombre_zip)
    
    # Extensiones y nombres a excluir para mantener el zip ultra ligero
    excluir_ext = (".pyc", ".pyo", ".pyd", ".log", ".pt", ".caffemodel", ".task", ".exe")
    excluir_dirs = ("__pycache__", "build", "dist", "installer_output", "Lib", "Scripts")

    archivos_agregados = 0
    with zipfile.ZipFile(ruta_zip, "w", zipfile.ZIP_DEFLATED) as zipf:
        # 1. Archivos individuales en la raíz de la app
        for arch in archivos_incluir:
            path_completo = os.path.join(ruta_origen, arch)
            if os.path.exists(path_completo):
                zipf.write(path_completo, arcname=arch)
                archivos_agregados += 1

        # 2. Carpetas completas
        for carpeta in carpetas_incluir:
            path_carpeta = os.path.join(ruta_origen, carpeta)
            if not os.path.exists(path_carpeta):
                continue
            for root, dirs, files in os.walk(path_carpeta):
                dirs[:] = [d for d in dirs if d not in excluir_dirs]
                for file in files:
                    if any(file.endswith(ext) for ext in excluir_ext):
                        continue
                    full_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_path, ruta_origen)
                    zipf.write(full_path, arcname=rel_path)
                    archivos_agregados += 1

    tamano_mb = os.path.getsize(ruta_zip) / (1024 * 1024)
    print(f" -> {nombre_zip}: {tamano_mb:.2f} MB ({archivos_agregados} archivos empaquetados)")
    return ruta_zip

def main():
    print("=" * 60)
    print("   GENERADOR DE PARCHES ULTRA LIVIANOS (GITHUB RELEASES)")
    print("=" * 60)

    # 1. Empaquetar AppProfesor
    print("\n[1/2] Empaquetando AppProfesor...")
    crear_zip(
        nombre_zip="AppProfesor_patch.zip",
        ruta_origen=os.path.join(BASE_DIR, "AppProfesor"),
        carpetas_incluir=["api", "config", "utils", "vista", "recursos"],
        archivos_incluir=["main.py", "requerimientos.txt"]
    )

    # 2. Empaquetar AppSupervision
    print("\n[2/2] Empaquetando AppSupervision...")
    crear_zip(
        nombre_zip="AppSupervision_patch.zip",
        ruta_origen=os.path.join(BASE_DIR, "AppSupervision"),
        carpetas_incluir=["api", "config", "utils", "vista", "recursos", "motor_ia"],
        archivos_incluir=["main.py", "iniciar_IA.py", "launcher.py", "requirements.txt"]
    )

    print("\n" + "=" * 60)
    print("¡PARCHES GENERADOS CON EXITO EN LA CARPETA 'actualizaciones/'!")
    print("=" * 60)
    print("Pasos para publicarlo en GitHub Releases:")
    print(" 1. Entra a: https://github.com/NickMedina141/proyectoGrado_Apps/releases/new")
    print(" 2. En 'Choose a tag', escribe una etiqueta (ejemplo: v1.0.1 o parche-1)")
    print(" 3. En 'Release title', pon un título (ejemplo: Parche de Estabilidad)")
    print(" 4. Arrastra los 2 archivos que están en la carpeta 'actualizaciones/'")
    print(" 5. Haz clic en 'Publish release'")
    print("=" * 60)
    print("Cuando tu compañero abra la app, se actualizará sola en 3 segundos.\n")

if __name__ == "__main__":
    main()
