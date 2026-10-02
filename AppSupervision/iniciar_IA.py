import sys
import os

ruta_base = os.path.dirname(os.path.abspath(__file__))
venv_python = os.path.join(ruta_base, "Scripts", "python.exe")

# Si el usuario ejecuta con un Python global (ej. Python313) en lugar del venv (Python312)
if sys.executable.lower() != venv_python.lower() and os.path.exists(venv_python):
  print(f"Redirigiendo al Python del entorno virtual: {venv_python}")
  # Relanzar este mismo script pero usando el python correcto
  os.execl(venv_python, venv_python, *sys.argv)

import uvicorn
sys.path.append(ruta_base)
os.chdir(ruta_base)

if __name__ == "__main__":
  print("Iniciando el Cerebro de IA (FastAPI)...")
  print("Por favor espera a que diga 'Application startup complete'.")
  # Llama a uvicorn directamente desde código
  uvicorn.run("motor_ia.main_api:app", host="127.0.0.1", port=8005, reload=False)
