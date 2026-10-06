# vista/modal_registro_biometrico.py
"""
Modal de Registro Biométrico Inicial con Óvalo Facial y Detección en Tiempo Real.
Estilo sobrio, elegante e institucional con la paleta de colores de la UPC.
"""

import os
import sys
import time
import json
import cv2
import numpy as np

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QWidget, QProgressBar, QMessageBox, QFrame
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QRectF, QPointF
from PyQt6.QtGui import (
    QImage, QPixmap, QPainter, QPen, QBrush,
    QColor, QPainterPath, QFont, QIcon
)

from motor_ia.biometria_facial import biometria_motor


class HiloCamaraRegistro(QThread):
    """
    Hilo dedicado para captura continua de la cámara a 30 FPS.
    Mantiene encendido el hardware de la cámara y el LED indicador durante el registro.
    """
    senal_frame = pyqtSignal(np.ndarray)
    senal_error = pyqtSignal(str)

    def __init__(self, indice_camara=0):
        super().__init__()
        self.indice_camara = indice_camara
        self.activo = True
        self.cap = None

    def run(self):
        # Usar DirectShow en Windows para activación instantánea
        self.cap = cv2.VideoCapture(self.indice_camara, cv2.CAP_DSHOW)
        if not self.cap.isOpened():
            # Fallback a captura estándar
            self.cap = cv2.VideoCapture(self.indice_camara)
            
        if not self.cap.isOpened():
            self.senal_error.emit("No se pudo acceder a la cámara web. Verifica que no esté en uso por otra aplicación.")
            return

        # Configurar resolución recomendada para biometría
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

        while self.activo:
            ret, frame = self.cap.read()
            if ret and frame is not None:
                self.senal_frame.emit(frame)
            else:
                time.sleep(0.02)
            time.sleep(0.03)  # ~30 FPS

        if self.cap:
            self.cap.release()
            self.cap = None

    def detener(self):
        self.activo = False
        self.wait(1500)
        if self.cap:
            try:
                self.cap.release()
            except Exception:
                pass


