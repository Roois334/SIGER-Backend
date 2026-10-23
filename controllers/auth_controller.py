from flask import Blueprint, request, jsonify
from dtos.user_dto import UserRegisterDTO, UserLoginDTO
from services.auth_service import AuthService
from services.recuperacion_service import RecuperacionService
from utilities.limitador import LimitadorIntentos

# 5 intentos fallidos por correo cada 15 minutos
_limitador_login = LimitadorIntentos(maximo=5, ventana_seg=900)

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
            rol="ciudadano",  # el registro publico SIEMPRE crea ciudadanos
            municipio=data.get("municipio"),
            tipo_documento=data.get("tipo_documento"),
            documento=data.get("documento"),
            telefono=data.get("telefono"),
        )
        token, user = AuthService.register(dto)
        return jsonify({"token": token, "usuario": user.to_dict()}), 201
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    clave = str(data.get("email") or "").strip().lower()
    espera = _limitador_login.segundos_bloqueado(clave)
    if espera:
        minutos = espera // 60 + 1
        return jsonify({"error": f"Demasiados intentos fallidos. Intenta de nuevo en {minutos} minuto(s)"}), 429
    try:
        dto = UserLoginDTO(email=data.get("email"), password=data.get("password"))
        token, user = AuthService.login(dto)
        _limitador_login.registrar_exito(clave)
        return jsonify({"token": token, "usuario": user.to_dict()}), 200
    except ValueError as e:
        _limitador_login.registrar_fallo(clave)
        return jsonify({"error": str(e)}), 401



@auth_bp.route("/olvide-password", methods=["POST"])
def olvide_password():
    """Envia un enlace de recuperacion. Responde siempre igual para no revelar que correos existen."""
    data = request.get_json(silent=True) or {}
    try:
        RecuperacionService.solicitar(data.get("email"))
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    return jsonify({"mensaje": "Si el correo esta registrado, te enviamos un enlace para restablecer tu contrasena"}), 200


@auth_bp.route("/restablecer/<token>", methods=["GET"])
def validar_enlace(token):
    try:
        return jsonify(RecuperacionService.validar(token)), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 410


@auth_bp.route("/restablecer", methods=["POST"])
def restablecer_password():
    data = request.get_json(silent=True) or {}
    try:
        RecuperacionService.restablecer(data.get("token"), data.get("nueva"))
        return jsonify({"mensaje": "Contrasena actualizada"}), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
