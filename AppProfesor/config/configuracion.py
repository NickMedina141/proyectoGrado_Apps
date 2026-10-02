url = "https://apiproyectogrado-production.up.railway.app/api"
# url = "http://localhost:8080/api"

url_login_profesor = f"{url}/auth/login/profesor"
url_examenes = f"{url}/examenes"
url_crear_examen = f"{url_examenes}/crearExamen"

url_websocket = "wss://apiproyectogrado-production.up.railway.app/ws-supervision"
# url_websocket = "ws://localhost:8080/ws-supervision"
# --- SEGURIDAD E2EE ---
AES_SECRET_KEY = b'w_bq-llZ8nDN8qRkr7xxVOH0dwPR9ll6QIkZL7pZKcM='
