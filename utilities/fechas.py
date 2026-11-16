from datetime import datetime, timedelta, timezone

ZONA_COLOMBIA = timezone(timedelta(hours=-5))


def ahora():
    return datetime.now(ZONA_COLOMBIA).replace(tzinfo=None)


def parsear_fecha(texto, nombre):
    texto = (texto or "").strip()
    if not texto:
        return None
    try:
        return datetime.strptime(texto, "%Y-%m-%d").date()
    except ValueError:
        raise ValueError(f"La fecha '{nombre}' no es valida")


def rango_fechas(desde, hasta):
    f_desde, f_hasta = parsear_fecha(desde, "desde"), parsear_fecha(hasta, "hasta")
    if f_desde and f_hasta and f_desde > f_hasta:
        raise ValueError("La fecha 'desde' no puede ser posterior a la fecha 'hasta'")
    return f_desde, f_hasta


def filtrar_por_fecha(query, columna, f_desde, f_hasta):
    if f_desde:
        query = query.filter(columna >= datetime.combine(f_desde, datetime.min.time()))
    if f_hasta:
        query = query.filter(columna < datetime.combine(f_hasta + timedelta(days=1), datetime.min.time()))
    return query
