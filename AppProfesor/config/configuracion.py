url = "https://apiproyectogrado-production.up.railway.app/api"
# url = "http://localhost:8080/api"

url_login_profesor = f"{url}/auth/login/profesor"
url_registro_solicitar_codigo = f"{url}/auth/registro/solicitar-codigo"
url_registro_confirmar_profesor = f"{url}/auth/registro/confirmar-profesor"
url_recuperar_solicitar_codigo = f"{url}/auth/recuperar/solicitar-codigo"
url_recuperar_confirmar = f"{url}/auth/recuperar/confirmar"

url_admin = f"{url}/admin"
url_admin_resumen = f"{url_admin}/resumen"
url_admin_profesores = f"{url_admin}/profesores"
url_admin_estudiantes = f"{url_admin}/estudiantes"

url_examenes = f"{url}/examenes"
url_crear_examen = f"{url_examenes}/crearExamen"

url_websocket = "wss://apiproyectogrado-production.up.railway.app/ws-supervision"
# url_websocket = "ws://localhost:8080/ws-supervision"
# --- SEGURIDAD E2EE ---
AES_SECRET_KEY = b'w_bq-llZ8nDN8qRkr7xxVOH0dwPR9ll6QIkZL7pZKcM='
