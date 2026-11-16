from models.notificacion import Notificacion
from services import notificacion_service as ns
from services.notificacion_service import NotificacionService
from tests.conftest import cabeceras


def _escenario(datos):
    return {
        "ciudadano": datos.usuario(), "gestor": datos.usuario("gestor_municipal"),
        "org": datos.usuario("organismo_atencion", organismo=datos.bomberos),
        "org2": datos.usuario("organismo_atencion", organismo=datos.cruz_roja),
    }


def _tipos(usuario):
    return sorted(n.tipo for n in Notificacion.query.filter_by(usuario_id=usuario.id))


class TestEventos:
    def test_reporte_nuevo_avisa_al_gestor(self, datos):
        e = _escenario(datos)
        r = datos.reporte(e["ciudadano"], tipo="Inundacion")
        NotificacionService.reporte_nuevo(r)
        assert _tipos(e["gestor"]) == ["reporte_nuevo"] and _tipos(e["ciudadano"]) == []

    def test_asignar_avisa_al_ciudadano_y_al_organismo_pero_no_al_actor(self, client, datos):
        e = _escenario(datos)
        r = datos.reporte(e["ciudadano"])
        client.post(f"/api/reportes/{r.id}/asignar", headers=cabeceras(e["gestor"]), json={"organismo_id": datos.bomberos.id})
        assert _tipos(e["ciudadano"]) == ["asignado"] and _tipos(e["org"]) == ["asignado"]
        assert _tipos(e["gestor"]) == [] and _tipos(e["org2"]) == []

    def test_reasignar_avisa_tambien_al_organismo_anterior(self, client, datos):
        e = _escenario(datos)
        r = datos.reporte(e["ciudadano"])
        h = cabeceras(e["gestor"])
        client.post(f"/api/reportes/{r.id}/asignar", headers=h, json={"organismo_id": datos.bomberos.id})
        client.post(f"/api/reportes/{r.id}/asignar", headers=h, json={"organismo_id": datos.cruz_roja.id})
        assert "reasignado" in _tipos(e["ciudadano"]) and "reasignado" in _tipos(e["org2"]) and "reasignado" in _tipos(e["org"])

    def test_ciclo_de_estados(self, client, datos):
        e = _escenario(datos)
        r = datos.reporte(e["ciudadano"], estado="asignado", organismo_id=datos.bomberos.id)
        post = lambda u, accion, **x: client.post(f"/api/reportes/{r.id}/estado", headers=cabeceras(u), json={"accion": accion, **x})
        post(e["org"], "iniciar")
        post(e["org"], "resolver")
        post(e["gestor"], "cerrar")
        assert _tipos(e["ciudadano"]) == ["cerrado", "en_atencion", "resuelto"]
        assert _tipos(e["gestor"]) == ["en_atencion", "resuelto"]

    def test_devolver_y_descartar(self, client, datos):
        e = _escenario(datos)
        r = datos.reporte(e["ciudadano"], estado="asignado", organismo_id=datos.bomberos.id)
        client.post(f"/api/reportes/{r.id}/estado", headers=cabeceras(e["org"]), json={"accion": "devolver", "comentario": "Sin unidades"})
        assert _tipos(e["gestor"]) == ["devuelto"]
        client.post(f"/api/reportes/{r.id}/estado", headers=cabeceras(e["gestor"]), json={"accion": "descartar", "comentario": "Falsa alarma"})
        assert _tipos(e["ciudadano"]) == ["descartado"]

    def test_reclasificar_avisa_al_ciudadano_y_al_organismo(self, client, datos):
        e = _escenario(datos)
        r = datos.reporte(e["ciudadano"], estado="asignado", organismo_id=datos.bomberos.id)
        client.post(f"/api/reportes/{r.id}/tipo", headers=cabeceras(e["gestor"]), json={"tipo": "Deslizamiento", "comentario": "Corregido"})
        assert _tipos(e["ciudadano"]) == ["reclasificado"] and _tipos(e["org"]) == ["reclasificado"]

    def test_accion_desconocida_no_genera_nada(self, datos):
        e = _escenario(datos)
        NotificacionService.cambio_estado(datos.reporte(e["ciudadano"]), e["gestor"], "otra")
        assert Notificacion.query.count() == 0

    def test_un_fallo_al_notificar_no_rompe_la_accion(self, client, datos, monkeypatch):
        e = _escenario(datos)
        monkeypatch.setattr(NotificacionService, "_crear", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")))
        r = datos.reporte(e["ciudadano"])
        res = client.post(f"/api/reportes/{r.id}/asignar", headers=cabeceras(e["gestor"]), json={"organismo_id": datos.bomberos.id})
        assert res.status_code == 200 and res.get_json()["reporte"]["estado"] == "asignado"

    def test_destinatarios_inactivos_o_repetidos_se_omiten(self, datos):
        e = _escenario(datos)
        e["ciudadano"].activo = False
        datos.db.session.commit()
        r = datos.reporte(e["ciudadano"])
        creadas = NotificacionService._crear([e["gestor"], e["gestor"], None], r, "x", "t" * 200, "m" * 400)
        assert len(creadas) == 1 and len(creadas[0][1].titulo) == 150 and len(creadas[0][1].mensaje) == 300
        assert ns._ciudadano(r) == [] and ns._organismo(None, 1) == []


class TestConsulta:
    def _con_tres(self, datos):
        e = _escenario(datos)
        r = datos.reporte(e["ciudadano"])
        for i in range(3):
            datos.db.session.add(Notificacion(usuario_id=e["ciudadano"].id, reporte_id=r.id, tipo="asignado",
                                              titulo=f"T{i}", mensaje="m", leida=(i == 0)))
        datos.db.session.commit()
        return e["ciudadano"]

    def test_listar_contar_y_paginar(self, client, datos):
        u = self._con_tres(datos)
        h = cabeceras(u)
        d = client.get("/api/notificaciones", headers=h).get_json()
        assert len(d["notificaciones"]) == 3 and d["no_leidas"] == 2 and not d["hay_mas"]
        assert d["notificaciones"][0]["folio"].startswith("RPT-")
        assert len(client.get("/api/notificaciones?no_leidas=1", headers=h).get_json()["notificaciones"]) == 2
        pag = client.get("/api/notificaciones?limite=2", headers=h).get_json()
        assert len(pag["notificaciones"]) == 2 and pag["hay_mas"]
        ultimo = pag["notificaciones"][-1]["id"]
        assert len(client.get(f"/api/notificaciones?antes_id={ultimo}", headers=h).get_json()["notificaciones"]) == 1
        assert client.get("/api/notificaciones/contador", headers=h).get_json() == {"no_leidas": 2}

    def test_marcar_leidas(self, client, datos):
        u = self._con_tres(datos)
        h = cabeceras(u)
        pendiente = Notificacion.query.filter_by(leida=False).first()
        r = client.post(f"/api/notificaciones/{pendiente.id}/leer", headers=h)
        assert r.get_json()["no_leidas"] == 1 and r.get_json()["notificacion"]["leida"]
        assert client.post(f"/api/notificaciones/{pendiente.id}/leer", headers=h).status_code == 200
        assert client.post("/api/notificaciones/leer-todas", headers=h).get_json() == {"no_leidas": 0}

    def test_no_se_pueden_leer_las_de_otro(self, client, datos):
        u = self._con_tres(datos)
        ajena = Notificacion.query.first()
        assert client.post(f"/api/notificaciones/{ajena.id}/leer", headers=cabeceras(datos.usuario())).status_code == 404

    def test_limite_se_acota(self, datos):
        u = self._con_tres(datos)
        assert len(NotificacionService.listar(u, limite=0)["notificaciones"]) == 3
        assert len(NotificacionService.listar(u, limite=9999)["notificaciones"]) == 3


class TestCorreo:
    def test_solo_el_ciudadano_recibe_correo_cuando_esta_activado(self, datos, monkeypatch):
        e = _escenario(datos)
        monkeypatch.setenv("NOTIFICAR_CORREO", "1")
        monkeypatch.setenv("MAIL_USER", "siger@gmail.com")
        monkeypatch.setenv("MAIL_PASSWORD", "clave")
        enviados = []
        import utilities.correo as correo
        monkeypatch.setattr(correo, "enviar_correo", lambda destino, asunto, html, texto, **k: enviados.append((destino, html)))
        r = datos.reporte(e["ciudadano"], estado="asignado", organismo_id=datos.bomberos.id)
        NotificacionService.cambio_estado(r, e["org"], "iniciar")
        assert [d for d, _ in enviados] == [e["ciudadano"].email]
        assert r.folio in enviados[0][1]

    def test_html_escapa_el_contenido(self, datos):
        e = _escenario(datos)
        r = datos.reporte(e["ciudadano"])
        n = Notificacion(titulo="<script>x</script>", mensaje="a & b")
        html = NotificacionService._correo_html("<b>Ana</b>", r, n)
        assert "<script>" not in html and "&lt;b&gt;Ana&lt;/b&gt;" in html and "a &amp; b" in html

    def test_apagado_por_defecto(self, datos, monkeypatch):
        e = _escenario(datos)
        import utilities.correo as correo
        monkeypatch.setattr(correo, "enviar_correo", lambda *a, **k: (_ for _ in ()).throw(AssertionError("no debe enviar")))
        NotificacionService._enviar_correos(datos.reporte(e["ciudadano"]), [(e["ciudadano"], Notificacion(titulo="t", mensaje="m"))])

    def test_correo_no_configurado_o_con_error_no_rompe(self, datos, monkeypatch):
        e = _escenario(datos)
        monkeypatch.setenv("NOTIFICAR_CORREO", "1")
        r = datos.reporte(e["ciudadano"])
        NotificacionService._enviar_correos(r, [(e["ciudadano"], Notificacion(titulo="t", mensaje="m"))])
        monkeypatch.setenv("MAIL_USER", "a@b.com")
        monkeypatch.setenv("MAIL_PASSWORD", "x")
        import utilities.correo as correo
        monkeypatch.setattr(correo, "enviar_correo", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("smtp caido")))
        NotificacionService._enviar_correos(r, [(e["ciudadano"], Notificacion(titulo="t", mensaje="m"))])
