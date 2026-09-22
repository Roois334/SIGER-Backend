from extensions import db
from models.user import User
from models.catalogos import Rol, Municipio
from dtos.user_dto import UserAdminDTO
import os
import uuid
from werkzeug.utils import secure_filename

ROLES_VALIDOS = ["ciudadano", "gestor_municipal", "organismo_atencion", "administrador"]
EXTENSIONES_FOTO_VALIDAS = {"jpg", "jpeg", "png", "webp"}
MAX_FOTO_BYTES = 5 * 1024 * 1024  # 5 MB


class UserService:
    @staticmethod
    def _to_admin_dto(user):
        return UserAdminDTO(
            user.id, user.nombre, user.apellido, user.email,
            user.rol.nombre, user.municipio.nombre if user.municipio else None,
            user.activo, user.fecha_creacion, user.foto_url,
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

    @staticmethod
    def _extension_valida(nombre_archivo):
        return "." in nombre_archivo and \
            nombre_archivo.rsplit(".", 1)[1].lower() in EXTENSIONES_FOTO_VALIDAS

    @staticmethod
    def update_foto(user_id, archivo, upload_folder):
        """Guarda la foto de perfil del propio usuario y devuelve su nueva URL."""
        user = User.query.get(user_id)
        if not user:
            raise ValueError("Usuario no encontrado")

        if not archivo or not archivo.filename:
            raise ValueError("No se recibio ningun archivo")

        if not UserService._extension_valida(archivo.filename):
            raise ValueError("Formato de imagen no permitido (usa jpg, png o webp)")

        os.makedirs(upload_folder, exist_ok=True)

        # Borra la foto anterior si existia, para no acumular archivos huerfanos
        if user.foto_url:
            ruta_anterior = os.path.join(upload_folder, os.path.basename(user.foto_url))
            if os.path.exists(ruta_anterior):
                os.remove(ruta_anterior)

        extension = archivo.filename.rsplit(".", 1)[1].lower()
        nombre_unico = f"usuario_{user.id}_{uuid.uuid4().hex[:8]}.{extension}"
        ruta_absoluta = os.path.join(upload_folder, nombre_unico)
        archivo.save(ruta_absoluta)

        user.foto_url = f"/static/uploads/perfiles/{nombre_unico}"
        db.session.commit()
        return UserService._to_admin_dto(user).to_dict()