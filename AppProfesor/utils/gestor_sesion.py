
class GestorSesion:
  __instancia = None

  def __new__(cls):
    if cls.__instancia is None:
      cls.__instancia = super(GestorSesion, cls).__new__(cls)
      cls.__instancia.token = None
      cls.__instancia.profesor_id = None
    return cls.__instancia

  def guardar_sesion(self, token: str, profesor_id: str):
    self.token = token
    self.profesor_id = profesor_id

  def guardar_token(self, token: str):
    self.token = token

  def obtener_token(self) ->str:
    return self.token

  def obtener_profesor_id(self) ->str:
    return self.profesor_id

  def cerrar_sesion(self):
    self.token = None
    self.profesor_id = None

sesion_actual = GestorSesion()