"""
HU-10: calculo de la prioridad de una emergencia con variables numericas.

Cada variable suma puntos; el total decide el nivel. El tipo de emergencia pone un PISO
(una fuga o una emergencia medica nunca baja de 'critica' por tener pocas variables).
Los umbrales estan aqui, en un solo lugar, para ajustarlos facil.
"""

PRIORIDADES = ["baja", "media", "alta", "critica"]
RIESGOS = ("bajo", "medio", "alto")
MAX_VIAS = 100
MAX_AREA = 10000000  # metros cuadrados

_PUNTOS_RIESGO = {"bajo": 0, "medio": 1, "alto": 3}


def _escala(valor, cortes):
    """Cuenta cuantos cortes alcanza el valor. cortes=[1, 6, 21] -> 0, 1, 2 o 3 puntos."""
    return sum(1 for c in cortes if (valor or 0) >= c)


def calcular_prioridad(tipo_prioridad_base, afectados, heridos, vias, area, riesgo):
    """
    Devuelve (prioridad, puntos).
    tipo_prioridad_base: la prioridad que ya trae el tipo de emergencia (piso).
    Puntos: personas afectadas 0-3, heridos 0-3, vias 0-2, area 0-2, riesgo de propagacion 0-3.
    """
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
