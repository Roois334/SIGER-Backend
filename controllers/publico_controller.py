"""
Datos PUBLICOS (sin iniciar sesion) para el mapa que ve cualquier visitante.

Privacidad: solo se expone lo necesario para ubicar el incidente en el mapa.
NO se entrega folio, descripcion, direccion exacta, nombre del ciudadano, organismo ni
evidencias; y la coordenada se redondea (~110 m). Los reportes pendientes (aun sin
revisar por el gestor) y los descartados no se publican.
"""
from datetime import datetime, timedelta, timezone

from flask import Blueprint, jsonify
from sqlalchemy.orm import joinedload

from models.reporte import Reporte

publico_bp = Blueprint("publico_bp", __name__, url_prefix="/api/publico")

# Estados que se muestran al publico: el gestor ya confirmo el incidente y sigue abierto
ESTADOS_PUBLICOS = ("asignado", "en_atencion")


@publico_bp.route("/mapa", methods=["GET"])
def mapa_publico():
    reportes = (Reporte.query.options(joinedload(Reporte.municipio))
                .filter(Reporte.estado.in_(ESTADOS_PUBLICOS),
                        Reporte.latitud.isnot(None), Reporte.longitud.isnot(None))
                .order_by(Reporte.fecha_hora.desc()).limit(300).all())
    datos = [{
        "id": r.id,
        "tipo": r.tipo,
        "prioridad": r.prioridad,
        "estado": r.estado,
        "latitud": round(r.latitud, 3),
        "longitud": round(r.longitud, 3),
        "municipio": r.municipio.nombre if r.municipio else None,
        "fecha_hora": r.fecha_hora.isoformat() if r.fecha_hora else None,
    } for r in reportes]
    resp = jsonify({"reportes": datos})
    resp.headers["Cache-Control"] = "no-store"
    return resp, 200
