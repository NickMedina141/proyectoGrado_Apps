import socket
import time
from PyQt6.QtCore import QThread, pyqtSignal

class MonitorRed(QThread):
    """
    Centinela Activo de Conectividad de Red (Network Sentinel).
    Sondea la red cada 1.5 segundos mediante conexiones socket ultra-livianas (timeout < 1s).
    Detecta cortes de router, apagado de Wi-Fi o desconexión de cable en menos de 3 segundos,
    sin depender de la latencia pasiva del sistema operativo ni de sockets WebSocket colgados.
    """
    senal_estado_red = pyqtSignal(bool)  # True = Conectado, False = Desconectado

    def __init__(self, intervalo_segundos=1.5):
        super().__init__()
        self.intervalo = intervalo_segundos
        self.activo = True
        self.conectado_actual = True
        self.fallos_consecutivos = 0
        self.exitos_consecutivos = 0
        self.UMBRAL_FALLOS_DESCONEXION = 2  # 2 fallos continuos (~3.0s) confirman corte de red

    def run(self):
        while self.activo:
            hay_red = self._verificar_acceso_red()
            if hay_red:
                self.fallos_consecutivos = 0
                self.exitos_consecutivos += 1
                if not self.conectado_actual and self.exitos_consecutivos >= 1:
                    self.conectado_actual = True
                    print("[MONITOR RED] Red restablecida detectada por el centinela.")
                    self.senal_estado_red.emit(True)
            else:
                self.exitos_consecutivos = 0
                self.fallos_consecutivos += 1
                if self.conectado_actual and self.fallos_consecutivos >= self.UMBRAL_FALLOS_DESCONEXION:
                    self.conectado_actual = False
                    print(f"[MONITOR RED] Corte de red detectado tras {self.fallos_consecutivos} fallos continuos.")
                    self.senal_estado_red.emit(False)

            time.sleep(self.intervalo)

    def _verificar_acceso_red(self):
        # 1. Probar servidores DNS públicos ultra-estables (puerto 53 TCP)
        destinos = [("8.8.8.8", 53), ("1.1.1.1", 53)]
        for host, puerto in destinos:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(0.85)
                s.connect((host, puerto))
                s.close()
                return True
            except Exception:
                continue

        # 2. Respaldo: Intentar conectar directamente al host del backend configurado
        try:
            from config.configuracion import url
            from urllib.parse import urlparse
            parsed = urlparse(url)
            host = parsed.hostname
            puerto = parsed.port or (443 if parsed.scheme == "https" else 80)
            if host:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(0.95)
                s.connect((host, puerto))
                s.close()
                return True
        except Exception:
            pass

        return False

    def detener(self):
        self.activo = False
        self.wait(1200)
