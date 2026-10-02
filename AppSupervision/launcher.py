"""
Lanzador Supervision UPC (Estudiante).
Abre main.py usando el Python del venv instalado.
Los errores se guardan en AppData/SupervisionUPC/estudiante_error.log
"""
import os
import sys
import subprocess

LOCAL_APP_DATA = os.getenv('LOCALAPPDATA', os.path.expanduser('~'))
VENV_DIR = os.path.join(LOCAL_APP_DATA, "SupervisionUPC", "Estudiante_env")
VENV_PYTHON = os.path.join(VENV_DIR, "Scripts", "python.exe")
LOG_FILE = os.path.join(LOCAL_APP_DATA, "SupervisionUPC", "estudiante_error.log")

if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

main_py = os.path.join(BASE_DIR, "main.py")

if not os.path.exists(VENV_PYTHON):
    import tkinter as tk
    from tkinter import messagebox
    root = tk.Tk()
    root.withdraw()
    messagebox.showerror(
        "Instalación incompleta",
        f"No se encontró el entorno de ejecución.\n\nRuta esperada:\n{VENV_PYTHON}\n\nPor favor, reinstale la aplicación."
    )
    sys.exit(1)

if not os.path.exists(main_py):
    import tkinter as tk
    from tkinter import messagebox
    root = tk.Tk()
    root.withdraw()
    messagebox.showerror(
        "Archivo no encontrado",
        f"No se encontró main.py en:\n{main_py}\n\nPor favor, reinstale la aplicación."
    )
    sys.exit(1)

# Entorno limpio para evitar conflictos con PyInstaller
env = os.environ.copy()
env.pop("PYTHONPATH", None)
env.pop("PYTHONHOME", None)
env.pop("_MEIPASS2", None)
env.pop("PYTHONEXECUTABLE", None)

try:
    with open(LOG_FILE, "w", encoding="utf-8") as log:
        log.write(f"BASE_DIR: {BASE_DIR}\n")
        log.write(f"VENV_PYTHON: {VENV_PYTHON}\n")
        log.write(f"main_py: {main_py}\n")
        log.write(f"VENV_PYTHON exists: {os.path.exists(VENV_PYTHON)}\n")
        log.write(f"main_py exists: {os.path.exists(main_py)}\n")
        log.write("--- Iniciando aplicacion ---\n")
        log.flush()
        cmd = [VENV_PYTHON, main_py] + sys.argv[1:]
        subprocess.Popen(
            cmd,
            cwd=BASE_DIR,
            stdout=log,
            stderr=log,
            env=env,
            creationflags=0x08000000  # CREATE_NO_WINDOW
        )
except Exception as e:
    import tkinter as tk
    from tkinter import messagebox
    root = tk.Tk()
    root.withdraw()
    messagebox.showerror("Error al iniciar", f"No se pudo iniciar la aplicación:\n\n{e}")
