import os


class ReporteCreateDTO:
    def __init__(self, tipo, municipio_id, direccion, descripcion,
                 latitud=None, longitud=None, afectados=0, heridos=0):
        self.tipo = tipo
        self.municipio_id = municipio_id
        self.direccion = direccion
        self.descripcion = descripcion
        self.latitud = latitud
        self.longitud = longitud
        self.afectados = afectados
        self.heridos = heridos


_TIPOS_ARCHIVO = {
    "png": "imagen", "jpg": "imagen", "jpeg": "imagen", "gif": "imagen",
    "mp4": "video",
    "pdf": "pdf",
}


class EvidenciaDTO:
    def __init__(self, id, nombre_archivo, ruta_archivo, fecha_carga=None):
        self.id = id
        self.nombre_archivo = nombre_archivo
        self.ruta_archivo = ruta_archivo
        self.fecha_carga = fecha_carga

    def to_dict(self):
        extension = os.path.splitext(self.nombre_archivo or "")[1].lstrip(".").lower()
        return {
            "id": self.id,
            "nombre_archivo": self.nombre_archivo,
            "tipo": _TIPOS_ARCHIVO.get(extension, "archivo"),
            "url": f"/api/reportes/evidencias/{self.id}",
            "fecha_carga": self.fecha_carga.isoformat() if self.fecha_carga else None,
        }


class ReporteDTO:
    def __init__(self, id, folio, tipo, prioridad, descripcion, direccion, latitud, longitud,
                 afectados, estado, fecha_hora, ciudadano_id, municipio_nombre,
                 evidencias=None, ciudadano_nombre=None,
                 organismo_id=None, organismo_nombre=None, fecha_asignacion=None, asignado_por=None,
                 heridos=0, vias_afectadas=None, area_afectada=None, riesgo_propagacion=None,
                 fecha_actualizacion=None, apoyos=None):
        self.id = id
        self.folio = folio
        self.tipo = tipo
        self.prioridad = prioridad
        self.descripcion = descripcion
        self.direccion = direccion
        self.latitud = latitud
        self.longitud = longitud
        self.afectados = afectados
        self.heridos = heridos
        self.vias_afectadas = vias_afectadas
        self.area_afectada = area_afectada
        self.riesgo_propagacion = riesgo_propagacion
        self.fecha_actualizacion = fecha_actualizacion
        self.apoyos = apoyos or []
        self.estado = estado
        self.fecha_hora = fecha_hora
        self.ciudadano_id = ciudadano_id
        self.municipio_nombre = municipio_nombre
        self.evidencias = evidencias or []
        self.ciudadano_nombre = ciudadano_nombre
        self.organismo_id = organismo_id
        self.organismo_nombre = organismo_nombre
        self.fecha_asignacion = fecha_asignacion
        self.asignado_por = asignado_por

    def to_dict(self):
        return {
            "id": self.id,
            "folio": self.folio,
            "tipo": self.tipo,
            "prioridad": self.prioridad,
            "descripcion": self.descripcion,
            "direccion": self.direccion,
            "latitud": self.latitud,
            "longitud": self.longitud,
            "afectados": self.afectados,
            "heridos": self.heridos,
            "vias_afectadas": self.vias_afectadas,
            "area_afectada": self.area_afectada,
            "riesgo_propagacion": self.riesgo_propagacion,
            "fecha_actualizacion": self.fecha_actualizacion.isoformat() if self.fecha_actualizacion else None,
            "apoyos": self.apoyos,
            "estado": self.estado,
            "fecha_hora": self.fecha_hora.isoformat() if self.fecha_hora else None,
            "ciudadano_id": self.ciudadano_id,
            "ciudadano": self.ciudadano_nombre,
            "municipio": self.municipio_nombre,
            "organismo_id": self.organismo_id,
            "organismo": self.organismo_nombre,
            "fecha_asignacion": self.fecha_asignacion.isoformat() if self.fecha_asignacion else None,
            "asignado_por": self.asignado_por,
            "evidencias": [e.to_dict() if hasattr(e, "to_dict") else e for e in self.evidencias],
        }
