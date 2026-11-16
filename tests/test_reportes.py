"""Reportes de emergencia: creacion, consulta, asignacion, atencion, apoyos y evidencias."""
import io
import os

from models.reporte import Evidencia, Reporte, ReporteHistorial
from services.reporte_service import ReporteService
from tests.conftest import JPG, PDF, PNG, cabeceras


def _formulario(datos, **cambios):
    f = {"tipo": "Incendio", "municipio_id": str(datos.facatativa.id), "direccion": "Calle 1 # 2-3",
         "descripcion": "Hay humo denso saliendo de la bodega", "afectados": "3", "heridos": "1",
         "latitud": "4.8", "longitud": "-74.3"}
    f.update(cambios)
    return {k: v for k, v in f.items() if v is not None}


def _post(client, u, datos, evidencias=None, **cambios):
    data = _formulario(datos, **cambios)
    if evidencias:
        data["evidencias"] = evidencias
    return client.post("/api/reportes", headers=cabeceras(u), data=data, content_type="multipart/form-data")


class TestConfiguracion:
    def test_devuelve_tipos_y_limites(self, client, datos):
        r = client.get("/api/reportes/configuracion", headers=cabeceras(datos.usuario()))
        cuerpo = r.get_json()
        assert r.status_code == 200
        assert {"nombre": "Incendio", "prioridad": "alta"} in cuerpo["tipos"]
        assert cuerpo["limites"]["max_evidencias"] == 5 and "png" in cuerpo["extensiones"]


class TestCrear:
    def test_crea_con_evidencias_guardadas_en_disco(self, client, datos, app):
        u = datos.usuario()
        r = _post(client, u, datos, evidencias=[(io.BytesIO(PNG), "../foto mala.png", "image/png"),
                                                (io.BytesIO(PDF), "acta.pdf", "application/pdf")])
        assert r.status_code == 201
        rep = r.get_json()["reporte"]
        assert rep["folio"].startswith("RPT-") and rep["estado"] == "pendiente" and rep["prioridad"] == "alta"
        assert len(rep["evidencias"]) == 2
        carpeta = app.config["UPLOAD_FOLDER"]
        assert len(os.listdir(carpeta)) == 2
        assert all(".." not in n and "/" not in n for n in os.listdir(carpeta))  # nombre saneado

    def test_folios_consecutivos(self, client, datos):
        u = datos.usuario()
        a = _post(client, u, datos).get_json()["reporte"]["folio"]
        b = _post(client, u, datos).get_json()["reporte"]["folio"]
        assert int(b[-5:]) == int(a[-5:]) + 1

    def test_solo_el_ciudadano_crea(self, client, datos):
        assert _post(client, datos.usuario("gestor_municipal"), datos).status_code == 403

    def test_la_prioridad_la_define_el_tipo_y_no_el_cliente(self, client, datos):
        u = datos.usuario()
        r = _post(client, u, datos, tipo="Emergencia medica", prioridad="baja")
        assert r.get_json()["reporte"]["prioridad"] == "critica"

    def test_validaciones_de_campos(self, client, datos):
        u = datos.usuario()
        casos = [
            {"tipo": "Marciano"}, {"tipo": None}, {"municipio_id": None}, {"municipio_id": str(datos.inactivo.id)},
            {"direccion": "  "}, {"direccion": "x" * 201}, {"descripcion": "corta"}, {"descripcion": "x" * 2001},
            {"afectados": "abc"}, {"afectados": "-1"}, {"afectados": "100001"},
            {"heridos": "abc"}, {"heridos": "-1"}, {"afectados": "1", "heridos": "5"},
            {"latitud": "4.8", "longitud": None}, {"latitud": "40.0", "longitud": "-74.3"},
        ]
        for caso in casos:
            r = _post(client, u, datos, **caso)
            assert r.status_code == 400, caso
        assert Reporte.query.count() == 0

    def test_validaciones_de_archivos(self, client, datos):
        u = datos.usuario()
        malos = [
            [(io.BytesIO(b"x"), "virus.exe", "application/octet-stream")],
            [(io.BytesIO(PNG), "falso.png", "text/html")],
            [(io.BytesIO(b"no es png"), "falso.png", "image/png")],
            [(io.BytesIO(b""), "vacio.png", "image/png")],
            [(io.BytesIO(PNG + b"0" * (10 * 1024 * 1024)), "grande.png", "image/png")],
            [(io.BytesIO(PNG), f"f{i}.png", "image/png") for i in range(6)],
        ]
        for evidencias in malos:
            assert _post(client, u, datos, evidencias=evidencias).status_code == 400

    def test_firmas_validas_de_cada_formato(self, client, datos):
        u = datos.usuario()
        buenos = [(PNG, "a.png", "image/png"), (JPG, "a.jpg", "image/jpeg"), (b"GIF89a" + b"0" * 20, "a.gif", "image/gif"),
                  (PDF, "a.pdf", "application/pdf"), (b"\x00\x00\x00\x18ftypmp42" + b"0" * 20, "a.mp4", "video/mp4")]
        for contenido, nombre, mime in buenos:
            assert _post(client, u, datos, evidencias=[(io.BytesIO(contenido), nombre, mime)]).status_code == 201, nombre

    def test_si_falla_el_guardado_no_queda_nada(self, client, datos, monkeypatch, app):
        u = datos.usuario()
        from werkzeug.datastructures import FileStorage
        monkeypatch.setattr(FileStorage, "save", lambda self, destino, *a, **k: (_ for _ in ()).throw(OSError("disco lleno")))
        r = _post(client, u, datos, evidencias=[(io.BytesIO(PNG), "a.png", "image/png")])
        assert r.status_code == 400 and "evidencias" in r.get_json()["error"]
        assert Reporte.query.count() == 0

    def test_sin_coordenadas_es_valido(self, client, datos):
        assert _post(client, datos.usuario(), datos, latitud=None, longitud=None).status_code == 201


