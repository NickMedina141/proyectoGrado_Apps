import os
from PyQt6.QtWidgets import QWidget, QMessageBox
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6 import uic
from api.cliente_respuesta import cliente_api
from utils.gestor_sesion import sesion_actual

class ReporteIA(QWidget):
  senal_llm_exito = pyqtSignal(dict)
  senal_llm_error = pyqtSignal(str)

  def __init__(self):
    super().__init__()
    self.senal_llm_exito.connect(self.mostrar_resultado_llm)
    self.senal_llm_error.connect(self.mostrar_error_llm)
    
    base_path = os.path.dirname(__file__)
    uic.loadUi(os.path.join(base_path, "reporte_ia.xml"), self)
    
    self.btn_descargar_pdf.setText("Analizar con IA y descargar reportes")
    from PyQt6.QtWidgets import QSizePolicy
    self.btn_descargar_pdf.setMinimumHeight(40)
    self.btn_descargar_pdf.setSizePolicy(
        QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
    self.btn_descargar_pdf.setStyleSheet("background-color: #8E44AD; color: white; border-radius: 6px; font-weight: bold; font-size: 13px;")
    
    self.btn_descargar_pdf.clicked.connect(self.generar_reporte_llm_global)
    
    self.examenes_ids = []
    self.sesiones_actuales = []
    
    self.combo_examenes.currentIndexChanged.connect(self.actualizar_reporte)

    self.ranking_item_1.setVisible(False)
    self.ranking_item_2.setVisible(False)
    self.ranking_item_3.setVisible(False)

    # Componente visual Radar / Telaraña Forense de anomalías
    from vista.grafico_radar import GraficoRadar
    from PyQt6.QtWidgets import QVBoxLayout
    if hasattr(self, 'contenedor_dona'):
      lay_d = QVBoxLayout(self.contenedor_dona)
      lay_d.setContentsMargins(0, 0, 0, 0)
      self.grafico_radar = GraficoRadar()
      lay_d.addWidget(self.grafico_radar)
    else:
      self.grafico_radar = None

    # Directorio de todos los estudiantes
    self.estudiantes_para_modal = []
    if hasattr(self, 'btn_ver_todos_estudiantes'):
      self.btn_ver_todos_estudiantes.clicked.connect(self.abrir_directorio_estudiantes)
    
  def cargar_examenes(self, callback_finalizado=None):
    profesor_id = sesion_actual.obtener_profesor_id()
    if not profesor_id:
      if callback_finalizado:
          try: callback_finalizado()
          except Exception: pass
      return

    def _tarea_red():
        return cliente_api.obtener_mis_examenes(profesor_id)

    def _al_recibir(resultado):
        exito, examenes = resultado
        id_seleccionado = None
        idx_actual = self.combo_examenes.currentIndex()
        if idx_actual >= 0 and idx_actual < len(self.examenes_ids):
            id_seleccionado = self.examenes_ids[idx_actual]

        self.combo_examenes.blockSignals(True)
        self.combo_examenes.clear()
        self.examenes_ids.clear()

        if exito and isinstance(examenes, list):
          for ex in examenes:
            control = ex.get("controlAcceso") or {}
            estado = control.get("estadoPin", "")
            if estado == "FINALIZADO":
              materia = ex.get("materiaCodigo") or "Desconocida"
              fecha_dict = ex.get("fechaExamen") or {}
              fecha = fecha_dict.get("horaFin") or fecha_dict.get("horaInicio", "Sin Fecha")
              if "T" in fecha:
                fecha = fecha.split("T")[0]
              texto = f"Examen: {materia} - Finalizado el {fecha}"
              self.combo_examenes.addItem(texto)
              id_ex = ex.get("codigoExamen") or ex.get("id")
              self.examenes_ids.append(id_ex)
              if not hasattr(self, 'examenes_completos'):
                  self.examenes_completos = {}
              self.examenes_completos[id_ex] = ex

        if id_seleccionado and id_seleccionado in self.examenes_ids:
            nuevo_idx = self.examenes_ids.index(id_seleccionado)
            self.combo_examenes.setCurrentIndex(nuevo_idx)

        self.combo_examenes.blockSignals(False)

        if self.combo_examenes.count() > 0:
            self.actualizar_reporte(callback_finalizado=callback_finalizado)
        elif callback_finalizado:
            try: callback_finalizado()
            except Exception: pass

    from vista.overlay_carga import HiloTrabajador
    self._hilo_examenes = HiloTrabajador(_tarea_red)
    self._hilo_examenes.senal_resultado.connect(_al_recibir)
    self._hilo_examenes.start()

  def actualizar_reporte(self, callback_finalizado=None):
    idx = self.combo_examenes.currentIndex()
    if idx < 0 or idx >= len(self.examenes_ids):
      if callback_finalizado:
          try: callback_finalizado()
          except Exception: pass
      return

    codigo_examen = self.examenes_ids[idx]

    def _tarea_red():
        return cliente_api.obtener_sesiones_examen(codigo_examen, todas=True)

    def _al_recibir(resultado):
        exito, sesiones = resultado
        if not exito or not isinstance(sesiones, list):
          if callback_finalizado:
              try: callback_finalizado()
              except Exception: pass
          return

        self._procesar_datos_reporte(sesiones, codigo_examen)
        if callback_finalizado:
            try: callback_finalizado()
            except Exception: pass

    from vista.overlay_carga import HiloTrabajador
    self._hilo_sesiones = HiloTrabajador(_tarea_red)
    self._hilo_sesiones.senal_resultado.connect(_al_recibir)
    self._hilo_sesiones.start()

  def _procesar_datos_reporte(self, sesiones, codigo_examen=None):
    if not codigo_examen:
      idx = self.combo_examenes.currentIndex()
      if 0 <= idx < len(self.examenes_ids):
        codigo_examen = self.examenes_ids[idx]
      else:
        codigo_examen = ""
    self.codigo_examen_actual = codigo_examen
    self.sesiones_actuales = sesiones
    
    alumnos_rojos = 0
    alumnos_naranjas = 0
    alumnos_verdes = 0
    
    anomalias_audio = 0
    objetos = 0
    procesos = 0
    teclado = 0
    total_anomalias = 0
    
    ranking = []
    
    
    # Construir mapa de cédulas desde la lista de inscritos del examen
    mapa_cedulas_examen = {}
    ex_actual = getattr(self, 'examenes_completos', {}).get(codigo_examen, {})
    inscritos = (
        ex_actual.get("estudiantesInscritos") or
        ex_actual.get("estudiantes") or
        ex_actual.get("listaEstudiantes") or []
    )
    for ins in inscritos:
      if isinstance(ins, dict):
        c = str(ins.get("cedula") or ins.get("documento") or ins.get("numeroDocumento") or "").strip()
        if c:
          nom_completo = f"{ins.get('nombre', '')} {ins.get('apellidos', '')}".strip().lower()
          if nom_completo:
            mapa_cedulas_examen[nom_completo] = c
          if ins.get("nombre"):
            mapa_cedulas_examen[str(ins.get("nombre")).strip().lower()] = c
          if ins.get("email"):
            mapa_cedulas_examen[str(ins.get("email")).strip().lower()] = c
          if ins.get("id"):
            mapa_cedulas_examen[str(ins.get("id")).strip().lower()] = c
          if ins.get("estudianteId"):
            mapa_cedulas_examen[str(ins.get("estudianteId")).strip().lower()] = c

    # Agrupar por estudiante
    estudiantes_unicos = {}
    self.nombres_estudiantes = {}
    
    for sesion in sesiones:
      sesion_id = sesion.get("sesionId") or sesion.get("id") or ""
      estudiante_id = sesion.get("estudianteId", "Desconocido")
      nombre_est = sesion.get("nombreEstudiante") or estudiante_id
      self.nombres_estudiantes[estudiante_id] = nombre_est

      # Buscar cédula en la sesión misma o en el objeto estudiante anidado
      cedula_sesion = (
          sesion.get("cedula") or 
          sesion.get("cedulaEstudiante") or 
          sesion.get("documento") or 
          sesion.get("documentoEstudiante") or 
          sesion.get("numeroDocumento") or 
          sesion.get("identificacion") or 
          sesion.get("estudianteCedula")
      )
      if not cedula_sesion and isinstance(sesion.get("estudiante"), dict):
          e_sub = sesion.get("estudiante")
          cedula_sesion = (
              e_sub.get("cedula") or 
              e_sub.get("documento") or 
              e_sub.get("numeroDocumento") or 
              e_sub.get("identificacion")
          )
      if not cedula_sesion:
          cedula_sesion = (
              mapa_cedulas_examen.get(nombre_est.strip().lower()) or 
              mapa_cedulas_examen.get(str(estudiante_id).strip().lower())
          )
      if not cedula_sesion:
          from utils.gestor_estudiantes import gestor_estudiantes
          cedula_sesion = gestor_estudiantes.obtener_cedula(
              nombre=nombre_est,
              estudiante_id=estudiante_id,
              email=sesion.get("email", "") or sesion.get("emailEstudiante", "")
          )
      
      # Sobrescribir siempre con la sesion mas reciente para ese estudiante (ignorar acumulados historicos)
      estudiantes_unicos[estudiante_id] = {
          "nombre": nombre_est,
          "cedula": str(cedula_sesion).strip() if cedula_sesion else "",
          "sesion_id": sesion_id,
          "alertas": []
      }
          
    # Ahora descargar las alertas SOLO de la ultima sesion de cada estudiante
    for estudiante_id, data in estudiantes_unicos.items():
      exito_al, alertas = cliente_api.obtener_alertas(data["sesion_id"])
      if exito_al and isinstance(alertas, list):
          data["alertas"] = alertas
          
    self.estudiantes_para_modal = []
    integridades_estudiantes = []

    for estudiante_id, data in estudiantes_unicos.items():
      nombre_est = data["nombre"]
      cedula_est = data.get("cedula", "")
      sesion_id = data["sesion_id"]
      alertas = data["alertas"]
      
      cant_alertas = len(alertas)
      es_fraude_inminente = False
      es_sospechoso = False
      deduccion_integridad = 0
      
      for al in alertas:
        clase = str(al.get("claseAlerta", "")).upper()
        if any(grave in clase for grave in ["OBJETO", "CELULAR", "PROCESO", "TECLADO", "SUPLANTACION", "FRAUDE", "EVASION", "MULTIPLES"]):
          es_fraude_inminente = True
          deduccion_integridad += 30
        elif any(medio in clase for medio in ["AUDIO", "VISION", "DESATENCION", "LEVANTANDOSE", "ROSTRO_NO_DETECTADO"]):
          es_sospechoso = True
          deduccion_integridad += 15
        else:
          deduccion_integridad += 5
          
      if es_fraude_inminente or cant_alertas >= 3:
        categoria_est = "ROJO"
        alumnos_rojos += 1
      elif es_sospechoso or cant_alertas > 0:
        categoria_est = "NARANJA"
        alumnos_naranjas += 1
      else:
        categoria_est = "VERDE"
        alumnos_verdes += 1

      integridades_estudiantes.append(max(0, 100 - deduccion_integridad))

      self.estudiantes_para_modal.append({
          "nombre": nombre_est,
          "cedula": cedula_est,
          "estudiante_id": estudiante_id,
          "sesion_id": sesion_id,
          "total_alertas": cant_alertas,
          "categoria_riesgo": categoria_est
      })
        
      for al in alertas:
        total_anomalias += 1
        clase = al.get("claseAlerta", "")
        if "AUDIO" in clase:
          anomalias_audio += 1
        elif ("VISION" in clase or "OBJETO" in clase):
          objetos += 1
        elif "PROCESO" in clase:
          procesos += 1
        elif "TECLADO" in clase:
          teclado += 1
          
      if cant_alertas > 0:
        ranking.append({"nombre": f"{nombre_est} ({estudiante_id})", "alertas": cant_alertas, "id": sesion_id})
        
    # Tarjetas Superiores
    self.val_top_rojo.setText(f"{alumnos_rojos} Alumnos")
    self.val_top_naranja.setText(f"{alumnos_naranjas} Alumnos")
    self.val_top_verde.setText(f"{alumnos_verdes} Alumnos")

    # Nuevas Tarjetas Analíticas (Fila 2)
    total_est = len(self.estudiantes_para_modal)
    if hasattr(self, 'val_kpi_total'):
      self.val_kpi_total.setText(f"{total_est} Alumnos")

    if hasattr(self, 'val_kpi_predominante'):
      conteo_anomalias = {
          "Visión y Objetos": objetos,
          "Audio": anomalias_audio,
          "Procesos": procesos,
          "Teclado": teclado
      }
      if total_anomalias > 0:
        pred = max(conteo_anomalias, key=conteo_anomalias.get)
        pct_pred = int((conteo_anomalias[pred] / total_anomalias) * 100)
        self.val_kpi_predominante.setText(f"{pred} ({pct_pred}%)")
      else:
        self.val_kpi_predominante.setText("Ninguna (0%)")

    # Fórmula 1 Ponderada: (Verdes * 1.0 + Naranjas * 0.5) / Total * 100
    if hasattr(self, 'val_kpi_transparencia'):
      if total_est > 0:
        transparencia = ((alumnos_verdes * 1.0 + alumnos_naranjas * 0.5) / total_est) * 100.0
      else:
        transparencia = 100.0
      self.val_kpi_transparencia.setText(f"{transparencia:.1f}%")

    # Actualizar botón de Directorio Completo
    if hasattr(self, 'btn_ver_todos_estudiantes'):
      self.btn_ver_todos_estudiantes.setText(f"👥 Ver Directorio Completo de Estudiantes ({total_est}) →")
      self.btn_ver_todos_estudiantes.setEnabled(total_est > 0)
    
    # Barras
    def calc_pct(valor, total):
      return int((valor / total) * 100) if total>0 else 0
      
    pct_audio = calc_pct(anomalias_audio, total_anomalias)
    pct_objetos = calc_pct(objetos, total_anomalias)
    pct_procesos = calc_pct(procesos, total_anomalias)
    pct_teclado = calc_pct(teclado, total_anomalias)
    
    self.val_an1.setText(f"{pct_audio}%")
    self.bar_an1.setValue(pct_audio)
    
    self.val_an2.setText(f"{pct_objetos}%")
    self.bar_an2.setValue(pct_objetos)
    
    self.val_an3.setText(f"{pct_procesos}%")
    self.bar_an3.setValue(pct_procesos)
    
    try:
      self.val_an4.setText(f"{pct_teclado}%")
      self.bar_an4.setValue(pct_teclado)
    except:
      pass

    # Actualizar Gráfico de Radar / Telaraña Forense
    if hasattr(self, 'grafico_radar') and self.grafico_radar:
      self.grafico_radar.actualizar_datos(
          anomalias_audio=anomalias_audio,
          anomalias_vision=objetos,
          anomalias_procesos=procesos,
          anomalias_teclado=teclado,
          pct_audio=pct_audio,
          pct_vision=pct_objetos,
          pct_procesos=pct_procesos,
          pct_teclado=pct_teclado,
          total_alertas=total_anomalias
      )
    
    # Ranking
    ranking.sort(key=lambda x: x["alertas"], reverse=True)
    
    if len(ranking)>0:
      self.ranking_item_1.setVisible(True)
      self.rank_name_1.setText(ranking[0]["nombre"])
      self.rank_al_1.setText(f"{ranking[0]['alertas']} Alertas")
      try: self.btn_ap_1.clicked.disconnect()
      except: pass
      self.btn_ap_1.clicked.connect(lambda checked, name=ranking[0]["nombre"], eid=ranking[0]["id"]: self.ver_detalle(name, eid))
    else:
      self.ranking_item_1.setVisible(False)
      
    if len(ranking)>1:
      self.ranking_item_2.setVisible(True)
      self.rank_name_2.setText(ranking[1]["nombre"])
      self.rank_al_2.setText(f"{ranking[1]['alertas']} Alertas")
      try: self.btn_ap_2.clicked.disconnect()
      except: pass
      self.btn_ap_2.clicked.connect(lambda checked, name=ranking[1]["nombre"], eid=ranking[1]["id"]: self.ver_detalle(name, eid))
    else:
      self.ranking_item_2.setVisible(False)
      
    if len(ranking)>2:
      self.ranking_item_3.setVisible(True)
      self.rank_name_3.setText(ranking[2]["nombre"])
      self.rank_al_3.setText(f"{ranking[2]['alertas']} Alertas")
      try: self.btn_ap_3.clicked.disconnect()
      except: pass
      self.btn_ap_3.clicked.connect(lambda checked, name=ranking[2]["nombre"], eid=ranking[2]["id"]: self.ver_detalle(name, eid))
    else:
      self.ranking_item_3.setVisible(False)
      
    # Veredicto Generativo de IA - cargar desde BD si existe, sino mostrar placeholder
    try:
        exito_bd, analisis_bd = cliente_api.obtener_analisis_ia(codigo_examen)
        if exito_bd and analisis_bd:
            resumen_bd = analisis_bd.get("resumenDetallado", "")
            puntaje_bd = analisis_bd.get("puntajeRiesgoCalculado", "—")
            modelo_bd = analisis_bd.get("modeloIaUtilizado", "IA local")
            if hasattr(self, 'badge_veredicto_modelo'):
              self.badge_veredicto_modelo.setText(f"🤖 Modelo: {modelo_bd}")
            if hasattr(self, 'badge_veredicto_riesgo'):
              self.badge_veredicto_riesgo.setText(f"🛡️ Riesgo Evaluado: {puntaje_bd}%")
            self.texto_veredicto.setText(resumen_bd)
        else:
            if hasattr(self, 'badge_veredicto_modelo'):
              self.badge_veredicto_modelo.setText("🤖 Modelo: Pendiente")
            if hasattr(self, 'badge_veredicto_riesgo'):
              self.badge_veredicto_riesgo.setText("🛡️ Riesgo Evaluado: —")
            self.texto_veredicto.setText(
                "💡 El análisis forense consolidado y perfil conductual de la clase por IA se generará cuando "
                "presiones el botón superior 'Analizar con IA y descargar reportes'.\n"
                "El modelo procesará todas las incidencias y emitirá un dictamen integral certificado."
            )
    except Exception as e:
        print(f"[ReporteIA] No se pudo cargar análisis de BD: {e}")
        self.texto_veredicto.setText("El análisis global de la clase aparecerá aquí una vez que se genere el reporte con IA.")

  def ver_detalle(self, nombre, id_estudiante):
    parent = self.window()
    if hasattr(parent, "abrir_carpetas_forenses"):
      parent.abrir_carpetas_forenses(nombre, id_estudiante)

  def abrir_directorio_estudiantes(self):
    if not hasattr(self, 'estudiantes_para_modal') or not self.estudiantes_para_modal:
      from PyQt6.QtWidgets import QMessageBox
      QMessageBox.information(self, "Directorio", "No hay estudiantes registrados en este examen.")
      return
    from vista.modal_estudiantes_reporte import ModalEstudiantesReporte
    idx = self.combo_examenes.currentIndex()
    codigo = self.examenes_ids[idx] if idx >= 0 and idx < len(self.examenes_ids) else "Examen"
    modal = ModalEstudiantesReporte(
        lista_estudiantes=self.estudiantes_para_modal,
        codigo_examen=codigo,
        callback_ver_detalle=self.ver_detalle,
        parent=self.window()
    )
    modal.exec()

  def generar_reporte_llm_global(self):
    """
    Genera un reporte consolidado usando Llama 3 para el examen seleccionado.
    """
    idx = self.combo_examenes.currentIndex()
    if idx < 0 or len(self.sesiones_actuales) == 0:
      from PyQt6.QtWidgets import QMessageBox
      QMessageBox.warning(self, "Atención", "No hay ningún examen o sesión seleccionada para analizar.")
      return
      
    self.btn_descargar_pdf.setEnabled(False)
    self.btn_descargar_pdf.setText("Generando reportes (IA)...")
    
    win = self.window()
    if hasattr(win, 'overlay_carga'):
      win.overlay_carga.mostrar("Generando dictamen forense con IA...\nAnalizando evidencias y preparando reportes...")
    
    texto_global = ""
    self.alertas_por_estudiante = {}
    self.mapa_id_corto = {}
    # Resumen estadístico por estudiante para el análisis global de clase
    resumen_estadistico = []

    for sesion in self.sesiones_actuales:
      s_id = sesion.get("sesionId")
      est_id = sesion.get("estudianteId", "Desc")
      nombre_est = sesion.get("nombreEstudiante") or est_id
      from api.cliente_respuesta import cliente_api
      ex, alertas = cliente_api.obtener_alertas(s_id)
      if ex and isinstance(alertas, list) and len(alertas) > 0:
        self.alertas_por_estudiante[est_id] = alertas
        cnt_audio = sum(1 for a in alertas if "AUDIO" in str(a.get("claseAlerta", "")).upper())
        cnt_vision = sum(1 for a in alertas if "VISION" in str(a.get("claseAlerta", "")).upper() or "OBJETO" in str(a.get("claseAlerta", "")).upper())
        cnt_proceso = sum(1 for a in alertas if "PROCESO" in str(a.get("claseAlerta", "")).upper())
        cnt_teclado = sum(1 for a in alertas if "TECLADO" in str(a.get("claseAlerta", "")).upper())
        resumen_estadistico.append(
          f"- {nombre_est} ({est_id}): {len(alertas)} alertas totales "
          f"[Audio: {cnt_audio}, Cámara/Objeto: {cnt_vision}, Proceso: {cnt_proceso}, Teclado: {cnt_teclado}]"
        )
        texto_global += f"\n--- Estudiante: {est_id} ({nombre_est}) ---\n"
        for i, al in enumerate(alertas):
          clase = al.get('claseAlerta', '')
          desc = al.get('objetoDetectado', '') or al.get('nombreProceso', '') or al.get('combinacionTeclas', '') or "Comportamiento sospechoso"
          id_real = str(al.get('idAlerta', '0'))
          id_corto = f"E{i+1}"
          self.mapa_id_corto[id_real] = id_corto
          # Las alertas de audio no se analizan por IA - se manejan localmente con texto fijo
          if "AUDIO" not in str(clase).upper():
            texto_global += f"- ID_{id_corto}: {clase} - {desc}\n"

    if not texto_global.strip():
      from PyQt6.QtWidgets import QMessageBox
      QMessageBox.information(self, "Clase Limpia", "Ningún estudiante cometió infracciones.")
      self.btn_descargar_pdf.setEnabled(True)
      self.btn_descargar_pdf.setText("Analizar con IA y descargar reportes")
      return

    total_estudiantes = len(self.alertas_por_estudiante)
    total_alertas = sum(len(alertas) for alertas in self.alertas_por_estudiante.values())
    resumen_est_texto = f"ESTADÍSTICAS TOTALES REALES DE LA CLASE: Hubo exactamente {total_estudiantes} estudiante(s) con infracciones, sumando un total global de {total_alertas} alertas.\n" + "\n".join(resumen_estadistico)

    import threading
    def tarea_llm():
      import json
      import urllib.request
      from PyQt6.QtWidgets import QMessageBox
      from PyQt6.QtCore import QTimer

      try:
        print("[LLM] Iniciando hilo para conectar con LM Studio...")
        prompt = f"""Eres un inspector académico forense de exámenes universitarios. Eres CONSERVADOR y ESTRICTO al clasificar evidencias.
Tienes el registro de incidencias de una sesión de examen. Analiza con rigor.

RESUMEN ESTADÍSTICO POR ESTUDIANTE:
{resumen_est_texto}

DETALLE DE ALERTAS (solo alertas de cámara, objetos, procesos y teclado - sin audio):
{texto_global}

INSTRUCCIONES ESTRICTAS:
1. En 'resumen_comportamiento': escribe un análisis detallado del comportamiento GLOBAL DE LA CLASE. DEBES usar EXACTAMENTE las 'ESTADÍSTICAS TOTALES REALES' proporcionadas arriba ({total_estudiantes} estudiante(s) y {total_alertas} alertas). NO sumes por tu cuenta, NO inventes otras cantidades de estudiantes ni de alertas. Menciona cuáles tipos predominaron y qué patrón general observas.
2. En 'veredicto_final': da una recomendación concreta al profesor sobre qué casos investigar con prioridad y por qué.
3. Para cada estudiante en 'analisis_evidencias': analiza EXACTAMENTE lo que dice la alerta. Si dice GIRO_IZQUIERDA, di que el estudiante giró la cabeza a la izquierda. Si dice OBJETO_CELULAR, di que se detectó un celular. NO inventes objetos ni comportamientos que no estén en la alerta.
4. Cada análisis de evidencia debe tener entre 3 y 5 oraciones completas. Explica: qué detectó el sistema, en qué contexto ocurrió dentro del examen, qué comportamiento implica esto, y qué debería evaluar el profesor al revisar la evidencia.
5. SOLO genera el análisis para los estudiantes EXPLÍCITAMENTE mencionados en el texto. NO INVENTES identificadores de estudiantes que no estén en los registros (ej. EST-2001).
6. CRITERIOS DE CLASIFICACIÓN MUY ESTRICTOS - ÚSALOS AL PIE DE LA LETRA:
   - [FRAUDE]: SOLO si hay detección directa e irrefutable de trampa: objeto como celular/libro/auriculares físicamente en uso, suplantación de identidad confirmada, uso de software prohibido claramente visible. Requiere evidencia visual clara.
   - [SOSPECHOSO]: Comportamientos ambiguos que podrían tener explicación inocente: girar la cabeza, desviar la mirada, uso de programas que pueden tener uso legítimo, atajos de teclado comunes, desatención momentánea.
   - [NORMAL]: Comportamiento que claramente no representa intento de fraude o cuya causa inocente es más probable.
   - NUNCA marques [FRAUDE] por simples giros de cabeza, desatención, o procesos normales del sistema. Se CONSERVADOR.

Usa este formato JSON EXACTO:
{{
  "probabilidad_fraude_porcentaje": 80,
  "resumen_comportamiento": "Análisis detallado de la clase basado en estadísticas reales...",
  "veredicto_final": "Recomendación concreta al profesor con casos prioritarios...",
  "estudiantes": [
    {{
      "id": "ID del estudiante",
      "conclusion_general": "Análisis psicológico/conductual del estudiante en 3-4 oraciones basado en sus alertas específicas",
      "analisis_evidencias": {{
        "ID_E1": "[FRAUDE/SOSPECHOSO/NORMAL] Descripción detallada en 3-5 oraciones. Qué detectó el sistema, qué implica, qué revisar.",
        "ID_E2": "[SOSPECHOSO] Descripción detallada..."
      }}
    }}
  ]
}}"""

        payload = {
          "model": "local-model",
          "messages": [
            {"role": "system", "content": "Eres un sistema de análisis forense de fraude en exámenes. Respondes SIEMPRE en formato JSON. Eres conservador y no marcas FRAUDE sin evidencia clara."},
            {"role": "user", "content": prompt}
          ],
          "temperature": 0.1,
          "max_tokens": 6000
        }
        
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request("http://127.0.0.1:1234/v1/chat/completions", data=data)
        req.add_header('Content-Type', 'application/json')
        
        print("[LLM] Haciendo POST a LM Studio...")
        try:
          response = urllib.request.urlopen(req, timeout=600.0) # 10 minutos para reportes gigantes
          resp_body = response.read().decode('utf-8')
          print("[LLM] Respuesta recibida exitosamente")
        except urllib.error.URLError as e:
          print(f"[LLM ERROR URL] {e}")
          self.senal_llm_error.emit(f"No se pudo conectar a LM Studio.\n\nAsegurate de que el servidor local de LM Studio este iniciado en el puerto 1234.\nDetalle: {e.reason}")
          return
        except Exception as e:
          print(f"[LLM ERROR EXTRA] {e}")
          self.senal_llm_error.emit(str(e))
          return
        
        resp_json = json.loads(resp_body)
        contenido = resp_json["choices"][0]["message"]["content"].strip()
        
        if contenido.startswith("```json"):
          contenido = contenido[7:]
        elif contenido.startswith("```"):
          contenido = contenido[3:]
        if contenido.endswith("```"):
          contenido = contenido[:-3]
        contenido = contenido.strip()
        
        try:
          import re
          # Limpiar comas huérfanas al final de listas/diccionarios generadas por LLMs
          contenido_limpio = re.sub(r',\s*}', '}', contenido)
          contenido_limpio = re.sub(r',\s*]', ']', contenido_limpio)
          datos = json.loads(contenido_limpio)
          
          # Inyectar el nombre real del modelo que procesó la solicitud (dinámico)
          datos["modelo_usado_api"] = resp_json.get("model", "Meta Llama 3.1 8B Instruct")
          
          self.senal_llm_exito.emit(datos)
        except json.JSONDecodeError:
          self.senal_llm_error.emit("LM Studio no devolvio un JSON valido. Intentalo de nuevo.")
          
      except Exception as e:
        self.senal_llm_error.emit(str(e))
        
    t = threading.Thread(target=tarea_llm, daemon=True)
    t.start()

  def mostrar_error_llm(self, mensaje):
    win = self.window()
    if hasattr(win, 'overlay_carga'):
      win.overlay_carga.ocultar()
    from PyQt6.QtWidgets import QMessageBox
    QMessageBox.critical(self, "Error LM Studio", mensaje)
    self.btn_descargar_pdf.setEnabled(True)
    self.btn_descargar_pdf.setText("Analizar con IA y descargar reportes")

  def mostrar_resultado_llm(self, datos_json):
    win = self.window()
    if hasattr(win, 'overlay_carga'):
      win.overlay_carga.ocultar()
    from PyQt6.QtWidgets import QMessageBox
    self.btn_descargar_pdf.setEnabled(True)
    self.btn_descargar_pdf.setText("Analizar con IA y descargar reportes")

    prob = datos_json.get("probabilidad_fraude_porcentaje", 0)
    resumen = datos_json.get("resumen_comportamiento", "Sin resumen")
    veredicto = datos_json.get("veredicto_final", "Inconcluso")
    modelo_dinamico = datos_json.get("modelo_usado_api", "Meta Llama 3.1 8B Instruct")

    texto_ui = f"DICTAMEN FORENSE CERTIFICADO\n\n{resumen}\n\nRECOMENDACIÓN DEL TRIBUNAL DE IA:\n{veredicto}"
    try:
        self.texto_veredicto.setText(texto_ui)
        if hasattr(self, 'badge_veredicto_modelo'):
          self.badge_veredicto_modelo.setText(f"🤖 Modelo: {modelo_dinamico}")
        if hasattr(self, 'badge_veredicto_riesgo'):
          self.badge_veredicto_riesgo.setText(f"🛡️ Riesgo Evaluado: {prob}%")
    except:
        pass

    # Guardar el análisis en la base de datos para que persista
    idx = self.combo_examenes.currentIndex()
    if idx >= 0 and idx < len(self.examenes_ids):
        codigo_examen = self.examenes_ids[idx]
        modelo_dinamico = datos_json.get("modelo_usado_api", "Meta Llama 3.1 8B Instruct")
        guardado = cliente_api.guardar_analisis_ia(codigo_examen, resumen, veredicto, prob, modelo_dinamico)
        if guardado:
            print(f"[ReporteIA] Análisis de IA guardado en BD para examen {codigo_examen} usando modelo {modelo_dinamico}")
        else:
            print(f"[ReporteIA] Advertencia: no se pudo guardar el análisis en BD")

    ruta_carpeta = self.generar_pdf_reporte(datos_json)
    QMessageBox.information(self, "Reportes Generados", f"Los reportes individuales se guardaron en la carpeta:\n{ruta_carpeta}")

  def generar_pdf_reporte(self, datos_json):
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas
    from reportlab.lib import colors
    import os
    import textwrap
    
    prob = datos_json.get("probabilidad_fraude_porcentaje", 0)
    resumen = datos_json.get("resumen_comportamiento", "Sin resumen")
    veredicto = datos_json.get("veredicto_final", "Inconcluso")
    estudiantes = datos_json.get("estudiantes", [])

    descargas = os.path.join(os.path.expanduser('~'), 'Downloads', 'Reportes_Fraude_IA')
    
    idx = self.combo_examenes.currentIndex()
    if idx >= 0:
      nombre_examen = self.combo_examenes.currentText().split(" - ")[0].replace("Examen: ", "")
    else:
      nombre_examen = "General"
      
    # Crear carpeta específica para el examen
    carpeta_examen = os.path.join(descargas, nombre_examen)
    os.makedirs(carpeta_examen, exist_ok=True)
    
    ancho, alto = letter
    
    # Colores
    color_upc = colors.Color(0, 59/255.0, 19/255.0) # Verde
    color_amarillo = colors.Color(241/255.0, 196/255.0, 15/255.0) # Amarillo UPC
    color_gris = colors.Color(235/255.0, 237/255.0, 239/255.0)
    
    def dibujar_cabecera(c, titulo, subtitulo):
        # Fondo gris claro
        c.setFillColor(color_gris)
        c.rect(0, 0, ancho, alto, fill=1, stroke=0)
        
        # Franja Verde
        c.setFillColor(color_upc)
        c.rect(0, alto - 80, ancho, 80, fill=1, stroke=0)
        # Linea amarilla
        c.setFillColor(color_amarillo)
        c.rect(0, alto - 85, ancho, 5, fill=1, stroke=0)
        
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 12)
        c.drawString(40, alto - 25, "UNIVERSIDAD POPULAR DEL CESAR")
        c.setFont("Helvetica-Bold", 22)
        c.drawString(40, alto - 60, titulo)
        
        c.setFillColor(color_amarillo)
        c.setFont("Helvetica-Bold", 14)
        c.drawRightString(ancho - 40, alto - 45, subtitulo)
        c.setFillColor(colors.black)

    # --- Generar un PDF individual por cada estudiante ---
    for est in estudiantes:
      id_est = str(est.get("id", "Desconocido"))
      # Si el id tiene "ID_EST-2000" quitarle el prefijo si lo tiene
      if id_est.startswith("ID_"):
          id_est = id_est[3:]
          
      # Evitar alucinaciones de la IA: si el estudiante no tiene alertas reales, saltarlo
      alertas_est = self.alertas_por_estudiante.get(id_est, [])
      if not alertas_est:
        for k, v in self.alertas_por_estudiante.items():
            if id_est in k or k in id_est:
                alertas_est = v
                break
      if not alertas_est:
          continue
          
      nombre_est = getattr(self, 'nombres_estudiantes', {}).get(id_est, id_est)
      # Limpiar nombre para nombre de archivo (remover espacios extra, caracteres inválidos)
      import re
      nombre_est_limpio = re.sub(r'[<>:"/\\|?*]', '_', nombre_est).strip()
          
      ruta_pdf_est = os.path.join(carpeta_examen, f"Reporte_detalles_{nombre_examen}_{nombre_est_limpio}.pdf")
      c = canvas.Canvas(ruta_pdf_est, pagesize=letter)
      conclusion = str(est.get("conclusion_general", "Sin datos"))
      dict_evidencias = est.get("analisis_evidencias", {})

      dibujar_cabecera(c, "Análisis Individual", f"Estudiante: {id_est}")



      c.setFillColor(colors.white)
      c.rect(40, 40, ancho - 80, alto - 140, fill=1, stroke=0)
      c.setFillColor(colors.black)

      # --- Resumen estadístico del estudiante ---
      cnt_total = len(alertas_est)
      cnt_audio_e = sum(1 for a in alertas_est if "AUDIO" in str(a.get("claseAlerta","")).upper())
      cnt_vision_e = sum(1 for a in alertas_est if "VISION" in str(a.get("claseAlerta","")).upper() or "OBJETO" in str(a.get("claseAlerta","")).upper() or "MULTIPLES" in str(a.get("claseAlerta","")).upper() or "DESATENCION" in str(a.get("claseAlerta","")).upper() or "GIRO" in str(a.get("claseAlerta","")).upper())
      cnt_proceso_e = sum(1 for a in alertas_est if "PROCESO" in str(a.get("claseAlerta","")).upper())
      cnt_teclado_e = sum(1 for a in alertas_est if "TECLADO" in str(a.get("claseAlerta","")).upper())

      # Título de resumen
      c.setFont("Helvetica-Bold", 13)
      c.drawString(50, alto - 115, "Resumen de Alertas del Estudiante:")

      # Texto con conteos
      c.setFont("Helvetica", 11)
      y_res = alto - 135
      c.drawString(55, y_res, f"Total de alertas registradas: {cnt_total}")
      y_res -= 16
      if cnt_audio_e > 0:
          c.drawString(55, y_res, f"  • Alertas de Micrófono (Audio): {cnt_audio_e}")
          y_res -= 14
      if cnt_vision_e > 0:
          c.drawString(55, y_res, f"  • Alertas de Cámara / Comportamiento Visual: {cnt_vision_e}")
          y_res -= 14
      if cnt_proceso_e > 0:
          c.drawString(55, y_res, f"  • Alertas de Programa Bloqueado: {cnt_proceso_e}")
          y_res -= 14
      if cnt_teclado_e > 0:
          c.drawString(55, y_res, f"  • Alertas de Atajo de Teclado: {cnt_teclado_e}")
          y_res -= 14

      # --- Gráfico de Torta (usando ReportLab puro) ---
      import math
      if cnt_total > 0:
          y_res -= 10
          cx = 140  # centro X del gráfico
          cy = y_res - 70  # centro Y
          radio = 60

          categorias = []
          colores_pie = []
          if cnt_audio_e > 0:
              categorias.append(("Audio", cnt_audio_e, colors.Color(52/255, 152/255, 219/255)))
          if cnt_vision_e > 0:
              categorias.append(("Cámara/Visión", cnt_vision_e, colors.Color(231/255, 76/255, 60/255)))
          if cnt_proceso_e > 0:
              categorias.append(("Proceso", cnt_proceso_e, colors.Color(243/255, 156/255, 18/255)))
          if cnt_teclado_e > 0:
              categorias.append(("Teclado", cnt_teclado_e, colors.Color(39/255, 174/255, 96/255)))

          angulo_inicio = 90.0  # empieza desde arriba
          for (nombre_cat, cantidad_cat, color_cat) in categorias:
              porcentaje = cantidad_cat / cnt_total
              angulo_fin = angulo_inicio - (porcentaje * 360.0)
              c.setFillColor(color_cat)
              c.setStrokeColor(colors.white)
              c.setLineWidth(1.5)
              c.wedge(cx - radio, cy - radio, cx + radio, cy + radio,
                      angulo_fin, angulo_inicio - angulo_fin,
                      fill=1, stroke=1)
              angulo_inicio = angulo_fin

          # Leyenda al lado del gráfico
          lx = cx + radio + 20
          ly = cy + 50
          c.setFont("Helvetica-Bold", 10)
          c.setFillColor(colors.black)
          c.drawString(lx, ly + 12, "Distribución de Alertas:")
          ly -= 5
          c.setFont("Helvetica", 10)
          for (nombre_cat, cantidad_cat, color_cat) in categorias:
              pct = round(cantidad_cat / cnt_total * 100)
              c.setFillColor(color_cat)
              c.rect(lx, ly, 12, 12, fill=1, stroke=0)
              c.setFillColor(colors.black)
              c.drawString(lx + 18, ly + 2, f"{nombre_cat}: {cantidad_cat} ({pct}%)")
              ly -= 18

          y_res = cy - radio - 20

      # Separador
      y_res -= 5
      c.setStrokeColor(color_amarillo)
      c.setLineWidth(2)
      c.line(50, y_res, ancho - 50, y_res)
      c.setStrokeColor(colors.black)
      c.setLineWidth(1)
      y_res -= 15

      # --- Perfil Psicológico y Conductual ---
      c.setFont("Helvetica-Bold", 13)
      c.setFillColor(colors.black)
      c.drawString(50, y_res, "Perfil Psicológico y Conductual (Generado por IA):")
      y_res -= 18

      c.setFont("Helvetica", 11)
      txt_perfil = c.beginText(50, y_res)
      for p in conclusion.split('\n'):
          for linea in textwrap.wrap(p, width=90):
              txt_perfil.textLine(linea)
              if txt_perfil.getY() < 80:
                  c.drawText(txt_perfil)
                  c.showPage()
                  dibujar_cabecera(c, "Análisis Individual (Cont.)", f"Estudiante: {id_est}")
                  c.setFillColor(colors.white)
                  c.rect(40, 40, ancho - 80, alto - 140, fill=1, stroke=0)
                  c.setFillColor(colors.black)
                  txt_perfil = c.beginText(50, alto - 110)
                  txt_perfil.setFont("Helvetica", 11)
          txt_perfil.moveCursor(0, 5)
      c.drawText(txt_perfil)

      y_pos = txt_perfil.getY() - 25

      # Separador antes de evidencias
      c.setStrokeColor(color_amarillo)
      c.setLineWidth(2)
      c.line(50, y_pos, ancho - 50, y_pos)
      c.setStrokeColor(colors.black)
      c.setLineWidth(1)
      y_pos -= 18

      c.setFont("Helvetica-Bold", 13)
      c.setFillColor(colors.black)
      c.drawString(50, y_pos, "Desglose de Evidencias:")
      y_pos -= 20

      for al in alertas_est:
        if y_pos < 300:
            c.showPage()
            dibujar_cabecera(c, "Evidencias", f"Estudiante: {id_est}")
            c.setFillColor(colors.white)
            c.rect(40, 40, ancho - 80, alto - 140, fill=1, stroke=0)
            c.setFillColor(colors.black)
            y_pos = alto - 120

        id_alerta = str(al.get('idAlerta', '0'))
        clase_al = al.get('claseAlerta', '')
        desc = al.get('objetoDetectado', '') or al.get('nombreProceso', '') or al.get('combinacionTeclas', '') or "Evidencia"

        # 1. Dibujar Imagen
        img_path = al.get('urlFotoWebcam') or al.get('urlCapturaPantalla')
        if img_path:
            abs_path = os.path.join(os.path.expanduser('~'), 'Documents', 'evidencias_examenes', img_path.replace("/", os.sep).replace("\\", os.sep))
            if not os.path.exists(abs_path):
                from api.cliente_respuesta import cliente_api
                os.makedirs(os.path.dirname(abs_path), exist_ok=True)
                cliente_api.descargar_evidencia(img_path, abs_path)
            if os.path.exists(abs_path):
                import io, base64
                from cryptography.fernet import Fernet
                from config.configuracion import AES_SECRET_KEY
                from reportlab.lib.utils import ImageReader
                
                img_data = None
                try:
                    with open(abs_path, 'rb') as f:
                        cont_cifrado = f.read()
                    try:
                        f_crypto = Fernet(AES_SECRET_KEY)
                        b64_desc = f_crypto.decrypt(cont_cifrado).decode('utf-8')
                        img_data = base64.b64decode(b64_desc)
                    except Exception:
                        img_data = cont_cifrado # Fallback por si la imagen está en texto plano
                except Exception as e:
                    pass
                    
                if img_data:
                    try:
                        img_io = io.BytesIO(img_data)
                        ir = ImageReader(img_io)
                        c.drawImage(ir, (ancho - 320)/2, y_pos - 180, width=320, height=180, preserveAspectRatio=True)
                        y_pos -= 190
                    except Exception as e:
                        c.setFont("Helvetica-Oblique", 10)
                        c.drawString(50, y_pos, "(La evidencia no se pudo descifrar)")
                        y_pos -= 20
                else:
                    c.setFont("Helvetica-Oblique", 10)
                    c.drawString(50, y_pos, "(Evidencia dañada)")
                    y_pos -= 20
            else:
                c.setFont("Helvetica-Oblique", 10)
                c.setFillColor(colors.gray)
                c.drawString(50, y_pos, "(Imagen no disponible localmente ni en servidor)")
                c.setFillColor(colors.black)
                y_pos -= 20
        else:
            y_pos -= 10

        # 2. Dibujar Titulo
        c.setFont("Helvetica-Bold", 12)
        c.setFillColor(color_upc)

        tipo_ev = ""
        if "VISION" in str(clase_al).upper() or "OBJETO" in str(clase_al).upper() or "MULTIPLES" in str(clase_al).upper() or "DESATENCION" in str(clase_al).upper() or "GIRO" in str(clase_al).upper():
            tipo_ev = "Cámara de Video"
        elif "PROCESO" in str(clase_al).upper():
            tipo_ev = "Programa Bloqueado"
        elif "TECLADO" in str(clase_al).upper():
            tipo_ev = "Atajo Bloqueado"
        elif "AUDIO" in str(clase_al).upper():
            tipo_ev = "Micrófono (Voz)"
        else:
            tipo_ev = clase_al

        id_corto = self.mapa_id_corto.get(id_alerta, id_alerta)
        c.drawString(50, y_pos, f"Evidencia {id_corto}: {tipo_ev} - {desc}")
        c.setFillColor(colors.black)
        y_pos -= 18

        # 3. Dibujar Análisis IA (o texto fijo para audio)
        if "AUDIO" in str(clase_al).upper():
            analisis_ia = "[SOSPECHOSO] Esta alerta de audio requiere revisión manual por parte del profesor. La IA no puede determinar el contenido del audio capturado; le corresponde al profesor escuchar el archivo de evidencia para evaluar si representa una conducta fraudulenta."
        else:
            analisis_ia = dict_evidencias.get(f"ID_{id_corto}") or dict_evidencias.get(id_corto) or "La IA no proporcionó un análisis detallado para esta captura."

        c.setFont("Helvetica", 11)
        txt_ev = c.beginText(50, y_pos)
        for p in str(analisis_ia).split('\n'):
            for linea in textwrap.wrap(p, width=95):
                txt_ev.textLine(linea)
                if txt_ev.getY() < 60:
                    c.drawText(txt_ev)
                    c.showPage()
                    dibujar_cabecera(c, "Evidencias (Cont.)", f"Estudiante: {id_est}")
                    c.setFillColor(colors.white)
                    c.rect(40, 40, ancho - 80, alto - 140, fill=1, stroke=0)
                    c.setFillColor(colors.black)
                    txt_ev = c.beginText(50, alto - 110)
                    txt_ev.setFont("Helvetica", 11)
        c.drawText(txt_ev)

        y_pos = txt_ev.getY() - 35

      # Cerrar y guardar el PDF del estudiante actual
      c.save()

    return carpeta_examen
