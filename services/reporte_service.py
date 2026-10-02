import os
import uuid
from datetime import datetime
from werkzeug.utils import secure_filename

from extensions import db
from models.reporte import Reporte, Evidencia
from models.catalogos import Municipio
from dtos.reporte_dto import ReporteDTO, EvidenciaDTO

TIPOS_EMERGENCIA = [
    "Incendio",
    "Inundacion",
    "Accidente de transito",
    "Deslizamiento",
    "Fuga o derrame de sustancias",
    "Emergencia medica",
    "Otro",
]

PRIORIDAD_POR_TIPO = {
    "Incendio": "alta",
    "Inundacion": "alta",
    "Accidente de transito": "media",
    "Deslizamiento": "alta",
    "Fuga o derrame de sustancias": "critica",
    "Emergencia medica": "critica",
    "Otro": "media",
}

EXTENSIONES_PERMITIDAS = {"png", "jpg", "jpeg", "gif", "pdf", "mp4"}
MIMETYPES_PERMITIDOS = {
    "image/png", "image/jpeg", "image/gif",
    "application/pdf", "video/mp4",
}
MAX_EVIDENCIAS = 5
MAX_TAMANO_ARCHIVO_MB = 10
MAX_AFECTADOS = 100000


class ReporteService:

    @staticmethod
    def _extension_valida(filename):
        return "." in filename and filename.rsplit(".", 1)[1].lower() in EXTENSIONES_PERMITIDAS

    @staticmethod
    def _tamano_valido(archivo):
        """Revisa el tamano real del archivo sin cargarlo completo a memoria."""
        archivo.stream.seek(0, os.SEEK_END)
        tamano_bytes = archivo.stream.tell()
        archivo.stream.seek(0)
        return tamano_bytes <= MAX_TAMANO_ARCHIVO_MB * 1024 * 1024

    @staticmethod
    def _generar_folio():
        """Genera un identificador unico tipo RPT-2026-00001, correlativo por anio."""
        anio = datetime.utcnow().year
        prefijo = f"RPT-{anio}-"
        ultimo = (
            Reporte.query.filter(Reporte.folio.like(f"{prefijo}%"))
            .order_by(Reporte.id.desc())
            .first()
        )
        siguiente = 1
        if ultimo:
            try:
                siguiente = int(ultimo.folio.replace(prefijo, "")) + 1
            except ValueError:
                siguiente = Reporte.query.count() + 1
        return f"{prefijo}{siguiente:05d}"

    @staticmethod
    def _to_dto(r):
        return ReporteDTO(
            r.id, r.folio, r.tipo, r.prioridad, r.descripcion, r.direccion, r.latitud, r.longitud,
            r.afectados, r.estado, r.fecha_hora, r.ciudadano_id,
            r.municipio.nombre if r.municipio else None,
            evidencias=[EvidenciaDTO(e.id, e.nombre_archivo, e.ruta_archivo, e.fecha_carga) for e in r.evidencias],
        )

    @staticmethod
    def create_reporte(dto, ciudadano_id, archivos=None, upload_folder=None):
        # --- Validaciones de campos obligatorios ---
        if not dto.tipo or dto.tipo not in TIPOS_EMERGENCIA:
            raise ValueError("Debes seleccionar un tipo de emergencia valido")

        if not dto.direccion or not dto.direccion.strip():
            raise ValueError("La ubicacion / direccion es obligatoria")

        if not dto.descripcion or len(dto.descripcion.strip()) < 15:
            raise ValueError("La descripcion debe tener al menos 15 caracteres")

        if not dto.municipio_id:
            raise ValueError("Debes seleccionar el municipio donde ocurre la emergencia")

        municipio = Municipio.query.get(dto.municipio_id)
        if not municipio or not municipio.activo:
            raise ValueError("Municipio invalido")

        try:
            afectados = int(dto.afectados or 0)
            if afectados < 0:
                raise ValueError
            if afectados > MAX_AFECTADOS:
                raise ValueError(f"El numero de afectados no puede superar {MAX_AFECTADOS}")
        except (ValueError, TypeError):
            raise ValueError("El numero de afectados debe ser un entero valido")

        # --- Validaciones de coordenadas ---
        if (dto.latitud is None) != (dto.longitud is None):
            raise ValueError("Debes proporcionar tanto la latitud como la longitud, o ninguna de las dos")

        if dto.latitud is not None and not (-90 <= dto.latitud <= 90):
            raise ValueError("La latitud debe estar entre -90 y 90 grados")

        if dto.longitud is not None and not (-180 <= dto.longitud <= 180):
            raise ValueError("La longitud debe estar entre -180 y 180 grados")

        # --- Validacion de evidencias (formato y tamano) ---
        archivos_validos = []
        if archivos:
            archivos_validos = [f for f in archivos if f and f.filename][:MAX_EVIDENCIAS]
            for archivo in archivos_validos:
                if not ReporteService._extension_valida(archivo.filename):
                    raise ValueError(f"Formato de archivo no permitido: {archivo.filename}")
                if archivo.mimetype not in MIMETYPES_PERMITIDOS:
                    raise ValueError(f"El archivo {archivo.filename} no tiene un tipo de contenido valido")
                if not ReporteService._tamano_valido(archivo):
                    raise ValueError(f"El archivo {archivo.filename} supera el tamano maximo de {MAX_TAMANO_ARCHIVO_MB} MB")

        # --- Creacion del reporte ---
        reporte = Reporte(
            folio=ReporteService._generar_folio(),
            ciudadano_id=ciudadano_id,
            municipio_id=dto.municipio_id,
            tipo=dto.tipo,
            prioridad=PRIORIDAD_POR_TIPO.get(dto.tipo, "media"),
            descripcion=dto.descripcion.strip(),
            direccion=dto.direccion.strip(),
            latitud=dto.latitud,
            longitud=dto.longitud,
            afectados=afectados,
            estado="pendiente",
        )
        db.session.add(reporte)
        db.session.flush()  # asigna reporte.id sin cerrar la transaccion

        # --- Carga de evidencias (opcional) ---
        if archivos_validos and upload_folder:
            os.makedirs(upload_folder, exist_ok=True)
            for archivo in archivos_validos:
                nombre_seguro = secure_filename(archivo.filename)
                nombre_unico = f"{reporte.folio}_{uuid.uuid4().hex[:8]}_{nombre_seguro}"
                ruta_absoluta = os.path.join(upload_folder, nombre_unico)
                archivo.save(ruta_absoluta)

                evidencia = Evidencia(
                    reporte_id=reporte.id,
                    nombre_archivo=nombre_seguro,
                    ruta_archivo=f"/static/uploads/evidencias/{nombre_unico}",
                )
                db.session.add(evidencia)

        db.session.commit()
        return ReporteService._to_dto(reporte).to_dict()

    @staticmethod
    def get_reporte(reporte_id, ciudadano_id=None):
        r = Reporte.query.get(reporte_id)
        if not r:
            raise ValueError("Reporte no encontrado")
        if ciudadano_id is not None and r.ciudadano_id != ciudadano_id:
            raise ValueError("No tienes acceso a este reporte")
        return ReporteService._to_dto(r).to_dict()

    @staticmethod
    def list_reportes_ciudadano(ciudadano_id):
        reportes = (
            Reporte.query.filter_by(ciudadano_id=ciudadano_id)
            .order_by(Reporte.fecha_hora.desc())
            .all()
        )
        return [ReporteService._to_dto(r).to_dict() for r in reportes]

    @staticmethod
    def list_reportes_gestion(busqueda=None, tipo=None, estado=None, prioridad=None, municipio_id=None):
        """Listado centralizado para gestores/administradores, con filtros opcionales."""
        query = Reporte.query

        if busqueda:
            like = f"%{busqueda.strip()}%"
            query = query.filter(
                db.or_(
                    Reporte.folio.ilike(like),
                    Reporte.tipo.ilike(like),
                    Reporte.direccion.ilike(like),
                )
            )

        if tipo:
            query = query.filter(Reporte.tipo == tipo)

        if estado:
            query = query.filter(Reporte.estado == estado)

        if prioridad:
            query = query.filter(Reporte.prioridad == prioridad)

        if municipio_id:
            query = query.filter(Reporte.municipio_id == municipio_id)

        reportes = query.order_by(Reporte.fecha_hora.desc()).all()
        return [ReporteService._to_dto(r).to_dict() for r in reportes]

    @staticmethod
    def get_evidencia_autorizada(evidencia_id, usuario_id, rol):
        """
        Devuelve la evidencia solo si el usuario es dueno del reporte
        al que pertenece, o tiene rol gestor_municipal / administrador.
        """
        evidencia = Evidencia.query.get(evidencia_id)
        if not evidencia:
            raise ValueError("Evidencia no encontrada")

        reporte = evidencia.reporte
        es_dueno = reporte.ciudadano_id == usuario_id
        es_gestor_o_admin = rol in ("gestor_municipal", "administrador")

        if not es_dueno and not es_gestor_o_admin:
            raise ValueError("No tienes permiso para acceder a esta evidencia")

        return evidencia