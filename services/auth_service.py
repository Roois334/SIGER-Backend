from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import create_access_token
from extensions import db
from models.user import User
from models.catalogos import Rol, Municipio
from dtos.user_dto import UserResponseDTO


class AuthService:
    @staticmethod
    def register(dto):
        rol = Rol.query.filter_by(nombre=dto.rol).first()
        if not rol:
            raise ValueError("Rol invalido")

        if not dto.email or User.query.filter_by(email=dto.email).first():
            raise ValueError("Ya existe una cuenta con ese correo")

        if not dto.password or len(dto.password) < 6:
            raise ValueError("La contrasena debe tener minimo 6 caracteres")

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
        )
        return token, dto