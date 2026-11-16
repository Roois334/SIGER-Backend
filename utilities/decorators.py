from functools import wraps
from flask import jsonify, g
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
from extensions import db
from models.user import User
from utilities.permisos import tiene_permiso, ADMINISTRADOR


def _cargar_usuario_actual():
    verify_jwt_in_request()
    user = db.session.get(User, int(get_jwt_identity()))
    if not user or not user.activo:
        return None
    g.usuario = user
    return user


def _no_autorizado():
    return jsonify({"error": "Tu sesion ya no es valida o tu cuenta esta inactiva"}), 401


def login_activo_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not _cargar_usuario_actual():
            return _no_autorizado()
        return fn(*args, **kwargs)
    return wrapper


def permiso_required(permiso):
    def decorador(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            user = _cargar_usuario_actual()
            if not user:
                return _no_autorizado()
            if not tiene_permiso(user.rol.nombre, permiso):
                return jsonify({"error": "No tienes permisos para realizar esta accion"}), 403
            return fn(*args, **kwargs)
        return wrapper
    return decorador


def roles_required(*roles_permitidos):
    def decorador(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            user = _cargar_usuario_actual()
            if not user:
                return _no_autorizado()
            if user.rol.nombre not in roles_permitidos:
                return jsonify({"error": "No tienes permisos para acceder a este recurso"}), 403
            return fn(*args, **kwargs)
        return wrapper
    return decorador


def admin_required(fn):
    return roles_required(ADMINISTRADOR)(fn)
