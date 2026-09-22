from extensions import db
from models.user import User
from models.catalogos import Rol, Municipio
from dtos.user_dto import UserAdminDTO

ROLES_VALIDOS = ["ciudadano", "gestor_municipal", "organismo_atencion", "administrador"]


class UserService:
    @staticmethod
    def _to_admin_dto(user):
        return UserAdminDTO(
            user.id, user.nombre, user.apellido, user.email,
            user.rol.nombre, user.municipio.nombre if user.municipio else None,
            user.activo, user.fecha_creacion,
        )

    @staticmethod
    def list_users(busqueda=None, rol=None, activo=None):
        query = User.query.join(Rol)

        if busqueda:
            like = f"%{busqueda.strip()}%"
            query = query.filter(
                db.or_(
                    User.nombre.ilike(like),
                    User.apellido.ilike(like),
                    User.email.ilike(like),
                )
            )

        if rol:
            if rol not in ROLES_VALIDOS:
                raise ValueError("Rol invalido")
            query = query.filter(Rol.nombre == rol)

        if activo is not None:
            query = query.filter(User.activo == activo)

        usuarios = query.order_by(User.id.asc()).all()
        return [UserService._to_admin_dto(u).to_dict() for u in usuarios]

    @staticmethod
    def get_user(user_id):
        user = User.query.get(user_id)
        if not user:
            raise ValueError("Usuario no encontrado")
        return UserService._to_admin_dto(user).to_dict()

    @staticmethod
    def update_user(user_id, dto):
        user = User.query.get(user_id)
        if not user:
            raise ValueError("Usuario no encontrado")

        if dto.email:
            email = dto.email.strip().lower()
            if email != user.email and User.query.filter(User.email == email, User.id != user_id).first():
                raise ValueError("Ya existe una cuenta con ese correo")
            user.email = email

        if dto.nombre:
            user.nombre = dto.nombre.strip()

        if dto.apellido:
            user.apellido = dto.apellido.strip()

        if dto.municipio is not None:
            if dto.municipio == "":
                user.municipio_id = None
            else:
                municipio = Municipio.query.filter_by(nombre=dto.municipio).first()
                if not municipio:
                    raise ValueError("Municipio invalido")
                user.municipio_id = municipio.id

        if dto.rol:
            if dto.rol not in ROLES_VALIDOS:
                raise ValueError("Rol invalido")
            rol = Rol.query.filter_by(nombre=dto.rol).first()
            if not rol:
                raise ValueError("Rol invalido")
            user.rol_id = rol.id

        db.session.commit()
        return UserService._to_admin_dto(user).to_dict()

    @staticmethod
    def set_active(user_id, activo, admin_id):
        if str(user_id) == str(admin_id) and not activo:
            raise ValueError("No puedes desactivar tu propia cuenta")

        user = User.query.get(user_id)
        if not user:
            raise ValueError("Usuario no encontrado")

        user.activo = activo
        db.session.commit()
        return UserService._to_admin_dto(user).to_dict()