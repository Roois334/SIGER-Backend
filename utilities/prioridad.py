PRIORIDADES = ["baja", "media", "alta", "critica"]
RIESGOS = ("bajo", "medio", "alto")
MAX_VIAS = 100
MAX_AREA = 10000000

_PUNTOS_RIESGO = {"bajo": 0, "medio": 1, "alto": 3}


def _escala(valor, cortes):
    return sum(1 for c in cortes if (valor or 0) >= c)


def calcular_prioridad(tipo_prioridad_base, afectados, heridos, vias, area, riesgo):
    puntos = (
        _escala(afectados, [1, 6, 21])
        + _escala(heridos, [1, 3, 10])
        + _escala(vias, [1, 2])
        + _escala(area, [100, 1001])
        + _PUNTOS_RIESGO.get(riesgo or "", 0)
    )
    if puntos >= 8:
        nivel = "critica"
    elif puntos >= 5:
        nivel = "alta"
    elif puntos >= 2:
        nivel = "media"
    else:
        nivel = "baja"
    piso = tipo_prioridad_base if tipo_prioridad_base in PRIORIDADES else "media"
    if PRIORIDADES.index(piso) > PRIORIDADES.index(nivel):
        nivel = piso
    return nivel, puntos
