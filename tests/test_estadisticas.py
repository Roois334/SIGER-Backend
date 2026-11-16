"""HU-17: indicadores y distribuciones."""
from datetime import datetime, timedelta

from models.reporte import ReporteHistorial
from services.estadistica_service import EstadisticaService, _pct, _promedio_min
from tests.conftest import cabeceras


def _historial(datos, reporte, accion, minutos):
    datos.db.session.add(ReporteHistorial(reporte_id=reporte.id, accion=accion, estado_nuevo="x",
                                          fecha=reporte.fecha_hora + timedelta(minutes=minutos)))
    datos.db.session.commit()


def _poblar(datos):
    c = datos.usuario()
    base = datetime(2026, 3, 1, 8, 0)
    r1 = datos.reporte(c, estado="resuelto", prioridad="critica", afectados=10, heridos=2, fecha_hora=base,
                       organismo_id=datos.bomberos.id)
    r2 = datos.reporte(c, estado="pendiente", prioridad="critica", tipo="Inundacion", fecha_hora=base + timedelta(days=1))
    r3 = datos.reporte(c, estado="descartado", prioridad="baja", fecha_hora=base + timedelta(days=2))
    r4 = datos.reporte(c, municipio=datos.madrid, estado="en_atencion", prioridad="media",
                       fecha_hora=base + timedelta(days=3), organismo_id=datos.cruz_roja.id)
    _historial(datos, r1, "asignar", 30)
    _historial(datos, r1, "resolver", 90)
    return r1


class TestEstadisticas:
    def test_indicadores_del_administrador(self, client, datos):
        _poblar(datos)
        admin = datos.usuario("administrador", municipio=None)
        r = client.get("/api/estadisticas", headers=cabeceras(admin))
        d = r.get_json()
        k = d["kpis"]
        assert r.status_code == 200 and d["alcance"] == "region"
        assert (k["total"], k["activas"], k["resueltas"], k["descartadas"]) == (4, 2, 1, 1)
        assert k["criticas_activas"] == 1 and k["afectados"] == 10 + 4 * 3 and k["heridos"] == 2 + 3
        assert k["tiempo_respuesta_min"] == 30.0 and k["tiempo_atencion_min"] == 90.0
        assert k["pct_activas"] == 50.0 and k["pct_resueltas"] == 25.0
        assert [x["clave"] for x in d["por_prioridad"]] == ["critica", "alta", "media", "baja"]
        assert {x["clave"]: x["total"] for x in d["por_municipio"]} == {"Facatativa": 3, "Madrid": 1}
        assert {x["clave"] for x in d["por_organismo"]} == {"Bomberos", "Cruz Roja"}

    def test_el_gestor_queda_limitado_a_su_municipio(self, client, datos):
        _poblar(datos)
        gestor = datos.usuario("gestor_municipal")
        d = client.get(f"/api/estadisticas?municipio_id={datos.madrid.id}", headers=cabeceras(gestor)).get_json()
        assert d["alcance"] == "municipio" and d["kpis"]["total"] == 3

    def test_filtros(self, client, datos):
        _poblar(datos)
        h = cabeceras(datos.usuario("administrador", municipio=None))
        total = lambda q: client.get("/api/estadisticas?" + q, headers=h).get_json()["kpis"]["total"]
        assert total("tipo=Inundacion") == 1 and total("prioridad=critica") == 2
        assert total("estado=activas") == 2 and total("estado=resueltas") == 1 and total("estado=descartado") == 1
        assert total(f"municipio_id={datos.madrid.id}") == 1
        assert total("desde=2026-03-02&hasta=2026-03-03") == 2

    def test_serie_diaria_y_mensual(self, client, datos):
        _poblar(datos)
        h = cabeceras(datos.usuario("administrador", municipio=None))
        diaria = client.get("/api/estadisticas", headers=h).get_json()["serie"]
        assert diaria["granularidad"] == "dia" and [p["total"] for p in diaria["puntos"]] == [1, 1, 1, 1]
        mensual = client.get("/api/estadisticas?desde=2026-01-01&hasta=2026-12-31", headers=h).get_json()["serie"]
        assert mensual["granularidad"] == "mes" and len(mensual["puntos"]) == 12
        assert [p["total"] for p in mensual["puntos"] if p["etiqueta"] == "2026-03"] == [4]

    def test_sin_datos(self, client, datos):
        d = client.get("/api/estadisticas", headers=cabeceras(datos.usuario("administrador", municipio=None))).get_json()
        assert d["kpis"]["total"] == 0 and d["kpis"]["tiempo_respuesta_min"] is None and d["serie"]["puntos"] == []

    def test_validaciones_y_permisos(self, client, datos):
        h = cabeceras(datos.usuario("administrador", municipio=None))
        for q in ("prioridad=enorme", "estado=raro", "desde=mal", "desde=2000-01-01&hasta=2026-01-01"):
            assert client.get("/api/estadisticas?" + q, headers=h).status_code == 400, q
        assert client.get("/api/estadisticas", headers=cabeceras(datos.usuario())).status_code == 403
        assert client.get("/api/estadisticas", headers=cabeceras(datos.usuario("gestor_municipal", municipio=None))).status_code == 400

    def test_el_servicio_rechaza_a_un_rol_sin_permiso(self, datos):
        import pytest
        with pytest.raises(PermissionError):
            EstadisticaService.consultar(datos.usuario())

    def test_el_controlador_responde_403_si_el_servicio_levanta_permiso(self, client, datos, monkeypatch):
        monkeypatch.setattr(EstadisticaService, "consultar", staticmethod(lambda *a, **k: (_ for _ in ()).throw(PermissionError("no"))))
        r = client.get("/api/estadisticas", headers=cabeceras(datos.usuario("administrador", municipio=None)))
        assert r.status_code == 403

    def test_ayudas(self):
        assert _pct(1, 3) == 33.3 and _pct(1, 0) == 0.0
        assert _promedio_min([10, 20]) == 15.0 and _promedio_min([]) is None
