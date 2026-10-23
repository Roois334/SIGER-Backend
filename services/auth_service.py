from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import create_access_token
from extensions import db
from models.user import User
from models.catalogos import Rol, Municipio
from dtos.user_dto import UserResponseDTO
from utilities.validaciones import validar_email, validar_password


class AuthService:
    @staticmethod
    def register(dto):
        # El registro publico SIEMPRE crea ciudadanos, sin importar lo que llegue en dto.rol
        rol = Rol.query.filter_by(nombre="ciudadano").first()
        if not rol:
            raise ValueError("Rol invalido")

        dto.nombre = (dto.nombre or "").strip()
        dto.apellido = (dto.apellido or "").strip()
        if not dto.nombre or not dto.apellido:
            raise ValueError("Nombre y apellido son obligatorios")
        if len(dto.nombre) > 80 or len(dto.apellido) > 80:
            raise ValueError("Nombre y apellido no pueden superar 80 caracteres")

        dto.email = validar_email(dto.email)
        if User.query.filter_by(email=dto.email).first():
            raise ValueError("Ya existe una cuenta con ese correo")

        validar_password(dto.password)

        municipio = None
        if dto.municipio:
            municipio = Municipio.query.filter_by(nombre=dto.municipio).first()
            if not municipio:
                raise ValueError("Municipio invalido")

        user = User(
            nombre=dto.nombre,
            apellido=dto.apellido,
            email=dto.email,
            password_hash=generate_password_hash(dto.password),
            rol_id=rol.id,
            municipio_id=municipio.id if municipio else None,
        )
        db.session.add(user)
        db.session.commit()

        return AuthService._emitir_token(user)

    @staticmethod
    def login(dto):
        user = User.query.filter_by(email=dto.email, activo=True).first()
        if not user or not check_password_hash(user.password_hash, dto.password):
            raise ValueError("Correo o contrasena incorrectos")

        return AuthService._emitir_token(user)

    @staticmethod
    def _emitir_token(user):
        token = create_access_token(identity=str(user.id), additional_claims={"rol": user.rol.nombre})
        dto = UserResponseDTO(
            user.id,
            user.nombre,
            user.apellido,
            user.email,
            user.rol.nombre,
            user.municipio.nombre if user.municipio else None,
            user.foto_url,
            organismo=user.organismo.nombre if user.organismo else None,
        )
        return token, dto