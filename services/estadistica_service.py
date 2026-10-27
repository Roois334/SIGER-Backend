"""
HU-17 - Estadisticas de emergencias.

Calcula indicadores a partir de los reportes registrados: total, activas, resueltas,
distribucion (con porcentajes) por tipo, municipio, prioridad y estado, serie en el
tiempo y tiempos promedio de respuesta y de atencion.

  activa   = pendiente, asignado o en_atencion
  resuelta = resuelto o cerrado
  tiempo de respuesta = desde que se reporta hasta que el gestor la asigna por primera vez
  tiempo de atencion  = desde que se reporta hasta que el organismo la marca como resuelta
"""

from datetime import timedelta

from sqlalchemy.orm import joinedload

from models.reporte import Reporte, ReporteHistorial
from utilities.permisos import ADMINISTRADOR, GESTOR_MUNICIPAL
from utilities.prioridad import PRIORIDADES
from utilities.fechas import ahora, rango_fechas, filtrar_por_fecha

ACTIVAS = ("pendiente", "asignado", "en_atencion")
RESUELTAS = ("resuelto", "cerrado")
ORDEN_PRIORIDAD = list(reversed(PRIORIDADES))
ORDEN_ESTADO = ["pendiente", "asignado", "en_atencion", "resuelto", "cerrado", "descartado"]
MAX_DIAS_SERIE_DIARIA = 92
MAX_RANGO_DIAS = 3660


def _pct(parte, total):
    return round(parte * 100.0 / total, 1) if total else 0.0


def _promedio_min(valores):
    return round(sum(valores) / len(valores), 1) if valores else None


def _distribucion(contador, total, orden=None):
    claves = orden if orden else sorted(contador, key=lambda k: (-contador[k], str(k)))
    return [{"clave": k, "total": contador.get(k, 0), "porcentaje": _pct(contador.get(k, 0), total)} for k in claves]


