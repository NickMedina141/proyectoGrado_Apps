import datetime

def formatear_hora_local_12h(hora_raw):
    """
    Convierte una marca de tiempo (generalmente en UTC de Railway/nube)
    a la hora local de la máquina del docente en formato 12 horas con AM/PM.
    Ejemplos:
      "2026-10-03T22:36:14" -> "05:36 PM" (en Colombia UTC-5)
      "2026-10-03T22:36:14Z" -> "05:36 PM"
      "22:36:00" -> "10:36 PM"
    """
    if not hora_raw:
        return datetime.datetime.now().strftime("%I:%M %p")

    try:
        hora_str = str(hora_raw).strip()
        if "T" in hora_str:
            limpio = hora_str.replace("Z", "+00:00")
            dt = datetime.datetime.fromisoformat(limpio)
            if dt.tzinfo is None:
                # El backend genera LocalDateTime en UTC sin zona explícita
                dt = dt.replace(tzinfo=datetime.timezone.utc)
            dt_local = dt.astimezone()
            return dt_local.strftime("%I:%M %p")
        elif ":" in hora_str:
            partes = hora_str.split(":")
            h = int(partes[0])
            m = int(partes[1])
            periodo = "PM" if h >= 12 else "AM"
            h12 = h % 12
            if h12 == 0:
                h12 = 12
            return f"{h12:02d}:{m:02d} {periodo}"
    except Exception:
        pass

    return str(hora_raw)
