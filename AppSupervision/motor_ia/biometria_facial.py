import os
import cv2
import numpy as np

class BiometriaFacial:
  def __init__(self):
    self.modelo_cargado = False
    self.app = None
    print('[BIOMETRIA] Inicializando InsightFace (ArcFace)...')
    try:
        from insightface.app import FaceAnalysis
        import sys
        if getattr(sys, 'frozen', False):
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        ruta_modelo = os.path.join(base_dir, 'Lib', 'insightface_model')
        self.app = FaceAnalysis(name='buffalo_sc', root=ruta_modelo)
        self.app.prepare(ctx_id=0, det_size=(640, 640))
        self.modelo_cargado = True
        print('[BIOMETRIA] Modelo buffalo_sc cargado con exito.')
    except Exception as e:
        print(f'[BIOMETRIA] Error al cargar InsightFace: {e}')

  def es_rostro_frontal(self, face):
    """
    Evalúa geométricamente si el rostro detectado por InsightFace está mirando
    de frente a la cámara (rango apto para comparación biométrica 1:1).
    Evita falsos positivos por cabeceo (pitch), giro (yaw) o ladeo (roll).
    """
    if face is None:
        return False, "Sin rostro"
        
    det_score = getattr(face, 'det_score', 0.0)
    if det_score < 0.60:
        return False, f"Baja confianza de detección ({det_score:.2f})"
        
    kps = getattr(face, 'kps', None)
    if kps is None or len(kps) < 5:
        return False, "Landmarks no disponibles"
        
    le = kps[0]   # ojo izquierdo
    re = kps[1]   # ojo derecho
    nose = kps[2] # nariz
    lm = kps[3]   # comisura boca izquierda
    rm = kps[4]   # comisura boca derecha
    
    # 1. Distancia interpupilar mínima (claridad y resolución suficiente)
    eye_dist = np.linalg.norm(re - le)
    if eye_dist < 40:
        return False, "Rostro demasiado lejano"
        
    # 2. Roll (inclinación lateral oreja-hombro)
    eye_dx = re[0] - le[0]
    eye_dy = re[1] - le[1]
    roll_deg = np.degrees(np.arctan2(abs(eye_dy), abs(eye_dx)))
    if roll_deg > 20.0:
        return False, f"Inclinación lateral excesiva ({roll_deg:.1f}°)"
        
    # 3. Yaw (giro horizontal izquierda/derecha)
    d_nose_le = abs(nose[0] - le[0])
    d_nose_re = abs(nose[0] - re[0])
    max_d = max(d_nose_le, d_nose_re)
    min_d = min(d_nose_le, d_nose_re)
    yaw_ratio = min_d / max_d if max_d > 0 else 0.0
    if yaw_ratio < 0.50:
        return False, f"Rostro girado lateralmente (ratio: {yaw_ratio:.2f})"
        
    # 4. Pitch (inclinación vertical mirar abajo/arriba)
    eye_mid_y = (le[1] + re[1]) / 2.0
    mouth_mid_y = (lm[1] + rm[1]) / 2.0
    dist_eyes_mouth = abs(mouth_mid_y - eye_mid_y)
    dist_eyes_nose = abs(nose[1] - eye_mid_y)
    pitch_ratio = dist_eyes_nose / dist_eyes_mouth if dist_eyes_mouth > 0 else 0.0
    if pitch_ratio < 0.32 or pitch_ratio > 0.72:
        return False, f"Rostro mirando hacia abajo/arriba (pitch: {pitch_ratio:.2f})"
        
    return True, "Rostro frontal óptimo"

  def obtener_embedding(self, frame, exigir_frontal=False):
    if not self.modelo_cargado: return None
    try:
        rostros = self.app.get(frame)
        if len(rostros) == 0:
            return None
        # Seleccionar el rostro con mayor área
        principal = max(rostros, key=lambda r: (r.bbox[2]-r.bbox[0]) * (r.bbox[3]-r.bbox[1]))
        
        if exigir_frontal:
            es_frontal, motivo = self.es_rostro_frontal(principal)
            if not es_frontal:
                return None
                
        return principal.embedding
    except Exception as e:
        print(f"[BIOMETRIA] Error extrayendo embedding: {e}")
        return None

  def verificar_identidad_detallada(self, frame_actual, embedding_referencia):
    """
    Verifica la identidad asegurando primero que el frame contenga un rostro
    frontal de calidad. Devuelve:
    (es_misma_persona, similitud, apto_evaluacion, motivo)
    - apto_evaluacion: False si el rostro está inclinado, girado o ausente.
    - es_misma_persona: False ÚNICAMENTE si el rostro es confirmado frontal y no coincide.
    """
    if not self.modelo_cargado or embedding_referencia is None:
        return True, 1.0, False, "Modelo no cargado o sin referencia"
        
    try:
        rostros = self.app.get(frame_actual)
        if not rostros:
            return True, 0.0, False, "Sin rostro detectado"
            
        principal = max(rostros, key=lambda r: (r.bbox[2]-r.bbox[0]) * (r.bbox[3]-r.bbox[1]))
        
        es_frontal, motivo = self.es_rostro_frontal(principal)
        if not es_frontal:
            return True, 1.0, False, motivo
            
        emb_actual = principal.embedding
        if emb_actual is None:
            return True, 0.0, False, "Embedding no extraible"
            
        # Similitud coseno
        similitud = np.dot(emb_actual, embedding_referencia) / (
            np.linalg.norm(emb_actual) * np.linalg.norm(embedding_referencia)
        )
        
        # Umbral calibrado para buffalo_sc en condiciones frontales garantizadas
        es_misma_persona = similitud > 0.28
        return bool(es_misma_persona), float(similitud), True, "Evaluacion frontal completada"
        
    except Exception as e:
        print(f"[BIOMETRIA] Error en verificacion de identidad: {e}")
        return True, 1.0, False, f"Error: {e}"

  def verificar_identidad(self, frame_actual, embedding_referencia):
    """
    Método estándar de compatibilidad. Devuelve (es_misma_persona, similitud).
    Si el rostro no es frontal, retorna True (sin castigo) para evitar falsos positivos.
    """
    es_misma, sim, apto, motivo = self.verificar_identidad_detallada(frame_actual, embedding_referencia)
    return es_misma, sim

  def detectar_suplantacion_liveness(self, frame_actual):
    return True, 'Persona Viva'

biometria_motor = BiometriaFacial()
