class ReporteCreateDTO:
    def __init__(self, tipo, municipio_id, direccion, descripcion,
                 latitud=None, longitud=None, afectados=0):
        self.tipo = tipo
        self.municipio_id = municipio_id
        self.direccion = direccion
        self.descripcion = descripcion
        self.latitud = latitud
        self.longitud = longitud
        self.afectados = afectados


class EvidenciaDTO:
    def __init__(self, id, nombre_archivo, ruta_archivo, fecha_carga=None):
        self.id = id
        self.nombre_archivo = nombre_archivo
        self.ruta_archivo = ruta_archivo
        self.fecha_carga = fecha_carga

    def to_dict(self):
        return {
            "id": self.id,
            "nombre_archivo": self.nombre_archivo,
            "ruta_archivo": self.ruta_archivo,
            "fecha_carga": self.fecha_carga.isoformat() if self.fecha_carga else None,
        }


class ReporteDTO:
    def __init__(self, id, folio, tipo, descripcion, direccion, latitud, longitud,
                 afectados, estado, fecha_hora, ciudadano_id, municipio_nombre,
                 evidencias=None):
        self.id = id
        self.folio = folio
        self.tipo = tipo
        self.descripcion = descripcion
        self.direccion = direccion
        self.latitud = latitud
        self.longitud = longitud
        self.afectados = afectados
        self.estado = estado
        self.fecha_hora = fecha_hora
        self.ciudadano_id = ciudadano_id
        self.municipio_nombre = municipio_nombre
        self.evidencias = evidencias or []

    def to_dict(self):
        return {
            "id": self.id,
            "folio": self.folio,
            "tipo": self.tipo,
            "descripcion": self.descripcion,
            "direccion": self.direccion,
            "latitud": self.latitud,
            "longitud": self.longitud,
            "afectados": self.afectados,
            "estado": self.estado,
            "fecha_hora": self.fecha_hora.isoformat() if self.fecha_hora else None,
            "ciudadano_id": self.ciudadano_id,
            "municipio": self.municipio_nombre,
            "evidencias": [e.to_dict() if hasattr(e, "to_dict") else e for e in self.evidencias],
        }