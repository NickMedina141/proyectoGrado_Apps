from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush
from PyQt6.QtCore import Qt, QTimer, QRectF
import math
import random

class FaroAnimado(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(90, 40)
        
        # Estado
        self.riesgo = 0
        self.parpadeando = False
        
        # Animacion base
        self.timer_animacion = QTimer(self)
        self.timer_animacion.timeout.connect(self._actualizar_animacion)
        self.timer_animacion.start(50) # 20 FPS
        
        # Parpadeo aleatorio
        self.timer_parpadeo = QTimer(self)
        self.timer_parpadeo.timeout.connect(self._iniciar_parpadeo)
        self.timer_parpadeo.start(3000)
        
        self.apertura_ojos = 1.0 # 1.0 abierto, 0.0 cerrado
        self.desplazamiento_x = 0
        self.fase_animacion = 0.0
        
    def set_riesgo(self, nivel):
        if nivel == self.riesgo:
            return  # No cambio, no hacer nada
        self.riesgo = nivel
        self.update()
        self._emitir_pitido(nivel)

    def _emitir_pitido(self, nivel):
        """Emite un pitido proporcional al nivel de riesgo, sin bloquear la UI."""
        # Nivel 0 y 1 son tonos de verde (riesgo nulo/minimo) = Silencio para no distraer
        if nivel <= 1:
            return
            
        def _sonido_thread():
            try:
                import winsound
                import time
                if nivel == 2:
                    freq, dur, rep = 1000, 150, 2
                elif nivel == 3:
                    freq, dur, rep = 1500, 150, 3
                elif nivel == 4:
                    freq, dur, rep = 2000, 150, 4
                else:  # nivel >= 5
                    freq, dur, rep = 2500, 150, 5
                    
                for _ in range(rep):
                    winsound.Beep(freq, dur)
                    time.sleep(0.08) # Pausa corta entre pitidos
            except Exception:
                pass

        import threading
        t = threading.Thread(target=_sonido_thread, daemon=True)
        t.start()
        
    def _iniciar_parpadeo(self):
        # Si el riesgo es maximo, parpadea menos o distinto
        if random.random() < 0.7:
            self.parpadeando = True
            self.timer_parpadeo.setInterval(random.randint(2000, 5000))
            
    def _actualizar_animacion(self):
        self.fase_animacion += 0.1
        
        # Logica de parpadeo
        if self.parpadeando:
            self.apertura_ojos -= 0.3
            if self.apertura_ojos <= 0.0:
                self.apertura_ojos = 0.0
                self.parpadeando = False
        else:
            if self.apertura_ojos < 1.0:
                self.apertura_ojos += 0.15
            else:
                self.apertura_ojos = 1.0
                
        # Animacion segun riesgo
        if self.riesgo == 0:
            # Mirada tranquila (pequeño movimiento idle)
            self.desplazamiento_x = math.sin(self.fase_animacion * 0.5) * 1.5
        elif self.riesgo == 1:
            # Mirada nerviosa
            self.desplazamiento_x = math.sin(self.fase_animacion * 2.0) * 3.0
        elif self.riesgo == 2:
            # Ojos cerrandose ligeramente (sospecha)
            if self.apertura_ojos == 1.0: 
                self.apertura_ojos = 0.6
            self.desplazamiento_x = math.sin(self.fase_animacion * 3.0) * 4.0
        elif self.riesgo >= 3:
            # Temblor de enojo / advertencia
            self.desplazamiento_x = math.sin(self.fase_animacion * 5.0) * 2.0
            
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 1. Fondo (capsula)
        color_fondo = QColor("#27AE60")
        if self.riesgo == 1: color_fondo = QColor("#2ECC71")
        elif self.riesgo == 2: color_fondo = QColor("#F1C40F")
        elif self.riesgo == 3: color_fondo = QColor("#F39C12")
        elif self.riesgo == 4: color_fondo = QColor("#E67E22")
        elif self.riesgo >= 5: color_fondo = QColor("#C0392B")
            
        painter.setBrush(QBrush(color_fondo))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(self.rect(), 15, 15)
        
        # 2. Dibujar Ojos
        ancho = self.width()
        alto = self.height()
        
        centro_y = alto / 2
        centro_x_izq = ancho / 3
        centro_x_der = (ancho / 3) * 2
        
        radio_ojo_w = 8
        radio_ojo_h = 10 * self.apertura_ojos
        
        # Cambios de expresion
        if self.riesgo >= 3:
            # Ojos enojados (mas planos)
            radio_ojo_h = 4 * self.apertura_ojos
            
        if self.riesgo >= 5:
            # Ojos de 'X' (se dibujan lineas cruzadas)
            painter.setPen(QPen(Qt.GlobalColor.white, 3, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            tam_x = 5
            # Ojo izq
            painter.drawLine(int(centro_x_izq - tam_x), int(centro_y - tam_x), int(centro_x_izq + tam_x), int(centro_y + tam_x))
            painter.drawLine(int(centro_x_izq + tam_x), int(centro_y - tam_x), int(centro_x_izq - tam_x), int(centro_y + tam_x))
            # Ojo der
            painter.drawLine(int(centro_x_der - tam_x), int(centro_y - tam_x), int(centro_x_der + tam_x), int(centro_y + tam_x))
            painter.drawLine(int(centro_x_der + tam_x), int(centro_y - tam_x), int(centro_x_der - tam_x), int(centro_y + tam_x))
        else:
            # Ojos normales
            color_ojo = Qt.GlobalColor.black if self.riesgo < 4 else Qt.GlobalColor.white
            painter.setBrush(QBrush(color_ojo))
            painter.setPen(Qt.PenStyle.NoPen)
            
            # Dibujar ojo izquierdo
            rect_izq = QRectF(centro_x_izq - radio_ojo_w + self.desplazamiento_x, 
                              centro_y - radio_ojo_h, 
                              radio_ojo_w * 2, 
                              radio_ojo_h * 2)
            painter.drawEllipse(rect_izq)
            
            # Dibujar ojo derecho
            rect_der = QRectF(centro_x_der - radio_ojo_w + self.desplazamiento_x, 
                              centro_y - radio_ojo_h, 
                              radio_ojo_w * 2, 
                              radio_ojo_h * 2)
            painter.drawEllipse(rect_der)
            
        painter.end()
