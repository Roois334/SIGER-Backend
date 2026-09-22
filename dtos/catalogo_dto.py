class MunicipioCreateDTO:
    def __init__(self, codigo, nombre):
        self.codigo = codigo
        self.nombre = nombre


class MunicipioUpdateDTO:
    def __init__(self, codigo=None, nombre=None):
        self.codigo = codigo
        self.nombre = nombre


class MunicipioDTO:
    def __init__(self, id, codigo, nombre, activo, fecha_creacion=None):
        self.id = id
        self.codigo = codigo
        self.nombre = nombre
        self.activo = activo
        self.fecha_creacion = fecha_creacion

    def to_dict(self):
        return {
            "id": self.id,
            "codigo": self.codigo,
            "nombre": self.nombre,
            "activo": self.activo,
            "fecha_creacion": self.fecha_creacion.isoformat() if self.fecha_creacion else None,
        }


class OrganismoCreateDTO:
    def __init__(self, codigo, nombre, tipo=None, municipios=None):
        self.codigo = codigo
        self.nombre = nombre
        self.tipo = tipo
        self.municipios = municipios or []


class OrganismoUpdateDTO:
    def __init__(self, codigo=None, nombre=None, tipo=None):
        self.codigo = codigo
        self.nombre = nombre
        self.tipo = tipo


class OrganismoDTO:
    def __init__(self, id, codigo, nombre, tipo, activo, municipios=None, fecha_creacion=None):
        self.id = id
        self.codigo = codigo
        self.nombre = nombre
        self.tipo = tipo
        self.activo = activo
        self.municipios = municipios or []
        self.fecha_creacion = fecha_creacion

    def to_dict(self):
        return {
            "id": self.id,
            "codigo": self.codigo,
            "nombre": self.nombre,
            "tipo": self.tipo,
            "activo": self.activo,
            "municipios": self.municipios,
            "fecha_creacion": self.fecha_creacion.isoformat() if self.fecha_creacion else None,
        }