class TestConsultas:
    def test_mis_reportes(self, client, datos):
        yo, otro = datos.usuario(), datos.usuario()
        datos.reporte(yo)
        datos.reporte(otro)
        r = client.get("/api/reportes", headers=cabeceras(yo))
        assert len(r.get_json()["reportes"]) == 1
        assert client.get("/api/reportes", headers=cabeceras(datos.usuario("gestor_municipal"))).status_code == 403

    def test_detalle_con_permisos(self, client, datos):
        dueno, otro = datos.usuario(), datos.usuario()
        gestor = datos.usuario("gestor_municipal")
        gestor_madrid = datos.usuario("gestor_municipal", municipio="madrid")
        admin = datos.usuario("administrador", municipio=None)
        r = datos.reporte(dueno)
        url = f"/api/reportes/{r.id}"
        assert client.get(url, headers=cabeceras(dueno)).status_code == 200
        assert client.get(url, headers=cabeceras(gestor)).status_code == 200
        assert client.get(url, headers=cabeceras(admin)).status_code == 200
        assert client.get(url, headers=cabeceras(otro)).status_code == 403
        assert client.get(url, headers=cabeceras(gestor_madrid)).status_code == 403
        assert client.get("/api/reportes/9999", headers=cabeceras(admin)).status_code == 404

    def test_el_gestor_ve_acciones_y_organismos_disponibles(self, client, datos):
        gestor = datos.usuario("gestor_municipal")
        r = datos.reporte(datos.usuario())
        d = client.get(f"/api/reportes/{r.id}", headers=cabeceras(gestor)).get_json()["reporte"]
        assert d["acciones"]["asignar"] and d["acciones"]["descartar"] and not d["acciones"]["iniciar"]
        nombres = [o["nombre"] for o in d["organismos_disponibles"]]
        assert nombres[0] == "Bomberos" and "Defensa Civil" not in nombres  # sugerido primero; inactivo fuera

    def test_gestion_filtra_por_municipio_y_filtros(self, client, datos):
        c = datos.usuario()
        gestor = datos.usuario("gestor_municipal")
        admin = datos.usuario("administrador", municipio=None)
        datos.reporte(c, tipo="Incendio", direccion="Calle Luna")
        datos.reporte(c, tipo="Inundacion", prioridad="media", estado="asignado")
        datos.reporte(c, municipio=datos.madrid)
        h = cabeceras(gestor)
        lista = lambda q="", h=h: client.get("/api/reportes/gestion" + q, headers=h).get_json()["reportes"]
        assert len(lista()) == 2  # el de Madrid no se ve
        assert len(lista(f"?municipio_id={datos.madrid.id}")) == 2  # el gestor no puede salirse de su municipio
        assert len(lista("?q=luna")) == 1 and len(lista("?tipo=Inundacion")) == 1
        assert len(lista("?estado=asignado")) == 1 and len(lista("?prioridad=media")) == 1
        assert len(lista("?desde=2000-01-01&hasta=2100-01-01")) == 2
        assert len(lista("?desde=2100-01-01")) == 0
        assert len(lista(h=cabeceras(admin))) == 3
        assert len(lista(f"?municipio_id={datos.madrid.id}", h=cabeceras(admin))) == 1
        assert client.get("/api/reportes/gestion?desde=mal", headers=h).status_code == 400
        assert client.get("/api/reportes/gestion", headers=cabeceras(c)).status_code == 403

    def test_gestion_exige_municipio_y_organismo(self, client, datos):
        sin_municipio = datos.usuario("gestor_municipal", municipio=None)
        assert client.get("/api/reportes/gestion", headers=cabeceras(sin_municipio)).status_code == 400
        sin_organismo = datos.usuario("organismo_atencion")
        assert client.get("/api/reportes/gestion", headers=cabeceras(sin_organismo)).status_code == 400

    def test_organismo_ve_solo_lo_asignado_y_marca_apoyo(self, client, datos):
        c = datos.usuario()
        org = datos.usuario("organismo_atencion", organismo=datos.bomberos)
        propio = datos.reporte(c, estado="asignado", organismo_id=datos.bomberos.id)
        apoyo = datos.reporte(c, estado="asignado", organismo_id=datos.cruz_roja.id)
        apoyo.apoyos = [datos.bomberos]
        datos.reporte(c, estado="asignado", organismo_id=datos.cruz_roja.id)  # no le corresponde
        datos.db.session.commit()
        h = cabeceras(org)
        lista = client.get("/api/reportes/gestion", headers=h).get_json()["reportes"]
        assert {r["id"]: r["es_apoyo"] for r in lista} == {propio.id: False, apoyo.id: True}
        det = client.get(f"/api/reportes/{apoyo.id}", headers=h).get_json()["reporte"]
        assert det["es_apoyo"] and not det["acciones"]["iniciar"]


