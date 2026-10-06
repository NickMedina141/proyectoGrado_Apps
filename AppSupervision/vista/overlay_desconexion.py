import os
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QFrame, QHBoxLayout
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont, QIcon, QPixmap

class OverlayBloqueoDesconexion(QWidget):
    """
    Overlay de Bloqueo Inmediato por Desconexión de Red.
    Cubre el contenido del examen con un fondo sutil y una tarjeta sobria,
    adaptada dinámicamente al tema Claro u Oscuro de la Universidad Popular del Cesar.
    """
    tiempo_expirado = pyqtSignal()
    limite_desconexiones_superado = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self.hide()

        # Parámetros de seguridad de red
        self.TIEMPO_MAXIMO_SEGUNDOS = 1800  # 30 minutos de gracia
        self.MAX_DESCONEXIONES_PERMITIDAS = 3
        self.tiempo_restante = self.TIEMPO_MAXIMO_SEGUNDOS
        self.contador_desconexiones = 0
        self.activo = False
        self.tema_actual = "claro"

        # Timer de 1 segundo para la cuenta regresiva
        self.timer_cuenta = QTimer(self)
        self.timer_cuenta.timeout.connect(self._actualizar_segundo)

        self._construir_ui()

        # Conectar al gestor de temas si está disponible en la jerarquía
        self._sincronizar_con_gestor_temas()

    def _sincronizar_con_gestor_temas(self):
        """Detecta el tema activo y se suscribe a los cambios reactivos de tema"""
        tema_detectado = "claro"
        try:
            if self.parent() and hasattr(self.parent(), 'app_principal') and self.parent().app_principal:
                gestor = getattr(self.parent().app_principal, 'gestor_temas', None)
                if gestor:
                    tema_detectado = getattr(gestor, 'tema_actual', 'claro')
                    gestor.tema_cambiado.connect(self.aplicar_tema)
        except Exception:
            pass
        self.aplicar_tema(tema_detectado)

    def _construir_ui(self):
        layout_principal = QVBoxLayout(self)
        layout_principal.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout_principal.setContentsMargins(40, 40, 40, 40)

        # Tarjeta central sobria institucional
        self.tarjeta = QFrame(self)
        self.tarjeta.setObjectName("tarjeta_overlay")
        self.tarjeta.setFixedWidth(620)
        
        lay_tarjeta = QVBoxLayout(self.tarjeta)
        lay_tarjeta.setSpacing(14)
        lay_tarjeta.setContentsMargins(36, 32, 36, 32)

        # 1. Cabecera Institucional (UPC)
        lay_cabecera = QVBoxLayout()
        lay_cabecera.setSpacing(2)
        lay_cabecera.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.lbl_institucion = QLabel("UNIVERSIDAD POPULAR DEL CESAR", self.tarjeta)
        self.lbl_institucion.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.lbl_subinstitucion = QLabel("Sistema de Evaluación y Supervisión Académica", self.tarjeta)
        self.lbl_subinstitucion.setAlignment(Qt.AlignmentFlag.AlignCenter)

        lay_cabecera.addWidget(self.lbl_institucion)
        lay_cabecera.addWidget(self.lbl_subinstitucion)

        # 2. Título de Advertencia Sobrio (Conexión pausada)
        self.lbl_titulo = QLabel("Conexión a internet interrumpida", self.tarjeta)
        self.lbl_titulo.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # 3. Mensaje claro, sobrio y humano
        self.lbl_mensaje = QLabel(
            "El examen se encuentra pausado temporalmente mientras se restablece tu conexión.\n"
            "Tu avance se encuentra protegido. Por favor, verifica tu red Wi-Fi o cable de red para reanudar la prueba.",
            self.tarjeta
        )
        self.lbl_mensaje.setWordWrap(True)
        self.lbl_mensaje.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # 4. Caja del Temporizador de Reconexión
        self.frame_tiempo = QFrame(self.tarjeta)
        self.frame_tiempo.setObjectName("frame_tiempo")
        lay_tiempo = QVBoxLayout(self.frame_tiempo)
        lay_tiempo.setSpacing(4)
        lay_tiempo.setContentsMargins(20, 12, 20, 12)

        self.lbl_tiempo_titulo = QLabel("TIEMPO DISPONIBLE PARA RECONEXIÓN", self.frame_tiempo)
        self.lbl_tiempo_titulo.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.lbl_reloj = QLabel("30:00", self.frame_tiempo)
        self.lbl_reloj.setAlignment(Qt.AlignmentFlag.AlignCenter)

        lay_tiempo.addWidget(self.lbl_tiempo_titulo)
        lay_tiempo.addWidget(self.lbl_reloj)

        # 5. Contador de incidentes de red
        self.lbl_contador = QLabel("Incidente de red detectado: 1 de 3 permitidos", self.tarjeta)
        self.lbl_contador.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # 6. Aviso al pie sobrio
        self.lbl_aviso = QLabel(
            "El examen se reanudará automáticamente al detectar señal de red.\n"
            "Si el tiempo límite expira o se superan los 3 incidentes, el examen se enviará de forma automática.",
            self.tarjeta
        )
        self.lbl_aviso.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Ensamblar tarjeta
        lay_tarjeta.addLayout(lay_cabecera)
        lay_tarjeta.addSpacing(4)
        lay_tarjeta.addWidget(self.lbl_titulo)
        lay_tarjeta.addWidget(self.lbl_mensaje)
        lay_tarjeta.addSpacing(2)
        lay_tarjeta.addWidget(self.frame_tiempo)
        lay_tarjeta.addWidget(self.lbl_contador)
        lay_tarjeta.addSpacing(2)
        lay_tarjeta.addWidget(self.lbl_aviso)

        layout_principal.addWidget(self.tarjeta)

    def aplicar_tema(self, tema: str = "claro"):
        """Aplica la paleta estética sobria según el tema actual (claro u oscuro)"""
        self.tema_actual = str(tema).lower()

        if self.tema_actual == "oscuro":
            # --- PALETA MODO OSCURO SOBRIO ---
            self.setStyleSheet("background-color: rgba(15, 23, 42, 220);")
            self.tarjeta.setStyleSheet("""
                QFrame#tarjeta_overlay {
                    background-color: #1E293B;
                    border: 1px solid #334155;
                    border-radius: 12px;
                }
                QFrame#tarjeta_overlay QLabel {
                    background-color: transparent;
                    border: none;
                }
            """)
            self.lbl_institucion.setStyleSheet("color: #34D399; font-size: 11px; font-weight: bold; letter-spacing: 1.2px; background-color: transparent; border: none;")
            self.lbl_subinstitucion.setStyleSheet("color: #94A3B8; font-size: 11px; background-color: transparent; border: none;")
            self.lbl_titulo.setStyleSheet("color: #F8FAFC; font-size: 21px; font-weight: bold; background-color: transparent; border: none; padding-top: 4px;")
            self.lbl_mensaje.setStyleSheet("color: #CBD5E1; font-size: 13px; line-height: 1.5; background-color: transparent; border: none; padding: 0 10px;")
            self.frame_tiempo.setStyleSheet("""
                QFrame#frame_tiempo {
                    background-color: #0F172A;
                    border: 1px solid #334155;
                    border-radius: 8px;
                }
                QFrame#frame_tiempo QLabel {
                    background-color: transparent;
                    border: none;
                }
            """)
            self.lbl_tiempo_titulo.setStyleSheet("color: #94A3B8; font-size: 11px; font-weight: bold; letter-spacing: 0.8px; background-color: transparent; border: none;")
            self.lbl_reloj.setStyleSheet("color: #F8FAFC; font-size: 36px; font-weight: bold; font-family: 'Consolas', 'Segoe UI', monospace; background-color: transparent; border: none;")
            self.lbl_contador.setStyleSheet("color: #FBBF24; font-size: 12px; font-weight: 600; background-color: transparent; border: none;")
            self.lbl_aviso.setStyleSheet("color: #64748B; font-size: 11px; line-height: 1.4; background-color: transparent; border: none;")

        else:
            # --- PALETA MODO CLARO SOBRIO INSTITUCIONAL ---
            self.setStyleSheet("background-color: rgba(15, 23, 42, 140);")
            self.tarjeta.setStyleSheet("""
                QFrame#tarjeta_overlay {
                    background-color: #FFFFFF;
                    border: 1px solid #CBD5E1;
                    border-radius: 12px;
                }
                QFrame#tarjeta_overlay QLabel {
                    background-color: transparent;
                    border: none;
                }
            """)
            self.lbl_institucion.setStyleSheet("color: #196F3D; font-size: 11px; font-weight: bold; letter-spacing: 1.2px; background-color: transparent; border: none;")
            self.lbl_subinstitucion.setStyleSheet("color: #64748B; font-size: 11px; background-color: transparent; border: none;")
            self.lbl_titulo.setStyleSheet("color: #0F172A; font-size: 21px; font-weight: bold; background-color: transparent; border: none; padding-top: 4px;")
            self.lbl_mensaje.setStyleSheet("color: #334155; font-size: 13px; line-height: 1.5; background-color: transparent; border: none; padding: 0 10px;")
            self.frame_tiempo.setStyleSheet("""
                QFrame#frame_tiempo {
                    background-color: #F8FAFC;
                    border: 1px solid #E2E8F0;
                    border-radius: 8px;
                }
                QFrame#frame_tiempo QLabel {
                    background-color: transparent;
                    border: none;
                }
            """)
            self.lbl_tiempo_titulo.setStyleSheet("color: #64748B; font-size: 11px; font-weight: bold; letter-spacing: 0.8px; background-color: transparent; border: none;")
            self.lbl_reloj.setStyleSheet("color: #0F172A; font-size: 36px; font-weight: bold; font-family: 'Consolas', 'Segoe UI', monospace; background-color: transparent; border: none;")
            self.lbl_contador.setStyleSheet("color: #B45309; font-size: 12px; font-weight: 600; background-color: transparent; border: none;")
            self.lbl_aviso.setStyleSheet("color: #64748B; font-size: 11px; line-height: 1.4; background-color: transparent; border: none;")

    def iniciar_bloqueo(self):
        """Activa el overlay, incrementa incidentes y arranca la cuenta regresiva."""
        if self.activo:
            return

        self.activo = True
        self.contador_desconexiones += 1
        self.lbl_contador.setText(f"Incidente de red detectado: {self.contador_desconexiones} de {self.MAX_DESCONEXIONES_PERMITIDAS} permitidos")

        # Verificar si excedió el límite de reincidencias
        if self.contador_desconexiones > self.MAX_DESCONEXIONES_PERMITIDAS:
            print(f"[SEGURIDAD RED] Límite de desconexiones superado ({self.contador_desconexiones}).")
            self.limite_desconexiones_superado.emit()
            return

        # Ajustar dimensiones a la ventana padre
        if self.parent():
            self.resize(self.parent().size())

        # Asegurar tema actualizado
        if self.parent() and hasattr(self.parent(), 'app_principal') and self.parent().app_principal:
            gestor = getattr(self.parent().app_principal, 'gestor_temas', None)
            if gestor:
                self.aplicar_tema(getattr(gestor, 'tema_actual', 'claro'))

        self._actualizar_etiqueta_reloj()
        self.timer_cuenta.start(1000)
        self.show()
        self.raise_()

    def restablecer_conexion(self):
        """Oculta el overlay cuando la red se recupera satisfactoriamente."""
        if not self.activo:
            return

        self.activo = False
        self.timer_cuenta.stop()
        self.hide()
        print("[SEGURIDAD RED] Conexión recuperada. Examen reanudado.")

    def _actualizar_segundo(self):
        self.tiempo_restante -= 1
        self._actualizar_etiqueta_reloj()

        if self.tiempo_restante <= 0:
            self.timer_cuenta.stop()
            print("[SEGURIDAD RED] Tiempo límite de 30 minutos sin internet expirado.")
            self.tiempo_expirado.emit()

    def _actualizar_etiqueta_reloj(self):
        minutos = max(0, self.tiempo_restante) // 60
        segundos = max(0, self.tiempo_restante) % 60
        self.lbl_reloj.setText(f"{minutos:02d}:{segundos:02d}")

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.parent():
            self.resize(self.parent().size())
