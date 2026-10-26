from flask import Blueprint, request, jsonify, g

from utilities.decorators import login_activo_required
from services.notificacion_service import NotificacionService

notificacion_bp = Blueprint("notificacion_bp", __name__, url_prefix="/api/notificaciones")


@notificacion_bp.route("", methods=["GET"])
@login_activo_required
def listar():
    """Mis notificaciones (mas nuevas primero) y cuantas tengo sin leer."""
    datos = NotificacionService.listar(
        g.usuario,
        solo_no_leidas=request.args.get("no_leidas") == "1",
        limite=request.args.get("limite", 50, type=int),
        antes_id=request.args.get("antes_id", type=int),
    )
    return jsonify(datos), 200


@notificacion_bp.route("/contador", methods=["GET"])
@login_activo_required
def contador():
    return jsonify({"no_leidas": NotificacionService.contar_no_leidas(g.usuario)}), 200


@notificacion_bp.route("/<int:notificacion_id>/leer", methods=["POST"])
@login_activo_required
def leer(notificacion_id):
    try:
        n = NotificacionService.marcar_leida(notificacion_id, g.usuario)
    except LookupError as e:
        return jsonify({"error": str(e)}), 404
    return jsonify({"notificacion": n, "no_leidas": NotificacionService.contar_no_leidas(g.usuario)}), 200


@notificacion_bp.route("/leer-todas", methods=["POST"])
@login_activo_required
def leer_todas():
    NotificacionService.marcar_todas(g.usuario)
    return jsonify({"no_leidas": 0}), 200
