from functools import wraps
from flask import jsonify, g
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
from models.user import User
from utilities.permisos import tiene_permiso, ADMINISTRADOR


def _cargar_usuario_actual():
    """
    Valida el JWT y carga el usuario DESDE LA BASE DE DATOS.
    Asi, si el administrador le cambia el rol o desactiva la cuenta,
    el cambio aplica de inmediato (no se confia en el rol guardado en el token).
    Deja el usuario disponible en g.usuario.
    """
    verify_jwt_in_request()
    user = User.query.get(int(get_jwt_identity()))
    if not user or not user.activo:
        return None
    g.usuario = user
    return user


def _no_autorizado():
    return jsonify({"error": "Tu sesion ya no es valida o tu cuenta esta inactiva"}), 401


def login_activo_required(fn):
    """Cualquier usuario autenticado y con la cuenta activa."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not _cargar_usuario_actual():
            return _no_autorizado()
        return fn(*args, **kwargs)
    return wrapper


def permiso_required(permiso):
    """
    Protege una ruta segun la matriz de utilities/permisos.py.
    Uso: @permiso_required("reportes.crear")
    """
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
    """
    Protege una ruta para una lista explicita de roles (rol leido desde la BD).
    Uso: @roles_required("gestor_municipal", "administrador")
    """
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
    """Solo administradores activos (rol leido desde la BD)."""
    return roles_required(ADMINISTRADOR)(fn)
