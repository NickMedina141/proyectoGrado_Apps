url = "https://apiproyectogrado-production.up.railway.app/api"
# url = "http://localhost:8080/api"

url_login_estudiante = f"{url}/auth/login/estudiante"
url_registro_solicitar_codigo = f"{url}/auth/registro/solicitar-codigo"
url_registro_confirmar_estudiante = f"{url}/auth/registro/confirmar-estudiante"
url_recuperar_solicitar_codigo = f"{url}/auth/recuperar/solicitar-codigo"
url_recuperar_confirmar = f"{url}/auth/recuperar/confirmar"
url_supervision_iniciar = f"{url}/supervision/iniciar"
url_supervision_base = f"{url}/supervision"
url_reglas_examen = f"{url}/supervision/reglas"
url_subir_evidencia = f"{url}/evidencias/subir"

url_websocket = "wss://apiproyectogrado-production.up.railway.app/ws-supervision"
# url_websocket = "ws://localhost:8080/ws-supervision"

# --- SEGURIDAD E2EE ---
AES_SECRET_KEY = b'w_bq-llZ8nDN8qRkr7xxVOH0dwPR9ll6QIkZL7pZKcM='
