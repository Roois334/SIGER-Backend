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
