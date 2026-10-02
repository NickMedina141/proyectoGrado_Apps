# deteccion/analizador_comportamiento.py

import time

class AnalizadorComportamiento:
  """
  Cerebro del sistema de supervisión.
  Recibe los resultados de los tres detectores y decide
  cuándo una situación es realmente sospechosa,
  evitando falsas alarmas por movimientos normales.
  """

  def __init__(self, funcion_alerta_global=None):

    # Función que se llama cuando se confirma comportamiento sospechoso
    # Recibe (tipo_alerta, nivel_riesgo, descripcion)
    self.funcion_alerta_global = funcion_alerta_global

    # --- Niveles de riesgo ---
    self.RIESGO_BAJO = 1
    self.RIESGO_MEDIO = 2
    self.RIESGO_ALTO = 3

    # --- Historial de alertas recientes ---
    # { "nombre_alerta": timestamp_ultima_vez }
    self.historial_alertas = {}

    # Tiempo mínimo entre dos alertas del mismo tipo (evita spam)
    self.TIEMPO_ENTRE_ALERTAS = 10.0 # segundos

    # --- Contadores de comportamiento sospechoso ---
    # Cuántas veces se ha detectado cada comportamiento en la sesión
    self.conteo_alertas = {}

    # --- Combinaciones sospechosas ---
    # Si se detectan varias alertas a la vez, el riesgo sube
    self.combinaciones_peligrosas = [
      {"alertas": {"MIRADA_DERECHA",  "GIRO_SOSPECHOSO_DERECHA"}, "descripcion": "Mira y gira hacia la derecha"},
      {"alertas": {"MIRADA_IZQUIERDA", "GIRO_SOSPECHOSO_IZQUIERDA"}, "descripcion": "Mira y gira hacia la izquierda"},
      {"alertas": {"MANOS_NO_VISIBLES", "MIRADA_ABAJO"},       "descripcion": "Manos ocultas y mirada abajo"},
      {"alertas": {"OBJETO_SOSPECHOSO_CELULAR", "MIRADA_ABAJO"},   "descripcion": "Celular detectado y mira abajo"},
      {"alertas": {"AUDIO_HABLANDO", "MIRADA_IZQUIERDA"}, "descripcion": "Hablando y mirando a alguien a la izquierda"},
      {"alertas": {"AUDIO_HABLANDO", "MIRADA_DERECHA"}, "descripcion": "Hablando y mirando a alguien a la derecha"},
      {"alertas": {"AUDIO_HABLANDO", "MULTIPLES_ROSTROS"}, "descripcion": "Hablando con otra persona en camara"},
    ]

    # --- Resumen de la sesión ---
    self.inicio_sesion  = time.time()
    self.total_alertas  = 0
    self.eventos_criticos = [] # lista de eventos de riesgo alto

  def configurar_sensibilidad(self, nivel: str):
    if nivel == "ALTA":
        self.TIEMPO_ENTRE_ALERTAS = 5.0
    elif nivel == "BAJA":
        self.TIEMPO_ENTRE_ALERTAS = 15.0
    else:
        self.TIEMPO_ENTRE_ALERTAS = 10.0


  # ─────────────────────────────────────────────
  # MÉTODO PRINCIPAL
  # ─────────────────────────────────────────────
  def analizar(self, datos_rostro, datos_objetos, datos_postura, datos_audio=None):
    """
    Recibe los dicts de resultados de los tres detectores,
    analiza el comportamiento global y devuelve un dict con
    el nivel de riesgo actual y las alertas confirmadas.
    """

    resultado = {
      "nivel_riesgo"   : self.RIESGO_BAJO,
      "alertas_confirmadas": [],
      "descripcion"    : "Normal"
    }

    # Reunir todas las alertas activas de los tres detectores
    alertas_activas = set()
    alertas_activas.update(datos_rostro.get("alertas", []))
    alertas_activas.update(datos_objetos.get("alertas", []))
    alertas_activas.update(datos_postura.get("alertas", []))
    
    if datos_audio and datos_audio.get("hablando"):
        alertas_activas.add("AUDIO_HABLANDO")

    if not alertas_activas:
      return resultado

    ahora = time.time()

    # ── Filtrar alertas repetidas recientes ──
    alertas_nuevas = self._filtrar_repetidas(alertas_activas, ahora)

    if not alertas_nuevas:
      return resultado

    # ── Clasificar nivel de riesgo ────────────
    nivel, descripcion = self._clasificar_riesgo(alertas_nuevas, alertas_activas)
    resultado["nivel_riesgo"]    = nivel
    resultado["descripcion"]    = descripcion
    resultado["alertas_confirmadas"] = list(alertas_nuevas)

    # ── Registrar en historial ────────────────
    for alerta in alertas_nuevas:
      self.historial_alertas[alerta] = ahora
      self.conteo_alertas[alerta]  = self.conteo_alertas.get(alerta, 0) + 1
      self.total_alertas      += 1

    # ── Guardar eventos críticos ──────────────
    if nivel == self.RIESGO_ALTO:
      self.eventos_criticos.append({
        "momento"  : ahora,
        "alertas"  : list(alertas_nuevas),
        "descripcion": descripcion
      })

    # ── Disparar alerta global ────────────────
    if self.funcion_alerta_global:
      self.funcion_alerta_global(
        list(alertas_nuevas), nivel, descripcion
      )

    return resultado


  # ─────────────────────────────────────────────
  # FILTRAR ALERTAS REPETIDAS
  # ─────────────────────────────────────────────
  def _filtrar_repetidas(self, alertas_activas, ahora):
    """
    Filtra alertas que ya se reportaron hace poco
    para no generar spam en el informe.
    """
    alertas_nuevas = set()
    for alerta in alertas_activas:
      ultima_vez = self.historial_alertas.get(alerta, 0)
      if ahora - ultima_vez>= self.TIEMPO_ENTRE_ALERTAS:
        alertas_nuevas.add(alerta)
    return alertas_nuevas


  # ─────────────────────────────────────────────
  # CLASIFICAR NIVEL DE RIESGO
  # ─────────────────────────────────────────────
  def _clasificar_riesgo(self, alertas_nuevas, alertas_activas):
    """
    Determina el nivel de riesgo según qué alertas están activas
    y si hay combinaciones peligrosas.
    """

    # Alertas que por sí solas son de riesgo alto
    alertas_alto_riesgo = {
      "OBJETO_SOSPECHOSO_CELULAR",
      "OBJETO_SOSPECHOSO_AURICULARES",
      "OBJETO_SOSPECHOSO_AURICULAR",
      "ROSTRO_NO_DETECTADO",
      "CUERPO_NO_DETECTADO",
    }

    # Alertas de riesgo medio
    alertas_medio_riesgo = {
      "MIRADA_DERECHA",
      "MIRADA_IZQUIERDA",
      "MANOS_NO_VISIBLES",
      "GIRO_SOSPECHOSO_DERECHA",
      "GIRO_SOSPECHOSO_IZQUIERDA",
      "CABEZA_INCLINADA_DERECHA",
      "CABEZA_INCLINADA_IZQUIERDA",
      "ESTUDIANTE_LEVANTANDOSE",
    }

    # Verificar combinaciones peligrosas primero
    for combinacion in self.combinaciones_peligrosas:
      if combinacion["alertas"].issubset(alertas_activas):
        return self.RIESGO_ALTO, combinacion["descripcion"]

    # Verificar alertas individuales de alto riesgo
    for alerta in alertas_nuevas:
      if alerta in alertas_alto_riesgo:
        return self.RIESGO_ALTO, f"Detectado: {alerta}"

    # Verificar si hay varias alertas medias al mismo tiempo
    alertas_medias_activas = alertas_nuevas.intersection(alertas_medio_riesgo)
    if len(alertas_medias_activas)>= 2:
      return self.RIESGO_ALTO, "Multiples comportamientos sospechosos simultaneos"

    if alertas_medias_activas:
      return self.RIESGO_MEDIO, f"Comportamiento inusual: {', '.join(alertas_medias_activas)}"

    return self.RIESGO_BAJO, "Actividad leve"


  # ─────────────────────────────────────────────
  # RESUMEN DE SESIÓN
  # ─────────────────────────────────────────────
  def obtener_resumen(self):
    """
    Devuelve un resumen completo de la sesión para el informe final.
    """
    duracion = time.time() - self.inicio_sesion
    minutos = int(duracion // 60)
    segundos = int(duracion % 60)

    return {
      "duracion_sesion" : f"{minutos}m {segundos}s",
      "total_alertas"  : self.total_alertas,
      "conteo_por_alerta": dict(self.conteo_alertas),
      "eventos_criticos" : self.eventos_criticos,
      "nivel_riesgo_sesion": (
        "ALTO" if self.eventos_criticos else
        "MEDIO" if self.total_alertas>5 else
        "BAJO"
      )
    }


  def reiniciar(self):
    """Limpia el estado para una nueva sesión de examen."""
    self.historial_alertas = {}
    self.conteo_alertas  = {}
    self.total_alertas   = 0
    self.eventos_criticos = []
    self.inicio_sesion   = time.time()
