class UserRegisterDTO:
    def __init__(self, nombre, apellido, email, password, rol="ciudadano", municipio=None):
        self.nombre = nombre
        self.apellido = apellido
        self.email = email
        self.password = password
        self.rol = rol
        self.municipio = municipio


class UserLoginDTO:
    def __init__(self, email, password):
        self.email = email
        self.password = password


class UserResponseDTO:
    def __init__(self, id, nombre, apellido, email, rol, municipio):
        self.id = id
        self.nombre = nombre
        self.apellido = apellido
        self.email = email
        self.rol = rol
        self.municipio = municipio

    def to_dict(self):
        return {
            "id": self.id,
            "nombre": self.nombre,
            "apellido": self.apellido,
            "email": self.email,
            "rol": self.rol,
            "municipio": self.municipio,
        }


class UserUpdateDTO:
    """Datos que un administrador puede modificar de un usuario existente."""
    def __init__(self, nombre=None, apellido=None, email=None, municipio=None, rol=None):
        self.nombre = nombre
        self.apellido = apellido
        self.email = email
        self.municipio = municipio
        self.rol = rol


class UserAdminDTO:
    """Representacion de un usuario para el panel de administracion."""
    def __init__(self, id, nombre, apellido, email, rol, municipio, activo, fecha_creacion):
        self.id = id
        self.nombre = nombre
        self.apellido = apellido
        self.email = email
        self.rol = rol
        self.municipio = municipio
        self.activo = activo
        self.fecha_creacion = fecha_creacion

    def to_dict(self):
        return {
            "id": self.id,
            "nombre": self.nombre,
            "apellido": self.apellido,
            "email": self.email,
            "rol": self.rol,
            "municipio": self.municipio,
            "activo": self.activo,
            "fecha_creacion": self.fecha_creacion.isoformat() if self.fecha_creacion else None,
        }