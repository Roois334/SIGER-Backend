from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import get_jwt_identity, jwt_required
from dtos.user_dto import UserUpdateDTO
from services.user_service import UserService
from utilities.decorators import admin_required

user_bp = Blueprint("user_bp", __name__, url_prefix="/api/usuarios")


@user_bp.route("/me", methods=["GET"])
@jwt_required()
def obtener_mi_perfil():
    """Cualquier usuario autenticado puede consultar sus propios datos."""
    user_id = int(get_jwt_identity())
    try:
        usuario = UserService.get_user(user_id)
        return jsonify({"usuario": usuario}), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 404


@user_bp.route("/me/foto", methods=["POST"])
@jwt_required()
def subir_mi_foto():
    """Cualquier usuario autenticado puede cambiar su propia foto de perfil."""
    user_id = int(get_jwt_identity())
    archivo = request.files.get("foto")

    try:
        usuario = UserService.update_foto(
            user_id, archivo,
            upload_folder=current_app.config["UPLOAD_FOLDER_PERFILES"],
        )
        return jsonify({"usuario": usuario}), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


@user_bp.route("", methods=["GET"])
@admin_required
def listar_usuarios():
    busqueda = request.args.get("q")
    rol = request.args.get("rol")
    estado = request.args.get("estado")  # "activo" | "inactivo"

    activo = None
    if estado == "activo":
        activo = True
    elif estado == "inactivo":
        activo = False

    try:
        usuarios = UserService.list_users(busqueda=busqueda, rol=rol, activo=activo)
        return jsonify({"usuarios": usuarios}), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


@user_bp.route("/<int:user_id>", methods=["GET"])
@admin_required
def obtener_usuario(user_id):
    try:
        usuario = UserService.get_user(user_id)
        return jsonify({"usuario": usuario}), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 404


@user_bp.route("/<int:user_id>", methods=["PUT"])
@admin_required
def actualizar_usuario(user_id):
    data = request.get_json() or {}
    dto = UserUpdateDTO(
        nombre=data.get("nombre"),
        apellido=data.get("apellido"),
        email=data.get("email"),
        municipio=data.get("municipio"),
        rol=data.get("rol"),
    )
    try:
        usuario = UserService.update_user(user_id, dto)
        return jsonify({"usuario": usuario}), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


@user_bp.route("/<int:user_id>/estado", methods=["PATCH"])
@admin_required
def cambiar_estado(user_id):
    data = request.get_json() or {}
    activo = data.get("activo")
    if not isinstance(activo, bool):
        return jsonify({"error": "El campo 'activo' debe ser true o false"}), 400

    try:
        usuario = UserService.set_active(user_id, activo, get_jwt_identity())
        return jsonify({"usuario": usuario}), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 400