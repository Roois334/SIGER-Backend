import os
import uuid
from datetime import datetime, timedelta, timezone
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload, selectinload
from werkzeug.utils import secure_filename

from extensions import db
from models.reporte import Reporte, Evidencia, ReporteHistorial
from models.catalogos import Municipio, Organismo, organismo_municipio
from dtos.reporte_dto import ReporteDTO, EvidenciaDTO
from utilities.permisos import (
    ADMINISTRADOR, GESTOR_MUNICIPAL, ORGANISMO_ATENCION,
    tiene_alcance_municipal, tiene_permiso,
)

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

# Flujo: pendiente -> asignado -> en_atencion -> resuelto -> cerrado   (o descartado)
PRIORIDADES = ["baja", "media", "alta", "critica"]
MIN_COMENTARIO_OBLIGATORIO = 5
# Mientras la emergencia siga abierta el gestor puede corregir su tipo
ESTADOS_RECLASIFICABLES = ("pendiente", "asignado", "en_atencion")
MAX_COMENTARIO = 300

# Organismos que normalmente atienden cada tipo (solo para SUGERIR al gestor;
# el gestor puede elegir cualquier organismo activo del municipio).
CODIGOS_SUGERIDOS = {
    "Incendio": ["BOM", "CAR"],
    "Inundacion": ["DEF", "GRD", "CRC"],
    "Accidente de transito": ["TRA", "BOM", "SAL", "CRC", "POL"],
    "Deslizamiento": ["DEF", "GRD"],
    "Fuga o derrame de sustancias": ["BOM", "SSP", "CAR"],
    "Emergencia medica": ["SAL", "CRC"],
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

# Datos relacionados que usan los listados: se piden de una vez (la base es remota y cada consulta tarda)
_CARGA_REPORTE = (
    joinedload(Reporte.municipio), joinedload(Reporte.ciudadano),
    joinedload(Reporte.organismo), joinedload(Reporte.asignado_por),
    selectinload(Reporte.evidencias),
)


def _ahora():
    """Fecha y hora actual de Colombia, sin zona (como se guarda en la BD)."""
    return datetime.now(ZONA_COLOMBIA).replace(tzinfo=None)


class PermisoError(ValueError):
    """El usuario no tiene acceso a ese reporte (se responde 403)."""


class NoEncontradoError(ValueError):
    """El reporte no existe (se responde 404)."""


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
            organismo_id=r.organismo_id,
            organismo_nombre=r.organismo.nombre if r.organismo else None,
            fecha_asignacion=r.fecha_asignacion,
            heridos=r.heridos or 0,
            asignado_por=f"{r.asignado_por.nombre} {r.asignado_por.apellido}".strip() if r.asignado_por else None,
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
    def _validar_heridos(dto, afectados):
        """Heridos: entero >= 0 y nunca mayor que las personas afectadas."""
        try:
            heridos = int(str(getattr(dto, "heridos", 0) or 0).strip() or 0)
        except (ValueError, TypeError):
            raise ValueError("El numero de heridos debe ser un entero valido")
        if heridos < 0:
            raise ValueError("El numero de heridos no puede ser negativo")
        if heridos > afectados:
            raise ValueError("El numero de heridos no puede ser mayor que el de personas afectadas")
        return heridos

    @staticmethod
    def create_reporte(dto, ciudadano_id, archivos=None, upload_folder=None):
        afectados = ReporteService._validar_campos(dto)
        heridos = ReporteService._validar_heridos(dto, afectados)
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
                heridos=heridos,
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
        if rol == ORGANISMO_ATENCION:
            # Solo ve lo que el gestor le ASIGNO a su organismo en su municipio
            return ReporteService._es_organismo_del_reporte(reporte, usuario)
        if tiene_alcance_municipal(rol):
            return usuario.municipio_id is not None and reporte.municipio_id == usuario.municipio_id
        return False

    @staticmethod
    def _es_organismo_del_reporte(reporte, usuario):
        return (
            usuario.organismo_id is not None
            and reporte.organismo_id == usuario.organismo_id
            and usuario.municipio_id is not None
            and reporte.municipio_id == usuario.municipio_id
        )

    @staticmethod
    def _puede_gestionar(reporte, usuario):
        """Administrador, o gestor del municipio del reporte."""
        rol = usuario.rol.nombre
        if not tiene_permiso(rol, "reportes.asignar"):
            return False
        return rol == ADMINISTRADOR or (
            usuario.municipio_id is not None and reporte.municipio_id == usuario.municipio_id
        )

    @staticmethod
    def _acciones(reporte, usuario):
        """Que botones puede usar ESTE usuario sobre ESTE reporte, segun su estado."""
        gestiona = ReporteService._puede_gestionar(reporte, usuario)
        atiende = (
            tiene_permiso(usuario.rol.nombre, "reportes.atender")
            and ReporteService._es_organismo_del_reporte(reporte, usuario)
        )
        e = reporte.estado
        return {
            "asignar": gestiona and e in ("pendiente", "asignado"),
            "descartar": gestiona and e == "pendiente",
            "iniciar": atiende and e == "asignado",
            "devolver": atiende and e == "asignado",
            "resolver": atiende and e == "en_atencion",
            "cerrar": gestiona and e == "resuelto",
            "reclasificar": gestiona and e in ESTADOS_RECLASIFICABLES,
        }

    @staticmethod
    def _organismos_para(reporte):
        """Organismos activos que operan en el municipio del reporte (los afines al tipo, primero)."""
        organismos = (
            Organismo.query.join(organismo_municipio, organismo_municipio.c.organismo_id == Organismo.id)
            .filter(Organismo.activo.is_(True), organismo_municipio.c.municipio_id == reporte.municipio_id)
            .order_by(Organismo.nombre.asc())
            .all()
        )
        sugeridos = CODIGOS_SUGERIDOS.get(reporte.tipo, [])
        lista = [
            {"id": o.id, "nombre": o.nombre, "tipo": o.tipo, "sugerido": o.codigo in sugeridos}
            for o in organismos
        ]
        lista.sort(key=lambda o: (not o["sugerido"], o["nombre"]))
        return lista

    @staticmethod
    def _historial(reporte, usuario):
        es_ciudadano = usuario.id == reporte.ciudadano_id and usuario.rol.nombre != ADMINISTRADOR
        items = []
        for h in reporte.historial:
            if es_ciudadano and h.accion == "devolver":
                continue  # movimiento interno entre gestor y organismo
            items.append({
                "accion": h.accion,
                "estado_anterior": h.estado_anterior,
                "estado_nuevo": h.estado_nuevo,
                "comentario": h.comentario,
                "fecha": h.fecha.isoformat() if h.fecha else None,
                "autor": f"{h.usuario.nombre} {h.usuario.apellido}".strip() if h.usuario else None,
            })
        return items

    @staticmethod
    def _detalle(reporte, usuario):
        d = ReporteService._to_dto(reporte).to_dict()
        acciones = ReporteService._acciones(reporte, usuario)
        d["acciones"] = acciones
        d["historial"] = ReporteService._historial(reporte, usuario)
        if acciones["asignar"]:
            d["organismos_disponibles"] = ReporteService._organismos_para(reporte)
        return d

    @staticmethod
    def get_reporte(reporte_id, usuario):
        r = Reporte.query.get(reporte_id)
        if not r:
            raise ValueError("Reporte no encontrado")
        if not ReporteService._puede_ver(r, usuario):
            raise ValueError("No tienes acceso a este reporte")
        return ReporteService._detalle(r, usuario)

    # ------------------------------------------------------------------ asignacion y atencion

    @staticmethod
    def _comentario(texto, obligatorio=False):
        texto = (texto or "").strip()
        if obligatorio and len(texto) < MIN_COMENTARIO_OBLIGATORIO:
            raise ValueError(f"Escribe un motivo (minimo {MIN_COMENTARIO_OBLIGATORIO} caracteres)")
        if len(texto) > MAX_COMENTARIO:
            raise ValueError(f"El comentario no puede superar {MAX_COMENTARIO} caracteres")
        return texto or None

    @staticmethod
    def _registrar(reporte, usuario, accion, anterior, nuevo, comentario):
        db.session.add(ReporteHistorial(
            reporte_id=reporte.id, usuario_id=usuario.id, accion=accion,
            estado_anterior=anterior, estado_nuevo=nuevo,
            comentario=comentario, fecha=_ahora(),
        ))

    @staticmethod
    def _reporte_accesible(reporte_id, usuario):
        r = Reporte.query.get(reporte_id)
        if not r:
            raise NoEncontradoError("Reporte no encontrado")
        if not ReporteService._puede_ver(r, usuario):
            raise PermisoError("No tienes acceso a este reporte")
        return r

    @staticmethod
    def asignar_reporte(reporte_id, organismo_id, usuario, prioridad=None, comentario=None):
        """
        El gestor ACEPTA el reporte y lo asigna a un organismo. Solo desde ese
        momento el organismo (de ese municipio) puede verlo.
        """
        r = ReporteService._reporte_accesible(reporte_id, usuario)
        if not ReporteService._puede_gestionar(r, usuario):
            raise PermisoError("No tienes permiso para asignar este reporte")
        if r.estado not in ("pendiente", "asignado"):
            raise ValueError("Este reporte ya esta en atencion o fue cerrado; ya no se puede asignar")

        try:
            organismo = Organismo.query.get(int(organismo_id))
        except (TypeError, ValueError):
            organismo = None
        if not organismo or not organismo.activo:
            raise ValueError("Selecciona un organismo valido")
        if r.municipio_id not in [m.id for m in organismo.municipios]:
            raise ValueError("Ese organismo no opera en el municipio del reporte")

        notas = []
        if prioridad:
            if prioridad not in PRIORIDADES:
                raise ValueError("Prioridad invalida")
            if prioridad != r.prioridad:
                notas.append(f"Prioridad: {r.prioridad} -> {prioridad}")
                r.prioridad = prioridad
        comentario = ReporteService._comentario(comentario)

        anterior = r.estado
        previo = r.organismo.nombre if r.organismo else None
        if anterior == "asignado" and r.organismo_id == organismo.id and not notas and not comentario:
            raise ValueError("El reporte ya esta asignado a ese organismo")
        reasigna = anterior == "asignado"

        r.organismo_id = organismo.id
        r.estado = "asignado"
        r.asignado_por_id = usuario.id
        r.fecha_asignacion = _ahora()

        texto = (f"Reasignado de {previo} a {organismo.nombre}" if reasigna and previo
                 else f"Asignado a {organismo.nombre}")
        partes = [texto] + notas + ([comentario] if comentario else [])
        ReporteService._registrar(r, usuario, "reasignar" if reasigna else "asignar",
                                  anterior, "asignado", ". ".join(partes)[:MAX_COMENTARIO])
        db.session.commit()
        return ReporteService._detalle(r, usuario)

    @staticmethod
    def cambiar_estado(reporte_id, accion, usuario, comentario=None):
        """
        Acciones: descartar (gestor), iniciar / resolver / devolver (organismo asignado).
        Cada una solo funciona si el reporte esta en el estado correcto.
        """
        if accion not in ("descartar", "iniciar", "resolver", "devolver", "cerrar"):
            raise ValueError("Accion no valida")
        r = ReporteService._reporte_accesible(reporte_id, usuario)
        if not ReporteService._acciones(r, usuario).get(accion):
            raise ValueError("Esa accion ya no esta disponible (el estado del reporte cambio). Recarga la pagina")

        anterior = r.estado
        if accion == "descartar":
            comentario = ReporteService._comentario(comentario, obligatorio=True)
            r.estado = "descartado"
        elif accion == "iniciar":
            comentario = ReporteService._comentario(comentario)
            r.estado = "en_atencion"
        elif accion == "resolver":
            comentario = ReporteService._comentario(comentario)
            r.estado = "resuelto"
        elif accion == "cerrar":  # el gestor confirma el cierre; queda en el historial con su nombre y fecha
            comentario = ReporteService._comentario(comentario)
            r.estado = "cerrado"
        else:  # devolver: el organismo no puede atenderlo, vuelve al gestor
            comentario = ReporteService._comentario(comentario, obligatorio=True)
            r.estado = "pendiente"
            r.organismo_id = None
            r.asignado_por_id = None
            r.fecha_asignacion = None

        ReporteService._registrar(r, usuario, accion, anterior, r.estado, comentario)
        db.session.commit()
        return ReporteService._detalle(r, usuario)

    @staticmethod
    def cambiar_tipo(reporte_id, nuevo_tipo, usuario, comentario=None):
        """
        El gestor del municipio (o el administrador) corrige el tipo de una emergencia abierta.
        El motivo es obligatorio y queda en el historial con el tipo anterior y el nuevo.
        La prioridad NO cambia sola: se ajusta al asignar.
        """
        r = ReporteService._reporte_accesible(reporte_id, usuario)
        if not ReporteService._puede_gestionar(r, usuario):
            raise PermisoError("Solo el gestor del municipio puede cambiar el tipo de la emergencia")
        if r.estado not in ESTADOS_RECLASIFICABLES:
            raise ValueError("Esta emergencia ya no se puede reclasificar (esta " + r.estado + "). Recarga la pagina")
        if not nuevo_tipo or nuevo_tipo not in TIPOS_EMERGENCIA:
            raise ValueError("Debes seleccionar un tipo de emergencia valido")
        if nuevo_tipo == r.tipo:
            raise ValueError("La emergencia ya tiene ese tipo")
        motivo = ReporteService._comentario(comentario, obligatorio=True)

        anterior_tipo = r.tipo
        r.tipo = nuevo_tipo
        texto = f"Tipo: {anterior_tipo} → {nuevo_tipo}. {motivo}"[:300]
        ReporteService._registrar(r, usuario, "reclasificar", r.estado, r.estado, texto)
        db.session.commit()
        return ReporteService._detalle(r, usuario)

    @staticmethod
    def list_reportes_ciudadano(ciudadano_id):
        reportes = (
            Reporte.query.filter_by(ciudadano_id=ciudadano_id)
            .options(*_CARGA_REPORTE)
            .order_by(Reporte.fecha_hora.desc())
            .all()
        )
        return [ReporteService._to_dto(r).to_dict() for r in reportes]

    @staticmethod
    def _parsear_fecha(texto, nombre):
        """Acepta AAAA-MM-DD (lo que envia el campo de fecha). Vacio = sin filtro."""
        texto = (texto or "").strip()
        if not texto:
            return None
        try:
            return datetime.strptime(texto, "%Y-%m-%d")
        except ValueError:
            raise ValueError(f"La fecha '{nombre}' no es valida")

    @staticmethod
    def list_reportes_gestion(busqueda=None, tipo=None, estado=None, prioridad=None, municipio_id=None, usuario=None,
                              desde=None, hasta=None):
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
            if usuario.rol.nombre == ORGANISMO_ATENCION:
                # El organismo solo ve lo que el gestor le asigno
                if not usuario.organismo_id:
                    raise ValueError("Tu usuario no tiene un organismo asignado. Contacta al administrador")
                query = query.filter(Reporte.organismo_id == usuario.organismo_id)

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

        f_desde = ReporteService._parsear_fecha(desde, "desde")
        f_hasta = ReporteService._parsear_fecha(hasta, "hasta")
        if f_desde and f_hasta and f_desde > f_hasta:
            raise ValueError("La fecha 'desde' no puede ser posterior a la fecha 'hasta'")
        if f_desde:
            query = query.filter(Reporte.fecha_hora >= f_desde)
        if f_hasta:  # incluye todo el dia final
            query = query.filter(Reporte.fecha_hora < f_hasta + timedelta(days=1))

        reportes = query.options(*_CARGA_REPORTE).order_by(Reporte.fecha_hora.desc()).all()
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
