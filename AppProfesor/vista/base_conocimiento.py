# base_conocimiento.py
# --------------------------------------------------------------------
# Base de conocimiento del Asistente Virtual del Panel Docente.
# Estructura: árbol de decisiones por menús y submenús.
# Para agregar nuevas preguntas/respuestas, solo edita este archivo.
# NO modifiques el archivo modal_chatbot.py para cambiar contenido.
# --------------------------------------------------------------------

BIENVENIDA = (
    "¡Hola, profesor! 👋 Soy tu Asistente Virtual del Panel Docente.\n\n"
    "Estoy aquí para ayudarte a resolver cualquier duda sobre el sistema "
    "de supervisión. Selecciona el tema en el que necesitas ayuda:"
)

# Cada nodo del árbol puede ser:
#   - Un MENÚ (tiene clave "opciones"): muestra botones de navegación
#   - Una HOJA  (tiene clave "respuesta"): muestra texto y permite volver

MENU_PRINCIPAL = {
    "titulo": "📋 Menú Principal",
    "opciones": [
        {
            "etiqueta": "📝  Gestión de Exámenes",
            "nodo": "examenes"
        },
        {
            "etiqueta": "🎥  Sala de Supervisión",
            "nodo": "supervision"
        },
        {
            "etiqueta": "🤖  Reportes de Inteligencia Artificial",
            "nodo": "reportes"
        },
        {
            "etiqueta": "⚖️  Segunda Revisión y Apelaciones",
            "nodo": "apelaciones"
        },
        {
            "etiqueta": "🛡️  Seguridad y Auditoría Forense",
            "nodo": "forense"
        },
    ]
}

