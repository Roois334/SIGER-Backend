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