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

EXTENSIONES_PERMITIDAS = {"png", "jpg", "jpeg", "gif", "pdf", "mp4"}
MAX_EVIDENCIAS = 5


class ReporteService:

    @staticmethod
    def _extension_valida(filename):
        return "." in filename and filename.rsplit(".", 1)[1].lower() in EXTENSIONES_PERMITIDAS

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
            r.id, r.folio, r.tipo, r.descripcion, r.direccion, r.latitud, r.longitud,
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
        except (ValueError, TypeError):
            raise ValueError("El numero de afectados debe ser un entero valido")

        # --- Creacion del reporte ---
        reporte = Reporte(
            folio=ReporteService._generar_folio(),
            ciudadano_id=ciudadano_id,
            municipio_id=dto.municipio_id,
            tipo=dto.tipo,
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
        if archivos and upload_folder:
            archivos_validos = [f for f in archivos if f and f.filename][:MAX_EVIDENCIAS]
            os.makedirs(upload_folder, exist_ok=True)
            for archivo in archivos_validos:
                if not ReporteService._extension_valida(archivo.filename):
                    raise ValueError(f"Formato de archivo no permitido: {archivo.filename}")
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