class EstadisticaService:

    @staticmethod
    def consultar(usuario, desde=None, hasta=None, municipio_id=None, tipo=None, prioridad=None, estado=None):
        rol = usuario.rol.nombre
        if rol not in (GESTOR_MUNICIPAL, ADMINISTRADOR):
            raise PermissionError("No tienes permisos para consultar estadisticas")

        f_desde, f_hasta = rango_fechas(desde, hasta)
        if f_desde and f_hasta and (f_hasta - f_desde).days > MAX_RANGO_DIAS:
            raise ValueError("El periodo no puede superar 10 anos")
        if prioridad and prioridad not in ORDEN_PRIORIDAD:
            raise ValueError("Prioridad invalida")
        if estado and estado not in ORDEN_ESTADO and estado not in ("activas", "resueltas"):
            raise ValueError("Estado invalido")

        # El gestor solo ve su municipio, sin importar lo que envie
        if rol == GESTOR_MUNICIPAL:
            if not usuario.municipio_id:
                raise ValueError("Tu usuario no tiene un municipio asignado. Contacta al administrador")
            municipio_id = usuario.municipio_id

        q = Reporte.query.options(joinedload(Reporte.municipio), joinedload(Reporte.organismo))
        if municipio_id:
            q = q.filter(Reporte.municipio_id == int(municipio_id))
        if tipo:
            q = q.filter(Reporte.tipo == tipo)
        if prioridad:
            q = q.filter(Reporte.prioridad == prioridad)
        if estado == "activas":
            q = q.filter(Reporte.estado.in_(ACTIVAS))
        elif estado == "resueltas":
            q = q.filter(Reporte.estado.in_(RESUELTAS))
        elif estado:
            q = q.filter(Reporte.estado == estado)
        q = filtrar_por_fecha(q, Reporte.fecha_hora, f_desde, f_hasta)
        reportes = q.all()
        total = len(reportes)

        # --- tiempos: primer movimiento "asignar" y primer "resolver" de cada reporte ---
        ids = [r.id for r in reportes]
        primeros = {"asignar": {}, "resolver": {}}
        if ids:
            for i in range(0, len(ids), 500):
                filas = (ReporteHistorial.query
                         .filter(ReporteHistorial.reporte_id.in_(ids[i:i + 500]),
                                 ReporteHistorial.accion.in_(("asignar", "resolver")))
                         .order_by(ReporteHistorial.fecha, ReporteHistorial.id).all())
                for h in filas:
                    primeros[h.accion].setdefault(h.reporte_id, h.fecha)
        resp, aten = [], []
        for r in reportes:
            if not r.fecha_hora:
                continue
            a = primeros["asignar"].get(r.id)
            if a and a >= r.fecha_hora:
                resp.append((a - r.fecha_hora).total_seconds() / 60)
            s = primeros["resolver"].get(r.id)
            if s and s >= r.fecha_hora:
                aten.append((s - r.fecha_hora).total_seconds() / 60)

        # --- conteos ---
        c_tipo, c_mun, c_pri, c_est, c_org = {}, {}, {}, {}, {}
        activas = resueltas = descartadas = criticas_activas = afectados = heridos = 0
        for r in reportes:
            c_tipo[r.tipo] = c_tipo.get(r.tipo, 0) + 1
            nm = r.municipio.nombre if r.municipio else "Sin municipio"
            c_mun[nm] = c_mun.get(nm, 0) + 1
            c_pri[r.prioridad] = c_pri.get(r.prioridad, 0) + 1
            c_est[r.estado] = c_est.get(r.estado, 0) + 1
            if r.organismo and r.estado not in ("pendiente", "descartado"):
                c_org[r.organismo.nombre] = c_org.get(r.organismo.nombre, 0) + 1
            if r.estado in ACTIVAS:
                activas += 1
                if r.prioridad == "critica":
                    criticas_activas += 1
            elif r.estado in RESUELTAS:
                resueltas += 1
            elif r.estado == "descartado":
                descartadas += 1
            afectados += r.afectados or 0
            heridos += r.heridos or 0

        return {
            "filtros": {"desde": desde or "", "hasta": hasta or "", "municipio_id": municipio_id or "",
                        "tipo": tipo or "", "prioridad": prioridad or "", "estado": estado or ""},
            "alcance": "municipio" if rol == GESTOR_MUNICIPAL else "region",
            "generado": ahora().strftime("%Y-%m-%d %H:%M"),
            "kpis": {
                "total": total,
                "activas": activas,
                "resueltas": resueltas,
                "descartadas": descartadas,
                "criticas_activas": criticas_activas,
                "pct_activas": _pct(activas, total),
                "pct_resueltas": _pct(resueltas, total),
                "afectados": afectados,
                "heridos": heridos,
                "tiempo_respuesta_min": _promedio_min(resp),
                "tiempo_atencion_min": _promedio_min(aten),
                "con_tiempo_respuesta": len(resp),
                "con_tiempo_atencion": len(aten),
            },
            "por_tipo": _distribucion(c_tipo, total),
            "por_municipio": _distribucion(c_mun, total),
            "por_prioridad": _distribucion(c_pri, total, ORDEN_PRIORIDAD),
            "por_estado": _distribucion(c_est, total, ORDEN_ESTADO),
            "por_organismo": _distribucion(c_org, sum(c_org.values()))[:8],
            "serie": EstadisticaService._serie(reportes, f_desde, f_hasta),
        }

    @staticmethod
    def _serie(reportes, f_desde, f_hasta):
        """Emergencias reportadas por dia (periodos cortos) o por mes (periodos largos)."""
        fechas = [r.fecha_hora.date() for r in reportes if r.fecha_hora]
        if not fechas:
            return {"granularidad": "dia", "puntos": []}
        ini = f_desde or min(fechas)
        fin = f_hasta or max(fechas)
        if (fin - ini).days <= MAX_DIAS_SERIE_DIARIA:
            cont = {}
            for f in fechas:
                cont[f] = cont.get(f, 0) + 1
            puntos, d = [], ini
            while d <= fin:
                puntos.append({"etiqueta": d.isoformat(), "total": cont.get(d, 0)})
                d += timedelta(days=1)
            return {"granularidad": "dia", "puntos": puntos}
        cont = {}
        for f in fechas:
            k = (f.year, f.month)
            cont[k] = cont.get(k, 0) + 1
        puntos, y, m = [], ini.year, ini.month
        while (y, m) <= (fin.year, fin.month):
            puntos.append({"etiqueta": f"{y:04d}-{m:02d}", "total": cont.get((y, m), 0)})
            m += 1
            if m > 12:
                y, m = y + 1, 1
        return {"granularidad": "mes", "puntos": puntos}
