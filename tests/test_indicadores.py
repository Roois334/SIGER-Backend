"""
Indicadores calculados por procedimientos almacenados de PostgreSQL y apoyo a la auditoria.

Las pruebas corren en SQLite, donde esos procedimientos no existen: se simula la respuesta de
PostgreSQL y se comprueba que la app llama al procedimiento correcto, con el alcance correcto.
Los procedimientos en si se prueban contra PostgreSQL (ver README, "Triggers y procedimientos").
"""
from decimal import Decimal

import pytest

from services import indicador_service
from tests.conftest import cabeceras
from utilities import auditoria


class _Fila:
    def __init__(self, **valores):
        self._mapping = valores


@pytest.fixture
def postgres_simulado(monkeypatch):
    """Hace creer a la app que usa PostgreSQL y guarda cada consulta que hace."""
    llamadas = []
    respuestas = {
        "fn_resumen_municipio": [_Fila(estado="pendiente", total=2, critica=1, alta=1, media=0, baja=0)],
        "fn_tiempo_respuesta": [_Fila(reportes=3, con_asignacion=2, promedio_asignacion_min=Decimal("45.5"),
                                      con_resolucion=1, promedio_resolucion_min=None)],
        "fn_carga_organismos": [_Fila(organismo_id=1, organismo="Bomberos", principales=2, de_apoyo=1,
                                      total_activas=3)],
    }

    def ejecutar(sql, parametros=None):
        llamadas.append((str(sql), parametros))
        return next(v for k, v in respuestas.items() if k in str(sql))

    monkeypatch.setattr(indicador_service, "usa_postgresql", lambda: True)
    monkeypatch.setattr(indicador_service.db.session, "execute", ejecutar)
    return llamadas


class TestIndicadores:
    def test_resumen_del_administrador_de_un_municipio(self, client, datos, postgres_simulado):
        admin = datos.usuario("administrador", municipio=None)
        r = client.get(f"/api/indicadores/resumen?municipio_id={datos.madrid.id}", headers=cabeceras(admin))
        assert r.status_code == 200
        assert r.get_json() == {"municipio_id": datos.madrid.id, "estados": [
            {"estado": "pendiente", "total": 2, "critica": 1, "alta": 1, "media": 0, "baja": 0}]}
        assert "fn_resumen_municipio" in postgres_simulado[0][0]
        assert postgres_simulado[0][1] == {"m": datos.madrid.id}

    def test_administrador_sin_municipio_ve_la_region(self, client, datos, postgres_simulado):
        admin = datos.usuario("administrador", municipio=None)
        r = client.get("/api/indicadores/resumen", headers=cabeceras(admin))
        assert r.status_code == 200 and r.get_json()["municipio_id"] is None

    def test_el_gestor_queda_en_su_municipio(self, client, datos, postgres_simulado):
        gestor = datos.usuario("gestor_municipal")
        r = client.get(f"/api/indicadores/resumen?municipio_id={datos.madrid.id}", headers=cabeceras(gestor))
        assert r.status_code == 200 and r.get_json()["municipio_id"] == datos.facatativa.id
        assert postgres_simulado[0][1] == {"m": datos.facatativa.id}

    def test_gestor_sin_municipio(self, client, datos, postgres_simulado):
        gestor = datos.usuario("gestor_municipal", municipio=None)
        r = client.get("/api/indicadores/resumen", headers=cabeceras(gestor))
        assert r.status_code == 400 and "municipio" in r.get_json()["error"]

    def test_tiempos_con_fechas_y_decimales(self, client, datos, postgres_simulado):
        admin = datos.usuario("administrador", municipio=None)
        r = client.get("/api/indicadores/tiempos?desde=2026-01-01&hasta=2026-01-31", headers=cabeceras(admin))
        d = r.get_json()
        assert r.status_code == 200
        assert d["promedio_asignacion_min"] == 45.5 and d["promedio_resolucion_min"] is None
        assert "fn_tiempo_respuesta" in postgres_simulado[0][0]
        assert str(postgres_simulado[0][1]["d"]) == "2026-01-01" and str(postgres_simulado[0][1]["h"]) == "2026-01-31"

    def test_tiempos_con_fechas_invalidas(self, client, datos, postgres_simulado):
        admin = datos.usuario("administrador", municipio=None)
        r = client.get("/api/indicadores/tiempos?desde=2026-02-01&hasta=2026-01-01", headers=cabeceras(admin))
        assert r.status_code == 400 and postgres_simulado == []

    def test_carga_de_organismos(self, client, datos, postgres_simulado):
        gestor = datos.usuario("gestor_municipal")
        r = client.get("/api/indicadores/carga-organismos", headers=cabeceras(gestor))
        assert r.status_code == 200
        assert r.get_json()["organismos"][0] == {"organismo_id": 1, "organismo": "Bomberos", "principales": 2,
                                                 "de_apoyo": 1, "total_activas": 3}

    @pytest.mark.parametrize("rol,ruta", [
        ("ciudadano", "resumen"), ("ciudadano", "tiempos"), ("ciudadano", "carga-organismos"),
        ("organismo_atencion", "resumen"), ("organismo_atencion", "carga-organismos"),
    ])
    def test_roles_sin_permiso(self, client, datos, postgres_simulado, rol, ruta):
        usuario = datos.usuario(rol, organismo=datos.bomberos if rol == "organismo_atencion" else None)
        r = client.get(f"/api/indicadores/{ruta}", headers=cabeceras(usuario))
        assert r.status_code == 403 and postgres_simulado == []

    def test_sin_postgresql_responde_501(self, client, datos):
        admin = datos.usuario("administrador", municipio=None)
        r = client.get("/api/indicadores/resumen", headers=cabeceras(admin))
        assert r.status_code == 501 and "PostgreSQL" in r.get_json()["error"]


class TestAuditoria:
    def test_en_sqlite_no_hace_nada(self, app, monkeypatch):
        llamadas = []
        monkeypatch.setattr(auditoria.db.session, "execute", lambda *a, **k: llamadas.append(a))
        with app.app_context():
            assert auditoria.usa_postgresql() is False
            auditoria.registrar_actor(5)
        assert llamadas == []

    def test_en_postgresql_informa_el_actor(self, app, monkeypatch):
        llamadas = []
        monkeypatch.setattr(auditoria, "usa_postgresql", lambda: True)
        monkeypatch.setattr(auditoria.db.session, "execute", lambda sql, p=None: llamadas.append((str(sql), p)))
        auditoria.registrar_actor(7)
        auditoria.registrar_actor(None)
        assert llamadas == [("SELECT set_config('siger.usuario_actual', :id, true)", {"id": "7"})]

    def test_cambiar_rol_y_estado_informa_al_administrador(self, client, datos, monkeypatch):
        from services import user_service
        actores = []
        monkeypatch.setattr(user_service, "registrar_actor", actores.append)
        admin = datos.usuario("administrador", municipio=None)
        u = datos.usuario()
        assert client.put(f"/api/usuarios/{u.id}", json={"rol": "gestor_municipal"},
                          headers=cabeceras(admin)).status_code == 200
        assert client.patch(f"/api/usuarios/{u.id}/estado", json={"activo": False},
                            headers=cabeceras(admin)).status_code == 200
        assert actores == [admin.id, admin.id]