class TestAsignar:
    def _gestor_y_reporte(self, datos, **extra):
        return datos.usuario("gestor_municipal"), datos.reporte(datos.usuario(), **extra)

    def test_asigna_y_deja_historial(self, client, datos):
        gestor, r = self._gestor_y_reporte(datos)
        res = client.post(f"/api/reportes/{r.id}/asignar", headers=cabeceras(gestor),
                          json={"organismo_id": datos.bomberos.id, "prioridad": "critica", "comentario": "Urgente"})
        d = res.get_json()["reporte"]
        assert res.status_code == 200 and d["estado"] == "asignado" and d["prioridad"] == "critica"
        assert d["organismo"] == "Bomberos" and d["asignado_por"]
        assert d["historial"][0]["accion"] == "asignar" and "Urgente" in d["historial"][0]["comentario"]

    def test_prioridad_automatica_y_variables(self, client, datos):
        gestor, r = self._gestor_y_reporte(datos, prioridad="baja", tipo="Otro", afectados=30, heridos=11)
        res = client.post(f"/api/reportes/{r.id}/asignar", headers=cabeceras(gestor), json={
            "organismo_id": datos.bomberos.id, "prioridad": "auto", "vias_afectadas": "2",
            "area_afectada": "2000", "riesgo_propagacion": "alto"})
        d = res.get_json()["reporte"]
        assert d["prioridad"] == "critica" and d["vias_afectadas"] == 2 and d["riesgo_propagacion"] == "alto"
        assert "pts" in d["historial"][0]["comentario"]

    def test_reasignar_y_repetir(self, client, datos):
        gestor, r = self._gestor_y_reporte(datos)
        h = cabeceras(gestor)
        url = f"/api/reportes/{r.id}/asignar"
        client.post(url, headers=h, json={"organismo_id": datos.bomberos.id})
        assert client.post(url, headers=h, json={"organismo_id": datos.bomberos.id}).status_code == 400  # sin cambios
        res = client.post(url, headers=h, json={"organismo_id": datos.cruz_roja.id})
        assert res.status_code == 200 and res.get_json()["reporte"]["historial"][-1]["accion"] == "reasignar"
        assert "Reasignado de Bomberos a Cruz Roja" in res.get_json()["reporte"]["historial"][-1]["comentario"]
        res = client.post(url, headers=h, json={"organismo_id": datos.cruz_roja.id, "comentario": "Nota nueva"})
        assert "Datos actualizados" in res.get_json()["reporte"]["historial"][-1]["comentario"]

    def test_rechazos(self, client, datos):
        gestor, r = self._gestor_y_reporte(datos)
        h = cabeceras(gestor)
        url = f"/api/reportes/{r.id}/asignar"
        post = lambda c: client.post(url, headers=h, json=c)
        assert post({}).status_code == 400
        assert post({"organismo_id": "x"}).status_code == 400
        assert post({"organismo_id": datos.defensa.id}).status_code == 400  # inactivo
        assert post({"organismo_id": 9999}).status_code == 400
        assert post({"organismo_id": datos.bomberos.id, "prioridad": "enorme"}).status_code == 400
        assert post({"organismo_id": datos.bomberos.id, "riesgo_propagacion": "raro"}).status_code == 400
        assert post({"organismo_id": datos.bomberos.id, "vias_afectadas": "abc"}).status_code == 400
        assert post({"organismo_id": datos.bomberos.id, "vias_afectadas": "101"}).status_code == 400
        assert post({"organismo_id": datos.bomberos.id, "comentario": "x" * 301}).status_code == 400
        # un organismo que no opera en el municipio del reporte
        assert client.post(f"/api/reportes/{datos.reporte(datos.usuario(), municipio=datos.madrid).id}/asignar",
                           headers=cabeceras(datos.usuario("administrador", municipio=None)),
                           json={"organismo_id": datos.bomberos.id}).status_code == 400

    def test_permisos(self, client, datos):
        _, r = self._gestor_y_reporte(datos)
        ciudadano = datos.usuario()
        gestor_madrid = datos.usuario("gestor_municipal", municipio="madrid")
        url = f"/api/reportes/{r.id}/asignar"
        assert client.post(url, headers=cabeceras(ciudadano), json={"organismo_id": datos.bomberos.id}).status_code == 403
        assert client.post(url, headers=cabeceras(gestor_madrid), json={"organismo_id": datos.bomberos.id}).status_code == 403
        assert client.post("/api/reportes/9999/asignar", headers=cabeceras(datos.usuario("administrador", municipio=None)),
                           json={"organismo_id": datos.bomberos.id}).status_code == 404

    def test_no_se_asigna_un_reporte_en_atencion(self, client, datos):
        gestor, r = self._gestor_y_reporte(datos, estado="en_atencion")
        res = client.post(f"/api/reportes/{r.id}/asignar", headers=cabeceras(gestor), json={"organismo_id": datos.bomberos.id})
        assert res.status_code == 400


