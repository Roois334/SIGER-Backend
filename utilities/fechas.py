from datetime import datetime, timedelta, timezone

# Colombia no tiene horario de verano: UTC-5 fijo (no depende de tzdata/Windows).
ZONA_COLOMBIA = timezone(timedelta(hours=-5))


def ahora():
    """Fecha y hora actual de Colombia, sin zona (como se guarda en la BD)."""
    return datetime.now(ZONA_COLOMBIA).replace(tzinfo=None)


def parsear_fecha(texto, nombre):
    """Acepta AAAA-MM-DD (lo que envia el campo de fecha). Vacio = sin filtro. Devuelve un date."""
    texto = (texto or "").strip()
    if not texto:
        return None
    try:
        return datetime.strptime(texto, "%Y-%m-%d").date()
    except ValueError:
        raise ValueError(f"La fecha '{nombre}' no es valida")


def rango_fechas(desde, hasta):
    """Valida un rango desde/hasta. Devuelve (date|None, date|None)."""
    f_desde, f_hasta = parsear_fecha(desde, "desde"), parsear_fecha(hasta, "hasta")
    if f_desde and f_hasta and f_desde > f_hasta:
        raise ValueError("La fecha 'desde' no puede ser posterior a la fecha 'hasta'")
    return f_desde, f_hasta


def filtrar_por_fecha(query, columna, f_desde, f_hasta):
    """Filtra una consulta por un rango de dias completos (el dia final se incluye entero)."""
    if f_desde:
        query = query.filter(columna >= datetime.combine(f_desde, datetime.min.time()))
    if f_hasta:
        query = query.filter(columna < datetime.combine(f_hasta + timedelta(days=1), datetime.min.time()))
    return query
