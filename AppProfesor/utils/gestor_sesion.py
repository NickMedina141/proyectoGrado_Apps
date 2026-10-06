
class GestorSesion:
  __instancia = None

  def __new__(cls):
    if cls.__instancia is None:
      cls.__instancia = super(GestorSesion, cls).__new__(cls)
      cls.__instancia.token = None
      cls.__instancia.profesor_id = None
      cls.__instancia.rol = "PROFESOR"
      cls.__instancia.nombre = ""
    return cls.__instancia

  def guardar_sesion(self, token: str, profesor_id: str, rol: str = "PROFESOR", nombre: str = ""):
    self.token = token
    self.profesor_id = profesor_id
    self.rol = rol
    self.nombre = nombre

  def guardar_token(self, token: str):
    self.token = token

  def obtener_token(self) ->str:
    return self.token

  def obtener_profesor_id(self) ->str:
    return self.profesor_id

  def obtener_rol(self) -> str:
    return getattr(self, 'rol', 'PROFESOR')

  def obtener_nombre(self) -> str:
    return getattr(self, 'nombre', '')

  def es_admin(self) -> bool:
    rol = getattr(self, 'rol', 'PROFESOR')
    prof_id = getattr(self, 'profesor_id', '') or ''
    return rol in ('ADMIN', 'SUPERADMIN') or prof_id.upper().startswith('ADMIN')

  def cerrar_sesion(self):
    self.token = None
    self.profesor_id = None
    self.rol = "PROFESOR"
    self.nombre = ""

sesion_actual = GestorSesion()