class TestCicloDeAtencion:
    def _asignado(self, datos):
        gestor = datos.usuario("gestor_municipal")
        org = datos.usuario("organismo_atencion", organismo=datos.bomberos)
        ciudadano = datos.usuario()
        r = datos.reporte(ciudadano, estado="asignado", organismo_id=datos.bomberos.id)
        return gestor, org, ciudadano, r

    def _estado(self, client, r, usuario, accion, **extra):
        return client.post(f"/api/reportes/{r.id}/estado", headers=cabeceras(usuario), json={"accion": accion, **extra})

    def test_flujo_completo_hasta_el_cierre(self, client, datos):
        gestor, org, ciudadano, r = self._asignado(datos)
        assert self._estado(client, r, org, "iniciar").get_json()["reporte"]["estado"] == "en_atencion"
        assert self._estado(client, r, org, "resolver", comentario="Controlado").get_json()["reporte"]["estado"] == "resuelto"
        assert self._estado(client, r, gestor, "cerrar").get_json()["reporte"]["estado"] == "cerrado"
        acciones = [h.accion for h in ReporteHistorial.query.order_by(ReporteHistorial.id)]
        assert acciones == ["iniciar", "resolver", "cerrar"]

    def test_devolver_vuelve_al_gestor(self, client, datos):
        gestor, org, _, r = self._asignado(datos)
        r.apoyos = [datos.cruz_roja]
        datos.db.session.commit()
        assert self._estado(client, r, org, "devolver").status_code == 400  # motivo obligatorio
        d = self._estado(client, r, org, "devolver", comentario="No tenemos unidades").get_json()["reporte"]
        assert d["estado"] == "pendiente" and d["organismo_id"] is None and d["apoyos"] == []

    def test_descartar_exige_motivo(self, client, datos):
        gestor = datos.usuario("gestor_municipal")
        r = datos.reporte(datos.usuario())
        assert self._estado(client, r, gestor, "descartar").status_code == 400
        assert self._estado(client, r, gestor, "descartar", comentario="Falsa alarma").get_json()["reporte"]["estado"] == "descartado"

    def test_acciones_no_disponibles(self, client, datos):
        gestor, org, ciudadano, r = self._asignado(datos)
        assert self._estado(client, r, org, "inventada").status_code == 400
        assert self._estado(client, r, org, "resolver").status_code == 400  # aun no inicia
        assert self._estado(client, r, ciudadano, "iniciar").status_code == 400
        assert self._estado(client, r, datos.usuario("gestor_municipal", municipio="madrid"), "descartar").status_code == 403
        assert self._estado(client, r, gestor, "iniciar").status_code == 400  # el gestor no atiende

    def test_el_ciudadano_no_ve_los_movimientos_internos(self, client, datos):
        gestor, org, ciudadano, r = self._asignado(datos)
        self._estado(client, r, org, "devolver", comentario="Sin unidades disponibles")
        client.post(f"/api/reportes/{r.id}/asignar", headers=cabeceras(gestor),
                    json={"organismo_id": datos.bomberos.id, "comentario": "Atender ya. Nota interna"})
        d = client.get(f"/api/reportes/{r.id}", headers=cabeceras(ciudadano)).get_json()["reporte"]
        assert "devolver" not in [h["accion"] for h in d["historial"]]
        assert "Nota interna" not in str([h["comentario"] for h in d["historial"]])
        interno = client.get(f"/api/reportes/{r.id}", headers=cabeceras(gestor)).get_json()["reporte"]
        assert "devolver" in [h["accion"] for h in interno["historial"]]


