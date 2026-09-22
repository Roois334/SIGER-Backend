from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity

from dtos.reporte_dto import ReporteCreateDTO
from services.reporte_service import ReporteService

reporte_bp = Blueprint("reporte_bp", __name__, url_prefix="/api/reportes")


@reporte_bp.route("", methods=["POST"])
@jwt_required()
def crear_reporte():
    """
    Cualquier usuario autenticado (ciudadano) puede registrar una emergencia.
    Se envia como multipart/form-data para poder incluir las evidencias.
    """
    ciudadano_id = int(get_jwt_identity())
    data = request.form

    dto = ReporteCreateDTO(
        tipo=data.get("tipo"),
        municipio_id=data.get("municipio_id", type=int),
        direccion=data.get("direccion"),
        descripcion=data.get("descripcion"),
        latitud=data.get("latitud", type=float),
        longitud=data.get("longitud", type=float),
        afectados=data.get("afectados", 0),
    )

    archivos = request.files.getlist("evidencias")

    try:
        reporte = ReporteService.create_reporte(
            dto, ciudadano_id,
            archivos=archivos,
            upload_folder=current_app.config["UPLOAD_FOLDER"],
        )
        return jsonify({"reporte": reporte}), 201
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


@reporte_bp.route("", methods=["GET"])
@jwt_required()
def listar_mis_reportes():
    ciudadano_id = int(get_jwt_identity())
    reportes = ReporteService.list_reportes_ciudadano(ciudadano_id)
    return jsonify({"reportes": reportes}), 200


@reporte_bp.route("/<int:reporte_id>", methods=["GET"])
@jwt_required()
def obtener_reporte(reporte_id):
    ciudadano_id = int(get_jwt_identity())
    try:
        reporte = ReporteService.get_reporte(reporte_id, ciudadano_id=ciudadano_id)
        return jsonify({"reporte": reporte}), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 404