import os
import uuid

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload
from werkzeug.security import generate_password_hash, check_password_hash

from extensions import db
from models.user import User
from models.catalogos import Rol, Municipio, Organismo
from dtos.user_dto import UserAdminDTO
from utilities.validaciones import validar_email, validar_password
from utilities.validaciones_persona import validar_documento, validar_telefono, validar_nombre
from utilities.permisos import ROLES_VALIDOS, CIUDADANO, ORGANISMO_ATENCION, tiene_alcance_municipal

MAX_FOTO_BYTES = 5 * 1024 * 1024  # 5 MB
# Extension permitida -> como empiezan los bytes de ese formato
FIRMAS_FOTO = {
    "jpg": lambda c: c.startswith(b"\xff\xd8\xff"),
    "jpeg": lambda c: c.startswith(b"\xff\xd8\xff"),
    "png": lambda c: c.startswith(b"\x89PNG\r\n\x1a\n"),
    "webp": lambda c: c[:4] == b"RIFF" and c[8:12] == b"WEBP",
}


class UserService:
    @staticmethod
    def _to_admin_dto(user):
        return UserAdminDTO(
            user.id, user.nombre, user.apellido, user.email,
            user.rol.nombre, user.municipio.nombre if user.municipio else None,
            user.activo, user.fecha_creacion, user.foto_url,
            organismo=user.organismo.nombre if user.organismo else None,
            organismo_id=user.organismo_id,
            tipo_documento=user.tipo_documento, documento=user.documento, telefono=user.telefono,
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

        usuarios = (
            query.options(joinedload(User.rol), joinedload(User.municipio), joinedload(User.organismo))
            .order_by(User.id.asc()).all()
        )
        return [UserService._to_admin_dto(u).to_dict() for u in usuarios]

    @staticmethod
    def get_user(user_id):
        user = db.session.get(User, user_id)
        if not user:
            raise ValueError("Usuario no encontrado")
        return UserService._to_admin_dto(user).to_dict()

    @staticmethod
    def update_user(user_id, dto, admin_id=None):
        user = db.session.get(User, user_id)
        if not user:
            raise ValueError("Usuario no encontrado")

        # El administrador no puede cambiarse su propio rol (evita quedar sin admins)
        if dto.rol and str(user_id) == str(admin_id) and dto.rol != user.rol.nombre:
            raise ValueError("No puedes cambiar tu propio rol")

        if dto.email:
            email = validar_email(dto.email)
            if email != user.email and User.query.filter(User.email == email, User.id != user_id).first():
                raise ValueError("Ya existe una cuenta con ese correo")
            user.email = email

        # Solo se valida si el nombre cambio (cuentas antiguas con otro formato siguen editables)
        if dto.nombre and dto.nombre.strip() != user.nombre:
            user.nombre = validar_nombre(dto.nombre, "El nombre")

        if dto.apellido and dto.apellido.strip() != user.apellido:
            user.apellido = validar_nombre(dto.apellido, "El apellido")

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
                    organismo = db.session.get(Organismo, int(dto.organismo_id))
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
            organismo = db.session.get(Organismo, user.organismo_id)
            if organismo and user.municipio_id not in [m.id for m in organismo.municipios]:
                db.session.rollback()
                raise ValueError("Ese organismo no opera en el municipio asignado al usuario")

        db.session.commit()
        return UserService._to_admin_dto(user).to_dict()

    @staticmethod
    def set_active(user_id, activo, admin_id):
        if str(user_id) == str(admin_id) and not activo:
            raise ValueError("No puedes desactivar tu propia cuenta")

        user = db.session.get(User, user_id)
        if not user:
            raise ValueError("Usuario no encontrado")

        user.activo = activo
        db.session.commit()
        return UserService._to_admin_dto(user).to_dict()

    # ------------------------------------------------------------ perfil propio

    @staticmethod
    def update_me(user_id, nombre, apellido, municipio=None,
                  tipo_documento=None, documento=None, telefono=None):
        """El usuario edita sus datos personales. Solo el ciudadano puede cambiar su municipio."""
        user = db.session.get(User, user_id)
        if not user:
            raise ValueError("Usuario no encontrado")

        nombre = (nombre or "").strip()
        apellido = (apellido or "").strip()
        if not nombre or not apellido:
            raise ValueError("El nombre y el apellido son obligatorios")
        if nombre != user.nombre:
            nombre = validar_nombre(nombre, "El nombre")
        if apellido != user.apellido:
            apellido = validar_nombre(apellido, "El apellido")
        user.nombre = nombre
        user.apellido = apellido

        if municipio is not None and user.rol.nombre == CIUDADANO:
            municipio = municipio.strip()
            if municipio:
                m = Municipio.query.filter_by(nombre=municipio, activo=True).first()
                if not m:
                    db.session.rollback()
                    raise ValueError("Municipio invalido")
                user.municipio_id = m.id

        # Documento y telefono: si vienen vacios no se tocan (no se pueden borrar desde aqui)
        try:
            tipo = (tipo_documento or "").strip()
            numero = (documento or "").strip()
            if tipo or numero:
                tipo, numero = validar_documento(tipo, numero)
                repetido = User.query.filter(
                    User.tipo_documento == tipo, User.documento == numero, User.id != user.id
                ).first()
                if repetido:
                    raise ValueError("Ya existe una cuenta con ese documento")
                user.tipo_documento = tipo
                user.documento = numero
            if (telefono or "").strip():
                user.telefono = validar_telefono(telefono)
        except ValueError:
            db.session.rollback()
            raise

        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            raise ValueError("Ya existe una cuenta con ese documento")
        return UserService._to_admin_dto(user).to_dict()

    @staticmethod
    def change_email(user_id, nuevo_email, password):
        """Cambia el correo del propio usuario; exige la contrasena actual."""
        user = db.session.get(User, user_id)
        if not user:
            raise ValueError("Usuario no encontrado")
        if not password or not check_password_hash(user.password_hash, password):
            raise ValueError("La contrasena actual no es correcta")

        email = validar_email(nuevo_email)
        if email == user.email:
            raise ValueError("Ese ya es tu correo actual")
        if User.query.filter(User.email == email, User.id != user_id).first():
            raise ValueError("Ya existe una cuenta con ese correo")

        user.email = email
        db.session.commit()
        return UserService._to_admin_dto(user).to_dict()

    @staticmethod
    def change_password(user_id, actual, nueva):
        user = db.session.get(User, user_id)
        if not user:
            raise ValueError("Usuario no encontrado")
        if not actual or not check_password_hash(user.password_hash, actual):
            raise ValueError("La contrasena actual no es correcta")
        validar_password(nueva, "La contrasena nueva")
        if nueva == actual:
            raise ValueError("La contrasena nueva debe ser distinta a la actual")

        user.password_hash = generate_password_hash(nueva)
        db.session.commit()
        return UserService._to_admin_dto(user).to_dict()

    @staticmethod
    def _borrar_foto(upload_folder, foto_url):
        if foto_url:
            ruta = os.path.join(upload_folder, os.path.basename(foto_url))
            if os.path.exists(ruta):
                os.remove(ruta)

    @staticmethod
    def remove_foto(user_id, upload_folder):
        user = db.session.get(User, user_id)
        if not user:
            raise ValueError("Usuario no encontrado")
        if user.foto_url:
            UserService._borrar_foto(upload_folder, user.foto_url)
            user.foto_url = None
            db.session.commit()
        return UserService._to_admin_dto(user).to_dict()

    @staticmethod
    def update_foto(user_id, archivo, upload_folder):
        """Guarda la foto de perfil del propio usuario y devuelve su nueva URL."""
        user = db.session.get(User, user_id)
        if not user:
            raise ValueError("Usuario no encontrado")

        if not archivo or not archivo.filename:
            raise ValueError("No se recibio ningun archivo")

        extension = archivo.filename.rsplit(".", 1)[1].lower() if "." in archivo.filename else ""
        if extension not in FIRMAS_FOTO:
            raise ValueError("Formato de imagen no permitido (usa jpg, png o webp)")

        archivo.stream.seek(0, os.SEEK_END)
        tamano = archivo.stream.tell()
        archivo.stream.seek(0)
        if tamano == 0 or tamano > MAX_FOTO_BYTES:
            raise ValueError(f"La imagen esta vacia o supera {MAX_FOTO_BYTES // (1024 * 1024)} MB")
        cabecera = archivo.stream.read(16)
        archivo.stream.seek(0)
        if not FIRMAS_FOTO[extension](cabecera):
            raise ValueError("El archivo esta danado o no es una imagen valida")

        # Primero se guarda la nueva; la anterior se borra solo si todo salio bien
        os.makedirs(upload_folder, exist_ok=True)
        nombre_unico = f"usuario_{user.id}_{uuid.uuid4().hex[:8]}.{extension}"
        archivo.save(os.path.join(upload_folder, nombre_unico))

        foto_anterior = user.foto_url
        user.foto_url = f"/static/uploads/perfiles/{nombre_unico}"
        db.session.commit()
        UserService._borrar_foto(upload_folder, foto_anterior)
        return UserService._to_admin_dto(user).to_dict()