class TestApoyoYTipo:
    def _en_atencion(self, datos):
        gestor = datos.usuario("gestor_municipal")
        r = datos.reporte(datos.usuario(), estado="asignado", organismo_id=datos.bomberos.id)
        return gestor, r

    def test_definir_y_retirar_apoyos(self, client, datos):
        gestor, r = self._en_atencion(datos)
        h = cabeceras(gestor)
        url = f"/api/reportes/{r.id}/apoyo"
        d = client.post(url, headers=h, json={"organismo_ids": [datos.cruz_roja.id]}).get_json()["reporte"]
        assert [o["nombre"] for o in d["apoyos"]] == ["Cruz Roja"] and "agregado" in d["historial"][-1]["comentario"]
        d = client.post(url, headers=h, json={"organismo_ids": []}).get_json()["reporte"]
        assert d["apoyos"] == [] and "retirado" in d["historial"][-1]["comentario"]

    def test_rechazos_de_apoyo(self, client, datos):
        gestor, r = self._en_atencion(datos)
        h = cabeceras(gestor)
        post = lambda c: client.post(f"/api/reportes/{r.id}/apoyo", headers=h, json=c)
        assert post({"organismo_ids": []}).status_code == 400  # sin cambios
        assert post({"organismo_ids": "x"}).status_code == 400
        assert post({"organismo_ids": ["a"]}).status_code == 400
        assert post({"organismo_ids": [datos.bomberos.id]}).status_code == 400  # es el principal
        assert post({"organismo_ids": [9999]}).status_code == 400
        assert post({"organismo_ids": [datos.defensa.id]}).status_code == 400  # inactivo
        assert post({"organismo_ids": list(range(1, 8))}).status_code == 400  # demasiados
        assert client.post(f"/api/reportes/{r.id}/apoyo", headers=cabeceras(datos.usuario()), json={}).status_code == 403
        pendiente = datos.reporte(datos.usuario())
        assert client.post(f"/api/reportes/{pendiente.id}/apoyo", headers=h, json={"organismo_ids": []}).status_code == 400

    def test_cambiar_tipo(self, client, datos):
        gestor, r = self._en_atencion(datos)
        h = cabeceras(gestor)
        url = f"/api/reportes/{r.id}/tipo"
        post = lambda c: client.post(url, headers=h, json=c)
        assert post({"tipo": "Inundacion"}).status_code == 400  # motivo obligatorio
        assert post({"tipo": "Marciano", "comentario": "Motivo valido"}).status_code == 400
        assert post({"tipo": "Incendio", "comentario": "Motivo valido"}).status_code == 400  # ya es de ese tipo
        d = post({"tipo": "Inundacion", "comentario": "Lo corrigio el gestor"}).get_json()["reporte"]
        assert d["tipo"] == "Inundacion" and "Incendio" in d["historial"][-1]["comentario"]
        assert client.post(url, headers=cabeceras(datos.usuario()), json={"tipo": "Otro", "comentario": "Motivo valido"}).status_code == 403
        r.estado = "cerrado"
        datos.db.session.commit()
        assert post({"tipo": "Otro", "comentario": "Motivo valido"}).status_code == 400


