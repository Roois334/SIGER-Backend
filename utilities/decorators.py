from functools import wraps
from flask import jsonify
from flask_jwt_extended import verify_jwt_in_request, get_jwt


def admin_required(fn):
    """
    Protege una ruta para que solo pueda acceder un usuario autenticado
    (JWT valido) cuyo claim 'rol' sea 'administrador'.
    """
    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        claims = get_jwt()
        if claims.get("rol") != "administrador":
            return jsonify({"error": "No tienes permisos de administrador"}), 403
        return fn(*args, **kwargs)
    return wrapper

def roles_required(*roles_permitidos):
    """
    Protege una ruta para que solo accedan usuarios autenticados (JWT valido)
    cuyo claim 'rol' este dentro de los roles permitidos.
    Uso: @roles_required("gestor_municipal", "administrador")
    """
    def decorador(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            verify_jwt_in_request()
            claims = get_jwt()
            if claims.get("rol") not in roles_permitidos:
                return jsonify({"error": "No tienes permisos para acceder a este recurso"}), 403
            return fn(*args, **kwargs)
        return wrapper
    return decorador