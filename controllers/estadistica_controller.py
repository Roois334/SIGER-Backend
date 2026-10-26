from flask import Blueprint, request, jsonify, g

from utilities.decorators import permiso_required
from services.estadistica_service import EstadisticaService

estadistica_bp = Blueprint("estadistica_bp", __name__, url_prefix="/api/estadisticas")


@estadistica_bp.route("", methods=["GET"])
@permiso_required("estadisticas.ver")
def consultar():
    """
    Indicadores y distribuciones de las emergencias registradas.
    Filtros opcionales: desde, hasta (AAAA-MM-DD), municipio_id, tipo, prioridad, estado.
    El gestor siempre queda limitado a su municipio.
    """
    try:
        datos = EstadisticaService.consultar(
            g.usuario,
            desde=request.args.get("desde"), hasta=request.args.get("hasta"),
            municipio_id=request.args.get("municipio_id", type=int),
            tipo=request.args.get("tipo") or None,
            prioridad=request.args.get("prioridad") or None,
            estado=request.args.get("estado") or None,
        )
        return jsonify(datos), 200
    except PermissionError as e:
        return jsonify({"error": str(e)}), 403
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
