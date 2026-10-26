import os
from flask import Blueprint, request, jsonify, current_app, send_from_directory, g
from utilities.decorators import permiso_required, login_activo_required

from dtos.reporte_dto import ReporteCreateDTO
from services.reporte_service import ReporteService, PermisoError, NoEncontradoError

reporte_bp = Blueprint("reporte_bp", __name__, url_prefix="/api/reportes")


@reporte_bp.route("/configuracion", methods=["GET"])
@login_activo_required
def configuracion_reportes():
    """Tipos de emergencia, prioridades y limites que usa el formulario."""
    return jsonify(ReporteService.configuracion()), 200


@reporte_bp.route("", methods=["POST"])
@permiso_required("reportes.crear")
def crear_reporte():
    """
    Solo los ciudadanos registran emergencias (ver utilities/permisos.py).
    Se envia como multipart/form-data para poder incluir las evidencias.
    """
    ciudadano_id = g.usuario.id
    data = request.form

    dto = ReporteCreateDTO(
        tipo=data.get("tipo"),
        municipio_id=data.get("municipio_id", type=int),
        direccion=data.get("direccion"),
        descripcion=data.get("descripcion"),
        latitud=data.get("latitud", type=float),
        longitud=data.get("longitud", type=float),
        afectados=data.get("afectados", 0),
        heridos=data.get("heridos", 0),
    )

    archivos = request.files.getlist("evidencias")

    try:
        reporte = ReporteService.create_reporte(
            dto, ciudadano_id,
            archivos=archivos,
            upload_folder=current_app.config["UPLOAD_FOLDER"],
        )
        return jsonify({"reporte": reporte}), 201
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


@reporte_bp.route("", methods=["GET"])
@permiso_required("reportes.ver_propios")
def listar_mis_reportes():
    reportes = ReporteService.list_reportes_ciudadano(g.usuario.id)
    return jsonify({"reportes": reportes}), 200


@reporte_bp.route("/gestion", methods=["GET"])
@permiso_required("emergencias.consultar")
def listar_reportes_gestion():
    """
    Listado de emergencias. El administrador ve todo; gestores y organismos
    solo ven las de su municipio (el filtro lo aplica el servicio).
    """
    try:
        reportes = ReporteService.list_reportes_gestion(
            busqueda=request.args.get("q"),
            tipo=request.args.get("tipo"),
            estado=request.args.get("estado"),
            prioridad=request.args.get("prioridad"),
            municipio_id=request.args.get("municipio_id", type=int),
            usuario=g.usuario,
            desde=request.args.get("desde"),
            hasta=request.args.get("hasta"),
        )
        return jsonify({"reportes": reportes}), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


@reporte_bp.route("/estadisticas", methods=["GET"])
@permiso_required("emergencias.consultar")
def estadisticas_reportes():
    """Indicadores para estadisticas y dashboard (respetan el alcance del usuario)."""
    try:
        datos = ReporteService.estadisticas(
            g.usuario,
            desde=request.args.get("desde"), hasta=request.args.get("hasta"),
            municipio_id=request.args.get("municipio_id", type=int),
            tipo=request.args.get("tipo"), prioridad=request.args.get("prioridad"),
        )
        return jsonify(datos), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


@reporte_bp.route("/publico", methods=["GET"])
@login_activo_required
def listar_reportes_publicos():
    """Emergencias activas de la comunidad con datos recortados (sin informacion personal)."""
    reportes = ReporteService.list_reportes_publicos(g.usuario)
    return jsonify({"reportes": reportes}), 200


@reporte_bp.route("/<int:reporte_id>", methods=["GET"])
@login_activo_required
def obtener_reporte(reporte_id):
    try:
        reporte = ReporteService.get_reporte(reporte_id, usuario=g.usuario)
        return jsonify({"reporte": reporte}), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 404


def _error(e):
    codigo = 403 if isinstance(e, PermisoError) else 404 if isinstance(e, NoEncontradoError) else 400
    return jsonify({"error": str(e)}), codigo


@reporte_bp.route("/<int:reporte_id>/asignar", methods=["POST"])
@permiso_required("reportes.asignar")
def asignar_reporte(reporte_id):
    """El gestor acepta el reporte y lo asigna (o reasigna) a un organismo."""
    data = request.get_json(silent=True) or {}
    try:
        reporte = ReporteService.asignar_reporte(
            reporte_id, data.get("organismo_id"), g.usuario,
            prioridad=data.get("prioridad"), comentario=data.get("comentario"),
            vias_afectadas=data.get("vias_afectadas"), area_afectada=data.get("area_afectada"),
            riesgo_propagacion=data.get("riesgo_propagacion"),
        )
        return jsonify({"reporte": reporte}), 200
    except ValueError as e:
        return _error(e)


@reporte_bp.route("/<int:reporte_id>/estado", methods=["POST"])
@login_activo_required
def cambiar_estado_reporte(reporte_id):
    """
    Acciones: descartar (gestor), iniciar / resolver / devolver (organismo asignado).
    El servicio valida quien puede hacer cada una y desde que estado.
    """
    data = request.get_json(silent=True) or {}
    try:
        reporte = ReporteService.cambiar_estado(
            reporte_id, data.get("accion"), g.usuario, comentario=data.get("comentario"),
        )
        return jsonify({"reporte": reporte}), 200
    except ValueError as e:
        return _error(e)


@reporte_bp.route("/<int:reporte_id>/tipo", methods=["POST"])
@login_activo_required
def cambiar_tipo_reporte(reporte_id):
    """El gestor corrige el tipo de una emergencia abierta (motivo obligatorio)."""
    data = request.get_json(silent=True) or {}
    try:
        reporte = ReporteService.cambiar_tipo(
            reporte_id, data.get("tipo"), g.usuario, comentario=data.get("comentario"),
        )
        return jsonify({"reporte": reporte}), 200
    except ValueError as e:
        return _error(e)


@reporte_bp.route("/evidencias/<int:evidencia_id>", methods=["GET"])
@login_activo_required
def obtener_evidencia(evidencia_id):
    """
    Sirve el archivo de una evidencia solo si el usuario puede ver el
    reporte al que pertenece (dueno, admin, o gestor/organismo de ese municipio).
    """
    try:
        evidencia = ReporteService.get_evidencia_autorizada(evidencia_id, g.usuario)
    except ValueError as e:
        return jsonify({"error": str(e)}), 403

    # Se usa solo el nombre del archivo (nunca una ruta del cliente/BD) y se busca
    # primero en la carpeta privada actual y luego en la carpeta antigua (static),
    # para que las evidencias subidas antes de este cambio sigan funcionando.
    nombre = os.path.basename(evidencia.ruta_archivo)
    carpetas = [
        current_app.config["UPLOAD_FOLDER"],
        os.path.join(current_app.static_folder, "uploads", "evidencias"),
    ]
    for carpeta in carpetas:
        if os.path.isfile(os.path.join(carpeta, nombre)):
            respuesta = send_from_directory(carpeta, nombre, as_attachment=False)
            respuesta.headers["X-Content-Type-Options"] = "nosniff"
            respuesta.headers["Cache-Control"] = "private, max-age=3600"
            return respuesta

    return jsonify({"error": "El archivo de la evidencia ya no esta disponible"}), 404