class VisorCamaraOvalo(QWidget):
    """
    Widget visualizador del flujo de video en vivo con máscara de óvalo central,
    efecto de velo translúcido sobrio y borde dinámico institucional (Rojo / Verde UPC).
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(480, 360)
        self.frame_actual = None
        self.es_optimo = False
        self.progreso_captura = 0.0  # 0.0 a 1.0
        self.flash_activo = False

    def actualizar_frame(self, frame_bgr):
        self.frame_actual = frame_bgr
        self.update()

    def set_estado(self, es_optimo: bool, progreso: float = 0.0, mensaje: str = ""):
        self.es_optimo = es_optimo
        self.progreso_captura = max(0.0, min(1.0, progreso))
        self.update()

    def disparar_flash(self):
        self.flash_activo = True
        self.update()
        QTimer.singleShot(150, self._apagar_flash)

    def _apagar_flash(self):
        self.flash_activo = False
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        ancho_w = self.width()
        alto_w = self.height()

        # 1. Dibujar el fotograma de la cámara (efecto espejo natural)
        if self.frame_actual is not None:
            frame_espejo = cv2.flip(self.frame_actual, 1)
            frame_rgb = cv2.cvtColor(frame_espejo, cv2.COLOR_BGR2RGB)
            h, w, ch = frame_rgb.shape
            bytes_linea = ch * w
            q_img = QImage(frame_rgb.data, w, h, bytes_linea, QImage.Format.Format_RGB888)
            
            # Escalar manteniendo proporción
            q_pixmap = QPixmap.fromImage(q_img).scaled(
                ancho_w, alto_w,
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation
            )
            dx = (ancho_w - q_pixmap.width()) // 2
            dy = (alto_w - q_pixmap.height()) // 2
            painter.drawPixmap(dx, dy, q_pixmap)
        else:
            painter.fillRect(0, 0, ancho_w, alto_w, QColor(248, 250, 252))
            painter.setPen(QColor(100, 116, 139))
            painter.setFont(QFont("Arial", 11))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "Iniciando cámara...")

        # 2. Definir geometría del óvalo central (proporción 3:4 ergonómica)
        radio_x = int(ancho_w * 0.22)
        radio_y = int(alto_w * 0.36)
        centro_x = ancho_w // 2
        centro_y = alto_w // 2

        rect_ovalo = QRectF(centro_x - radio_x, centro_y - radio_y, radio_x * 2, radio_y * 2)

        # 3. Dibujar velo translúcido elegante fuera del óvalo (velo claro sobrio)
        path_completo = QPainterPath()
        path_completo.addRect(0, 0, ancho_w, alto_w)

        path_ovalo = QPainterPath()
        path_ovalo.addEllipse(rect_ovalo)

        # Máscara exterior translúcida
        mascara_exterior = path_completo.subtracted(path_ovalo)
        painter.fillPath(mascara_exterior, QBrush(QColor(255, 255, 255, 175)))

        # 4. Dibujar borde del óvalo (Rojo sobrio vs Verde institucional UPC #196F3D)
        color_borde = QColor(25, 111, 61) if self.es_optimo else QColor(217, 83, 79)
        pen_borde = QPen(color_borde, 3)
        pen_borde.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen_borde)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(rect_ovalo)

        # 5. Dibujar anillo de progreso exterior cuando está en cuenta regresiva
        if self.es_optimo and self.progreso_captura > 0.0:
            rect_anillo = rect_ovalo.adjusted(-7, -7, 7, 7)
            pen_anillo = QPen(QColor(25, 111, 61, 230), 4)
            pen_anillo.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(pen_anillo)
            angulo_inicio = 90 * 16  # Empezar en la parte superior
            angulo_extension = -int(self.progreso_captura * 360 * 16)
            painter.drawArc(rect_anillo, angulo_inicio, angulo_extension)

        # 6. Borde exterior general de la tarjeta de video
        painter.setPen(QPen(QColor(226, 232, 240), 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(0, 0, ancho_w - 1, alto_w - 1)

        # 7. Destello visual de confirmación de captura
        if self.flash_activo:
            painter.fillRect(0, 0, ancho_w, alto_w, QColor(255, 255, 255, 220))


class ModalRegistroBiometrico(QDialog):
    """
    Diálogo modal de registro biométrico facial inicial para estudiantes.
    Diseño sobrio, elegante y blanco con la identidad visual de la UPC.
    """
    def __init__(self, correo_estudiante: str, parent=None):
        super().__init__(parent)
        self.correo_estudiante = correo_estudiante
        self.correo_limpio = correo_estudiante.replace("@", "_").replace(".", "_")
        
        # Resultados de la captura
        self.embedding_capturado = None
        self.frame_capturado = None
        self.registro_exitoso = False

        # Variables de evaluación y estabilidad
        self.tiempo_inicio_optimo = None
        self.TIEMPO_REQUERIDO_ESTABLE = 1.8  # Segundos seguidos en posición óptima
        self.contador_evaluacion = 0
        self.ultimo_frame_raw = None
        self.evaluando_ia = False

        self._configurar_interfaz()
        self._iniciar_camara()

    def _configurar_interfaz(self):
        self.setWindowTitle("UPC SecureExam - Registro Biométrico Facial")
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        ruta_ico = os.path.join(base_dir, "recursos", "installer_icon.ico")
        ruta_png = os.path.join(os.path.dirname(__file__), "recursos", "logo_upc.png")
        ruta_icono = ruta_ico if os.path.exists(ruta_ico) else ruta_png
        if os.path.exists(ruta_icono):
            self.setWindowIcon(QIcon(ruta_icono))

        self.setFixedSize(580, 640)
        self.setModal(True)
        self.setStyleSheet("""
            QDialog {
                background-color: #FFFFFF;
                color: #2C3E50;
                font-family: 'Arial', 'Segoe UI', sans-serif;
            }
            QLabel {
                color: #2C3E50;
            }
        """)

        layout_principal = QVBoxLayout(self)
        layout_principal.setContentsMargins(28, 24, 28, 24)
        layout_principal.setSpacing(14)

        # Encabezado sobrio institucional
        lbl_titulo = QLabel("Calibración de Identidad Facial")
        lbl_titulo.setStyleSheet("""
            font-size: 20px; 
            font-weight: bold; 
            color: #1A252F; 
            letter-spacing: 0.3px;
        """)
        lbl_titulo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout_principal.addWidget(lbl_titulo)

        lbl_subtitulo = QLabel("Por favor, sitúa tu rostro dentro del óvalo guía con buena iluminación.")
        lbl_subtitulo.setStyleSheet("""
            font-size: 13px; 
            color: #7F8C8D;
            margin-bottom: 4px;
        """)
        lbl_subtitulo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_subtitulo.setWordWrap(True)
        layout_principal.addWidget(lbl_subtitulo)

        # Visor de la cámara con óvalo
        self.visor_camara = VisorCamaraOvalo(self)
        self.visor_camara.setFixedHeight(370)
        layout_principal.addWidget(self.visor_camara)

        # Píldora de estado / instrucciones dinámicas (sobria y clara)
        self.lbl_estado = QLabel("Alineando cámara...")
        self.lbl_estado.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_estado.setFixedHeight(40)
        self.lbl_estado.setStyleSheet("""
            background-color: #F8F9F9;
            color: #475569;
            border: 1px solid #E2E8F0;
            border-radius: 6px;
            font-size: 13px;
            font-weight: bold;
            padding: 4px 12px;
        """)
        layout_principal.addWidget(self.lbl_estado)

        # Barra de progreso institucional
        self.barra_progreso = QProgressBar(self)
        self.barra_progreso.setFixedHeight(6)
        self.barra_progreso.setTextVisible(False)
        self.barra_progreso.setStyleSheet("""
            QProgressBar {
                background-color: #E2E8F0;
                border-radius: 3px;
                border: none;
            }
            QProgressBar::chunk {
                background-color: #196F3D;
                border-radius: 3px;
            }
        """)
        self.barra_progreso.setValue(0)
        layout_principal.addWidget(self.barra_progreso)

        # Botones de acción sobrios y elegantes
        lay_botones = QHBoxLayout()
        lay_botones.setSpacing(14)

        self.btn_cancelar = QPushButton("Cancelar")
        self.btn_cancelar.setFixedHeight(42)
        self.btn_cancelar.setStyleSheet("""
            QPushButton {
                background-color: #FFFFFF;
                color: #475569;
                border: 1px solid #CBD5E1;
                border-radius: 6px;
                font-size: 14px;
                font-weight: bold;
                padding: 8px 20px;
            }
            QPushButton:hover {
                background-color: #F8FAFC;
                border-color: #94A3B8;
                color: #1E293B;
            }
        """)
        self.btn_cancelar.clicked.connect(self.cancelar_registro)
        lay_botones.addWidget(self.btn_cancelar)

        self.btn_capturar = QPushButton("Capturar Rostro")
        self.btn_capturar.setFixedHeight(42)
        self.btn_capturar.setEnabled(False)
        self.btn_capturar.setStyleSheet("""
            QPushButton {
                background-color: #196F3D;
                color: #FFFFFF;
                border: none;
                border-radius: 6px;
                font-size: 14px;
                font-weight: bold;
                padding: 8px 20px;
            }
            QPushButton:hover {
                background-color: #229954;
            }
            QPushButton:disabled {
                background-color: #E2E8F0;
                color: #94A3B8;
            }
        """)
        self.btn_capturar.clicked.connect(self._forzar_captura_manual)
        lay_botones.addWidget(self.btn_capturar)

        layout_principal.addLayout(lay_botones)

    def _iniciar_camara(self):
        self.hilo_camara = HiloCamaraRegistro(indice_camara=0)
        self.hilo_camara.senal_frame.connect(self._al_recibir_frame)
        self.hilo_camara.senal_error.connect(self._al_tener_error_camara)
        self.hilo_camara.start()

    def _al_tener_error_camara(self, error_msg):
        QMessageBox.critical(self, "Error de Cámara", error_msg)
        self.reject()

    def _al_recibir_frame(self, frame_bgr):
        if self.registro_exitoso:
            return

        self.ultimo_frame_raw = frame_bgr.copy()
        self.visor_camara.actualizar_frame(frame_bgr)

        # Evaluar IA cada 3 frames (~10 evaluaciones/segundo para mantener la GUI a 30 FPS fluidos)
        self.contador_evaluacion += 1
        if self.contador_evaluacion % 3 == 0:
            self._evaluar_rostro(frame_bgr)

    def _evaluar_geometria_ovalo(self, bbox, ancho_frame, alto_frame):
        """
        Valida que el rostro esté debidamente centrado y proporcionado.
        """
        x1, y1, x2, y2 = bbox
        cx = (x1 + x2) / 2.0
        cy = (y1 + y2) / 2.0
        ancho_rostro = x2 - x1

        centro_x = ancho_frame / 2.0
        centro_y = alto_frame / 2.0

        rx = ancho_frame * 0.22
        ry = alto_frame * 0.32

        dist_norm = ((cx - centro_x) ** 2) / (rx ** 2) + ((cy - centro_y) ** 2) / (ry ** 2)

        if dist_norm > 0.65:
            if cx < centro_x - rx * 0.4:
                return False, "Mueve tu rostro hacia la derecha"
            elif cx > centro_x + rx * 0.4:
                return False, "Mueve tu rostro hacia la izquierda"
            elif cy < centro_y - ry * 0.4:
                return False, "Baja un poco tu cabeza"
            else:
                return False, "Sube un poco tu cabeza"

        prop_ancho = ancho_rostro / float(ancho_frame)
        if prop_ancho < 0.20:
            return False, "Acércate más a la cámara"
        if prop_ancho > 0.62:
            return False, "Aléjate un poco de la cámara"

        return True, "Posición óptima"

    def _evaluar_rostro(self, frame_bgr):
        if self.evaluando_ia or self.registro_exitoso:
            return

        self.evaluando_ia = True
        try:
            h, w = frame_bgr.shape[:2]
            rostros = biometria_motor.app.get(frame_bgr)

            if not rostros or len(rostros) == 0:
                self._actualizar_estado_ui(False, 0.0, "No se detecta ningún rostro en cámara", "#FEF2F2", "#991B1B", "#FCA5A5")
                self.tiempo_inicio_optimo = None
                return

            if len(rostros) > 1:
                self._actualizar_estado_ui(False, 0.0, "Múltiples personas detectadas. Solo el estudiante debe estar presente.", "#FEF2F2", "#991B1B", "#FCA5A5")
                self.tiempo_inicio_optimo = None
                return

            principal = rostros[0]
            bbox = principal.bbox

            # 1. Evaluar si está dentro del óvalo
            dentro_ovalo, motivo_ovalo = self._evaluar_geometria_ovalo(bbox, w, h)
            if not dentro_ovalo:
                self._actualizar_estado_ui(False, 0.0, motivo_ovalo, "#FFFBEB", "#92400E", "#FDE68A")
                self.tiempo_inicio_optimo = None
                return

            # 2. Evaluar frontalidad del rostro (anti-giros)
            es_frontal, motivo_frontal = biometria_motor.es_rostro_frontal(principal)
            if not es_frontal:
                self._actualizar_estado_ui(False, 0.0, motivo_frontal, "#FFFBEB", "#92400E", "#FDE68A")
                self.tiempo_inicio_optimo = None
                return

            # 3. ¡Rostro en estado 100% óptimo!
            ahora = time.time()
            if self.tiempo_inicio_optimo is None:
                self.tiempo_inicio_optimo = ahora

            tiempo_transcurrido = ahora - self.tiempo_inicio_optimo
            progreso = min(1.0, tiempo_transcurrido / self.TIEMPO_REQUERIDO_ESTABLE)

            tiempo_restante = max(0.0, self.TIEMPO_REQUERIDO_ESTABLE - tiempo_transcurrido)
            if tiempo_restante > 0.05:
                mensaje = f"Posición óptima. Mantén la postura ({tiempo_restante:.1f}s)..."
            else:
                mensaje = "Capturando rostro base..."

            self._actualizar_estado_ui(True, progreso, mensaje, "#F0FDF4", "#166534", "#86EFAC")

            # Habilitar botón manual
            self.btn_capturar.setEnabled(True)

            # Auto-capturar cuando se cumpla el tiempo
            if progreso >= 1.0:
                self._ejecutar_captura_definitiva(frame_bgr)

        except Exception as e:
            print(f"[MODAL BIOMETRIA] Error evaluando frame: {e}")
        finally:
            self.evaluando_ia = False

    def _actualizar_estado_ui(self, es_optimo, progreso, mensaje, bg_hex, color_hex, border_hex):
        self.visor_camara.set_estado(es_optimo, progreso, mensaje)
        self.lbl_estado.setText(mensaje)
        self.lbl_estado.setStyleSheet(f"""
            background-color: {bg_hex};
            color: {color_hex};
            border: 1px solid {border_hex};
            border-radius: 6px;
            font-size: 13px;
            font-weight: bold;
            padding: 4px 12px;
        """)
        self.barra_progreso.setValue(int(progreso * 100))
        if not es_optimo:
            self.btn_capturar.setEnabled(False)

    def _forzar_captura_manual(self):
        if self.ultimo_frame_raw is not None and not self.registro_exitoso:
            self._ejecutar_captura_definitiva(self.ultimo_frame_raw)

    def _ejecutar_captura_definitiva(self, frame_bgr):
        if self.registro_exitoso:
            return
        self.registro_exitoso = True

        # Destello visual en el visor
        self.visor_camara.disparar_flash()
        self.lbl_estado.setText("Procesando embedding biométrico...")
        self.lbl_estado.setStyleSheet("background-color: #F0FDF4; color: #166534; border: 1px solid #86EFAC; border-radius: 6px; font-weight: bold;")
        self.btn_capturar.setEnabled(False)
        self.btn_cancelar.setEnabled(False)

        # Extraer embedding frontal
        emb = biometria_motor.obtener_embedding(frame_bgr, exigir_frontal=True)
        if emb is None:
            emb = biometria_motor.obtener_embedding(frame_bgr, exigir_frontal=False)

        if emb is None:
            self.registro_exitoso = False
            self.lbl_estado.setText("Error extrayendo características. Intenta de nuevo.")
            self.lbl_estado.setStyleSheet("background-color: #FEF2F2; color: #991B1B; border: 1px solid #FCA5A5; border-radius: 6px; font-weight: bold;")
            self.tiempo_inicio_optimo = None
            self.btn_cancelar.setEnabled(True)
            return

        # Guardar en disco
        if getattr(sys, 'frozen', False):
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        ruta_datos = os.path.join(base_dir, "datos_biometricos")
        os.makedirs(ruta_datos, exist_ok=True)

        ruta_emb = os.path.join(ruta_datos, f"emb_{self.correo_limpio}.json")
        ruta_foto = os.path.join(ruta_datos, f"rostro_{self.correo_limpio}.jpg")

        with open(ruta_emb, 'w', encoding='utf-8') as f:
            json.dump(emb.tolist(), f)
        cv2.imwrite(ruta_foto, frame_bgr)

        biometria_motor.ruta_emb_actual = ruta_emb
        self.embedding_capturado = emb
        self.frame_capturado = frame_bgr

        self.lbl_estado.setText("Rostro registrado con éxito. Ingresando...")
        self.lbl_estado.setStyleSheet("background-color: #DCFCE7; color: #14532D; border: 1px solid #86EFAC; border-radius: 6px; font-weight: bold;")

        # Pausar un momento para feedback positivo y cerrar
        QTimer.singleShot(900, self._finalizar_y_cerrar)

    def _finalizar_y_cerrar(self):
        self._limpiar_camara()
        self.accept()

    def cancelar_registro(self):
        self._limpiar_camara()
        self.reject()

    def _limpiar_camara(self):
        if hasattr(self, 'hilo_camara') and self.hilo_camara:
            self.hilo_camara.detener()
            self.hilo_camara = None

    def closeEvent(self, event):
        self._limpiar_camara()
        event.accept()
