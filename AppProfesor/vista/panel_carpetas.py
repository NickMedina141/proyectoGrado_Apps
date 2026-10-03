import os
import datetime
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                            QPushButton, QFrame, QGridLayout, QScrollArea, QSizePolicy, QComboBox)
from PyQt6.QtCore import Qt, QUrl, QSize, QRectF, QPointF
from PyQt6.QtGui import QFont, QColor, QPixmap, QDesktopServices, QPainter, QPen, QBrush, QPainterPath, QPolygonF, QLinearGradient

class LineaDeTiempoWidget(QWidget):
    def __init__(self, fn_abrir_categoria, fn_abrir_archivo=None):
        super().__init__()
        self.fn_abrir_categoria = fn_abrir_categoria
        self.fn_abrir_archivo = fn_abrir_archivo
        self.setMinimumHeight(300)
        self.setFixedHeight(310)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.eventos = []
        self.items_render = []
        self.hovered_idx = None
        self.hovered_card_rect = None
        self.t_min = 0
        self.t_max = 0
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
    def cargar_eventos(self, ruta_evidencias):
        self.eventos.clear()
        self.hovered_idx = None
        self.hovered_card_rect = None
        if not ruta_evidencias:
            self.update()
            return
            
        mapa_carpetas = {
            'audio': ('audio', 'Audio'),
            'proceso': ('proceso', 'Procesos y Sistema'),
            'webcam': ('webcam', 'Visión'),
            'teclado': ('teclado', 'Teclado')
        }
            
        for carpeta_id, info in mapa_carpetas.items():
            ruta_cat = os.path.join(ruta_evidencias, carpeta_id)
            if os.path.exists(ruta_cat):
                for arch in os.listdir(ruta_cat):
                    ruta_comp = os.path.join(ruta_cat, arch)
                    if os.path.isfile(ruta_comp):
                        ts = os.path.getmtime(ruta_comp)
                        motivo = info[1].upper()
                        if carpeta_id == 'webcam':
                            arch_lower = arch.lower()
                            if 'objeto' in arch_lower or 'celular' in arch_lower or 'telefono' in arch_lower or 'dispositivo' in arch_lower:
                                motivo = "OBJETO"
                            
                        self.eventos.append({
                            'time': ts,
                            'tipo': carpeta_id,
                            'titulo_cat': info[1],
                            'motivo': motivo,
                            'archivo': arch,
                            'ruta': ruta_comp
                        })
                        
        if not self.eventos:
            self.update()
            return
            
        self.eventos.sort(key=lambda x: x['time'])
        
        duracion_real = self.eventos[-1]['time'] - self.eventos[0]['time']
        padding = max(45, duracion_real * 0.08)
        self.t_min = self.eventos[0]['time'] - padding
        self.t_max = self.eventos[-1]['time'] + padding
        self.update()

    def _dibujar_bandera_3d_ribbon(self, painter, x, y, titulo, hora, es_inicio=True):
        """
        Dibuja un banderín ondeante 3D vectorial (Opción B):
        - Mástil metálico con esfera dorada/plateada en la punta.
        - Tela ondeante con corte de cola de golondrina y pliegue de sombra 3D.
        - Cápsula flotante minimalista con rótulo y hora tabular.
        """
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 1. Base / Ancla sobre el carril central
        painter.setPen(QPen(QColor('#FFFFFF'), 2))
        painter.setBrush(QBrush(QColor('#10B981' if es_inicio else '#059669')))
        painter.drawEllipse(QPointF(x, y), 6, 6)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor('#FFFFFF')))
        painter.drawEllipse(QPointF(x - 1.5, y - 1.5), 1.8, 1.8)
        
        # 2. Mástil metálico redondeado
        y_mastil_top = y - 44
        painter.setPen(QPen(QColor('#94A3B8'), 2.2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawLine(int(x), int(y - 5), int(x), int(y_mastil_top + 3))
        painter.setPen(QPen(QColor('#F1F5F9'), 1.1, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawLine(int(x - 0.5), int(y - 5), int(x - 0.5), int(y_mastil_top + 3))
        
        # 3. Pomo / Esfera en la punta superior
        grad_pomo = QLinearGradient(x - 3, y_mastil_top - 3, x + 3, y_mastil_top + 3)
        if es_inicio:
            grad_pomo.setColorAt(0.0, QColor('#FDE68A'))
            grad_pomo.setColorAt(0.5, QColor('#F59E0B'))
            grad_pomo.setColorAt(1.0, QColor('#B45309'))
        else:
            grad_pomo.setColorAt(0.0, QColor('#A7F3D0'))
            grad_pomo.setColorAt(0.5, QColor('#10B981'))
            grad_pomo.setColorAt(1.0, QColor('#047857'))
            
        painter.setPen(QPen(QColor('#78350F' if es_inicio else '#064E3B'), 0.8))
        painter.setBrush(QBrush(grad_pomo))
        painter.drawEllipse(QPointF(x, y_mastil_top), 3.5, 3.5)
        
        # 4. Banderín Ondeante 3D con corte de cola de golondrina
        dir_flag = 1 if es_inicio else -1
        p_mast_top = QPointF(x, y_mastil_top + 4)
        p_mast_bot = QPointF(x, y_mastil_top + 26)
        tip_top = QPointF(x + (dir_flag * 27), y_mastil_top + 2)
        inner_notch = QPointF(x + (dir_flag * 19), y_mastil_top + 15)
        tip_bot = QPointF(x + (dir_flag * 27), y_mastil_top + 27)
        
        path_flag = QPainterPath()
        path_flag.moveTo(p_mast_top)
        path_flag.cubicTo(
            x + (dir_flag * 8), y_mastil_top + 1,
            x + (dir_flag * 17), y_mastil_top + 5,
            tip_top.x(), tip_top.y()
        )
        path_flag.lineTo(inner_notch)
        path_flag.lineTo(tip_bot)
        path_flag.cubicTo(
            x + (dir_flag * 17), y_mastil_top + 31,
            x + (dir_flag * 8), y_mastil_top + 24,
            p_mast_bot.x(), p_mast_bot.y()
        )
        path_flag.closeSubpath()
        
        # Sombra suave de la bandera
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor(15, 23, 42, 20)))
        path_sombra = QPainterPath(path_flag)
        painter.drawPath(path_sombra.translated(dir_flag * 1.5, 2.5))
        
        # Relleno con gradiente institucional
        grad_flag = QLinearGradient(p_mast_top, tip_top)
        if es_inicio:
            grad_flag.setColorAt(0.0, QColor('#059669'))
            grad_flag.setColorAt(0.4, QColor('#10B981'))
            grad_flag.setColorAt(0.7, QColor('#34D399'))
            grad_flag.setColorAt(1.0, QColor('#059669'))
        else:
            grad_flag.setColorAt(0.0, QColor('#047857'))
            grad_flag.setColorAt(0.4, QColor('#059669'))
            grad_flag.setColorAt(0.7, QColor('#10B981'))
            grad_flag.setColorAt(1.0, QColor('#065F46'))
            
        painter.setPen(QPen(QColor('#064E3B'), 1.2))
        painter.setBrush(QBrush(grad_flag))
        painter.drawPath(path_flag)
        
        # Pliegue 3D de sombra en la tela
        path_pliegue = QPainterPath()
        path_pliegue.moveTo(x + (dir_flag * 11), y_mastil_top + 3.5)
        path_pliegue.cubicTo(
            x + (dir_flag * 13), y_mastil_top + 13,
            x + (dir_flag * 9), y_mastil_top + 19,
            x + (dir_flag * 12), y_mastil_top + 26
        )
        path_pliegue.lineTo(x + (dir_flag * 16), y_mastil_top + 27)
        path_pliegue.cubicTo(
            x + (dir_flag * 13), y_mastil_top + 19,
            x + (dir_flag * 17), y_mastil_top + 13,
            x + (dir_flag * 15), y_mastil_top + 3
        )
        path_pliegue.closeSubpath()
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor(0, 0, 0, 30)))
        painter.drawPath(path_pliegue)
        
        # Brillo de cresta
        painter.setPen(QPen(QColor(255, 255, 255, 85), 1.2))
        painter.drawLine(
            int(x + (dir_flag * 6)), int(y_mastil_top + 3),
            int(x + (dir_flag * 7)), int(y_mastil_top + 25)
        )
        
        # 5. Cápsula Flotante Minimalista para Hora y Estado
        pill_w = 64
        pill_h = 32
        pill_x = x - (pill_w / 2)
        pill_y = y + 14
        rect_pill = QRectF(pill_x, pill_y, pill_w, pill_h)
        
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor(15, 23, 42, 18)))
        painter.drawRoundedRect(rect_pill.translated(0, 2), 6, 6)
        
        painter.setBrush(QBrush(QColor('#FFFFFF')))
        painter.setPen(QPen(QColor('#A7F3D0' if es_inicio else '#BAE6FD'), 1.2))
        painter.drawRoundedRect(rect_pill, 6, 6)
        
        font_rot = QFont('Segoe UI', 7, QFont.Weight.Bold)
        font_rot.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 0.5)
        painter.setFont(font_rot)
        painter.setPen(QColor('#059669' if es_inicio else '#0284C7'))
        rect_txt_rot = QRectF(pill_x, pill_y + 3, pill_w, 12)
        painter.drawText(rect_txt_rot, Qt.AlignmentFlag.AlignCenter, titulo.upper())
        
        font_hr = QFont('Segoe UI', 8, QFont.Weight.Bold)
        painter.setFont(font_hr)
        painter.setPen(QColor('#0F172A'))
        rect_txt_hr = QRectF(pill_x, pill_y + 15, pill_w, 14)
        painter.drawText(rect_txt_hr, Qt.AlignmentFlag.AlignCenter, hora)
        
        painter.restore()

    def _dibujar_vector_icono(self, painter, tipo, motivo, x, y, size, color):
        """Dibuja iconos vectoriales puros garantizando nitidez sin depender de fuentes emoji"""
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(color, 1.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        s = size / 2.0

        if tipo == 'webcam' and motivo == 'OBJETO':
            # Celular / Smartphone
            rect = QRectF(x - s * 0.5, y - s * 0.85, s * 1.0, s * 1.7)
            painter.drawRoundedRect(rect, 2.5, 2.5)
            painter.drawLine(int(x - s * 0.3), int(y - s * 0.5), int(x + s * 0.3), int(y - s * 0.5))
            painter.drawPoint(QPointF(x, y + s * 0.55))
        elif tipo == 'webcam':
            # Ojo y pupila
            path = QPainterPath()
            path.moveTo(x - s, y)
            path.quadTo(x, y - s * 0.8, x + s, y)
            path.quadTo(x, y + s * 0.8, x - s, y)
            painter.drawPath(path)
            painter.setBrush(QBrush(color))
            painter.drawEllipse(QPointF(x, y), s * 0.35, s * 0.35)
        elif tipo == 'proceso':
            # Monitor / Ventana de sistema
            rect = QRectF(x - s * 0.85, y - s * 0.7, s * 1.7, s * 1.4)
            painter.drawRoundedRect(rect, 2, 2)
            painter.drawLine(int(x - s * 0.85), int(y - s * 0.25), int(x + s * 0.85), int(y - s * 0.25))
            painter.setBrush(QBrush(color))
            painter.drawEllipse(QPointF(x - s * 0.5, y - s * 0.45), 1.2, 1.2)
            painter.drawEllipse(QPointF(x - s * 0.2, y - s * 0.45), 1.2, 1.2)
        elif tipo == 'teclado':
            # Teclado físico
            rect = QRectF(x - s * 0.9, y - s * 0.6, s * 1.8, s * 1.2)
            painter.drawRoundedRect(rect, 2.5, 2.5)
            kw = s * 0.32
            kh = s * 0.25
            painter.drawRect(QRectF(x - s * 0.65, y - s * 0.35, kw, kh))
            painter.drawRect(QRectF(x - s * 0.16, y - s * 0.35, kw, kh))
            painter.drawRect(QRectF(x + s * 0.33, y - s * 0.35, kw, kh))
            painter.drawRect(QRectF(x - s * 0.5, y + s * 0.05, s * 1.0, kh))
        elif tipo == 'audio':
            # Micrófono
            capsule = QRectF(x - s * 0.35, y - s * 0.7, s * 0.7, s * 0.9)
            painter.setBrush(QBrush(color))
            painter.drawRoundedRect(capsule, s * 0.35, s * 0.35)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            arc = QPainterPath()
            arc.moveTo(x - s * 0.55, y - s * 0.2)
            arc.arcTo(QRectF(x - s * 0.55, y - s * 0.5, s * 1.1, s * 0.9), 180, 180)
            painter.drawPath(arc)
            painter.drawLine(int(x), int(y + s * 0.4), int(x), int(y + s * 0.7))
            painter.drawLine(int(x - s * 0.4), int(y + s * 0.7), int(x + s * 0.4), int(y + s * 0.7))
        painter.restore()

    def mouseMoveEvent(self, event):
        pos = event.position()
        nuevo_hover = None
        for it in self.items_render:
            hitbox = it.get('hitbox')
            if hitbox and hitbox.contains(pos):
                nuevo_hover = it['idx']
                break
        if nuevo_hover != self.hovered_idx:
            self.hovered_idx = nuevo_hover
            self.update()

    def leaveEvent(self, event):
        if self.hovered_idx is not None:
            self.hovered_idx = None
            self.update()

    def mousePressEvent(self, event):
        pos = event.position()
        if self.hovered_card_rect and self.hovered_card_rect.contains(pos):
            if self.hovered_idx is not None and 0 <= self.hovered_idx < len(self.eventos):
                ev = self.eventos[self.hovered_idx]
                if self.fn_abrir_archivo and ev.get('ruta') and os.path.exists(ev.get('ruta')):
                    self.fn_abrir_archivo(ev['ruta'])
                    return
                elif self.fn_abrir_categoria:
                    self.fn_abrir_categoria(ev['tipo'], ev['titulo_cat'])
                    return

        for it in self.items_render:
            hitbox = it.get('hitbox')
            if hitbox and hitbox.contains(pos):
                ev = it['ev']
                if self.fn_abrir_categoria:
                    self.fn_abrir_categoria(ev['tipo'], ev['titulo_cat'])
                return

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        
        w = self.width()
        h = self.height()
        margen_x = 85
        y_linea = h // 2
        ancho_linea = max(100, w - (margen_x * 2))
        
        if not self.eventos:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(QColor(226, 232, 240, 120)))
            painter.drawRoundedRect(QRectF(margen_x, y_linea - 3, ancho_linea, 6), 3, 3)
            font_empty = QFont('Segoe UI', 10)
            painter.setFont(font_empty)
            painter.setPen(QColor('#94A3B8'))
            msg = 'No hay evidencias ni alertas registradas en este intento.'
            fm = painter.fontMetrics()
            painter.drawText(int((w - fm.horizontalAdvance(msg)) / 2), y_linea - 15, msg)
            return
            
        duracion_total = max(1, self.t_max - self.t_min)
        
        # Track principal con glow verde sutil
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor(46, 204, 113, 35)))
        painter.drawRoundedRect(QRectF(margen_x - 3, y_linea - 5, ancho_linea + 6, 10), 5, 5)
        painter.setBrush(QBrush(QColor('#2ECC71')))
        painter.drawRoundedRect(QRectF(margen_x, y_linea - 3, ancho_linea, 6), 3, 3)
        
        # Banderas de Inicio y Fin 3D Ribbon (Opción B)
        dt_ini = datetime.datetime.fromtimestamp(self.t_min).strftime('%H:%M')
        dt_fin = datetime.datetime.fromtimestamp(self.t_max).strftime('%H:%M')
        self._dibujar_bandera_3d_ribbon(painter, margen_x, y_linea, 'Inicio', dt_ini, True)
        self._dibujar_bandera_3d_ribbon(painter, w - margen_x, y_linea, 'Fin', dt_fin, False)
        
        # Paleta y etiquetas por tipo
        config_tipo = {
            'webcam': {'color': QColor('#E11D48'), 'bg': QColor(255, 241, 242), 'borde': QColor(254, 205, 211), 'label': 'VISIÓN'},
            'objeto': {'color': QColor('#DC2626'), 'bg': QColor(254, 242, 242), 'borde': QColor(254, 202, 202), 'label': 'OBJETO'},
            'proceso': {'color': QColor('#0284C7'), 'bg': QColor(240, 249, 255), 'borde': QColor(186, 230, 253), 'label': 'PROCESOS'},
            'teclado': {'color': QColor('#7C3AED'), 'bg': QColor(245, 243, 255), 'borde': QColor(221, 214, 254), 'label': 'TECLADO'},
            'audio': {'color': QColor('#D97706'), 'bg': QColor(254, 243, 199), 'borde': QColor(253, 230, 138), 'label': 'AUDIO'}
        }
        
        # --- ALGORITMO MEJORADO: SMART BALANCING + TIER ESCALATION ---
        top_items = []
        bot_items = []
        last_top_x = -9999
        last_bot_x = -9999
        last_dir = -1
        
        for i, ev in enumerate(self.eventos):
            pct = (ev['time'] - self.t_min) / duracion_total
            xr = margen_x + int(pct * ancho_linea)
            
            dist_top = xr - last_top_x
            dist_bot = xr - last_bot_x
            
            UMBRAL = 64
            if dist_top >= UMBRAL and dist_bot >= UMBRAL:
                dir_y = -last_dir
            elif dist_top >= UMBRAL and dist_bot < UMBRAL:
                dir_y = -1
            elif dist_bot >= UMBRAL and dist_top < UMBRAL:
                dir_y = 1
            else:
                dir_y = -1 if dist_top >= dist_bot else 1
                
            last_dir = dir_y
            item = {
                'idx': i,
                'ev': ev,
                'x_raw': xr,
                'x_target': xr,
                'dir': dir_y,
                'tier': 0
            }
            if dir_y == -1:
                last_top_x = xr
                top_items.append(item)
            else:
                last_bot_x = xr
                bot_items.append(item)
                
        def procesar_lado(items):
            if not items:
                return
            for k in range(len(items) - 1):
                curr = items[k]
                sig = items[k + 1]
                diff = sig['x_target'] - curr['x_target']
                
                if diff < 70:
                    sig['tier'] = (curr['tier'] + 1) % 2
                    min_req = 56 if sig['tier'] != curr['tier'] else 72
                    if diff < min_req:
                        empuje = min_req - diff
                        sig['x_target'] += empuje
                        
        procesar_lado(top_items)
        procesar_lado(bot_items)
        
        todos = top_items + bot_items
        todos.sort(key=lambda x: x['idx'])
        
        # Limitar para que ningún nodo se salga del margen derecho
        max_x = w - margen_x - 30
        if todos and todos[-1]['x_target'] > max_x:
            overflow = todos[-1]['x_target'] - max_x
            for it in todos:
                it['x_target'] -= overflow
                
        # Asignar coordenadas Y finales con 2 tiers de altura limpia
        # Tier 0 = 45px, Tier 1 = 88px
        alturas = {0: 45, 1: 88}
        for it in todos:
            h_tier = alturas.get(it['tier'], 45)
            it['y_target'] = y_linea + (h_tier * it['dir'])
            
        self.items_render = todos
        
        # 1. Dibujar Mástiles Perpendiculares (con salida vertical recta a 90°)
        for it in todos:
            ev = it['ev']
            cfg_key = 'objeto' if ev.get('motivo') == 'OBJETO' else ev['tipo']
            conf = config_tipo.get(cfg_key, config_tipo['webcam'])
            col = conf['color']
            xr = it['x_raw']
            xt = it['x_target']
            yt = it['y_target']
            d = it['dir']
            
            path = QPainterPath()
            if abs(xt - xr) <= 2:
                # Mástil 100% vertical
                path.moveTo(xr, y_linea)
                path.lineTo(xr, yt)
            else:
                # Salida vertical recta (10px), transición suave en S y entrada vertical recta (10px)
                recta_salida = d * 10
                recta_llegada = d * 10
                p_start_rect = y_linea + recta_salida
                p_end_rect = yt - recta_llegada
                
                path.moveTo(xr, y_linea)
                path.lineTo(xr, p_start_rect)
                
                mid_y = (p_start_rect + p_end_rect) / 2.0
                path.cubicTo(
                    xr, mid_y,
                    xt, mid_y,
                    xt, p_end_rect
                )
                path.lineTo(xt, yt)
                
            painter.setPen(QPen(col, 2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
            painter.drawPath(path)
            
            # Ancla sobre el carril central
            painter.setPen(QPen(QColor('#FFFFFF'), 1.8))
            painter.setBrush(QBrush(col))
            painter.drawEllipse(QPointF(xr, y_linea), 4, 4)
            
        # 2. Dibujar nodos, iconos y píldoras
        font_pill = QFont('Segoe UI', 8, QFont.Weight.Bold)
        font_hora = QFont('Segoe UI', 7, QFont.Weight.DemiBold)
        
        for it in todos:
            ev = it['ev']
            cfg_key = 'objeto' if ev.get('motivo') == 'OBJETO' else ev['tipo']
            conf = config_tipo.get(cfg_key, config_tipo['webcam'])
            col = conf['color']
            xt = it['x_target']
            yt = it['y_target']
            d = it['dir']
            is_hovered = (it['idx'] == self.hovered_idx)
            
            radio = 14 if is_hovered else 12.5
            
            if is_hovered:
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QBrush(QColor(col.red(), col.green(), col.blue(), 50)))
                painter.drawEllipse(QPointF(xt, yt), radio + 8, radio + 8)
                
            painter.setPen(QPen(col, 2.5))
            painter.setBrush(QBrush(QColor('#FFFFFF')))
            painter.drawEllipse(QPointF(xt, yt), radio, radio)
            
            self._dibujar_vector_icono(painter, ev['tipo'], ev.get('motivo', ''), xt, yt, radio * 1.35, col)
            
            texto_pill = conf['label']
            painter.setFont(font_pill)
            fm_p = painter.fontMetrics()
            ancho_p = fm_p.horizontalAdvance(texto_pill) + 16
            alto_p = 17
            
            y_pill = (yt - radio - alto_p - 4) if d == -1 else (yt + radio + 4)
            rect_pill = QRectF(xt - (ancho_p / 2), y_pill, ancho_p, alto_p)
            
            painter.setPen(QPen(conf['borde'], 1))
            painter.setBrush(QBrush(conf['bg']))
            painter.drawRoundedRect(rect_pill, 8.5, 8.5)
            
            painter.setPen(col)
            painter.drawText(rect_pill, Qt.AlignmentFlag.AlignCenter, texto_pill)
            
            hora_str = datetime.datetime.fromtimestamp(ev['time']).strftime('%H:%M:%S')
            painter.setFont(font_hora)
            fm_h = painter.fontMetrics()
            ancho_h = fm_h.horizontalAdvance(hora_str)
            y_hora = (y_pill - 2) if d == -1 else (y_pill + alto_p + 11)
            painter.setPen(QColor('#64748B'))
            painter.drawText(int(xt - (ancho_h / 2)), int(y_hora), hora_str)
            
            # Hitbox para interacción del cursor
            rect_node = QRectF(xt - radio - 2, yt - radio - 2, (radio + 2) * 2, (radio + 2) * 2)
            it['hitbox'] = rect_node.united(rect_pill)
            
        # 3. Hover Card flotante interactiva
        self.hovered_card_rect = None
        if self.hovered_idx is not None and 0 <= self.hovered_idx < len(todos):
            item_h = todos[self.hovered_idx]
            ev_h = item_h['ev']
            cfg_h = 'objeto' if ev_h.get('motivo') == 'OBJETO' else ev_h['tipo']
            conf_h = config_tipo.get(cfg_h, config_tipo['webcam'])
            col_h = conf_h['color']
            
            card_w = 236
            card_h = 70
            if item_h['x_target'] + card_w + 30 < w - 20:
                card_x = item_h['x_target'] + 22
            else:
                card_x = item_h['x_target'] - card_w - 22
                
            card_y = item_h['y_target'] - (card_h // 2)
            card_y = max(8, min(h - card_h - 8, card_y))
            rect_card = QRectF(card_x, card_y, card_w, card_h)
            self.hovered_card_rect = rect_card
            
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(QColor(15, 23, 42, 35)))
            painter.drawRoundedRect(rect_card.translated(2, 3), 8, 8)
            
            painter.setBrush(QBrush(QColor('#0F172A')))
            painter.setPen(QPen(QColor(col_h.red(), col_h.green(), col_h.blue(), 220), 1.5))
            painter.drawRoundedRect(rect_card, 8, 8)
            
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(col_h))
            painter.drawEllipse(QPointF(card_x + 14, card_y + 16), 3.5, 3.5)
            
            font_c_title = QFont('Segoe UI', 9, QFont.Weight.Bold)
            painter.setFont(font_c_title)
            painter.setPen(QColor('#F8FAFC'))
            rect_t = QRectF(card_x + 24, card_y + 7, card_w - 32, 17)
            painter.drawText(rect_t, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, f"{ev_h['titulo_cat']}  •  Alerta IA")
            
            font_c_meta = QFont('Segoe UI', 8)
            painter.setFont(font_c_meta)
            painter.setPen(QColor('#94A3B8'))
            fm_m = painter.fontMetrics()
            hora_h = datetime.datetime.fromtimestamp(ev_h['time']).strftime('%H:%M:%S')
            arch_nombre = ev_h.get('archivo', 'evidencia')
            meta_str = f"Hora: {hora_h}   Archivo: {arch_nombre}"
            meta_elided = fm_m.elidedText(meta_str, Qt.TextElideMode.ElideRight, int(card_w - 28))
            rect_m = QRectF(card_x + 14, card_y + 27, card_w - 28, 16)
            painter.drawText(rect_m, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, meta_elided)
            
            font_c_cta = QFont('Segoe UI', 8, QFont.Weight.DemiBold)
            painter.setFont(font_c_cta)
            painter.setPen(QColor('#38BDF8'))
            rect_c = QRectF(card_x + 14, card_y + 46, card_w - 28, 16)
            painter.drawText(rect_c, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, 'Clic para abrir evidencia »')


