from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from dtos.catalogo_dto import (
    MunicipioCreateDTO, MunicipioUpdateDTO, OrganismoCreateDTO, OrganismoUpdateDTO,
)
from services.catalogo_service import MunicipioService, OrganismoService
from utilities.decorators import admin_required

municipio_bp = Blueprint("municipio_bp", __name__, url_prefix="/api/municipios")
organismo_bp = Blueprint("organismo_bp", __name__, url_prefix="/api/organismos")


def _estado_arg():
    estado = request.args.get("estado")
    return estado if estado in ("activo", "inactivo") else None


# ---------------- Municipios ----------------

@municipio_bp.route("/activos", methods=["GET"])
@jwt_required()
def listar_municipios_activos():
    """
    Listado de solo lectura para cualquier usuario autenticado (no solo admin).
    Lo usa, por ejemplo, el formulario de registro de emergencias.
    """
    municipios = MunicipioService.list_municipios(estado="activo")
    return jsonify({"municipios": municipios}), 200


@municipio_bp.route("", methods=["GET"])
@admin_required
def listar_municipios():
    try:
        municipios = MunicipioService.list_municipios(busqueda=request.args.get("q"), estado=_estado_arg())
        return jsonify({"municipios": municipios}), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


@municipio_bp.route("", methods=["POST"])
@admin_required
def crear_municipio():
    data = request.get_json() or {}
    dto = MunicipioCreateDTO(codigo=data.get("codigo"), nombre=data.get("nombre"))
    try:
        municipio = MunicipioService.create_municipio(dto)
        return jsonify({"municipio": municipio}), 201
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


@municipio_bp.route("/<int:municipio_id>", methods=["GET"])
@admin_required
def obtener_municipio(municipio_id):
    try:
        municipio = MunicipioService.get_municipio(municipio_id)
        return jsonify({"municipio": municipio}), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 404


@municipio_bp.route("/<int:municipio_id>", methods=["PUT"])
@admin_required
def actualizar_municipio(municipio_id):
    data = request.get_json() or {}
    dto = MunicipioUpdateDTO(codigo=data.get("codigo"), nombre=data.get("nombre"))
    try:
        municipio = MunicipioService.update_municipio(municipio_id, dto)
        return jsonify({"municipio": municipio}), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


@municipio_bp.route("/<int:municipio_id>/estado", methods=["PATCH"])
@admin_required
def cambiar_estado_municipio(municipio_id):
    data = request.get_json() or {}
    activo = data.get("activo")
    if not isinstance(activo, bool):
        return jsonify({"error": "El campo 'activo' debe ser true o false"}), 400
    try:
        municipio = MunicipioService.set_active(municipio_id, activo)
        return jsonify({"municipio": municipio}), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


# ---------------- Organismos ----------------

@organismo_bp.route("", methods=["GET"])
@admin_required
def listar_organismos():
    try:
        organismos = OrganismoService.list_organismos(busqueda=request.args.get("q"), estado=_estado_arg())
        return jsonify({"organismos": organismos}), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


@organismo_bp.route("", methods=["POST"])
@admin_required
def crear_organismo():
    data = request.get_json() or {}
    dto = OrganismoCreateDTO(
        codigo=data.get("codigo"),
        nombre=data.get("nombre"),
        tipo=data.get("tipo"),
        municipios=data.get("municipios", []),
    )
    try:
        organismo = OrganismoService.create_organismo(dto)
        return jsonify({"organismo": organismo}), 201
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


@organismo_bp.route("/<int:organismo_id>", methods=["GET"])
@admin_required
def obtener_organismo(organismo_id):
    try:
        organismo = OrganismoService.get_organismo(organismo_id)
        return jsonify({"organismo": organismo}), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 404


@organismo_bp.route("/<int:organismo_id>", methods=["PUT"])
@admin_required
def actualizar_organismo(organismo_id):
    data = request.get_json() or {}
    dto = OrganismoUpdateDTO(codigo=data.get("codigo"), nombre=data.get("nombre"), tipo=data.get("tipo"))
    try:
        organismo = OrganismoService.update_organismo(organismo_id, dto)
        return jsonify({"organismo": organismo}), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


@organismo_bp.route("/<int:organismo_id>/estado", methods=["PATCH"])
@admin_required
def cambiar_estado_organismo(organismo_id):
    data = request.get_json() or {}
    activo = data.get("activo")
    if not isinstance(activo, bool):
        return jsonify({"error": "El campo 'activo' debe ser true o false"}), 400
    try:
        organismo = OrganismoService.set_active(organismo_id, activo)
        return jsonify({"organismo": organismo}), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


@organismo_bp.route("/<int:organismo_id>/municipios", methods=["PUT"])
@admin_required
def asociar_municipios(organismo_id):
    data = request.get_json() or {}
    ids_municipios = data.get("municipios", [])
    if not isinstance(ids_municipios, list):
        return jsonify({"error": "El campo 'municipios' debe ser una lista de ids"}), 400
    try:
        organismo = OrganismoService.set_municipios(organismo_id, ids_municipios)
        return jsonify({"organismo": organismo}), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 400