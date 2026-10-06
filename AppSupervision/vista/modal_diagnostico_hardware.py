# vista/modal_diagnostico_hardware.py
"""
Modal Institucional de Diagnóstico de Dispositivos y Audio.
Verifica Cámara Web, Conexión de Red, Seguridad del Entorno y Micrófono en tiempo real.
Cierre automático cuando se confirma captación normal de audio y todo el hardware está operativo.
Diseño sobrio, institucional y desacoplado (estilos gestionados mediante QSS en tema_claro/oscuro.css).
"""

import os
import sys
import time
import numpy as np
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QProgressBar, QFrame, QSizePolicy
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QIcon, QPixmap

from motor_ia.anti_remoto import blindaje_remoto, detectar_maquina_virtual, detectar_camaras_virtuales_activas


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


class FilaDiagnostico(QFrame):
    """Componente reutilizable de diagnóstico gobernado puramente por propiedades de estilo QSS."""
    def __init__(self, titulo: str, detalle_inicial: str, parent=None):
        super().__init__(parent)
        self.setObjectName("fila_diagnostico")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 3, 0, 3)
        layout.setSpacing(2)

        top_layout = QHBoxLayout()
        top_layout.setContentsMargins(0, 0, 0, 0)

        self.lbl_titulo = QLabel(titulo)
        self.lbl_titulo.setObjectName("lbl_titulo_diagnostico")
        top_layout.addWidget(self.lbl_titulo)

        top_layout.addStretch()

        self.lbl_badge = QLabel("Comprobando...")
        self.lbl_badge.setObjectName("badge_diagnostico")
        self.lbl_badge.setProperty("estado", "pendiente")
        self.lbl_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        top_layout.addWidget(self.lbl_badge)

        layout.addLayout(top_layout)

        self.lbl_detalle = QLabel(detalle_inicial)
        self.lbl_detalle.setObjectName("lbl_detalle_diagnostico")
        self.lbl_detalle.setWordWrap(True)
        layout.addWidget(self.lbl_detalle)

    def actualizar(self, tipo_estado: str, texto_badge: str, detalle: str):
        self.lbl_badge.setText(texto_badge)
        self.lbl_badge.setProperty("estado", tipo_estado)
        self.lbl_badge.style().unpolish(self.lbl_badge)
        self.lbl_badge.style().polish(self.lbl_badge)
        self.lbl_detalle.setText(detalle)