class PanelCarpetas(QWidget):
    def __init__(self, fn_volver):
        super().__init__()
        self.fn_volver = fn_volver
        self.sesion_id = ""
        self.nombre = ""
        self.ruta_evidencias_local = ""
        
        self.setObjectName("panel_carpetas_main")
        self.lay_main = QVBoxLayout(self)
        self.lay_main.setContentsMargins(40, 40, 40, 40)
        self.lay_main.setSpacing(20)
        
        # --- HEADER PRINCIPAL ---
        self.lbl_titulo = QLabel("Apartado de evidencias del estudiante")
        self.lbl_titulo.setObjectName("pc_lbl_main_titulo")
        
        head_lay = QHBoxLayout()
        head_lay.addWidget(self.lbl_titulo)
        head_lay.addStretch()
        
        self.btn_volver_reporte = QPushButton("Volver al Reporte")
        self.btn_volver_reporte.setStyleSheet("background-color: #005928; color: white; border-radius: 4px; padding: 10px 20px; font-weight: bold;")
        self.btn_volver_reporte.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_volver_reporte.clicked.connect(self.fn_volver)
        
        self.btn_auditoria_forense = QPushButton("🛡 Auditoría Forense")
        self.btn_auditoria_forense.setStyleSheet("background-color: #2c3e50; color: white; border-radius: 4px; padding: 10px 20px; font-weight: bold; border: 2px solid #34495e;")
        self.btn_auditoria_forense.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_auditoria_forense.clicked.connect(self.ejecutar_auditoria)
        
        self.btn_volver_carpetas = QPushButton("Volver a Carpetas")
        self.btn_volver_carpetas.setStyleSheet("background-color: #555555; color: white; border-radius: 4px; padding: 10px 20px; font-weight: bold;")
        self.btn_volver_carpetas.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_volver_carpetas.clicked.connect(self.mostrar_vista_carpetas)
        self.btn_volver_carpetas.setVisible(False)
        
        head_lay.addWidget(self.btn_auditoria_forense)
        head_lay.addWidget(self.btn_volver_carpetas)
        head_lay.addWidget(self.btn_volver_reporte)
        self.lay_main.addLayout(head_lay)
        
        # --- SELECTOR DE REINTENTOS (Idéntico visualmente a ReporteIA) ---
        self.widget_selector_intentos = QWidget()
        self.widget_selector_intentos.setObjectName("widget_selector_intentos")
        lay_sel = QHBoxLayout(self.widget_selector_intentos)
        lay_sel.setContentsMargins(0, 4, 0, 10)
        lay_sel.setSpacing(12)
        
        self.lbl_seleccionar_intento = QLabel("Seleccionar Intento:")
        self.lbl_seleccionar_intento.setObjectName("lbl_seleccionar_intento")
        
        self.combo_intentos = QComboBox()
        self.combo_intentos.setObjectName("combo_intentos")
        self.combo_intentos.setMinimumHeight(35)
        self.combo_intentos.setMinimumWidth(350)
        self.combo_intentos.setCursor(Qt.CursorShape.PointingHandCursor)
        self.combo_intentos.currentIndexChanged.connect(self._al_cambiar_intento)
        
        lay_sel.addWidget(self.lbl_seleccionar_intento)
        lay_sel.addWidget(self.combo_intentos)
        lay_sel.addStretch()
        
        self.widget_selector_intentos.setVisible(False)
        self.lay_main.addWidget(self.widget_selector_intentos)
        
        # --- CONTENEDOR DINAMICO ---
        # Agregamos todo a un ScrollArea para evitar squishing en pantallas pequeñas
        self.scroll_principal = QScrollArea()
        self.scroll_principal.setWidgetResizable(True)
        # Hacemos que la barra de scroll sea invisible visualmente pero que siga funcionando
        self.scroll_principal.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_principal.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        self.lay_main.addWidget(self.scroll_principal)
        
        self.contenedor_dinamico = QWidget()
        self.contenedor_dinamico.setStyleSheet("background: transparent;")
        self.scroll_principal.setWidget(self.contenedor_dinamico)
        
        self.lay_dinamico = QVBoxLayout(self.contenedor_dinamico)
        self.lay_dinamico.setContentsMargins(0,0,0,0)
        
        self.cards = {}
        self.crear_vista_carpetas()
        
        # --- VISTA DE EVIDENCIAS ---
        self.widget_evidencias = QWidget()
        self.widget_evidencias.setObjectName("panel_carpetas_evidencias")
        self.lay_evidencias = QVBoxLayout(self.widget_evidencias)
        self.lay_evidencias.setSpacing(20)
        self.lay_evidencias.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        self.lay_dinamico.addWidget(self.widget_evidencias)
        self.widget_evidencias.setVisible(False)

    def crear_vista_carpetas(self):
        self.widget_carpetas = QWidget()
        self.widget_carpetas.setStyleSheet("background: transparent;")
        
        self.lay_carpetas_main = QVBoxLayout(self.widget_carpetas)
        self.lay_carpetas_main.setContentsMargins(0,0,0,0)
        self.lay_carpetas_main.setSpacing(30)
        
        widget_grid = QWidget()
        self.grid_carpetas = QGridLayout(widget_grid)
        self.grid_carpetas.setSpacing(25)
        self.grid_carpetas.setContentsMargins(0,0,0,0)
        
        self.cards['audio'] = self._crear_tarjeta(
            "VECTOR 01", "Audio", 
            "Archivos de sonido y grabaciones de voz del entorno.", 
            self.abrir_audio
        )
        self.cards['proceso'] = self._crear_tarjeta(
            "VECTOR 02", "Procesos y Sistema", 
            "Capturas de pantalla de aplicaciones no permitidas y alertas de sistema.", 
            self.abrir_procesos
        )
        self.cards['webcam'] = self._crear_tarjeta(
            "VECTOR 03", "Webcam", 
            "Capturas fotográficas de rostros no reconocidos, uso de celular o desatención.", 
            self.abrir_webcam
        )
        self.cards['teclado'] = self._crear_tarjeta(
            "VECTOR 04", "Teclado", 
            "Registro de comandos prohibidos como Alt+Tab o uso del portapapeles.", 
            self.abrir_teclado
        )
        
        for i, key in enumerate(['audio', 'proceso', 'webcam', 'teclado']):
            self.grid_carpetas.setColumnStretch(i % 2, 1)
        
        self.grid_carpetas.addWidget(self.cards['audio'][0], 0, 0)
        self.grid_carpetas.addWidget(self.cards['proceso'][0], 0, 1)
        self.grid_carpetas.addWidget(self.cards['webcam'][0], 1, 0)
        self.grid_carpetas.addWidget(self.cards['teclado'][0], 1, 1)
        
        self.lay_carpetas_main.addWidget(widget_grid)
        self.lay_carpetas_main.addSpacing(25)
        
        self.lbl_timeline_title = QLabel("Línea de Tiempo Analítica")
        self.lbl_timeline_title.setObjectName("pc_lbl_timeline_title")
        self.lbl_timeline_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_timeline_title.setStyleSheet("font-size: 20px; font-weight: bold; margin-bottom: 2px;")
        self.lay_carpetas_main.addWidget(self.lbl_timeline_title)
        
        self.timeline = LineaDeTiempoWidget(self.abrir_categoria, fn_abrir_archivo=self._abrir_archivo)
        
        # Contenedor limpio para la línea de tiempo sin barras de desplazamiento innecesarias
        self.scroll_timeline = QScrollArea()
        self.scroll_timeline.setWidgetResizable(True)
        self.scroll_timeline.setWidget(self.timeline)
        self.scroll_timeline.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        self.scroll_timeline.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_timeline.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_timeline.setFixedHeight(310)
        
        self.lay_carpetas_main.addWidget(self.scroll_timeline)
        
        self.lay_dinamico.addWidget(self.widget_carpetas)

    def _crear_tarjeta(self, vector, titulo, desc, fn_abrir):
        frame = QFrame()
        frame.setFixedHeight(260) # Aún más grandes a petición del usuario (tamaño mediano-grande)
        frame.setObjectName("pc_tarjeta_folder")
        lay = QVBoxLayout(frame)
        lay.setContentsMargins(20, 20, 20, 20)
        
        l1 = QLabel(vector)
        l1.setObjectName("pc_lbl_vector")
        l2 = QLabel(titulo)
        l2.setObjectName("pc_lbl_titulo")
        
        lbl_desc = QLabel(desc)
        lbl_desc.setWordWrap(True)
        lbl_desc.setObjectName("pc_lbl_desc")
        
        lbl_cantidad = QLabel("Calculando evidencias...")
        lbl_cantidad.setObjectName("pc_lbl_cantidad")
        
        btn_abrir = QPushButton("Abrir Carpeta →")
        btn_abrir.setObjectName("pc_btn_abrir")
        btn_abrir.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_abrir.clicked.connect(fn_abrir)
        
        lay.addWidget(l1)
        lay.addWidget(l2)
        lay.addWidget(lbl_desc)
        lay.addWidget(lbl_cantidad)
        lay.addStretch()
        lay.addWidget(btn_abrir, alignment=Qt.AlignmentFlag.AlignRight)
        
        return (frame, lbl_cantidad)

    def _buscar_ruta_sesion(self, sesion_id):
        base_dir = os.path.join(os.path.expanduser("~"), "Documents", "DataSupervision", "Examenes")
        if not os.path.exists(base_dir): return None
        for root, dirs, files in os.walk(base_dir):
            if sesion_id in dirs: return os.path.join(root, sesion_id)
        return None

    def cargar_datos(self, nombre, sesion_id):
        self.nombre = nombre
        self.sesion_id = sesion_id
        nombre_puro = nombre.split('(')[0].strip()
        self.lbl_titulo.setText(f"Apartado de evidencias del estudiante {nombre_puro}")
        
        # Determinar el código del examen de forma robusta
        codigo_examen = "Desconocido"
        parent = self.window()
        if hasattr(parent, "vista_sala") and getattr(parent.vista_sala, "codigo_examen_actual", None):
            codigo_examen = parent.vista_sala.codigo_examen_actual
            
        if codigo_examen == "Desconocido" and hasattr(parent, "vista_reporte") and hasattr(parent.vista_reporte, "combo_examenes"):
            idx = parent.vista_reporte.combo_examenes.currentIndex()
            if 0 <= idx < len(getattr(parent.vista_reporte, "examenes_ids", [])):
                codigo_examen = parent.vista_reporte.examenes_ids[idx]
                
        if codigo_examen == "Desconocido":
            ruta_ses = self._buscar_ruta_sesion(sesion_id)
            if ruta_ses:
                partes = os.path.normpath(ruta_ses).split(os.sep)
                if len(partes) >= 3 and partes[-3] not in ["Examenes", "DataSupervision"]:
                    codigo_examen = partes[-3]

        if codigo_examen == "Desconocido":
            from api.cliente_respuesta import cliente_api
            exito_sesion, sesion_info = cliente_api.obtener_sesion(sesion_id)
            if exito_sesion and isinstance(sesion_info, dict):
                ex = sesion_info.get("examen", {})
                if isinstance(ex, dict):
                    codigo_examen = ex.get("codigoExamen", ex.get("codigo", sesion_info.get("codigoExamen", "Desconocido")))
                else:
                    codigo_examen = sesion_info.get("codigoExamen", "Desconocido")

        self.codigo_examen_actual = codigo_examen
        
        # 1. Detectar si existen reintentos y configurar el combo selector
        self._detectar_intentos(codigo_examen, nombre_puro, sesion_id)
        
        # 2. Cargar y renderizar las evidencias de la sesión seleccionada
        self._aplicar_sesion(sesion_id)

    def _detectar_intentos(self, codigo_examen, nombre_puro, sesion_id_actual):
        """
        Escanea las sesiones de la base de datos (API) como fuente de verdad
        para detectar todos los intentos válidos del estudiante en el examen actual.
        Si la API no está disponible, utiliza el almacenamiento forense local como respaldo.
        Si hay más de 1 intento (> 0 reintentos), activa y llena el selector dinámico.
        """
        from api.cliente_respuesta import cliente_api
        import unicodedata
        import datetime
        
        def norm_str(s):
            if not s: return ""
            return "".join(c for c in unicodedata.normalize('NFD', str(s).lower()) if unicodedata.category(c) != 'Mn').replace("_", " ").strip()
            
        nom_norm = norm_str(nombre_puro)
        
        # 1. Consultar a la API para obtener las sesiones registradas en la Base de Datos
        sesiones_api = None
        if codigo_examen and codigo_examen != "Desconocido":
            try:
                exito, resp_api = cliente_api.obtener_sesiones_examen(codigo_examen, todas=True)
                if exito and isinstance(resp_api, list):
                    sesiones_api = resp_api
            except Exception as e:
                print(f"[PanelCarpetas] Error consultando API para sesiones: {e}")
                
        # Si la llamada a la API no devolvió lista pero la ventana padre tiene sesiones en memoria (ReporteIA)
        if sesiones_api is None:
            parent = self.window()
            if hasattr(parent, "vista_reporte") and getattr(parent.vista_reporte, "sesiones_actuales", None):
                sesiones_api = parent.vista_reporte.sesiones_actuales
                
        intentos_map = {}
        
        def calcular_timestamp(sid):
            ts = 0
            if len(sid) == 24:
                try:
                    ts_mongo = int(sid[:8], 16)
                    if 1577836800 <= ts_mongo <= 2208988800:
                        ts = ts_mongo
                except Exception:
                    pass
            if ts == 0:
                ruta_sid = self._buscar_ruta_sesion(sid)
                if ruta_sid and os.path.exists(ruta_sid):
                    try:
                        ts = min(os.path.getctime(ruta_sid), os.path.getmtime(ruta_sid))
                    except Exception:
                        pass
            return ts

        if sesiones_api is not None:
            # --- CASO PRINCIPAL: La API / Base de Datos es la fuente de verdad ---
            # Identificar el estudianteId correspondiente a la sesión actual
            target_estudiante_id = None
            for s in sesiones_api:
                if str(s.get("sesionId", "")).strip() == str(sesion_id_actual).strip():
                    target_estudiante_id = s.get("estudianteId")
                    break
                    
            if not target_estudiante_id:
                try:
                    ex, s_info = cliente_api.obtener_sesion(sesion_id_actual)
                    if ex and isinstance(s_info, dict):
                        target_estudiante_id = s_info.get("estudianteId")
                except Exception:
                    pass

            # Filtrar estrictamente las sesiones activas en la BD para este estudiante en este examen
            for s in sesiones_api:
                sid = str(s.get("sesionId", "")).strip()
                if not sid:
                    continue
                pertenece = False
                if target_estudiante_id and s.get("estudianteId") == target_estudiante_id:
                    pertenece = True
                elif not target_estudiante_id and s.get("nombreEstudiante"):
                    if norm_str(s.get("nombreEstudiante")) == nom_norm:
                        pertenece = True
                        
                if pertenece:
                    intentos_map[sid] = {
                        "sesion_id": sid,
                        "timestamp": calcular_timestamp(sid)
                    }
                    
            # Asegurar que al menos la sesión actual seleccionada esté presente
            if sesion_id_actual and sesion_id_actual not in intentos_map:
                intentos_map[sesion_id_actual] = {
                    "sesion_id": sesion_id_actual,
                    "timestamp": calcular_timestamp(sesion_id_actual)
                }

        else:
            # --- CASO SECUNDARIO (OFFLINE / FALLBACK): Escanear disco local ---
            intentos_map[sesion_id_actual] = {
                "sesion_id": sesion_id_actual,
                "timestamp": calcular_timestamp(sesion_id_actual)
            }
            ruta_actual = self._buscar_ruta_sesion(sesion_id_actual)
            carpeta_estudiante_disco = None
            if ruta_actual and os.path.exists(ruta_actual):
                carpeta_estudiante_disco = os.path.dirname(ruta_actual)
                
            if not carpeta_estudiante_disco and codigo_examen and codigo_examen != "Desconocido":
                nombre_limpio = nombre_puro.replace(" ", "_").strip("_")
                base_cand = os.path.join(os.path.expanduser("~"), "Documents", "DataSupervision", "Examenes", codigo_examen, nombre_limpio)
                if os.path.exists(base_cand):
                    carpeta_estudiante_disco = base_cand

            if carpeta_estudiante_disco and os.path.isdir(carpeta_estudiante_disco):
                try:
                    for entrada in os.listdir(carpeta_estudiante_disco):
                        ruta_sub = os.path.join(carpeta_estudiante_disco, entrada)
                        if os.path.isdir(ruta_sub):
                            es_sesion = any(os.path.exists(os.path.join(ruta_sub, cat)) for cat in ['audio', 'proceso', 'webcam', 'teclado'])
                            if es_sesion or len(entrada) == 24:
                                intentos_map[entrada] = {
                                    "sesion_id": entrada,
                                    "timestamp": calcular_timestamp(entrada)
                                }
                except Exception as e:
                    print(f"[PanelCarpetas] Error en fallback de disco: {e}")

        lista_intentos = list(intentos_map.values())
        lista_intentos.sort(key=lambda x: x["timestamp"])

        self.combo_intentos.blockSignals(True)
        self.combo_intentos.clear()

        if len(lista_intentos) > 1:
            total = len(lista_intentos)
            for idx, item in enumerate(lista_intentos, 1):
                sid = item["sesion_id"]
                ts = item["timestamp"]
                if ts > 0:
                    dt = datetime.datetime.fromtimestamp(ts)
                    fecha_str = dt.strftime("%d/%m/%Y %I:%M %p")
                else:
                    fecha_str = "Fecha no registrada"
                
                if idx == total:
                    texto = f"Intento {idx} (Más reciente) — {fecha_str}"
                else:
                    texto = f"Intento {idx} — {fecha_str}"
                    
                self.combo_intentos.addItem(texto, sid)
                
            idx_sel = -1
            for i in range(self.combo_intentos.count()):
                if self.combo_intentos.itemData(i) == sesion_id_actual:
                    idx_sel = i
                    break
            if idx_sel >= 0:
                self.combo_intentos.setCurrentIndex(idx_sel)
            else:
                self.combo_intentos.setCurrentIndex(self.combo_intentos.count() - 1)
                
            self.widget_selector_intentos.setVisible(True)
        else:
            self.widget_selector_intentos.setVisible(False)

        self.combo_intentos.blockSignals(False)


    def _al_cambiar_intento(self, index):
        """Manejador del evento de selección de un intento previo o reciente."""
        if index < 0:
            return
        nueva_sesion_id = self.combo_intentos.itemData(index)
        if not nueva_sesion_id or nueva_sesion_id == self.sesion_id:
            return
        self._aplicar_sesion(nueva_sesion_id)

    def _aplicar_sesion(self, sesion_id):
        """Aplica la sesión seleccionada, actualizando contadores, línea de tiempo y evidencias."""
        from api.cliente_respuesta import cliente_api
        
        self.sesion_id = sesion_id
        
        # Buscar la ruta real en el disco usando el sesion_id
        base_dir = self._buscar_ruta_sesion(sesion_id)

        if not base_dir:
            # Si no existe, crear la ruta por defecto
            nombre_real = self.nombre.split('(')[0].strip()
            nombre_limpio = nombre_real.replace(" ", "_").strip("_")
            codigo_ex = getattr(self, "codigo_examen_actual", "Desconocido")
            base_dir = os.path.join(os.path.expanduser("~"), "Documents", "DataSupervision", "Examenes", codigo_ex, nombre_limpio, sesion_id)
            for cat in ['audio', 'proceso', 'webcam', 'teclado']:
                os.makedirs(os.path.join(base_dir, cat), exist_ok=True)
            
        # Llamar a la API para traer la metadata con los hashes
        try:
            exito, alertas = cliente_api.obtener_alertas(sesion_id)
            self.alertas_metadata = alertas if exito else []
        except Exception as e:
            print(f"[PanelCarpetas] Error obteniendo alertas para sesion {sesion_id}: {e}")
            self.alertas_metadata = []
        
        self.ruta_evidencias_local = base_dir
        
        # Contar archivos en cada vector
        for carpeta in ['audio', 'proceso', 'webcam', 'teclado']:
            cantidad = 0
            if self.ruta_evidencias_local:
                ruta_cat = os.path.join(self.ruta_evidencias_local, carpeta)
                if os.path.exists(ruta_cat):
                    archivos = [a for a in os.listdir(ruta_cat) if os.path.isfile(os.path.join(ruta_cat, a))]
                    cantidad = len(archivos)
            lbl = self.cards[carpeta][1]
            if cantidad > 0:
                lbl.setText(f"📂 {cantidad} archivos de evidencia recopilados.")
                lbl.setStyleSheet("")
            else:
                lbl.setText("📁 Carpeta sin evidencias (0 archivos).")
                lbl.setStyleSheet("color: #777777; font-size: 13px; font-weight: bold; margin-top: 5px; border: none; background: transparent;")
                
        if self.ruta_evidencias_local:
            self.timeline.cargar_eventos(self.ruta_evidencias_local)
        else:
            self.timeline.cargar_eventos(None)
            
        self.mostrar_vista_carpetas()


    def mostrar_vista_carpetas(self):
        self.widget_evidencias.setVisible(False)
        self.widget_carpetas.setVisible(True)
        self.btn_volver_carpetas.setVisible(False)
        self.btn_volver_reporte.setVisible(True)

    def _abrir_archivo(self, ruta_archivo):
        # --- DESCIFRADO E2EE AES-256 PARA VISUALIZACION LOCAL ---
        import tempfile
        import os
        from cryptography.fernet import Fernet
        from config.configuracion import AES_SECRET_KEY
        import base64

        try:
            with open(ruta_archivo, 'rb') as f:
                contenido_cifrado = f.read()
            
            f_crypto = Fernet(AES_SECRET_KEY)
            base64_descifrado = f_crypto.decrypt(contenido_cifrado).decode('utf-8')
            contenido_final = base64.b64decode(base64_descifrado)
            
            # Detectar el formato real de la imagen segun su cabecera binaria
            if contenido_final.startswith(b'\xff\xd8\xff'):
                ext = ".jpg"
            elif contenido_final.startswith(b'RIFF') and b'WEBP' in contenido_final[:12]:
                ext = ".webp"
            elif contenido_final.startswith(b'\x89PNG'):
                ext = ".png"
            else:
                ext = os.path.splitext(ruta_archivo)[1] or ".jpg"
            
            fd, temp_path = tempfile.mkstemp(suffix=ext)
            with os.fdopen(fd, 'wb') as f_temp:
                f_temp.write(contenido_final)
                
            # Abrir el archivo temporal con el visor de Windows
            QDesktopServices.openUrl(QUrl.fromLocalFile(temp_path))
            print(f"[E2EE] Archivo abierto con exito (descifrado en {temp_path})")
            
        except Exception as e:
            print(f"[E2EE] El archivo no estaba cifrado o hubo un error al descifrar: {e}")
            # Fallback: abrir original por si no es cifrado (ej. fotos viejas antes del parche E2EE)
            QDesktopServices.openUrl(QUrl.fromLocalFile(ruta_archivo))

    def abrir_categoria(self, nombre_carpeta, titulo_cat):
        self.widget_carpetas.setVisible(False)
        self.btn_volver_reporte.setVisible(False)
        self.btn_volver_carpetas.setVisible(True)
        self.widget_evidencias.setVisible(True)
        
        while self.lay_evidencias.count():
            child = self.lay_evidencias.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
            elif child.layout():
                inner = child.layout()
                while inner.count():
                    item = inner.takeAt(0)
                    if item.widget():
                        item.widget().deleteLater()
                inner.deleteLater()
                
        lbl_cat = QLabel(f"Evidencias Locales de {titulo_cat}")
        lbl_cat.setObjectName("pc_lbl_cat")
        self.lay_evidencias.addWidget(lbl_cat)
        
        if not self.ruta_evidencias_local:
            lbl_vacio = QLabel("No se encontro el directorio local de DataSupervision.")
            self.lay_evidencias.addWidget(lbl_vacio)
            self.lay_evidencias.addStretch()
            return
            
        ruta_carpeta = os.path.join(self.ruta_evidencias_local, nombre_carpeta)
        
        if not os.path.exists(ruta_carpeta):
            lbl_vacio = QLabel(f"La carpeta '{nombre_carpeta}' esta vacia.")
            self.lay_evidencias.addWidget(lbl_vacio)
            self.lay_evidencias.addStretch()
            return
            
        archivos = os.listdir(ruta_carpeta)
        archivos = [a for a in archivos if os.path.isfile(os.path.join(ruta_carpeta, a))]
        
        if not archivos:
            lbl_vacio = QLabel("No hay archivos guardados.")
            self.lay_evidencias.addWidget(lbl_vacio)
            self.lay_evidencias.addStretch()
            return
            
        grid = QGridLayout()
        grid.setSpacing(20)
        self.lay_evidencias.addLayout(grid)
        
        fila = 0
        col = 0
        max_cols = 4 
        
        for c in range(max_cols):
            grid.setColumnStretch(c, 1)
            
        for i, archivo in enumerate(archivos):
            ruta_completa = os.path.join(ruta_carpeta, archivo)
            
            frame_card = QFrame()
            frame_card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            frame_card.setMinimumHeight(240)
            frame_card.setObjectName("pc_frame_card")
            lay_c = QVBoxLayout(frame_card)
            lay_c.setContentsMargins(15, 15, 15, 15)
            
            num = str(i+1).zfill(2)
            nombre_corto = f"EV_{nombre_carpeta}_{num}"
            
            lbl_info = QLabel(f"<b>{nombre_corto}</b>")
            lbl_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl_info.setObjectName("pc_lbl_info")
            lay_c.addWidget(lbl_info)
            
            lbl_img = QLabel()
            lbl_img.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl_img.setStyleSheet("border: none; background: transparent;")
            lbl_img.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            
            es_imagen = archivo.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))
            
            if es_imagen:
                try:
                    from cryptography.fernet import Fernet
                    from config.configuracion import AES_SECRET_KEY
                    f = Fernet(AES_SECRET_KEY)
                    with open(ruta_completa, 'rb') as file_obj:
                        datos = file_obj.read()
                    try:
                        datos = f.decrypt(datos)
                    except:
                        pass
                    pixmap = QPixmap()
                    pixmap.loadFromData(datos)
                    if not pixmap.isNull():
                        pix_scaled = pixmap.scaled(200, 150, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                        lbl_img.setPixmap(pix_scaled)
                    else:
                        lbl_img.setText("📷")
                        lbl_img.setStyleSheet("font-size: 40px; border: none; background: transparent;")
                except:
                    lbl_img.setText("📷")
                    lbl_img.setStyleSheet("font-size: 40px; border: none; background: transparent;")
            else:
                lbl_img.setText("🎵" if archivo.lower().endswith('.wav') else "📄")
                lbl_img.setStyleSheet("font-size: 60px; border: none; background: transparent;")
                
            lay_c.addWidget(lbl_img)
            lay_c.addStretch()
            
            btn_play = QPushButton("Ver" if es_imagen else "Reproducir")
            btn_play.setStyleSheet("QPushButton { background-color: #005928; color: white; border-radius: 4px; padding: 10px; font-weight: bold; } QPushButton:hover { background-color: #00451f; }")
            btn_play.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_play.clicked.connect(lambda checked, ruta=ruta_completa: self._abrir_archivo(ruta))
            
            lay_c.addWidget(btn_play)
            grid.addWidget(frame_card, fila, col)
            
            col += 1
            if col >= max_cols:
                col = 0
                fila += 1
                
        self.lay_evidencias.addStretch()

    def abrir_audio(self): self.abrir_categoria("audio", "Audio")
    def abrir_procesos(self): self.abrir_categoria("proceso", "Procesos y Sistema")
    def abrir_webcam(self): self.abrir_categoria("webcam", "Webcam")
    def abrir_teclado(self): self.abrir_categoria("teclado", "Teclado")


    def ejecutar_auditoria(self):
        import hashlib
        import os
        from PyQt6.QtWidgets import QMessageBox, QProgressDialog
        from PyQt6.QtCore import Qt
        
        if not hasattr(self, 'alertas_metadata') or not self.alertas_metadata:
            QMessageBox.information(self, "Auditoria", "No hay evidencias para auditar.")
            return
            
        total_archivos_esperados = 0
        for al in self.alertas_metadata:
            if al.get('hashWebcam'): total_archivos_esperados += 1
            if al.get('hashPantalla'): total_archivos_esperados += 1
            if al.get('hashAudio'): total_archivos_esperados += 1
            
        if total_archivos_esperados == 0:
            box = QMessageBox(self)
            box.setIcon(QMessageBox.Icon.Information)
            box.setWindowTitle("Auditoria")
            box.setText("No se encontraron archivos en el disco con un hash valido.\n\nNota: Las evidencias capturadas ANTES de implementar el Sello Forense no tienen firma matematica en la base de datos.\n\nPor favor, realiza un nuevo examen de prueba para verificar esta funcion.")
            box.exec()
            return
            
        progress = QProgressDialog("Analizando firma Hash de las evidencias...", "Cancelar", 0, total_archivos_esperados, self)
        progress.setWindowTitle("Sello Forense")
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(0) # Forzar que se muestre de inmediato
        progress.show()
        
        archivos_analizados = 0
        archivos_validos = 0
        archivos_manipulados = []
        
        for al in self.alertas_metadata:
            if progress.wasCanceled():
                break
                
            id_alerta = al.get('idAlerta', 'ws')
            
            # Revisar Webcam
            hash_webcam = al.get('hashWebcam')
            path_webcam = os.path.join(self.ruta_evidencias_local, "webcam", f"evidencia_{id_alerta}.webp")
            if hash_webcam and os.path.exists(path_webcam):
                archivos_analizados += 1
                progress.setLabelText(f"Analizando firma Hash de las evidencias {archivos_analizados}/{total_archivos_esperados}...")
                progress.setValue(archivos_analizados)
                import time
                time.sleep(0.8)
                from PyQt6.QtWidgets import QApplication
                QApplication.processEvents()
                with open(path_webcam, "rb") as f:
                    from cryptography.fernet import Fernet
                    from config.configuracion import AES_SECRET_KEY
                    f_crypto = Fernet(AES_SECRET_KEY)
                    try:
                        bytes_enc = f.read()
                        bytes_dec = f_crypto.decrypt(bytes_enc)
                        hash_calc = hashlib.sha256(bytes_dec).hexdigest()
                        if hash_calc == hash_webcam: archivos_validos += 1
                        else: archivos_manipulados.append(path_webcam)
                    except:
                        archivos_manipulados.append(path_webcam)
            
            # Revisar Proceso/Pantalla
            hash_pantalla = al.get('hashPantalla')
            clase = al.get('claseAlerta', '').upper()
            subc = "proceso" if clase in ["SISTEMA", "PROCESO", "PROCESOS"] else ("teclado" if clase == "TECLADO" else "webcam")
            suf = ".webp" if clase in ["SISTEMA", "PROCESO", "PROCESOS", "TECLADO"] else "_pantalla.webp"
            path_pantalla = os.path.join(self.ruta_evidencias_local, subc, f"evidencia_{id_alerta}{suf}")
            
            if hash_pantalla and os.path.exists(path_pantalla):
                archivos_analizados += 1
                progress.setLabelText(f"Analizando firma Hash de las evidencias {archivos_analizados}/{total_archivos_esperados}...")
                progress.setValue(archivos_analizados)
                import time
                time.sleep(0.8)
                from PyQt6.QtWidgets import QApplication
                QApplication.processEvents()
                with open(path_pantalla, "rb") as f:
                    from cryptography.fernet import Fernet
                    from config.configuracion import AES_SECRET_KEY
                    f_crypto = Fernet(AES_SECRET_KEY)
                    try:
                        bytes_enc = f.read()
                        bytes_dec = f_crypto.decrypt(bytes_enc)
                        hash_calc = hashlib.sha256(bytes_dec).hexdigest()
                        if hash_calc == hash_pantalla: archivos_validos += 1
                        else: archivos_manipulados.append(path_pantalla)
                    except:
                        archivos_manipulados.append(path_pantalla)
                        
            # Revisar Audio
            hash_audio = al.get('hashAudio')
            path_audio = os.path.join(self.ruta_evidencias_local, "audio", f"evidencia_{id_alerta}.wav")
            if hash_audio and os.path.exists(path_audio):
                archivos_analizados += 1
                progress.setLabelText(f"Analizando firma Hash de las evidencias {archivos_analizados}/{total_archivos_esperados}...")
                progress.setValue(archivos_analizados)
                import time
                time.sleep(0.8)
                from PyQt6.QtWidgets import QApplication
                QApplication.processEvents()
                with open(path_audio, "rb") as f:
                    from cryptography.fernet import Fernet
                    from config.configuracion import AES_SECRET_KEY
                    f_crypto = Fernet(AES_SECRET_KEY)
                    try:
                        bytes_enc = f.read()
                        bytes_dec = f_crypto.decrypt(bytes_enc)
                        hash_calc = hashlib.sha256(bytes_dec).hexdigest()
                        if hash_calc == hash_audio: archivos_validos += 1
                        else: archivos_manipulados.append(path_audio)
                    except:
                        archivos_manipulados.append(path_audio)
                        
        progress.setValue(total_archivos_esperados)
            
        if archivos_manipulados:
            msg = "PELIGRO DE SEGURIDAD\n\nSe auditaron " + str(archivos_analizados) + " archivos.\nArchivos Validos: " + str(archivos_validos) + "\nArchivos MANIPULADOS O CORRUPTOS: " + str(len(archivos_manipulados)) + "\n\nArchivos alterados:\n"
            msg += "\n".join([os.path.basename(p) for p in archivos_manipulados[:5]])
            if len(archivos_manipulados) > 5: msg += "..."
            
            box = QMessageBox(self)
            box.setIcon(QMessageBox.Icon.Critical)
            box.setWindowTitle("Sello Forense Roto")
            box.setText(msg)
            box.exec()
        else:
            box = QMessageBox(self)
            box.setIcon(QMessageBox.Icon.Information)
            box.setWindowTitle("Auditoria Forense Exitosa")
            msg2 = "INTEGRIDAD CONFIRMADA\n\nSe verificaron matematicamente " + str(archivos_analizados) + " archivos de evidencia con SHA-256.\n\nNingun archivo ha sido manipulado, editado ni corrompido desde que salio del PC del estudiante."
            box.setText(msg2)
            box.exec()
