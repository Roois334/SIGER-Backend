from extensions import db
from models.user import User
from models.catalogos import Rol, Municipio, Organismo
from dtos.user_dto import UserAdminDTO
import os
import uuid
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
import re

from utilities.permisos import ROLES_VALIDOS, ORGANISMO_ATENCION, tiene_alcance_municipal
EXTENSIONES_FOTO_VALIDAS = {"jpg", "jpeg", "png", "webp"}
MAX_FOTO_BYTES = 5 * 1024 * 1024  # 5 MB


class UserService:
    @staticmethod
    def _to_admin_dto(user):
        return UserAdminDTO(
            user.id, user.nombre, user.apellido, user.email,
            user.rol.nombre, user.municipio.nombre if user.municipio else None,
            user.activo, user.fecha_creacion, user.foto_url,
            organismo=user.organismo.nombre if user.organismo else None,
            organismo_id=user.organismo_id,
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
    def update_user(user_id, dto, admin_id=None):
        user = User.query.get(user_id)
        if not user:
            raise ValueError("Usuario no encontrado")

        # El administrador no puede cambiarse su propio rol (evita quedar sin admins)
        if dto.rol and str(user_id) == str(admin_id) and dto.rol != user.rol.nombre:
            raise ValueError("No puedes cambiar tu propio rol")

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

        if dto.organismo_id is not None:
            if str(dto.organismo_id).strip() in ("", "0"):
                user.organismo_id = None
            else:
                try:
                    organismo = Organismo.query.get(int(dto.organismo_id))
                except (TypeError, ValueError):
                    organismo = None
                if not organismo:
                    db.session.rollback()
                    raise ValueError("Organismo invalido")
                user.organismo_id = organismo.id

        if dto.rol:
            if dto.rol not in ROLES_VALIDOS:
                raise ValueError("Rol invalido")
            rol = Rol.query.filter_by(nombre=dto.rol).first()
            if not rol:
                raise ValueError("Rol invalido")
            user.rol_id = rol.id
            user.rol = rol

        # Gestores y organismos trabajan sobre un municipio: es obligatorio
        if tiene_alcance_municipal(user.rol.nombre) and not user.municipio_id:
            db.session.rollback()
            raise ValueError("Los gestores municipales y organismos de atencion deben tener un municipio asignado")

        # Solo los usuarios de organismo pertenecen a un organismo (y debe operar en su municipio)
        if user.rol.nombre != ORGANISMO_ATENCION:
            user.organismo_id = None
        else:
            if not user.organismo_id:
                db.session.rollback()
                raise ValueError("Los usuarios de organismo de atencion deben tener un organismo asignado")
            organismo = Organismo.query.get(user.organismo_id)
            if organismo and user.municipio_id not in [m.id for m in organismo.municipios]:
                db.session.rollback()
                raise ValueError("Ese organismo no opera en el municipio asignado al usuario")

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

    # ------------------------------------------------------------ perfil propio

    @staticmethod
    def update_me(user_id, nombre, apellido, municipio=None):
        """El usuario edita sus datos personales. Solo el ciudadano puede cambiar su municipio."""
        user = User.query.get(user_id)
        if not user:
            raise ValueError("Usuario no encontrado")

        nombre = (nombre or "").strip()
        apellido = (apellido or "").strip()
        if not nombre or not apellido:
            raise ValueError("El nombre y el apellido son obligatorios")
        if len(nombre) > 80 or len(apellido) > 80:
            raise ValueError("El nombre y el apellido no pueden superar 80 caracteres")
        user.nombre = nombre
        user.apellido = apellido

        if municipio is not None and user.rol.nombre == "ciudadano":
            municipio = municipio.strip()
            if municipio:
                m = Municipio.query.filter_by(nombre=municipio, activo=True).first()
                if not m:
                    db.session.rollback()
                    raise ValueError("Municipio invalido")
                user.municipio_id = m.id

        db.session.commit()
        return UserService._to_admin_dto(user).to_dict()

    @staticmethod
    def change_email(user_id, nuevo_email, password):
        """Cambia el correo del propio usuario; exige la contrasena actual."""
        user = User.query.get(user_id)
        if not user:
            raise ValueError("Usuario no encontrado")
        if not password or not check_password_hash(user.password_hash, password):
            raise ValueError("La contrasena actual no es correcta")

        email = (nuevo_email or "").strip().lower()
        if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email) or len(email) > 120:
            raise ValueError("Escribe un correo valido")
        if email == user.email:
            raise ValueError("Ese ya es tu correo actual")
        if User.query.filter(User.email == email, User.id != user_id).first():
            raise ValueError("Ya existe una cuenta con ese correo")

        user.email = email
        db.session.commit()
        return UserService._to_admin_dto(user).to_dict()

    @staticmethod
    def change_password(user_id, actual, nueva):
        user = User.query.get(user_id)
        if not user:
            raise ValueError("Usuario no encontrado")
        if not actual or not check_password_hash(user.password_hash, actual):
            raise ValueError("La contrasena actual no es correcta")
        if not nueva or len(nueva) < 6:
            raise ValueError("La contrasena nueva debe tener minimo 6 caracteres")
        if len(nueva) > 128:
            raise ValueError("La contrasena nueva es demasiado larga")
        if nueva == actual:
            raise ValueError("La contrasena nueva debe ser distinta a la actual")

        user.password_hash = generate_password_hash(nueva)
        db.session.commit()
        return UserService._to_admin_dto(user).to_dict()

    @staticmethod
    def remove_foto(user_id, upload_folder):
        user = User.query.get(user_id)
        if not user:
            raise ValueError("Usuario no encontrado")
        if user.foto_url:
            ruta = os.path.join(upload_folder, os.path.basename(user.foto_url))
            if os.path.exists(ruta):
                os.remove(ruta)
            user.foto_url = None
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