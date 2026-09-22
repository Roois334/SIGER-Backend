from flask import Blueprint, request, jsonify
from dtos.user_dto import UserRegisterDTO, UserLoginDTO
from services.auth_service import AuthService

auth_bp = Blueprint("auth_bp", __name__, url_prefix="/api/auth")


@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.get_json() or {}
    try:
        dto = UserRegisterDTO(
            nombre=data.get("nombre"),
            apellido=data.get("apellido"),
            email=data.get("email"),
            password=data.get("password"),
            rol=data.get("rol", "ciudadano"),
            municipio=data.get("municipio"),
        )
        token, user = AuthService.register(dto)
        return jsonify({"token": token, "usuario": user.to_dict()}), 201
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json() or {}
    try:
        dto = UserLoginDTO(email=data.get("email"), password=data.get("password"))
        token, user = AuthService.login(dto)
        return jsonify({"token": token, "usuario": user.to_dict()}), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 401
