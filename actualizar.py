# actualizar.py - Acceso directo a publicar_parche.py
import subprocess
import sys
import os

if __name__ == "__main__":
    ruta_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "publicar_parche.py")
    subprocess.run([sys.executable, ruta_script])
