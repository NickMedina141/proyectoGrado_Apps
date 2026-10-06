"""
Watchdog de Seguridad y Resiliencia para UPC SecureExam.
Se ejecuta como proceso supervisor independiente.
Monitorea la existencia del PID principal de la aplicación.
Si la aplicación es cerrada forzadamente (Task Manager, taskkill, etc.):
1. Captura evidencia fotográfica del escritorio en ese instante.
2. Envía alerta crítica inmediata al backend (APP_TERMINADA).
3. Marca la sesión en el servidor como INTERRUMPIDA.
4. Relanza la aplicación mostrando la pantalla de bloqueo de sesión interrumpida.
"""

import sys
import os
import time
import io
import base64
import subprocess
import psutil
from PIL import ImageGrab
import httpx

# Asegurar path
app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if app_dir not in sys.path:
    sys.path.insert(0, app_dir)

from config.configuracion import url_supervision_base, url_login_estudiante, AES_SECRET_KEY


def capturar_pantalla_b64():
    try:
        captura = ImageGrab.grab(all_screens=True)
        buffer = io.BytesIO()
        captura.save(buffer, format="WEBP", quality=45)
        return base64.b64encode(buffer.getvalue()).decode('utf-8')
    except Exception:
        return None


def notificar_cierre_abrupto(sesion_id: str, parent_pid: int, token: str = ""):
    print(f"[WATCHDOG] ¡ALERTA! El proceso principal (PID {parent_pid}) finalizó de forma inesperada.")
    img_b64 = capturar_pantalla_b64()

    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    cliente = httpx.Client(timeout=8.0)

    # 1. Enviar alerta crítica al profesor
    try:
        from cryptography.fernet import Fernet
        f_crypto = Fernet(AES_SECRET_KEY)
        img_cifrada = f_crypto.encrypt(img_b64.encode('utf-8')).decode('utf-8') if img_b64 else None
    except Exception:
        img_cifrada = img_b64

    alerta_payload = {
        "claseAlerta": "APP_TERMINADA",
        "nivelRiesgo": "CRITICO",
        "pidProceso": parent_pid,
        "nombreProceso": "CIERRE_FORZADO_APLICACION",
        "categoriaProceso": "CONTROL_REMOTO",
        "accionTomada": "BLOQUEADO",
        "urlCapturaPantalla": img_cifrada
    }

    try:
        url_alerta = f"{url_supervision_base}/{sesion_id}/alerta"
        cliente.post(url_alerta, json=alerta_payload, headers=headers)
        print("[WATCHDOG] Evidencia de cierre abrupto enviada al servidor.")
    except Exception as e:
        print(f"[WATCHDOG] Error enviando alerta de cierre: {e}")

    # 2. Interrumpir la sesión en el servidor
    try:
        url_interrumpir = f"{url_supervision_base}/{sesion_id}/interrumpir"
        cliente.post(url_interrumpir, params={"motivo": f"Proceso {parent_pid} terminado abruptamente"}, headers=headers)
        print("[WATCHDOG] Sesión marcada como INTERRUMPIDA en el servidor.")
    except Exception as e:
        print(f"[WATCHDOG] Error marcando sesión interrumpida: {e}")


def vigilar_proceso(parent_pid: int, sesion_id: str, ruta_bandera_limpia: str, token: str = ""):
    print(f"[WATCHDOG] Iniciando supervisión para PID {parent_pid}, Sesión: {sesion_id}")

    while True:
        # Si la bandera limpia existe, significa que el usuario salió legítimamente por el botón del examen
        if os.path.exists(ruta_bandera_limpia):
            print("[WATCHDOG] Salida limpia confirmada por usuario. Finalizando watchdog sin alertas.")
            try:
                os.remove(ruta_bandera_limpia)
            except Exception:
                pass
            sys.exit(0)

        # Verificar si el proceso principal sigue vivo
        if not psutil.pid_exists(parent_pid):
            # Proceso murió sin bandera limpia -> Cierre abrupto
            notificar_cierre_abrupto(sesion_id, parent_pid, token)

            # Relanzar main.py para bloquear la pantalla nuevamente
            try:
                main_py = os.path.join(app_dir, "main.py")
                python_exe = sys.executable
                subprocess.Popen([python_exe, main_py, "--interrumpido"], cwd=app_dir)
                print("[WATCHDOG] Aplicación relanzada en modo de recuperación.")
            except Exception as e:
                print(f"[WATCHDOG] Error al relanzar aplicación: {e}")

            sys.exit(0)

        # Chequear cada 1 segundo
        time.sleep(1.0)


if __name__ == "__main__":
    if len(sys.argv) >= 4:
        pid = int(sys.argv[1])
        s_id = sys.argv[2]
        bandera = sys.argv[3]
        tok = sys.argv[4] if len(sys.argv) > 4 else ""
        vigilar_proceso(pid, s_id, bandera, tok)
    else:
        print("Uso: watchdog.py <parent_pid> <sesion_id> <ruta_bandera_limpia> [token]")
