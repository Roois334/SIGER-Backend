from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import get_jwt_identity
from dtos.user_dto import UserUpdateDTO
from services.user_service import UserService
from utilities.decorators import admin_required, login_activo_required

user_bp = Blueprint("user_bp", __name__, url_prefix="/api/usuarios")


@user_bp.route("/me", methods=["GET"])
@login_activo_required
def obtener_mi_perfil():
    """Cualquier usuario autenticado puede consultar sus propios datos."""
    user_id = int(get_jwt_identity())
    try:
        usuario = UserService.get_user(user_id)
        return jsonify({"usuario": usuario}), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 404


@user_bp.route("/me", methods=["PUT"])
@login_activo_required
def actualizar_mi_perfil():
    """Nombre, apellido y (solo ciudadanos) municipio del propio usuario."""
    data = request.get_json(silent=True) or {}
    try:
        usuario = UserService.update_me(int(get_jwt_identity()), data.get("nombre"),
                                        data.get("apellido"), data.get("municipio"))
        return jsonify({"usuario": usuario}), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


@user_bp.route("/me/email", methods=["PUT"])
@login_activo_required
def cambiar_mi_correo():
    data = request.get_json(silent=True) or {}
    try:
        usuario = UserService.change_email(int(get_jwt_identity()), data.get("email"), data.get("password"))
        return jsonify({"usuario": usuario}), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


@user_bp.route("/me/password", methods=["PUT"])
@login_activo_required
def cambiar_mi_password():
    data = request.get_json(silent=True) or {}
    try:
        usuario = UserService.change_password(int(get_jwt_identity()), data.get("actual"), data.get("nueva"))
        return jsonify({"usuario": usuario}), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


@user_bp.route("/me/foto", methods=["DELETE"])
@login_activo_required
def quitar_mi_foto():
    try:
        usuario = UserService.remove_foto(int(get_jwt_identity()),
                                          upload_folder=current_app.config["UPLOAD_FOLDER_PERFILES"])
        return jsonify({"usuario": usuario}), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


@user_bp.route("/me/foto", methods=["POST"])
@login_activo_required
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
        organismo_id=data.get("organismo_id"),
    )
    try:
        usuario = UserService.update_user(user_id, dto, admin_id=get_jwt_identity())
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