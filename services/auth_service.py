from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import create_access_token
from extensions import db
from models.user import User
from dtos.user_dto import UserResponseDTO

ROLES_VALIDOS = ["ciudadano", "gestor_municipal", "organismo_atencion", "administrador"]


class AuthService:
    @staticmethod
    def register(dto):
        if dto.rol not in ROLES_VALIDOS:
            raise ValueError("Rol invalido")
        if User.query.filter_by(email=dto.email).first():
            raise ValueError("Ya existe una cuenta con ese correo")
        if len(dto.password) < 6:
            raise ValueError("La contrasena debe tener minimo 6 caracteres")

        user = User(
            nombre=dto.nombre,
            apellido=dto.apellido,
            email=dto.email,
            password_hash=generate_password_hash(dto.password),
            rol=dto.rol,
            municipio=dto.municipio,
        )
        db.session.add(user)
        db.session.commit()

        token = create_access_token(identity=str(user.id), additional_claims={"rol": user.rol})
        return token, UserResponseDTO(user.id, user.nombre, user.apellido, user.email, user.rol, user.municipio)

    @staticmethod
    def login(dto):
        user = User.query.filter_by(email=dto.email, activo=True).first()
        if not user or not check_password_hash(user.password_hash, dto.password):
            raise ValueError("Correo o contrasena incorrectos")

        token = create_access_token(identity=str(user.id), additional_claims={"rol": user.rol})
        return token, UserResponseDTO(user.id, user.nombre, user.apellido, user.email, user.rol, user.municipio)