class TestPublico:
    def test_mapa_para_ciudadanos_excluye_los_propios_y_recorta_datos(self, client, datos):
        yo, otro = datos.usuario(), datos.usuario()
        datos.reporte(otro, estado="asignado", latitud=4.81234, longitud=-74.31234)
        datos.reporte(yo, estado="asignado", latitud=4.8, longitud=-74.3)           # propio
        datos.reporte(otro, estado="pendiente", latitud=4.8, longitud=-74.3)        # sin aceptar
        datos.reporte(otro, estado="asignado", latitud=None, longitud=None)         # sin coordenadas
        lista = client.get("/api/reportes/publico", headers=cabeceras(yo)).get_json()["reportes"]
        assert len(lista) == 1
        assert lista[0]["latitud"] == 4.812 and "folio" not in lista[0] and "descripcion" not in lista[0]

    def test_mapa_publico_sin_sesion(self, client, datos):
        datos.reporte(datos.usuario(), estado="en_atencion", latitud=4.81234, longitud=-74.31234)
        datos.reporte(datos.usuario(), estado="pendiente", latitud=4.8, longitud=-74.3)
        r = client.get("/api/publico/mapa")
        assert r.status_code == 200 and r.headers["Cache-Control"] == "no-store"
        lista = r.get_json()["reportes"]
        assert len(lista) == 1 and set(lista[0]) == {"id", "tipo", "prioridad", "estado", "latitud", "longitud", "municipio", "fecha_hora"}


class TestEvidencias:
    def _con_evidencia(self, datos, app, contenido=PNG, en_disco=True):
        dueno = datos.usuario()
        r = datos.reporte(dueno)
        carpeta = app.config["UPLOAD_FOLDER"]
        os.makedirs(carpeta, exist_ok=True)
        if en_disco:
            with open(os.path.join(carpeta, "ev.png"), "wb") as f:
                f.write(contenido)
        e = Evidencia(reporte_id=r.id, nombre_archivo="ev.png", ruta_archivo="../../etc/ev.png")
        datos.db.session.add(e)
        datos.db.session.commit()
        return dueno, e

    def test_el_dueno_descarga_con_cabeceras_seguras(self, client, datos, app):
        dueno, e = self._con_evidencia(datos, app)
        r = client.get(f"/api/reportes/evidencias/{e.id}", headers=cabeceras(dueno))
        assert r.status_code == 200 and r.data == PNG
        assert r.headers["X-Content-Type-Options"] == "nosniff" and "private" in r.headers["Cache-Control"]

    def test_otro_ciudadano_no_puede(self, client, datos, app):
        _, e = self._con_evidencia(datos, app)
        assert client.get(f"/api/reportes/evidencias/{e.id}", headers=cabeceras(datos.usuario())).status_code == 403
        assert client.get("/api/reportes/evidencias/9999", headers=cabeceras(datos.usuario())).status_code == 404
        assert client.get(f"/api/reportes/evidencias/{e.id}").status_code == 401

    def test_archivo_borrado_del_disco(self, client, datos, app):
        dueno, e = self._con_evidencia(datos, app, en_disco=False)
        assert client.get(f"/api/reportes/evidencias/{e.id}", headers=cabeceras(dueno)).status_code == 404


class TestServicio:
    def test_generar_folio_se_recupera_de_un_folio_raro(self, datos):
        from utilities.fechas import ahora
        datos.reporte(datos.usuario(), folio=f"RPT-{ahora().year}-ABCDE")
        assert ReporteService._generar_folio().startswith(f"RPT-{ahora().year}-")

    def test_dto_sin_relaciones(self, datos):
        r = datos.reporte(datos.usuario())
        assert ReporteService._to_dto(r).to_dict()["evidencias"] == []