ARBOL = {

    # ──────────────────────────────────────────────────────────────
    # 1. GESTIÓN DE EXÁMENES
    # ──────────────────────────────────────────────────────────────
    "examenes": {
        "titulo": "📝 Gestión de Exámenes",
        "intro": "Perfecto. Sobre la gestión de exámenes, ¿qué deseas consultar?",
        "opciones": [
            {"etiqueta": "¿Cómo creo un nuevo examen?",             "nodo": "examenes_crear"},
            {"etiqueta": "¿Para qué sirve el PIN de sesión?",        "nodo": "examenes_pin"},
            {"etiqueta": "¿Qué significan los estados del examen?",  "nodo": "examenes_estados"},
            {"etiqueta": "¿Cómo abro o cierro un examen?",          "nodo": "examenes_abrir_cerrar"},
            {"etiqueta": "¿Cómo edito un examen ya creado?",         "nodo": "examenes_editar"},
            {"etiqueta": "¿Cómo subo la lista de estudiantes?",      "nodo": "examenes_csv"},
            {"etiqueta": "¿Qué módulos de IA puedo configurar?",     "nodo": "examenes_ia_modulos"},
            {"etiqueta": "¿Qué es la Sensibilidad de IA?",           "nodo": "examenes_sensibilidad"},
            {"etiqueta": "¿Cómo configuro programas y URLs permitidas?", "nodo": "examenes_permisos"},
        ]
    },
    "examenes_crear": {
        "respuesta": (
            "📝 **Cómo crear un nuevo examen — Paso a paso**\n\n"
            "**Paso 1 — Datos básicos:**\n"
            "1. En el menú lateral, haz clic en el logo o en el Dashboard.\n"
            "2. Presiona el botón verde **'+ Nuevo Examen'**.\n"
            "3. Completa los campos:\n"
            "   • **Materia / Código** → Ej: MAT-101 o Cálculo I\n"
            "   • **Fecha de inicio** → Selecciona la fecha del examen\n"
            "   • **Hora de inicio** → Selecciona la hora en formato AM/PM\n"
            "   • **Duración** → Minutos totales del examen (ej: 90)\n"
            "4. Presiona **'Siguiente →'**.\n\n"
            "**Paso 2 — Configuración de IA:**\n"
            "5. Activa o desactiva los módulos de supervisión que desees.\n"
            "6. Selecciona el nivel de Sensibilidad de IA.\n"
            "7. Opcionalmente, sube el CSV con la lista de estudiantes.\n"
            "8. Presiona **'Finalizar'**.\n\n"
            "✅ El examen aparecerá en tu Dashboard listo para usarse."
        )
    },
    "examenes_pin": {
        "respuesta": (
            "🔑 **El PIN de Sesión**\n\n"
            "El PIN de sesión es un **código numérico único** asignado automáticamente a cada examen.\n\n"
            "**¿Para qué sirve?**\n"
            "Los estudiantes deben ingresar este PIN en la aplicación de supervisión (AppSupervision) "
            "para unirse al examen correcto. Sin el PIN, no pueden acceder.\n\n"
            "**¿Dónde lo encuentro?**\n"
            "Está visible en la tarjeta de cada examen en tu Dashboard, debajo del nombre de la materia.\n\n"
            "**¿Cómo lo comparto?**\n"
            "Compártelo directamente con tus estudiantes antes de iniciar el examen (por correo, pantalla o verbalmente).\n\n"
            "⚠️ El PIN solo funciona cuando el examen está en estado **ACTIVO** (acceso abierto)."
        )
    },
    "examenes_estados": {
        "respuesta": (
            "🚦 **Estados de un Examen**\n\n"
            "Cada examen tiene uno de estos tres estados:\n\n"
            "🔵 **PROGRAMADO** → La fecha y hora de inicio aún no han llegado. "
            "Los estudiantes no pueden conectarse todavía.\n\n"
            "🟢 **ACTIVO / EN CURSO** → El examen está abierto. Los estudiantes pueden "
            "ingresar con el PIN y el sistema está supervisando en tiempo real.\n\n"
            "⚪ **FINALIZADO** → El examen terminó. Ya no acepta nuevas conexiones. "
            "Las evidencias y reportes quedan disponibles para revisión posterior.\n\n"
            "💡 Los estados cambian automáticamente según la fecha/hora configurada, "
            "pero también puedes abrirlo o cerrarlo manualmente con el botón de la tarjeta."
        )
    },
    "examenes_abrir_cerrar": {
        "respuesta": (
            "🔓🔒 **Abrir y Cerrar un Examen Manualmente**\n\n"
            "En cada tarjeta de examen del Dashboard verás un botón que dice:\n\n"
            "• **'Abrir'** → Activa el examen inmediatamente (permite que los estudiantes entren con el PIN) aunque aún no sea la hora programada.\n\n"
            "• **'Cerrar'** → Cierra el acceso al examen. Los estudiantes conectados serán desconectados y no se aceptarán nuevas conexiones.\n\n"
            "⚠️ **Importante:** Cerrar un examen desde el Dashboard NO lo finaliza permanentemente. "
            "Para finalizarlo de forma definitiva, usa el botón **'Finalizar Examen'** dentro de la Sala de Supervisión."
        )
    },
    "examenes_editar": {
        "respuesta": (
            "✏️ **Editar un Examen Existente**\n\n"
            "1. En el Dashboard, busca la tarjeta del examen que deseas modificar.\n"
            "2. Haz clic en el botón **⚙ (configuración)** en la esquina superior derecha de la tarjeta.\n"
            "3. Se abrirá un modal de edición con los **mismos 2 pasos** de creación, pero con los datos ya rellenados.\n\n"
            "**¿Qué puedes editar?**\n"
            "• Fecha, hora y duración del examen.\n"
            "• Todos los módulos de IA y su sensibilidad.\n"
            "• URLs y programas permitidos.\n"
            "• Subir una nueva lista de estudiantes CSV.\n\n"
            "⚠️ El nombre de la materia **no se puede cambiar** una vez creado el examen."
        )
    },
    "examenes_csv": {
        "respuesta": (
            "📄 **Subir Lista de Estudiantes (CSV)**\n\n"
            "Puedes cargar todos tus estudiantes de una sola vez con un archivo CSV.\n\n"
            "**Formato requerido del CSV:**\n"
            "El archivo debe tener estas columnas (en cualquier orden):\n"
            "| nombre | apellidos | cedula | email |\n\n"
            "Ejemplo:\n"
            "```\nnombre,apellidos,cedula,email\nJuan,Pérez García,12345678,juan@correo.com\nMaría,López Ruiz,87654321,maria@correo.com\n```\n\n"
            "**¿Cómo cargarlo?**\n"
            "1. En el Paso 2 de creación (o edición) del examen, haz clic en **'Adjuntar Lista CSV'**.\n"
            "2. Selecciona tu archivo CSV.\n"
            "3. Si el formato es correcto, el botón cambiará a verde mostrando **'Lista Adjunta (N estudiantes)'**.\n"
            "4. Al finalizar, el sistema inscribirá a todos automáticamente.\n\n"
            "💡 El sistema es flexible con mayúsculas/minúsculas en los encabezados."
        )
    },
    "examenes_ia_modulos": {
        "respuesta": (
            "🤖 **Módulos de IA disponibles**\n\n"
            "Al configurar un examen, puedes activar o desactivar 5 módulos de supervisión:\n\n"
            "👁️ **Reconocimiento Facial** → Compara el rostro del estudiante con su foto registrada. "
            "Si el rostro no coincide o desaparece, genera una alerta de suplantación.\n\n"
            "📦 **Detección de Objetos** → Analiza las imágenes de la cámara para detectar "
            "celulares, libros, auriculares u otros objetos no permitidos.\n\n"
            "🎤 **Análisis de Audio** → Detecta voces adicionales o ruidos sospechosos mediante el micrófono del estudiante.\n\n"
            "💻 **Monitoreo de Procesos** → Verifica qué aplicaciones están abiertas en el PC del estudiante. "
            "Si abre una prohibida, genera alerta inmediata.\n\n"
            "⌨️ **Análisis de Teclado** → Detecta atajos prohibidos como Alt+Tab, Ctrl+C, "
            "la tecla Windows, etc.\n\n"
            "💡 Por defecto, los módulos de Audio vienen desactivados. Los demás vienen activos."
        )
    },
    "examenes_sensibilidad": {
        "respuesta": (
            "📊 **Sensibilidad de IA — ¿Qué significa?**\n\n"
            "La sensibilidad controla qué tan agresiva es la IA para generar alertas.\n\n"
            "🟢 **BAJA** → Solo genera alertas cuando hay evidencia muy clara y contundente de fraude. "
            "Menos alertas, pero mayor certeza. Recomendada para grupos de alto rendimiento o exámenes breves.\n\n"
            "🟡 **MEDIA** *(recomendada)* → Equilibrio entre detección y falsos positivos. "
            "Ideal para la mayoría de exámenes.\n\n"
            "🔴 **ALTA** → Muy sensible. Genera alertas ante el mínimo comportamiento sospechoso. "
            "Más alertas, pero puede incluir falsos positivos (comportamientos normales marcados como fraude).\n\n"
            "💡 Tip: Si recibes muchas alertas de comportamientos normales, baja la sensibilidad para futuros exámenes."
        )
    },
    "examenes_permisos": {
        "respuesta": (
            "🌐 **Configurar Programas y URLs Permitidas**\n\n"
            "En el Paso 2 de configuración puedes especificar qué aplicaciones y sitios web "
            "están autorizados durante el examen.\n\n"
            "**URLs Permitidas:**\n"
            "Ingresa las direcciones web que los estudiantes pueden consultar, separadas por comas.\n"
            "Ejemplo: `https://docs.python.org, https://developer.mozilla.org`\n\n"
            "**Programas Permitidos:**\n"
            "Ingresa los nombres de los ejecutables que pueden tener abiertos, separados por comas.\n"
            "Ejemplo: `calculadora.exe, notepad.exe, python.exe`\n\n"
            "⚠️ Si el módulo de **Monitoreo de Procesos** está activo y el estudiante abre un programa "
            "que no está en esta lista, el sistema generará una alerta de tipo PROCESO."
        )
    },

    # ──────────────────────────────────────────────────────────────
    # 2. SALA DE SUPERVISIÓN
    # ──────────────────────────────────────────────────────────────
    "supervision": {
        "titulo": "🎥 Sala de Supervisión",
        "intro": "Entendido. Sobre la sala de supervisión en tiempo real, ¿qué necesitas saber?",
        "opciones": [
            {"etiqueta": "¿Cómo entro a supervisar un examen?",          "nodo": "sv_entrar"},
            {"etiqueta": "¿Qué significa el % de Integridad IA?",        "nodo": "sv_integridad"},
            {"etiqueta": "¿Cómo veo la cámara de un estudiante?",        "nodo": "sv_camara"},
            {"etiqueta": "¿Cómo envío una advertencia a un estudiante?", "nodo": "sv_advertencia"},
            {"etiqueta": "¿Cómo marco a un estudiante por fraude?",      "nodo": "sv_fraude"},
            {"etiqueta": "¿Qué es el Feed de Alertas?",                  "nodo": "sv_feed"},
            {"etiqueta": "¿Qué es el Mapa GPS?",                         "nodo": "sv_mapa"},
            {"etiqueta": "¿Cómo finalizo el examen?",                    "nodo": "sv_finalizar"},
            {"etiqueta": "Perdí la conexión, ¿qué hago?",                "nodo": "sv_conexion"},
        ]
    },
    "sv_entrar": {
        "respuesta": (
            "🎥 **Cómo entrar a supervisar un examen**\n\n"
            "1. Ve al **Dashboard** (pantalla principal).\n"
            "2. Busca la tarjeta del examen que deseas supervisar.\n"
            "3. Verifica que el examen esté en estado **ACTIVO** (badge verde).\n"
            "4. Haz clic en el botón **'Entrar a Supervisar'**.\n\n"
            "El sistema cargará la Sala de Supervisión con todos los estudiantes "
            "que ya se hayan conectado con el PIN del examen.\n\n"
            "⚡ Una vez dentro, la sala se actualiza en **tiempo real** mediante WebSocket: "
            "cada nueva alerta o estudiante que se conecte aparece automáticamente sin necesidad de recargar."
        )
    },
    "sv_integridad": {
        "respuesta": (
            "📊 **Porcentaje de Integridad IA**\n\n"
            "Es la métrica principal que indica qué tan 'limpia' es la sesión de cada estudiante.\n\n"
            "**¿Cómo funciona?**\n"
            "Cada estudiante comienza con **100% de integridad**. Cada alerta que genera el sistema "
            "descuenta puntos automáticamente:\n\n"
            "🔴 Alerta nivel ALTO → descuenta **30 puntos**\n"
            "🟠 Alerta nivel MEDIO → descuenta **15 puntos**\n"
            "🟡 Alerta nivel BAJO → descuenta **5 puntos**\n\n"
            "**Semáforo de colores:**\n"
            "🟢 ≥ 80% → Comportamiento normal\n"
            "🟠 50% – 79% → Comportamiento sospechoso\n"
            "🔴 < 50% → Fraude inminente — Requiere atención inmediata\n\n"
            "💡 Esta métrica es una guía; la decisión final siempre es tuya como profesor."
        )
    },
    "sv_camara": {
        "respuesta": (
            "📷 **Cómo ver la cámara de un estudiante**\n\n"
            "1. En la Sala de Supervisión, localiza la tarjeta del estudiante.\n"
            "2. Haz clic en el botón **'Ver Cámara'** en su tarjeta.\n"
            "3. Se abrirá la vista de **Detalle del Estudiante** con el video en vivo.\n\n"
            "**Indicadores de calidad del stream:**\n"
            "🟢 **Buena** → El video se recibe en menos de 0.5 segundos por frame\n"
            "🟠 **Regular** → Entre 0.5 y 2 segundos por frame\n"
            "🔴 **Mala** → Más de 2 segundos; posible mala conexión del estudiante\n\n"
            "💡 El stream de video **se activa bajo demanda**: solo consume ancho de banda "
            "cuando estás en la vista de detalle. Al volver a la sala, se detiene automáticamente."
        )
    },
    "sv_advertencia": {
        "respuesta": (
            "⚠️ **Cómo enviar una advertencia a un estudiante**\n\n"
            "Desde la vista de **Detalle del Estudiante** (botón 'Ver Cámara'):\n\n"
            "1. Haz clic en el botón **'Enviar Advertencia'**.\n"
            "2. Selecciona un mensaje predefinido o escribe uno personalizado:\n"
            "   • 'Por favor, mira a la cámara.'\n"
            "   • 'Evita el ruido ambiente excesivo.'\n"
            "   • 'Cierra pestañas o programas no autorizados.'\n"
            "   • Otra (mensaje libre)\n"
            "3. Presiona Aceptar.\n\n"
            "✅ El mensaje llega al estudiante en tiempo real a través del sistema de comunicación segura. "
            "El estudiante verá la advertencia en su pantalla inmediatamente."
        )
    },
    "sv_fraude": {
        "respuesta": (
            "🚫 **Cómo marcar a un estudiante por fraude**\n\n"
            "⚠️ Esta acción es **irreversible** — úsala solo cuando tengas certeza.\n\n"
            "Desde la vista de **Detalle del Estudiante**:\n\n"
            "1. Haz clic en el botón **'Marcar Fraude'** (rojo).\n"
            "2. Escribe el motivo del fraude (quedará registrado en el sistema).\n"
            "3. Presiona Aceptar.\n\n"
            "**¿Qué ocurre después?**\n"
            "• La sesión del estudiante queda marcada como **ANULADA** en la base de datos.\n"
            "• La aplicación del estudiante se cierra automáticamente.\n"
            "• El estudiante no puede volver a conectarse a ese examen.\n"
            "• El registro queda disponible para Segunda Revisión si el estudiante apela.\n\n"
            "💡 Si fue un error, el estudiante puede solicitar una **Segunda Revisión** desde su aplicación."
        )
    },
    "sv_feed": {
        "respuesta": (
            "📋 **El Feed de Alertas**\n\n"
            "Es el panel que aparece en la Sala de Supervisión mostrando en orden cronológico "
            "(más reciente arriba) todas las alertas generadas por todos los estudiantes del examen.\n\n"
            "**¿Qué muestra cada alerta?**\n"
            "• Tipo de alerta (VISION, AUDIO, PROCESO, TECLADO...)\n"
            "• Nivel de severidad (ALTO / MEDIO / BAJO) con color\n"
            "• Nombre del estudiante\n"
            "• Hora exacta de captura\n"
            "• Descripción del evento detectado\n"
            "• Botón **'Ver Evidencia'** para ir directamente al detalle de ese estudiante\n\n"
            "💡 Las alertas se actualizan en **tiempo real** sin necesidad de recargar la página."
        )
    },
    "sv_mapa": {
        "respuesta": (
            "🗺️ **El Mapa GPS**\n\n"
            "La Sala de Supervisión tiene un botón para activar una **vista de mapa interactivo** "
            "que muestra la ubicación geográfica de cada estudiante durante el examen.\n\n"
            "**¿Para qué sirve?**\n"
            "• Verifica que los estudiantes están físicamente en el lugar acordado.\n"
            "• Detecta si algún estudiante está en una ubicación inusual o diferente al resto.\n\n"
            "**¿Cómo activarlo?**\n"
            "Presiona el botón de mapa en la Sala de Supervisión. Los pines de ubicación "
            "se actualizan cada 5 segundos automáticamente.\n\n"
            "Para regresar a la vista normal de supervisión, presiona **'Regresar a la supervisión'**."
        )
    },
    "sv_finalizar": {
        "respuesta": (
            "🏁 **Cómo finalizar un examen**\n\n"
            "Desde la **Sala de Supervisión**:\n\n"
            "1. Haz clic en el botón **'Finalizar Examen'**.\n"
            "2. El sistema pedirá confirmación: *'¿Seguro que desea finalizar el monitoreo?'*\n"
            "3. Confirma y el examen quedará en estado **FINALIZADO**.\n\n"
            "**¿Qué ocurre?**\n"
            "• Todos los estudiantes conectados son desconectados.\n"
            "• El examen ya no acepta nuevas conexiones.\n"
            "• Las evidencias quedan disponibles en la sección de **Reportes de IA**.\n"
            "• El sistema vuelve al Dashboard.\n\n"
            "⚠️ Esta acción es definitiva. Una vez finalizado, el examen no puede reabrirse."
        )
    },
    "sv_conexion": {
        "respuesta": (
            "🔌 **Perdí la conexión — ¿Qué hago?**\n\n"
            "Si el sistema pierde la conexión con el servidor, verás un mensaje de "
            "**'CONEXIÓN PERDIDA — Intentando reconectar...'** sobre la pantalla.\n\n"
            "**¿Qué hace el sistema automáticamente?**\n"
            "Intenta reconectarse cada pocos segundos de forma automática. "
            "Una vez restablecida la conexión, el mensaje desaparece y la supervisión continúa normalmente.\n\n"
            "**Si la reconexión tarda mucho:**\n"
            "1. Verifica tu conexión a internet o red local.\n"
            "2. Asegúrate de que el servidor (Spring Boot / Railway) esté activo.\n"
            "3. Si persiste, cierra la aplicación y vuelve a abrir. Las evidencias ya guardadas localmente NO se pierden."
        )
    },

    # ──────────────────────────────────────────────────────────────
    # 3. REPORTES DE INTELIGENCIA ARTIFICIAL
    # ──────────────────────────────────────────────────────────────
    "reportes": {
        "titulo": "🤖 Reportes de Inteligencia Artificial",
        "intro": "Claro. Sobre los reportes de IA, ¿qué necesitas saber?",
        "opciones": [
            {"etiqueta": "¿Qué muestra el reporte de IA?",                    "nodo": "rp_que_muestra"},
            {"etiqueta": "¿Qué significan los colores Rojo/Naranja/Verde?",   "nodo": "rp_semaforo"},
            {"etiqueta": "¿Cómo se generan los PDFs de reporte?",             "nodo": "rp_pdf"},
            {"etiqueta": "¿Qué necesito para usar el análisis con IA?",       "nodo": "rp_lm_studio"},
            {"etiqueta": "¿Cómo ver las evidencias de un estudiante?",        "nodo": "rp_evidencias"},
        ]
    },
    "rp_que_muestra": {
        "respuesta": (
            "🤖 **¿Qué muestra el Reporte de IA?**\n\n"
            "El reporte de IA funciona como un **Dashboard Analítico Integral** para exámenes finalizados:\n\n"
            "📊 **Indicadores Ejecutivos (KPIs):** Alumnos en Fraude Inminente (🔴), "
            "Sospechosos (🟠), Sin Anomalías (🟢), Integridad Promedio de la clase, "
            "Total de incidencias y la Infracción Predominante.\n\n"
            "🍩 **Gráfico Circular de Anomalías:** Visualiza la proporción de alertas por vector: "
            "Audio, Visión/Objetos, Procesos no autorizados y Atajos de teclado.\n\n"
            "🏆 **Top Infractores y Directorio Completo:** Muestra los 3 casos más críticos en pantalla y "
            "cuenta con el botón **'Ver Directorio Completo'** para buscar, filtrar y auditar a cualquier alumno.\n\n"
            "⚖️ **Dictamen Forense de IA:** Resumen conductual, nivel de riesgo y veredicto certificado emitido por el modelo local de IA.\n\n"
            "💡 Usa el selector de examen (arriba) para alternar entre exámenes finalizados."
        )
    },
    "rp_semaforo": {
        "respuesta": (
            "🚦 **¿Qué significan los colores del semáforo de riesgo?**\n\n"
            "El sistema clasifica automáticamente a cada estudiante en tres categorías:\n\n"
            "🔴 **ROJO — Fraude Inminente:** El estudiante generó alertas graves como "
            "detección de objetos prohibidos, procesos no autorizados, suplantación de identidad, "
            "o tuvo 3 o más alertas en total. Requiere revisión inmediata.\n\n"
            "🟠 **NARANJA — Comportamiento Sospechoso:** Generó alertas de tipo visual "
            "(desatención, rostro no detectado) o de audio. Puede ser un falso positivo "
            "(mala iluminación, ruido ambiental) o un indicador real. Requiere revisión.\n\n"
            "🟢 **VERDE — Sin Anomalías:** No generó alertas significativas durante el examen. "
            "Comportamiento dentro de los parámetros normales.\n\n"
            "⚠️ Recuerda: estas clasificaciones son guías. La decisión final siempre la toma el profesor."
        )
    },
    "rp_pdf": {
        "respuesta": (
            "📄 **Cómo generar los reportes PDF**\n\n"
            "1. Selecciona el examen finalizado en el selector de la parte superior.\n"
            "2. Presiona el botón **'Analizar con IA y descargar reportes'**.\n"
            "3. El sistema enviará los datos al modelo de IA local para análisis.\n"
            "4. Una vez completado, se generará un **PDF por estudiante** automáticamente.\n\n"
            "**¿Dónde se guardan los PDFs?**\n"
            "En la carpeta: `Documentos → Descargas → Reportes_Fraude_IA → {nombre del examen}`\n\n"
            "**¿Qué contiene cada PDF?**\n"
            "• Datos del estudiante y resumen estadístico de alertas\n"
            "• Gráfico de distribución de tipos de fraude\n"
            "• Análisis conductual generado por la IA\n"
            "• Imágenes de las evidencias capturadas\n\n"
            "⚠️ Para usar esta función necesitas tener **LM Studio** corriendo en tu PC."
        )
    },
    "rp_lm_studio": {
        "respuesta": (
            "💻 **¿Qué necesito para usar el análisis con IA?**\n\n"
            "El sistema usa un **modelo de lenguaje local** (LLM) que corre en tu propio PC, "
            "sin enviar datos sensibles a internet.\n\n"
            "**Requisitos:**\n"
            "1. Tener instalado **LM Studio** (descárgalo en lmstudio.ai).\n"
            "2. Cargar un modelo compatible (ej: Llama 3, Mistral, Gemma).\n"
            "3. **Iniciar el servidor local** en LM Studio en el puerto **1234**.\n\n"
            "**¿Cómo verificar que está activo?**\n"
            "En LM Studio, ve a la pestaña 'Local Server' y presiona 'Start Server'. "
            "Deberías ver 'Listening on port 1234'.\n\n"
            "💡 Si el servidor no está activo, el botón de análisis fallará con un error de conexión."
        )
    },
    "rp_evidencias": {
        "respuesta": (
            "📁 **Cómo ver las evidencias de un estudiante desde Reportes**\n\n"
            "Tienes dos formas de acceder a las evidencias forenses:\n\n"
            "**1. Casos críticos (Top 3):**\n"
            "En la sección de **Top Infractores**, haz clic en el botón **'Ver Detalle'** del alumno.\n\n"
            "**2. Cualquier otro estudiante de la clase:**\n"
            "Debajo del Top 3, presiona el botón **'👥 Ver Directorio Completo de Estudiantes'**.\n"
            "Se abrirá una ventana con todos los inscritos donde puedes:\n"
            "• Buscar por nombre o cédula.\n"
            "• Filtrar por riesgo (Críticos, Sospechosos, Limpios).\n"
            "• Hacer clic en **'Ver Evidencias'** de cualquier estudiante para entrar a su expediente.\n\n"
            "Desde el Panel Forense podrás ver fotos, audios, alertas y ejecutar la Auditoría Criptográfica SHA-256."
        )
    },

    # ──────────────────────────────────────────────────────────────
    # 4. SEGUNDA REVISIÓN Y APELACIONES
    # ──────────────────────────────────────────────────────────────
    "apelaciones": {
        "titulo": "⚖️ Segunda Revisión y Apelaciones",
        "intro": "Entendido. Sobre el proceso de segunda revisión, ¿qué deseas consultar?",
        "opciones": [
            {"etiqueta": "¿Qué es una Segunda Revisión?",             "nodo": "ap_que_es"},
            {"etiqueta": "¿Cómo veo las apelaciones pendientes?",     "nodo": "ap_ver"},
            {"etiqueta": "¿Cómo apruebo una apelación?",              "nodo": "ap_aprobar"},
            {"etiqueta": "¿Cómo rechazo una apelación?",              "nodo": "ap_rechazar"},
            {"etiqueta": "¿Qué significan los estados de apelación?", "nodo": "ap_estados"},
        ]
    },
    "ap_que_es": {
        "respuesta": (
            "⚖️ **¿Qué es una Segunda Revisión?**\n\n"
            "Es el proceso formal mediante el cual un **estudiante impugna** una alerta o sanción "
            "que considera injusta o incorrecta (un falso positivo).\n\n"
            "**¿Cuándo puede solicitarla?**\n"
            "Cuando fue marcado como sospechoso o cuando su sesión fue anulada por fraude y "
            "considera que fue un error del sistema.\n\n"
            "**¿Qué pasa después?**\n"
            "La solicitud llega a esta sección con el motivo escrito por el estudiante. "
            "Tú como profesor debes revisar las evidencias y decidir si:\n\n"
            "✅ **Aprobar** → Fue un falso positivo; el estudiante queda libre de la sospecha.\n"
            "❌ **Rechazar** → El fraude se confirma y se mantiene la sanción."
        )
    },
    "ap_ver": {
        "respuesta": (
            "📋 **Cómo ver las apelaciones**\n\n"
            "1. En el menú lateral, haz clic en **'Segunda Revisión'**.\n"
            "2. Se mostrará una tabla con todas las solicitudes de tus estudiantes.\n"
            "3. Usa el filtro superior para ver:\n"
            "   • **Todas** → Muestra todas las apelaciones\n"
            "   • **Pendientes** → Solo las que aún no has resuelto\n"
            "   • **Aprobadas** → Las que aprobaste (falso positivo)\n"
            "   • **Rechazadas** → Las que rechazaste (fraude confirmado)\n\n"
            "Si hay muchas apelaciones, usa los botones de **paginación** "
            "(← →) para navegar entre páginas (6 apelaciones por página).\n\n"
            "💡 Haz clic en **'Ver Evidencia'** en cualquier fila para revisar las fotos y alertas del estudiante antes de decidir."
        )
    },
    "ap_aprobar": {
        "respuesta": (
            "✅ **Cómo aprobar una apelación (Falso Positivo)**\n\n"
            "1. Ve a **Segunda Revisión** en el menú lateral.\n"
            "2. Localiza la apelación del estudiante (estado: PENDIENTE).\n"
            "3. Opcionalmente, haz clic en **'Ver Evidencia'** para revisar los archivos.\n"
            "4. Haz clic en el botón **'Aprobar'** (verde) de esa fila.\n"
            "5. Escribe el motivo de tu decisión (ej: 'Se verificó que la alerta fue causada por mala iluminación').\n"
            "6. Confirma.\n\n"
            "**Resultado:**\n"
            "• La apelación queda en estado **APROBADA A FAVOR**.\n"
            "• El estudiante es notificado de que su caso fue revisado positivamente.\n"
            "• La sanción queda revocada en el sistema."
        )
    },
    "ap_rechazar": {
        "respuesta": (
            "❌ **Cómo rechazar una apelación (Fraude Confirmado)**\n\n"
            "1. Ve a **Segunda Revisión** en el menú lateral.\n"
            "2. Localiza la apelación del estudiante (estado: PENDIENTE).\n"
            "3. Revisa las evidencias haciendo clic en **'Ver Evidencia'** para fundamentar tu decisión.\n"
            "4. Haz clic en el botón **'Rechazar'** (rojo) de esa fila.\n"
            "5. Escribe el motivo del rechazo con detalle (este texto quedará registrado formalmente).\n"
            "6. Confirma.\n\n"
            "**Resultado:**\n"
            "• La apelación queda en estado **RECHAZADA — FRAUDE MANTENIDO**.\n"
            "• La sanción original se confirma definitivamente.\n"
            "• Queda constancia escrita de tu decisión y motivo."
        )
    },
    "ap_estados": {
        "respuesta": (
            "🔖 **Estados de una Apelación**\n\n"
            "🟡 **PENDIENTE / EN REVISIÓN** → El estudiante envió su solicitud. "
            "Aún no has tomado una decisión. Los botones Aprobar/Rechazar están activos.\n\n"
            "✅ **APROBADA A FAVOR** (verde) → Determinaste que fue un falso positivo del sistema. "
            "El estudiante queda libre de la sospecha.\n\n"
            "❌ **RECHAZADA — FRAUDE MANTENIDO** (rojo) → Confirmaste el fraude. "
            "La sanción se mantiene y queda el registro formal de tu decisión.\n\n"
            "⚪ **Ya Resuelta** → La apelación tiene una decisión tomada. "
            "Los botones de acción desaparecen y se muestra solo el estado final."
        )
    },

    # ──────────────────────────────────────────────────────────────
    # 5. SEGURIDAD Y AUDITORÍA FORENSE
    # ──────────────────────────────────────────────────────────────
    "forense": {
        "titulo": "🛡️ Seguridad y Auditoría Forense",
        "intro": "Entendido. Sobre la seguridad y auditoría forense de evidencias, ¿qué deseas saber?",
        "opciones": [
            {"etiqueta": "¿Qué es el Sello de Inmutabilidad Forense?",    "nodo": "sf_sello"},
            {"etiqueta": "¿Cómo abro el Panel de Carpetas Forenses?",     "nodo": "sf_panel"},
            {"etiqueta": "¿Qué son los Vectores de Evidencia?",           "nodo": "sf_vectores"},
            {"etiqueta": "¿Cómo ejecuto la Auditoría Forense?",           "nodo": "sf_auditoria"},
            {"etiqueta": "¿Qué significa 'Sello Forense Roto'?",         "nodo": "sf_roto"},
            {"etiqueta": "¿Cómo veo las imágenes o audios de evidencia?", "nodo": "sf_ver"},
            {"etiqueta": "¿Dónde se guardan las evidencias en mi PC?",    "nodo": "sf_donde"},
        ]
    },
    "sf_sello": {
        "respuesta": (
            "🛡️ **El Sello de Inmutabilidad Forense**\n\n"
            "Es el mecanismo de seguridad más avanzado del sistema. Garantiza que "
            "las evidencias capturadas durante el examen **no han sido alteradas** después de ser capturadas.\n\n"
            "**¿Cómo funciona?**\n"
            "En el momento exacto en que el sistema captura una foto o audio del estudiante:\n"
            "1. Calcula una **firma digital SHA-256** del archivo (una 'huella criptográfica' única de 64 caracteres).\n"
            "2. Guarda esa firma en la base de datos del servidor.\n"
            "3. Envía y guarda el archivo cifrado en tu PC.\n\n"
            "Cuando ejecutas la Auditoría Forense, el sistema:\n"
            "1. Descifra el archivo de tu PC.\n"
            "2. Recalcula la firma SHA-256.\n"
            "3. La compara con la guardada en el servidor.\n\n"
            "Si coinciden: **Integridad Confirmada** ✅\n"
            "Si no coinciden: **Sello Forense Roto** 🚨 — el archivo fue manipulado."
        )
    },
    "sf_panel": {
        "respuesta": (
            "📁 **Cómo abrir el Panel de Carpetas Forenses**\n\n"
            "El Panel de Evidencias Forenses se accede desde dos lugares:\n\n"
            "**Desde Reportes de IA:**\n"
            "1. Ve a la sección **Reportes** en el menú lateral.\n"
            "2. En el Top Infractores o en el botón **'Ver Directorio Completo'**, haz clic en **'Ver Detalle'** o **'Ver Evidencias'** de cualquier estudiante.\n\n"
            "**Desde Segunda Revisión:**\n"
            "1. Ve a **Segunda Revisión** en el menú lateral.\n"
            "2. En la tabla de apelaciones, haz clic en **'Ver Evidencia'** de cualquier fila.\n\n"
            "Para regresar, usa el botón **'Volver al Reporte'** o **'Volver a Segunda Revisión'** según desde donde entraste."
        )
    },
    "sf_vectores": {
        "respuesta": (
            "📂 **¿Qué son los Vectores de Evidencia?**\n\n"
            "El sistema organiza todas las evidencias en 4 categorías llamadas 'Vectores':\n\n"
            "🎤 **VECTOR 01 — Audio:** Grabaciones de sonido y voces detectadas en el entorno del estudiante.\n\n"
            "💻 **VECTOR 02 — Procesos y Sistema:** Capturas de pantalla de aplicaciones no permitidas y alertas del sistema operativo.\n\n"
            "📷 **VECTOR 03 — Webcam:** Fotografías capturadas cuando se detectó un rostro no reconocido, "
            "un objeto sospechoso o desatención.\n\n"
            "⌨️ **VECTOR 04 — Teclado:** Registros de combinaciones de teclas prohibidas (Alt+Tab, Ctrl+C, tecla Windows, etc.).\n\n"
            "Cada vector muestra el conteo de archivos recopilados. Si dice '0 archivos', "
            "significa que no hubo alertas de ese tipo en el examen."
        )
    },
    "sf_auditoria": {
        "respuesta": (
            "🔬 **Cómo ejecutar la Auditoría Forense**\n\n"
            "1. Abre el **Panel de Carpetas Forenses** de un estudiante.\n"
            "2. Haz clic en el botón **'🛡️ Auditoría Forense'** en la barra superior.\n"
            "3. Se mostrará una barra de progreso que analiza cada evidencia una por una:\n"
            "   *'Analizando firma Hash de las evidencias 1/N...'*\n"
            "4. Al terminar, aparecerá el resultado.\n\n"
            "**¿Qué procesa la auditoría?**\n"
            "Verifica la integridad criptográfica de cada imagen (webcam, pantalla) y audio "
            "comparando su firma SHA-256 actual con la registrada en el servidor al momento de la captura.\n\n"
            "⚠️ Esta función solo está disponible para evidencias capturadas con la versión actual del sistema."
        )
    },
    "sf_roto": {
        "respuesta": (
            "🚨 **¿Qué significa 'Sello Forense Roto'?**\n\n"
            "Es una alerta crítica de seguridad que indica que **uno o más archivos de evidencia "
            "fueron modificados** después de ser capturados.\n\n"
            "**¿Por qué ocurre?**\n"
            "• El archivo fue editado, recortado o manipulado después de la captura.\n"
            "• El archivo fue corrompido (daño en el almacenamiento).\n"
            "• Se intentó reemplazar la evidencia por otro archivo.\n\n"
            "**¿Qué debes hacer?**\n"
            "1. Anota los nombres de los archivos señalados como manipulados.\n"
            "2. No uses esas evidencias como prueba sin reportar la anomalía.\n"
            "3. Contacta al administrador del sistema para investigar.\n\n"
            "✅ Si la auditoría dice **'INTEGRIDAD CONFIRMADA'**, los archivos son auténticos "
            "y no han sido tocados desde que salieron del PC del estudiante."
        )
    },
    "sf_ver": {
        "respuesta": (
            "🖼️ **Cómo ver imágenes y audios de evidencia**\n\n"
            "1. Abre el **Panel de Carpetas Forenses** de un estudiante.\n"
            "2. Haz clic en el botón **'Abrir Carpeta →'** del vector que deseas revisar.\n"
            "3. Se mostrarán miniaturas de todas las evidencias de ese tipo.\n"
            "4. Haz clic en **'Ver'** (imágenes) o **'Reproducir'** (audios).\n\n"
            "El sistema descifra automáticamente el archivo y lo abre con el visor de tu sistema operativo "
            "(Fotos de Windows para imágenes, Media Player para audios).\n\n"
            "Para volver a la vista de carpetas, usa el botón **'Volver a Carpetas'**."
        )
    },
    "sf_donde": {
        "respuesta": (
            "💾 **¿Dónde se guardan las evidencias en mi PC?**\n\n"
            "Todas las evidencias se guardan localmente en tu equipo, en esta ubicación:\n\n"
            "`Documentos → DataSupervision → Examenes → {Código Examen} → {Nombre Estudiante} → {ID Sesión}`\n\n"
            "Dentro de cada sesión encontrarás 4 subcarpetas:\n"
            "📁 `audio/` → Archivos de sonido (.wav)\n"
            "📁 `proceso/` → Capturas de pantalla de procesos (.webp)\n"
            "📁 `webcam/` → Fotos de la cámara (.webp)\n"
            "📁 `teclado/` → Capturas de atajos de teclado (.webp)\n\n"
            "⚠️ Los archivos están **cifrados con AES-256**. No los abras directamente con un visor de imágenes; "
            "usa siempre el Panel de Evidencias del sistema para verlos correctamente descifrados.\n\n"
            "💡 No elimines estas carpetas: son la evidencia oficial del examen."
        )
    },
}
