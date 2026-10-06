# vista/modal_diagnostico_hardware.py
"""
Modal Institucional de Diagnóstico de Dispositivos y Audio.
Verifica Cámara Web, Ausencia de VPN y Micrófono en tiempo real.
Cierre automático e inteligente cuando se detecta captación normal de audio y todo el hardware está operativo.
Diseño sobrio, institucional y elegante (Universidad Popular del Cesar).
"""

import os
import sys
import time
import numpy as np
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QProgressBar, QFrame
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QIcon


class HiloPruebaAudio(QThread):
    senal_estado = pyqtSignal(bool, str)
    senal_nivel = pyqtSignal(int)

    def __init__(self):
        super().__init__()
        self.activo = True

    def run(self):
        p = None
        stream = None
        try:
            import pyaudio
            p = pyaudio.PyAudio()
            try:
                dev_info = p.get_default_input_device_info()
                nombre_dev = dev_info.get("name", "Micrófono predeterminado")
                self.senal_estado.emit(True, nombre_dev)
            except Exception:
                self.senal_estado.emit(False, "No se detectó ningún micrófono instalado.")
                return

            stream = p.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=16000,
                input=True,
                frames_per_buffer=1024
            )

            while self.activo:
                data = stream.read(1024, exception_on_overflow=False)
                audio_data = np.frombuffer(data, dtype=np.int16)
                rms = float(np.sqrt(np.mean(np.square(audio_data.astype(np.float32)))))
                nivel = int(min(100, (rms / 2500.0) * 100))
                self.senal_nivel.emit(nivel)
                time.sleep(0.04)

        except Exception as e:
            self.senal_estado.emit(False, f"Error de audio: {e}")
        finally:
            if stream:
                try:
                    stream.stop_stream()
                    stream.close()
                except Exception:
                    pass
            if p:
                try:
                    p.terminate()
                except Exception:
                    pass

    def detener(self):
        self.activo = False
        self.wait(800)


