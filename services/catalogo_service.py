from extensions import db
from models.catalogos import Municipio, Organismo
from dtos.catalogo_dto import MunicipioDTO, OrganismoDTO


class MunicipioService:
    @staticmethod
    def _to_dto(m):
        return MunicipioDTO(m.id, m.codigo, m.nombre, m.activo, m.fecha_creacion)

    @staticmethod
    def list_municipios(busqueda=None, estado=None):
        query = Municipio.query

        if busqueda:
            like = f"%{busqueda.strip()}%"
            query = query.filter(db.or_(Municipio.nombre.ilike(like), Municipio.codigo.ilike(like)))

        if estado == "activo":
            query = query.filter(Municipio.activo.is_(True))
        elif estado == "inactivo":
            query = query.filter(Municipio.activo.is_(False))

        municipios = query.order_by(Municipio.nombre.asc()).all()
        return [MunicipioService._to_dto(m).to_dict() for m in municipios]

    @staticmethod
    def get_municipio(municipio_id):
        m = Municipio.query.get(municipio_id)
        if not m:
            raise ValueError("Municipio no encontrado")
        return MunicipioService._to_dto(m).to_dict()

    @staticmethod
    def create_municipio(dto):
        codigo = (dto.codigo or "").strip()
        nombre = (dto.nombre or "").strip()
        if not codigo or not nombre:
            raise ValueError("Codigo y nombre son obligatorios")
        if Municipio.query.filter_by(codigo=codigo).first():
            raise ValueError("Ya existe un municipio con ese codigo")
        if Municipio.query.filter_by(nombre=nombre).first():
            raise ValueError("Ya existe un municipio con ese nombre")

        m = Municipio(codigo=codigo, nombre=nombre, activo=True)
        db.session.add(m)
        db.session.commit()
        return MunicipioService._to_dto(m).to_dict()

    @staticmethod
    def update_municipio(municipio_id, dto):
        m = Municipio.query.get(municipio_id)
        if not m:
            raise ValueError("Municipio no encontrado")

        if dto.codigo:
            codigo = dto.codigo.strip()
            if codigo != m.codigo and Municipio.query.filter(
                Municipio.codigo == codigo, Municipio.id != municipio_id
            ).first():
                raise ValueError("Ya existe un municipio con ese codigo")
            m.codigo = codigo

        if dto.nombre:
            nombre = dto.nombre.strip()
            if nombre != m.nombre and Municipio.query.filter(
                Municipio.nombre == nombre, Municipio.id != municipio_id
            ).first():
                raise ValueError("Ya existe un municipio con ese nombre")
            m.nombre = nombre

        db.session.commit()
        return MunicipioService._to_dto(m).to_dict()

    @staticmethod
    def set_active(municipio_id, activo):
        m = Municipio.query.get(municipio_id)
        if not m:
            raise ValueError("Municipio no encontrado")
        m.activo = activo
        db.session.commit()
        return MunicipioService._to_dto(m).to_dict()


class OrganismoService:
    @staticmethod
    def _to_dto(o):
        return OrganismoDTO(
            o.id, o.codigo, o.nombre, o.tipo, o.activo,
            municipios=[{"id": m.id, "nombre": m.nombre} for m in o.municipios],
            fecha_creacion=o.fecha_creacion,
        )

    @staticmethod
    def _resolver_municipios(ids_municipios):
        if not ids_municipios:
            return []
        ids_unicos = {int(i) for i in ids_municipios}
        municipios = Municipio.query.filter(Municipio.id.in_(ids_unicos)).all()
        if len(municipios) != len(ids_unicos):
            raise ValueError("Uno o mas municipios seleccionados no existen")
        return municipios

    @staticmethod
    def list_organismos(busqueda=None, estado=None):
        query = Organismo.query

        if busqueda:
            like = f"%{busqueda.strip()}%"
            query = query.filter(db.or_(Organismo.nombre.ilike(like), Organismo.codigo.ilike(like)))

        if estado == "activo":
            query = query.filter(Organismo.activo.is_(True))
        elif estado == "inactivo":
            query = query.filter(Organismo.activo.is_(False))

        organismos = query.order_by(Organismo.nombre.asc()).all()
        return [OrganismoService._to_dto(o).to_dict() for o in organismos]

    @staticmethod
    def get_organismo(organismo_id):
        o = Organismo.query.get(organismo_id)
        if not o:
            raise ValueError("Organismo no encontrado")
        return OrganismoService._to_dto(o).to_dict()

    @staticmethod
    def create_organismo(dto):
        codigo = (dto.codigo or "").strip()
        nombre = (dto.nombre or "").strip()
        if not codigo or not nombre:
            raise ValueError("Codigo y nombre son obligatorios")
        if Organismo.query.filter_by(codigo=codigo).first():
            raise ValueError("Ya existe un organismo con ese codigo")
        if Organismo.query.filter_by(nombre=nombre).first():
            raise ValueError("Ya existe un organismo con ese nombre")

        o = Organismo(codigo=codigo, nombre=nombre, tipo=(dto.tipo or "").strip() or None, activo=True)
        o.municipios = OrganismoService._resolver_municipios(dto.municipios)
        db.session.add(o)
        db.session.commit()
        return OrganismoService._to_dto(o).to_dict()

    @staticmethod
    def update_organismo(organismo_id, dto):
        o = Organismo.query.get(organismo_id)
        if not o:
            raise ValueError("Organismo no encontrado")

        if dto.codigo:
            codigo = dto.codigo.strip()
            if codigo != o.codigo and Organismo.query.filter(
                Organismo.codigo == codigo, Organismo.id != organismo_id
            ).first():
                raise ValueError("Ya existe un organismo con ese codigo")
            o.codigo = codigo

        if dto.nombre:
            nombre = dto.nombre.strip()
            if nombre != o.nombre and Organismo.query.filter(
                Organismo.nombre == nombre, Organismo.id != organismo_id
            ).first():
                raise ValueError("Ya existe un organismo con ese nombre")
            o.nombre = nombre

        if dto.tipo is not None:
            o.tipo = dto.tipo.strip() or None

        db.session.commit()
        return OrganismoService._to_dto(o).to_dict()

    @staticmethod
    def set_active(organismo_id, activo):
        o = Organismo.query.get(organismo_id)
        if not o:
            raise ValueError("Organismo no encontrado")
        o.activo = activo
        db.session.commit()
        return OrganismoService._to_dto(o).to_dict()

    @staticmethod
    def set_municipios(organismo_id, ids_municipios):
        o = Organismo.query.get(organismo_id)
        if not o:
            raise ValueError("Organismo no encontrado")
        o.municipios = OrganismoService._resolver_municipios(ids_municipios)
        db.session.commit()
        return OrganismoService._to_dto(o).to_dict()