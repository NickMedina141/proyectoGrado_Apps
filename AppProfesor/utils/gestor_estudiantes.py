import os
import csv
import json
import unicodedata

def normalizar_texto(texto: str) -> str:
    """Normaliza un texto eliminando acentos, diacríticos, mayúsculas y espacios sobrantes."""
    if not texto:
        return ""
    texto_norm = unicodedata.normalize('NFKD', str(texto))
    texto_sin_tildes = "".join(c for c in texto_norm if not unicodedata.combining(c))
    return " ".join(texto_sin_tildes.lower().strip().split())

class GestorEstudiantes:
    """
    Gestor centralizado del directorio y cédulas de estudiantes.
    Indexa rosters desde CSV, base de datos y memoria para garantizar
    que la cédula oficial de cada estudiante se resuelva con precisión
    sin confundirse con IDs internos del sistema (ej. EST-2000).
    """
    __instancia = None

    def __new__(cls):
        if cls.__instancia is None:
            cls.__instancia = super(GestorEstudiantes, cls).__new__(cls)
            cls.__instancia._inicializado = False
        return cls.__instancia

    def __init__(self):
        if getattr(self, '_inicializado', False):
            return
        self._inicializado = True
        self.mapa_cedulas_por_nombre = {}  # nombre_normalizado -> cedula
        self.mapa_cedulas_por_id = {}      # estudiante_id -> cedula
        self.mapa_cedulas_por_email = {}   # email_normalizado -> cedula
        
        self._ruta_cache = os.path.join(os.path.dirname(__file__), "cache_estudiantes.json")
        self._cargar_cache()
        self._auto_descubrir_csvs()

    def _cargar_cache(self):
        try:
            if os.path.exists(self._ruta_cache):
                with open(self._ruta_cache, 'r', encoding='utf-8') as f:
                    datos = json.load(f)
                    self.mapa_cedulas_por_nombre.update(datos.get("por_nombre", {}))
                    self.mapa_cedulas_por_id.update(datos.get("por_id", {}))
                    self.mapa_cedulas_por_email.update(datos.get("por_email", {}))
        except Exception as e:
            print(f"[GestorEstudiantes] Advertencia cargando caché local: {e}")

    def _guardar_cache(self):
        try:
            with open(self._ruta_cache, 'w', encoding='utf-8') as f:
                json.dump({
                    "por_nombre": self.mapa_cedulas_por_nombre,
                    "por_id": self.mapa_cedulas_por_id,
                    "por_email": self.mapa_cedulas_por_email
                }, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[GestorEstudiantes] Advertencia guardando caché local: {e}")

    def _auto_descubrir_csvs(self):
        """Busca archivos CSV de estudiantes en el entorno del proyecto y los indexa automáticamente."""
        rutas_posibles = [
            os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")), # Raíz proyectoGrado
            os.path.abspath(os.path.join(os.path.dirname(__file__), "..")),       # AppProfesor
            os.path.join(os.path.expanduser("~"), "Documents", "DataSupervision")
        ]
        for dir_base in rutas_posibles:
            if not os.path.exists(dir_base):
                continue
            try:
                for arch in os.listdir(dir_base):
                    if arch.lower().endswith(".csv"):
                        ruta_csv = os.path.join(dir_base, arch)
                        self.indexar_archivo_csv(ruta_csv)
            except Exception:
                pass

    def indexar_archivo_csv(self, ruta_csv: str):
        if not os.path.exists(ruta_csv):
            return
        try:
            with open(ruta_csv, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    row_clean = {
                        k.strip().lower() if isinstance(k, str) else k: str(v).strip() if v else ''
                        for k, v in row.items()
                    }
                    nombre = row_clean.get("nombre", "")
                    apellidos = row_clean.get("apellidos", "")
                    cedula = row_clean.get("cedula", "") or row_clean.get("documento", "")
                    email = row_clean.get("email", "")

                    if cedula and (nombre or apellidos):
                        self.registrar_estudiante(
                            nombre=nombre,
                            apellidos=apellidos,
                            cedula=cedula,
                            email=email
                        )
        except Exception as e:
            print(f"[GestorEstudiantes] Advertencia leyendo CSV {ruta_csv}: {e}")

    def registrar_estudiante(self, nombre: str, apellidos: str = "", cedula: str = "", email: str = "", estudiante_id: str = ""):
        cedula_str = str(cedula).strip()
        if not cedula_str:
            return

        nombre_completo = f"{nombre} {apellidos}".strip()
        nom_norm = normalizar_texto(nombre_completo)
        if nom_norm:
            self.mapa_cedulas_por_nombre[nom_norm] = cedula_str

        # Registrar también variación 'apellidos nombre'
        if nombre and apellidos:
            inverso = normalizar_texto(f"{apellidos} {nombre}")
            if inverso:
                self.mapa_cedulas_por_nombre[inverso] = cedula_str

        if email:
            email_norm = str(email).strip().lower()
            self.mapa_cedulas_por_email[email_norm] = cedula_str

        if estudiante_id:
            eid_norm = str(estudiante_id).strip().lower()
            self.mapa_cedulas_por_id[eid_norm] = cedula_str

        self._guardar_cache()

    def registrar_estudiantes_bulk(self, lista_estudiantes: list):
        for e in lista_estudiantes:
            if isinstance(e, dict):
                self.registrar_estudiante(
                    nombre=e.get("nombre", ""),
                    apellidos=e.get("apellidos", ""),
                    cedula=e.get("cedula", "") or e.get("documento", ""),
                    email=e.get("email", ""),
                    estudiante_id=e.get("id", "") or e.get("estudianteId", "")
                )

    def asociar_id_con_cedula(self, estudiante_id: str, cedula: str):
        if estudiante_id and cedula:
            self.mapa_cedulas_por_id[str(estudiante_id).strip().lower()] = str(cedula).strip()
            self._guardar_cache()

    def obtener_cedula(self, nombre: str = "", estudiante_id: str = "", email: str = "") -> str:
        """
        Resuelve y retorna la cédula real del estudiante a través de búsqueda multi-criterio.
        """
        # 1. Búsqueda directa por ID si ya está asociado
        if estudiante_id:
            c = self.mapa_cedulas_por_id.get(str(estudiante_id).strip().lower())
            if c:
                return c

        # 2. Búsqueda por Email
        if email:
            c = self.mapa_cedulas_por_email.get(str(email).strip().lower())
            if c:
                if estudiante_id:
                    self.asociar_id_con_cedula(estudiante_id, c)
                return c

        # 3. Búsqueda por Nombre Normalizado
        if nombre:
            norm_query = normalizar_texto(nombre)
            if norm_query in self.mapa_cedulas_por_nombre:
                c = self.mapa_cedulas_por_nombre[norm_query]
                if estudiante_id:
                    self.asociar_id_con_cedula(estudiante_id, c)
                return c

            # Comparación por conjunto de tokens para flexibilidad de orden
            tokens_query = set(norm_query.split())
            if len(tokens_query) >= 2:
                for nom_reg, c in self.mapa_cedulas_por_nombre.items():
                    tokens_reg = set(nom_reg.split())
                    if tokens_query == tokens_reg or tokens_query.issubset(tokens_reg) or tokens_reg.issubset(tokens_query):
                        if estudiante_id:
                            self.asociar_id_con_cedula(estudiante_id, c)
                        return c

        return ""

gestor_estudiantes = GestorEstudiantes()