class ModalDiagnosticoHardware(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(520, 470)
        self.setModal(True)
        self.setWindowTitle("UPC SecureExam - Verificación de Hardware y Audio")

        # Ícono institucional
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        ruta_ico = os.path.join(base_dir, "recursos", "installer_icon.ico")
        ruta_png = os.path.join(os.path.dirname(__file__), "recursos", "logo_upc.png")
        ruta_icono = ruta_ico if os.path.exists(ruta_ico) else ruta_png
        if os.path.exists(ruta_icono):
            self.setWindowIcon(QIcon(ruta_icono))

        # Estados de diagnóstico
        self.camara_ok = False
        self.red_ok = False
        self.microfono_ok = False
        self.seguridad_ok = False
        self.motivo_seguridad = ""
        self.audio_detectado = False
        self.conteo_frames_voz = 0
        self.completado = False
        self.hilo_audio = None

        self._construir_ui()
        self._ejecutar_diagnostico()

    def _construir_ui(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #FFFFFF;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QFrame#card_panel {
                background-color: #F8FAFC;
                border: 1px solid #E2E8F0;
                border-radius: 8px;
                padding: 12px;
            }
            QProgressBar {
                border: 1px solid #CBD5E1;
                border-radius: 4px;
                background-color: #EDF2F7;
                height: 8px;
            }
            QProgressBar::chunk {
                background-color: #196F3D;
                border-radius: 3px;
            }
            QPushButton#btn_reintentar {
                background-color: #196F3D;
                color: #FFFFFF;
                font-weight: bold;
                font-size: 12px;
                border-radius: 6px;
                padding: 8px 18px;
                border: none;
            }
            QPushButton#btn_reintentar:hover {
                background-color: #145A32;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        # Encabezado institucional
        header_layout = QHBoxLayout()
        header_layout.setSpacing(12)

        logo_path = os.path.join(os.path.dirname(__file__), "recursos", "logo_upc.png").replace("\\", "/")
        lbl_logo = QLabel()
        lbl_logo.setFixedSize(40, 40)
        if os.path.exists(logo_path):
            lbl_logo.setStyleSheet(f"border-image: url('{logo_path}');")
        else:
            lbl_logo.setText("🏛️")
            lbl_logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(lbl_logo)

        titulos_layout = QVBoxLayout()
        titulos_layout.setSpacing(2)
        lbl_tit = QLabel("Diagnóstico de Hardware y Audio")
        lbl_tit.setStyleSheet("font-size: 15px; font-weight: bold; color: #196F3D;")
        titulos_layout.addWidget(lbl_tit)

        lbl_sub = QLabel("Comprobación previa de dispositivos para el examen")
        lbl_sub.setStyleSheet("font-size: 11px; color: #64748B;")
        titulos_layout.addWidget(lbl_sub)

        header_layout.addLayout(titulos_layout)
        header_layout.addStretch()
        layout.addLayout(header_layout)

        # Panel de dispositivos
        self.card_panel = QFrame()
        self.card_panel.setObjectName("card_panel")
        lay_card = QVBoxLayout(self.card_panel)
        lay_card.setSpacing(12)
        lay_card.setContentsMargins(14, 12, 14, 12)

        # 1. Cámara
        self.lbl_camara = QLabel("📷 Cámara Web: Verificando...")
        self.lbl_camara.setStyleSheet("font-size: 12px; color: #334155;")
        lay_card.addWidget(self.lbl_camara)

        # 2. Red & VPN
        self.lbl_red = QLabel("🌐 Conexión & Red: Verificando...")
        self.lbl_red.setStyleSheet("font-size: 12px; color: #334155;")
        lay_card.addWidget(self.lbl_red)

        # 3. Entorno Seguro (Sin AnyDesk ni pantallas extra)
        self.lbl_seguridad = QLabel("🛡️ Entorno: Verificando...")
        self.lbl_seguridad.setStyleSheet("font-size: 12px; color: #334155;")
        lay_card.addWidget(self.lbl_seguridad)

        # 4. Micrófono & Audio
        lay_mic = QVBoxLayout()
        lay_mic.setSpacing(4)
        self.lbl_microfono = QLabel("🎤 Micrófono: Verificando...")
        self.lbl_microfono.setStyleSheet("font-size: 12px; color: #334155;")
        lay_mic.addWidget(self.lbl_microfono)

        self.barra_vumetro = QProgressBar()
        self.barra_vumetro.setMinimum(0)
        self.barra_vumetro.setMaximum(100)
        self.barra_vumetro.setValue(0)
        self.barra_vumetro.setTextVisible(False)
        self.barra_vumetro.setMaximumHeight(8)
        lay_mic.addWidget(self.barra_vumetro)

        self.lbl_guia_audio = QLabel("Habla hacia el micrófono para verificar la captación de audio.")
        self.lbl_guia_audio.setStyleSheet("font-size: 11px; color: #64748B;")
        lay_mic.addWidget(self.lbl_guia_audio)

        lay_card.addLayout(lay_mic)
        layout.addWidget(self.card_panel)

        # Banner de Estado / Notificación
        self.lbl_banner = QLabel("Esperando prueba de modulación de voz...")
        self.lbl_banner.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_banner.setStyleSheet("""
            QLabel {
                background-color: #F1F5F9;
                color: #475569;
                border-radius: 6px;
                padding: 10px;
                font-size: 12px;
            }
        """)
        layout.addWidget(self.lbl_banner)

        # Caja de advertencia por falla de hardware (oculta inicialmente)
        self.lbl_aviso_fallo = QLabel(
            "⚠️ Requisitos no cumplidos: Es obligatorio disponer de cámara y micrófono funcionales.\n"
            "Si tu equipo presenta fallas de driver, acude a las salas de cómputo de la UPC."
        )
        self.lbl_aviso_fallo.setStyleSheet("""
            background-color: #FDF2E9;
            color: #C0392B;
            border: 1px solid #FADBD8;
            border-radius: 6px;
            padding: 8px;
            font-size: 11px;
        """)
        self.lbl_aviso_fallo.setWordWrap(True)
        self.lbl_aviso_fallo.hide()
        layout.addWidget(self.lbl_aviso_fallo)

        # Botón de reintento
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.btn_reintentar = QPushButton("🔄 Reintentar Diagnóstico")
        self.btn_reintentar.setObjectName("btn_reintentar")
        self.btn_reintentar.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_reintentar.clicked.connect(self._ejecutar_diagnostico)
        self.btn_reintentar.hide()
        btn_layout.addWidget(self.btn_reintentar)
        layout.addLayout(btn_layout)

    def _ejecutar_diagnostico(self):
        self.completado = False
        self.audio_detectado = False
        self.conteo_frames_voz = 0
        self.lbl_aviso_fallo.hide()
        self.btn_reintentar.hide()
        self.barra_vumetro.setValue(0)
        self.lbl_banner.setText("Comprobando dispositivos...")
        self.lbl_banner.setStyleSheet("""
            background-color: #F1F5F9;
            color: #475569;
            border-radius: 6px;
            padding: 10px;
            font-size: 12px;
        """)

        # 1. Cámara Web
        try:
            from motor_ia.anti_remoto import detectar_camaras_virtuales_activas
            cams_v = detectar_camaras_virtuales_activas()
            if cams_v:
                self.camara_ok = False
                nombres = ", ".join([c[1] for c in cams_v])
                self.lbl_camara.setText(f"📷 Cámara Web: ❌ Software virtual activo ({nombres})")
                self.lbl_camara.setStyleSheet("font-size: 12px; color: #C0392B; font-weight: bold;")
            else:
                import cv2
                cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
                if cap.isOpened():
                    ret, _ = cap.read()
                    cap.release()
                    if ret:
                        self.camara_ok = True
                        self.lbl_camara.setText("📷 Cámara Web: ✓ Detectada y operativa")
                        self.lbl_camara.setStyleSheet("font-size: 12px; color: #196F3D; font-weight: bold;")
                    else:
                        self.camara_ok = False
                        self.lbl_camara.setText("📷 Cámara Web: ❌ No responde")
                        self.lbl_camara.setStyleSheet("font-size: 12px; color: #C0392B; font-weight: bold;")
                else:
                    self.camara_ok = False
                    self.lbl_camara.setText("📷 Cámara Web: ❌ No detectada o bloqueada")
                    self.lbl_camara.setStyleSheet("font-size: 12px; color: #C0392B; font-weight: bold;")
        except Exception:
            self.camara_ok = False
            self.lbl_camara.setText("📷 Cámara Web: ❌ Error al inicializar")
            self.lbl_camara.setStyleSheet("font-size: 12px; color: #C0392B; font-weight: bold;")

        # 2. Conexión & VPN & Máquina Virtual
        from motor_ia.anti_remoto import detectar_maquina_virtual
        es_vm, motivo_vm = detectar_maquina_virtual()

        vpn_activa = False
        interfaces_vpn = ['tun', 'tap', 'vpn', 'wireguard', 'nord', 'openvpn', 'tailscale', 'warp', 'surfshark']
        try:
            import psutil
            interfaces = psutil.net_if_addrs()
            stats = psutil.net_if_stats()
            for if_name, addrs in interfaces.items():
                if any(k in if_name.lower() for k in interfaces_vpn):
                    if if_name in stats and stats[if_name].isup:
                        vpn_activa = True
                        break
        except Exception:
            pass

        if es_vm:
            self.red_ok = False
            self.lbl_red.setText(f"🌐 Entorno: ❌ Máquina Virtual detectada ({motivo_vm})")
            self.lbl_red.setStyleSheet("font-size: 12px; color: #C0392B; font-weight: bold;")
        elif vpn_activa:
            self.red_ok = False
            self.lbl_red.setText("🌐 Red: ❌ Conexión VPN activa (Debes desactivarla)")
            self.lbl_red.setStyleSheet("font-size: 12px; color: #C0392B; font-weight: bold;")
        else:
            self.red_ok = True
            self.lbl_red.setText("🌐 Red: ✓ Conexión directa institucional (Sin VPN)")
            self.lbl_red.setStyleSheet("font-size: 12px; color: #196F3D; font-weight: bold;")

        # 3. Entorno Seguro & Control Remoto
        try:
            from motor_ia.anti_remoto import blindaje_remoto
            ok_remoto, motivo_remoto = blindaje_remoto.verificar_entorno_previo()
            if ok_remoto:
                self.seguridad_ok = True
                self.motivo_seguridad = ""
                self.lbl_seguridad.setText("🛡️ Entorno: ✓ Sin control remoto ni pantallas extra")
                self.lbl_seguridad.setStyleSheet("font-size: 12px; color: #196F3D; font-weight: bold;")
            else:
                self.seguridad_ok = False
                self.motivo_seguridad = motivo_remoto
                self.lbl_seguridad.setText(f"🛡️ Entorno: ❌ Infracción detectada")
                self.lbl_seguridad.setStyleSheet("font-size: 12px; color: #C0392B; font-weight: bold;")
        except Exception:
            self.seguridad_ok = True
            self.motivo_seguridad = ""

        # 4. Micrófono & Audio
        if self.hilo_audio:
            self.hilo_audio.detener()
            self.hilo_audio = None

        self.hilo_audio = HiloPruebaAudio()
        self.hilo_audio.senal_estado.connect(self._al_detectar_microfono)
        self.hilo_audio.senal_nivel.connect(self._al_recibir_nivel)
        self.hilo_audio.start()

        if not self.camara_ok or not self.red_ok or not self.seguridad_ok:
            self._mostrar_fallo_hardware()

    def _al_detectar_microfono(self, ok, info):
        self.microfono_ok = ok
        if ok:
            nombre = info[:25] + "..." if len(info) > 25 else info
            self.lbl_microfono.setText(f"🎤 Micrófono: ✓ Operativo ({nombre})")
            self.lbl_microfono.setStyleSheet("font-size: 12px; color: #196F3D; font-weight: bold;")
            if self.camara_ok and self.red_ok and self.seguridad_ok:
                self.lbl_banner.setText("🎤 Habla hacia el micrófono para verificar la captación...")
        else:
            self.lbl_microfono.setText(f"🎤 Micrófono: ❌ {info}")
            self.lbl_microfono.setStyleSheet("font-size: 12px; color: #C0392B; font-weight: bold;")
            self._mostrar_fallo_hardware()

    def _al_recibir_nivel(self, nivel):
        self.barra_vumetro.setValue(nivel)

        # Si todo el hardware base está OK y detectamos voz natural:
        if self.camara_ok and self.red_ok and self.microfono_ok and self.seguridad_ok and not self.completado:
            if nivel >= 15: # Modulación de voz detectada
                self.conteo_frames_voz += 1
                if self.conteo_frames_voz >= 3: # Confirmado ~0.15s de voz
                    self.completado = True
                    self.audio_detectado = True
                    self.lbl_banner.setText("✓ ¡Audio y dispositivos comprobados con éxito! Ingresando...")
                    self.lbl_banner.setStyleSheet("""
                        background-color: #E8F8F5;
                        color: #196F3D;
                        border: 1px solid #A3E4D7;
                        border-radius: 6px;
                        padding: 10px;
                        font-weight: bold;
                        font-size: 12px;
                    """)
                    if self.hilo_audio:
                        self.hilo_audio.detener()
                        self.hilo_audio = None
                    QTimer.singleShot(1100, self.accept)

    def _mostrar_fallo_hardware(self):
        self.lbl_banner.setText("❌ Fallo en requisitos obligatorios de hardware o seguridad.")
        self.lbl_banner.setStyleSheet("""
            background-color: #FDEDEC;
            color: #C0392B;
            border: 1px solid #F5B7B1;
            border-radius: 6px;
            padding: 10px;
            font-weight: bold;
            font-size: 12px;
        """)
        if getattr(self, 'motivo_seguridad', ''):
            self.lbl_aviso_fallo.setText(f"⚠️ Requisitos no cumplidos:\n{self.motivo_seguridad}")
        else:
            self.lbl_aviso_fallo.setText(
                "⚠️ Requisitos no cumplidos: Es obligatorio disponer de cámara y micrófono funcionales.\n"
                "Si tu equipo presenta fallas de driver, acude a las salas de cómputo de la UPC."
            )
        self.lbl_aviso_fallo.show()
        self.btn_reintentar.show()

    def closeEvent(self, event):
        if self.hilo_audio:
            self.hilo_audio.detener()
            self.hilo_audio = None
        super().closeEvent(event)
