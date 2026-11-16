from flask import Blueprint, request, jsonify, g

from utilities.decorators import permiso_required
from services.indicador_service import IndicadorService

indicador_bp = Blueprint("indicador_bp", __name__, url_prefix="/api/indicadores")


def _responder(funcion, **filtros):
    try:
        return jsonify(funcion(g.usuario, **filtros)), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 501


@indicador_bp.route("/resumen", methods=["GET"])
@permiso_required("estadisticas.ver")
def resumen():
    return _responder(IndicadorService.resumen, municipio_id=request.args.get("municipio_id", type=int))


@indicador_bp.route("/tiempos", methods=["GET"])
@permiso_required("estadisticas.ver")
def tiempos():
    return _responder(IndicadorService.tiempos, municipio_id=request.args.get("municipio_id", type=int),
                      desde=request.args.get("desde"), hasta=request.args.get("hasta"))


@indicador_bp.route("/carga-organismos", methods=["GET"])
@permiso_required("reportes.asignar")
def carga_organismos():
    return _responder(IndicadorService.carga_organismos, municipio_id=request.args.get("municipio_id", type=int))
