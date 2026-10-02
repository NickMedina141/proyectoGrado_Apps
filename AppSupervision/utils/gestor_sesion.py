class GestorSesion:
  __instancia = None

  def __new__(cls):
    if cls.__instancia is None:
      cls.__instancia = super(GestorSesion, cls).__new__(cls)
      cls.__instancia.token = None
      cls.__instancia.estudiante_id = None
      cls.__instancia.sesion_id = None
    return cls.__instancia

  def guardar_sesion_auth(self, token: str, estudiante_id: str):
    self.token = token
    self.estudiante_id = estudiante_id

  def guardar_sesion_examen(self, sesion_id: str):
    self.sesion_id = sesion_id

  def guardar_token(self, token: str):
    self.token = token

  def obtener_token(self) ->str:
    return self.token

  def obtener_estudiante_id(self) ->str:
    return self.estudiante_id
    
  def obtener_sesion_id(self) ->str:
    return self.sesion_id

  def cerrar_sesion(self):
    self.token = None
    self.estudiante_id = None
    self.sesion_id = None

sesion_actual = GestorSesion()
