"""
Indicadores que calcula la propia base de datos con procedimientos almacenados
(definidos directamente en la base PostgreSQL de Azure):

  fn_resumen_municipio  -> emergencias por estado y prioridad
  fn_tiempo_respuesta   -> minutos promedio en asignar y en resolver
  fn_carga_organismos   -> emergencias activas de cada organismo (para decidir a quien asignar)

El gestor siempre queda limitado a su municipio; el administrador puede elegir uno o ver toda la region.
"""
from decimal import Decimal

from sqlalchemy import text

from extensions import db
from utilities.auditoria import usa_postgresql
from utilities.fechas import rango_fechas
from utilities.permisos import tiene_alcance_municipal


def _valor(v):
    return float(v) if isinstance(v, Decimal) else v


class IndicadorService:

    @staticmethod
    def _municipio(usuario, municipio_id):
        if tiene_alcance_municipal(usuario.rol.nombre):
            if not usuario.municipio_id:
                raise ValueError("Tu usuario no tiene un municipio asignado. Contacta al administrador")
            return usuario.municipio_id
        return municipio_id

    @staticmethod
    def _consultar(sql, parametros):
        if not usa_postgresql():
            raise RuntimeError("Estos indicadores los calcula PostgreSQL y no estan disponibles en esta base")
        filas = db.session.execute(text(sql), parametros)
        return [{k: _valor(v) for k, v in f._mapping.items()} for f in filas]

    @staticmethod
    def resumen(usuario, municipio_id=None):
        municipio_id = IndicadorService._municipio(usuario, municipio_id)
        estados = IndicadorService._consultar("SELECT * FROM fn_resumen_municipio(:m)", {"m": municipio_id})
        return {"municipio_id": municipio_id, "estados": estados}

    @staticmethod
    def tiempos(usuario, municipio_id=None, desde=None, hasta=None):
        municipio_id = IndicadorService._municipio(usuario, municipio_id)
        f_desde, f_hasta = rango_fechas(desde, hasta)
        fila = IndicadorService._consultar("SELECT * FROM fn_tiempo_respuesta(:m, :d, :h)",
                                           {"m": municipio_id, "d": f_desde, "h": f_hasta})[0]
        return {"municipio_id": municipio_id, **fila}

    @staticmethod
    def carga_organismos(usuario, municipio_id=None):
        municipio_id = IndicadorService._municipio(usuario, municipio_id)
        organismos = IndicadorService._consultar("SELECT * FROM fn_carga_organismos(:m)", {"m": municipio_id})
        return {"municipio_id": municipio_id, "organismos": organismos}