class ModalDiagnosticoHardware(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ModalDiagnosticoHardware")
        self.setFixedSize(565, 530)
        self.setModal(True)
        self.setWindowTitle("Verificación de Dispositivos y Audio")

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
        self.audio_detectado = False
        self.conteo_frames_voz = 0
        self.completado = False
        self.hilo_audio = None
        self.procesos_bloqueantes = []

        self._construir_ui()
        self._ejecutar_diagnostico()

    def _construir_ui(self):
        layout_principal = QVBoxLayout(self)
        layout_principal.setContentsMargins(24, 20, 24, 20)
        layout_principal.setSpacing(14)

        # Encabezado institucional sobrio
        header_layout = QHBoxLayout()
        header_layout.setSpacing(12)

        logo_path = os.path.join(os.path.dirname(__file__), "recursos", "logo_upc.png")
        lbl_logo = QLabel()
        lbl_logo.setFixedSize(40, 40)
        if os.path.exists(logo_path):
            pix = QPixmap(logo_path)
            if not pix.isNull():
                lbl_logo.setPixmap(pix.scaled(40, 40, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
                lbl_logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(lbl_logo)

        titulos_layout = QVBoxLayout()
        titulos_layout.setSpacing(2)
        lbl_tit = QLabel("Diagnóstico del Sistema y Dispositivos")
        lbl_tit.setObjectName("etiqueta_titulo")
        titulos_layout.addWidget(lbl_tit)

        lbl_sub = QLabel("Comprobación técnica obligatoria antes de ingresar a la evaluación")
        lbl_sub.setObjectName("etiqueta_subtitulo")
        titulos_layout.addWidget(lbl_sub)

        header_layout.addLayout(titulos_layout)
        header_layout.addStretch()
        layout_principal.addLayout(header_layout)

        # Separador superior
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setObjectName("separador_diagnostico")
        layout_principal.addWidget(sep)

        # Panel contenedor de comprobaciones
        self.panel_diagnostico = QFrame()
        self.panel_diagnostico.setObjectName("panel_diagnostico")
        lay_panel = QVBoxLayout(self.panel_diagnostico)
        lay_panel.setContentsMargins(16, 12, 16, 14)
        lay_panel.setSpacing(10)

        # 1. Fila Cámara Web
        self.fila_camara = FilaDiagnostico("Cámara web", "Verificando disponibilidad de hardware...")
        lay_panel.addWidget(self.fila_camara)

        # 2. Fila Red & Conectividad
        self.fila_red = FilaDiagnostico("Conexión de red", "Verificando enlace directo institucional...")
        lay_panel.addWidget(self.fila_red)

        # 3. Fila Seguridad del Entorno
        self.fila_seguridad = FilaDiagnostico("Seguridad del entorno", "Comprobando procesos y monitores...")
        lay_panel.addWidget(self.fila_seguridad)

        # 4. Fila Micrófono
        self.fila_microfono = FilaDiagnostico("Micrófono", "Detectando dispositivo de entrada de audio...")
        lay_panel.addWidget(self.fila_microfono)

        # Sección de Vúmetro / Prueba de Audio
        lay_audio_test = QVBoxLayout()
        lay_audio_test.setSpacing(4)
        lay_audio_test.setContentsMargins(0, 4, 0, 0)

        top_audio = QHBoxLayout()
        lbl_audio_tit = QLabel("Nivel de entrada de audio")
        lbl_audio_tit.setObjectName("lbl_audio_tit")
        top_audio.addWidget(lbl_audio_tit)
        top_audio.addStretch()

        self.lbl_badge_audio = QLabel("En espera")
        self.lbl_badge_audio.setObjectName("badge_diagnostico")
        self.lbl_badge_audio.setProperty("estado", "pendiente")
        top_audio.addWidget(self.lbl_badge_audio)
        lay_audio_test.addLayout(top_audio)

        self.barra_vumetro = QProgressBar()
        self.barra_vumetro.setObjectName("barra_vumetro")
        self.barra_vumetro.setMinimum(0)
        self.barra_vumetro.setMaximum(100)
        self.barra_vumetro.setValue(0)
        self.barra_vumetro.setTextVisible(False)
        self.barra_vumetro.setMaximumHeight(7)
        lay_audio_test.addWidget(self.barra_vumetro)

        self.lbl_guia_audio = QLabel("Hable claramente al micrófono para confirmar la captación de audio.")
        self.lbl_guia_audio.setObjectName("lbl_guia_audio")
        lay_audio_test.addWidget(self.lbl_guia_audio)

        lay_panel.addLayout(lay_audio_test)
        layout_principal.addWidget(self.panel_diagnostico)

        # Notificación inferior de estado
        self.lbl_banner = QLabel("Comprobando requisitos técnicos...")
        self.lbl_banner.setObjectName("banner_diagnostico")
        self.lbl_banner.setProperty("estado", "espera")
        self.lbl_banner.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_banner.setWordWrap(True)
        layout_principal.addWidget(self.lbl_banner)

        # Barra de botones de acción
        self.lay_botones = QHBoxLayout()
        self.lay_botones.setSpacing(10)

        # Botón de cierre de procesos con tamaño adaptativo para evitar cualquier recorte
        self.btn_cerrar_apps = QPushButton("Cerrar programas no permitidos")
        self.btn_cerrar_apps.setObjectName("btn_cerrar_apps")
        self.btn_cerrar_apps.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_cerrar_apps.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self.btn_cerrar_apps.clicked.connect(self._cerrar_procesos_no_permitidos)
        self.btn_cerrar_apps.hide()
        self.lay_botones.addWidget(self.btn_cerrar_apps)

        self.lay_botones.addStretch()

        self.btn_reintentar = QPushButton("Reintentar comprobación")
        self.btn_reintentar.setObjectName("btn_reintentar")
        self.btn_reintentar.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_reintentar.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self.btn_reintentar.clicked.connect(self._ejecutar_diagnostico)
        self.btn_reintentar.hide()
        self.lay_botones.addWidget(self.btn_reintentar)

        self.btn_cancelar = QPushButton("Cancelar")
        self.btn_cancelar.setObjectName("btn_cancelar")
        self.btn_cancelar.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_cancelar.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self.btn_cancelar.clicked.connect(self.reject)
        self.lay_botones.addWidget(self.btn_cancelar)

        layout_principal.addLayout(self.lay_botones)

    def _actualizar_banner(self, texto: str, estado: str):
        """Actualiza el texto y la propiedad CSS del banner sin código quemado."""
        self.lbl_banner.setText(texto)
        self.lbl_banner.setProperty("estado", estado)
        self.lbl_banner.style().unpolish(self.lbl_banner)
        self.lbl_banner.style().polish(self.lbl_banner)

    def _ejecutar_diagnostico(self):
        self.completado = False
        self.audio_detectado = False
        self.conteo_frames_voz = 0
        self.procesos_bloqueantes = []
        self.btn_cerrar_apps.hide()
        self.btn_reintentar.hide()
        self.barra_vumetro.setValue(0)
        self.lbl_badge_audio.setText("En espera")
        self.lbl_badge_audio.setProperty("estado", "pendiente")
        self.lbl_badge_audio.style().unpolish(self.lbl_badge_audio)
        self.lbl_badge_audio.style().polish(self.lbl_badge_audio)

        self._actualizar_banner("Comprobando requisitos técnicos del equipo...", "espera")

        # 1. Cámara Web
        try:
            cams_v = detectar_camaras_virtuales_activas()
            if cams_v:
                self.camara_ok = False
                nombres = ", ".join([c[1] for c in cams_v])
                self.fila_camara.actualizar("error", "No autorizada", f"Software de cámara virtual activo ({nombres})")
            else:
                import cv2
                cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
                if cap.isOpened():
                    ret, _ = cap.read()
                    cap.release()
                    if ret:
                        self.camara_ok = True
                        self.fila_camara.actualizar("ok", "Operativa", "Dispositivo de video local disponible")
                    else:
                        self.camara_ok = False
                        self.fila_camara.actualizar("error", "No responde", "La cámara web local no transmite imagen")
                else:
                    self.camara_ok = False
                    self.fila_camara.actualizar("error", "No detectada", "No se detectó cámara web física conectada")
        except Exception:
            self.camara_ok = False
            self.fila_camara.actualizar("error", "Error", "Fallo al inicializar el controlador de video")

        # 2. Conexión de Red, VPN y Máquina Virtual (centralizado en motor_ia)
        es_vm = False
        motivo_vm = ""
        try:
            es_vm, motivo_vm = detectar_maquina_virtual()
        except Exception:
            pass

        vpn_activa = blindaje_remoto.es_vpn_activa()

        if es_vm:
            self.red_ok = False
            self.fila_red.actualizar("error", "No permitido", f"Entorno virtualizado detectado ({motivo_vm})")
        elif vpn_activa:
            self.red_ok = False
            self.fila_red.actualizar("error", "VPN activa", "Conexión intermedia no permitida. Desactive la VPN para continuar.")
        else:
            self.red_ok = True
            self.fila_red.actualizar("ok", "Conexión directa", "Conexión institucional directa sin intermediarios")

        # 3. Seguridad del Entorno y Procesos (UN SOLO barrido centralizado en motor_ia)
        self.seguridad_ok = True
        motivo_entorno = ""
        try:
            num_monitores = blindaje_remoto.contar_monitores()
            if num_monitores > 1:
                self.seguridad_ok = False
                motivo_entorno = f"Se detectaron {num_monitores} pantallas conectadas. Desconecte monitores extra."
            elif blindaje_remoto.es_sesion_rdp():
                self.seguridad_ok = False
                motivo_entorno = "Sesión de Escritorio Remoto (RDP) no permitida."
        except Exception:
            pass

        # Escanear procesos bloqueantes una sola vez
        procs_bloq, nombres_unicos = blindaje_remoto.escanear_procesos_bloqueantes()
        if procs_bloq:
            self.seguridad_ok = False
            self.procesos_bloqueantes = procs_bloq
            resumen_nombres = ", ".join(nombres_unicos[:3])
            if len(nombres_unicos) > 3:
                resumen_nombres += f" y {len(nombres_unicos)-3} más"
            motivo_entorno = f"Software no permitido en ejecución: {resumen_nombres}"
            self.btn_cerrar_apps.show()

        if self.seguridad_ok:
            self.fila_seguridad.actualizar("ok", "Verificado", "Sin aplicaciones remotas ni pantallas secundarias")
        else:
            self.fila_seguridad.actualizar("error", "Infracción", motivo_entorno)

        # 4. Micrófono & Audio
        if self.hilo_audio:
            self.hilo_audio.detener()
            self.hilo_audio = None

        self.hilo_audio = HiloPruebaAudio()
        self.hilo_audio.senal_estado.connect(self._al_detectar_microfono)
        self.hilo_audio.senal_nivel.connect(self._al_recibir_nivel)
        self.hilo_audio.start()

        if not (self.camara_ok and self.red_ok and self.seguridad_ok):
            self._mostrar_fallo_hardware()

    def _al_detectar_microfono(self, ok: bool, info: str):
        self.microfono_ok = ok
        if ok:
            nombre = info[:32] + "..." if len(info) > 32 else info
            self.fila_microfono.actualizar("ok", "Operativo", f"Dispositivo detectado: {nombre}")
            if self.camara_ok and self.red_ok and self.seguridad_ok:
                self._actualizar_banner("Hable claramente al micrófono para confirmar la captación de audio.", "espera")
        else:
            self.fila_microfono.actualizar("error", "No detectado", info)
            self._mostrar_fallo_hardware()

    def _al_recibir_nivel(self, nivel: int):
        self.barra_vumetro.setValue(nivel)

        if self.camara_ok and self.red_ok and self.microfono_ok and self.seguridad_ok and not self.completado:
            if nivel >= 15:
                self.conteo_frames_voz += 1
                self.lbl_badge_audio.setText("Voz detectada")
                self.lbl_badge_audio.setProperty("estado", "ok")
                self.lbl_badge_audio.style().unpolish(self.lbl_badge_audio)
                self.lbl_badge_audio.style().polish(self.lbl_badge_audio)

                if self.conteo_frames_voz >= 3:
                    self.completado = True
                    self.audio_detectado = True
                    self._actualizar_banner("Verificación técnica completada exitosamente. Ingresando a la evaluación...", "exito")
                    if self.hilo_audio:
                        self.hilo_audio.detener()
                        self.hilo_audio = None
                    QTimer.singleShot(900, self.accept)

    def _cerrar_procesos_no_permitidos(self):
        """Finaliza los procesos no autorizados y re-ejecuta la comprobación inmediatamente."""
        self.btn_cerrar_apps.setEnabled(False)
        self._actualizar_banner("Finalizando aplicaciones no autorizadas...", "aviso")

        # Sanitizar procesos a través del motor de seguridad (sin hardcoding en la vista)
        terminados = blindaje_remoto.sanitizar_aplicaciones_bloqueantes(self.procesos_bloqueantes)

        if terminados:
            resumen = ", ".join(terminados[:3])
            if len(terminados) > 3:
                resumen += f" (+{len(terminados)-3})"
            self._actualizar_banner(f"Programas cerrados ({resumen}). Re-verificando...", "aviso")
        else:
            self._actualizar_banner("No se encontraron procesos adicionales por cerrar. Re-verificando...", "aviso")

        self.btn_cerrar_apps.setEnabled(True)
        QTimer.singleShot(600, self._ejecutar_diagnostico)

    def _mostrar_fallo_hardware(self):
        self._actualizar_banner("Existen requisitos obligatorios pendientes antes de iniciar la evaluación.", "error")
        self.btn_reintentar.show()
        if self.procesos_bloqueantes:
            self.btn_cerrar_apps.show()

    def closeEvent(self, event):
        if self.hilo_audio:
            self.hilo_audio.detener()
            self.hilo_audio = None
        super().closeEvent(event)


def obtener_procesos_no_autorizados():
    """Delegador institucional hacia el motor de blindaje centralizado."""
    procs, _ = blindaje_remoto.escanear_procesos_bloqueantes()
    return procs


def terminar_procesos_no_autorizados(lista_procesos=None):
    """Delegador institucional hacia el motor de blindaje centralizado."""
    return blindaje_remoto.sanitizar_aplicaciones_bloqueantes(lista_procesos)

