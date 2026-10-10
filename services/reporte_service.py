import os
import uuid
from datetime import datetime, timedelta, timezone
from sqlalchemy.exc import IntegrityError
from werkzeug.utils import secure_filename

from extensions import db
from models.reporte import Reporte, Evidencia
from models.catalogos import Municipio
from dtos.reporte_dto import ReporteDTO, EvidenciaDTO
from utilities.permisos import ADMINISTRADOR, tiene_alcance_municipal

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
MAX_DIRECCION = 200
MIN_DESCRIPCION = 15
MAX_DESCRIPCION = 2000

# Caja geografica generosa que cubre la Sabana de Occidente y alrededores
# (Cundinamarca). Evita coordenadas absurdas (0,0, otro pais, etc.).
LAT_MIN, LAT_MAX = 4.3, 5.3
LON_MIN, LON_MAX = -75.0, -73.8

# Colombia no tiene horario de verano: UTC-5 fijo (no depende de tzdata/Windows).
ZONA_COLOMBIA = timezone(timedelta(hours=-5))


def _ahora():
    """Fecha y hora actual de Colombia, sin zona (como se guarda en la BD)."""
    return datetime.now(ZONA_COLOMBIA).replace(tzinfo=None)


class ReporteService:

    @staticmethod
    def configuracion():
        """Datos que el formulario necesita (una sola fuente de verdad)."""
        return {
            "tipos": [{"nombre": t, "prioridad": PRIORIDAD_POR_TIPO.get(t, "media")} for t in TIPOS_EMERGENCIA],
            "limites": {
                "max_evidencias": MAX_EVIDENCIAS,
                "max_mb": MAX_TAMANO_ARCHIVO_MB,
                "max_afectados": MAX_AFECTADOS,
                "min_descripcion": MIN_DESCRIPCION,
                "max_descripcion": MAX_DESCRIPCION,
                "max_direccion": MAX_DIRECCION,
            },
            "extensiones": sorted(EXTENSIONES_PERMITIDAS),
            "region": {"lat_min": LAT_MIN, "lat_max": LAT_MAX, "lon_min": LON_MIN, "lon_max": LON_MAX},
        }

    # ------------------------------------------------------------------ archivos

    @staticmethod
    def _extension(filename):
        return filename.rsplit(".", 1)[1].lower() if "." in filename else ""

    @staticmethod
    def _extension_valida(filename):
        return ReporteService._extension(filename) in EXTENSIONES_PERMITIDAS

    @staticmethod
    def _tamano_valido(archivo):
        """Revisa el tamano real del archivo sin cargarlo completo a memoria."""
        archivo.stream.seek(0, os.SEEK_END)
        tamano_bytes = archivo.stream.tell()
        archivo.stream.seek(0)
        return 0 < tamano_bytes <= MAX_TAMANO_ARCHIVO_MB * 1024 * 1024

    @staticmethod
    def _firma_valida(archivo, extension):
        """Comprueba los primeros bytes: el archivo es lo que dice ser."""
        cabecera = archivo.stream.read(16)
        archivo.stream.seek(0)
        if extension == "png":
            return cabecera.startswith(b"\x89PNG\r\n\x1a\n")
        if extension in ("jpg", "jpeg"):
            return cabecera.startswith(b"\xff\xd8\xff")
        if extension == "gif":
            return cabecera[:6] in (b"GIF87a", b"GIF89a")
        if extension == "pdf":
            return cabecera.startswith(b"%PDF")
        if extension == "mp4":
            return cabecera[4:8] == b"ftyp"
        return False

    # ------------------------------------------------------------------ folio / dto

    @staticmethod
    def _generar_folio():
        """Genera un identificador unico tipo RPT-2026-00001, correlativo por anio."""
        prefijo = f"RPT-{_ahora().year}-"
        ultimo = (
            Reporte.query.filter(Reporte.folio.like(f"{prefijo}%"))
            .order_by(Reporte.folio.desc())
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
            ciudadano_nombre=f"{r.ciudadano.nombre} {r.ciudadano.apellido}".strip() if r.ciudadano else None,
        )

    # ------------------------------------------------------------------ crear

    @staticmethod
    def _validar_campos(dto):
        """Valida los campos obligatorios y devuelve (afectados, municipio)."""
        if not dto.tipo or dto.tipo not in TIPOS_EMERGENCIA:
            raise ValueError("Debes seleccionar un tipo de emergencia valido")

        if not dto.municipio_id:
            raise ValueError("Debes seleccionar el municipio donde ocurre la emergencia")

        municipio = Municipio.query.get(dto.municipio_id)
        if not municipio or not municipio.activo:
            raise ValueError("Municipio invalido")

        direccion = (dto.direccion or "").strip()
        if not direccion:
            raise ValueError("La ubicacion / direccion es obligatoria")
        if len(direccion) > MAX_DIRECCION:
            raise ValueError(f"La direccion no puede superar {MAX_DIRECCION} caracteres")

        descripcion = (dto.descripcion or "").strip()
        if len(descripcion) < MIN_DESCRIPCION:
            raise ValueError(f"La descripcion debe tener al menos {MIN_DESCRIPCION} caracteres")
        if len(descripcion) > MAX_DESCRIPCION:
            raise ValueError(f"La descripcion no puede superar {MAX_DESCRIPCION} caracteres")

        try:
            afectados = int(str(dto.afectados).strip() or 0)
        except (ValueError, TypeError):
            raise ValueError("El numero de afectados debe ser un entero valido")
        if afectados < 0:
            raise ValueError("El numero de afectados no puede ser negativo")
        if afectados > MAX_AFECTADOS:
            raise ValueError(f"El numero de afectados no puede superar {MAX_AFECTADOS}")

        if (dto.latitud is None) != (dto.longitud is None):
            raise ValueError("Debes proporcionar tanto la latitud como la longitud, o ninguna de las dos")
        if dto.latitud is not None:
            if not (-90 <= dto.latitud <= 90):
                raise ValueError("La latitud debe estar entre -90 y 90 grados")
            if not (-180 <= dto.longitud <= 180):
                raise ValueError("La longitud debe estar entre -180 y 180 grados")
            if not (LAT_MIN <= dto.latitud <= LAT_MAX and LON_MIN <= dto.longitud <= LON_MAX):
                raise ValueError("La ubicacion marcada esta fuera de la region de la Sabana de Occidente")

        return afectados

    @staticmethod
    def _validar_archivos(archivos):
        validos = [f for f in (archivos or []) if f and f.filename]
        if len(validos) > MAX_EVIDENCIAS:
            raise ValueError(f"Puedes adjuntar maximo {MAX_EVIDENCIAS} evidencias")

        for archivo in validos:
            extension = ReporteService._extension(archivo.filename)
            if extension not in EXTENSIONES_PERMITIDAS:
                raise ValueError(f"Formato de archivo no permitido: {archivo.filename}")
            if archivo.mimetype not in MIMETYPES_PERMITIDOS:
                raise ValueError(f"El archivo {archivo.filename} no tiene un tipo de contenido valido")
            if not ReporteService._tamano_valido(archivo):
                raise ValueError(f"El archivo {archivo.filename} esta vacio o supera {MAX_TAMANO_ARCHIVO_MB} MB")
            if not ReporteService._firma_valida(archivo, extension):
                raise ValueError(f"El archivo {archivo.filename} esta danado o no corresponde a su formato")
        return validos

    @staticmethod
    def create_reporte(dto, ciudadano_id, archivos=None, upload_folder=None):
        afectados = ReporteService._validar_campos(dto)
        archivos_validos = ReporteService._validar_archivos(archivos)

        # --- Creacion del reporte (folio unico; reintenta si dos envios chocan) ---
        reporte = None
        for _ in range(5):
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
                fecha_hora=_ahora(),
            )
            db.session.add(reporte)
            try:
                db.session.flush()  # asigna reporte.id sin cerrar la transaccion
                break
            except IntegrityError:
                db.session.rollback()
                reporte = None
        if reporte is None:
            raise ValueError("No se pudo generar el identificador del reporte. Intenta de nuevo")

        # --- Carga de evidencias (opcional). Si algo falla, no queda nada a medias ---
        guardados = []
        if archivos_validos and upload_folder:
            try:
                os.makedirs(upload_folder, exist_ok=True)
                for archivo in archivos_validos:
                    nombre_seguro = secure_filename(archivo.filename) or "evidencia"
                    nombre_unico = f"{reporte.folio}_{uuid.uuid4().hex[:8]}_{nombre_seguro}"
                    archivo.save(os.path.join(upload_folder, nombre_unico))
                    guardados.append(nombre_unico)

                    db.session.add(Evidencia(
                        reporte_id=reporte.id,
                        nombre_archivo=nombre_seguro,
                        ruta_archivo=nombre_unico,  # solo el nombre; la carpeta sale de la config
                        fecha_carga=_ahora(),
                    ))
            except Exception:
                db.session.rollback()
                for nombre in guardados:
                    try:
                        os.remove(os.path.join(upload_folder, nombre))
                    except OSError:
                        pass
                raise ValueError("No se pudieron guardar las evidencias. Intenta de nuevo")

        db.session.commit()
        return ReporteService._to_dto(reporte).to_dict()

    # ------------------------------------------------------------------ consultas

    @staticmethod
    def _puede_ver(reporte, usuario):
        """Dueno del reporte, administrador, o gestor/organismo del mismo municipio."""
        rol = usuario.rol.nombre
        if reporte.ciudadano_id == usuario.id or rol == ADMINISTRADOR:
            return True
        if tiene_alcance_municipal(rol):
            return usuario.municipio_id is not None and reporte.municipio_id == usuario.municipio_id
        return False

    @staticmethod
    def get_reporte(reporte_id, usuario):
        r = Reporte.query.get(reporte_id)
        if not r:
            raise ValueError("Reporte no encontrado")
        if not ReporteService._puede_ver(r, usuario):
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
    def list_reportes_gestion(busqueda=None, tipo=None, estado=None, prioridad=None, municipio_id=None, usuario=None):
        """
        Listado para gestion, con filtros opcionales.
        Gestores y organismos quedan limitados a SU municipio, sin importar
        el municipio_id que envien en la peticion.
        """
        query = Reporte.query

        if usuario is not None and tiene_alcance_municipal(usuario.rol.nombre):
            if not usuario.municipio_id:
                raise ValueError("Tu usuario no tiene un municipio asignado. Contacta al administrador")
            municipio_id = usuario.municipio_id

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
    def get_evidencia_autorizada(evidencia_id, usuario):
        """Devuelve la evidencia solo si el usuario puede ver su reporte."""
        evidencia = Evidencia.query.get(evidencia_id)
        if not evidencia:
            raise ValueError("Evidencia no encontrada")

        if not ReporteService._puede_ver(evidencia.reporte, usuario):
            raise ValueError("No tienes permiso para acceder a esta evidencia")

        return evidencia
