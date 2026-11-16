"""Municipios y organismos (solo administrador, salvo el listado de municipios activos)."""
from tests.conftest import cabeceras


def _admin(datos):
    return cabeceras(datos.usuario("administrador", municipio=None))


class TestMunicipios:
    def test_activos_para_cualquier_usuario(self, client, datos):
        r = client.get("/api/municipios/activos", headers=cabeceras(datos.usuario()))
        assert [m["nombre"] for m in r.get_json()["municipios"]] == ["Facatativa", "Madrid"]

    def test_el_resto_es_solo_admin(self, client, datos):
        assert client.get("/api/municipios", headers=cabeceras(datos.usuario())).status_code == 403

    def test_listar_con_filtros(self, client, datos):
        h = _admin(datos)
        assert len(client.get("/api/municipios", headers=h).get_json()["municipios"]) == 3
        assert len(client.get("/api/municipios?q=mad", headers=h).get_json()["municipios"]) == 1
        assert len(client.get("/api/municipios?estado=inactivo", headers=h).get_json()["municipios"]) == 1
        assert len(client.get("/api/municipios?estado=activo", headers=h).get_json()["municipios"]) == 2

    def test_crear_y_duplicados(self, client, datos):
        h = _admin(datos)
        r = client.post("/api/municipios", headers=h, json={"codigo": "25286", "nombre": "Funza"})
        assert r.status_code == 201 and r.get_json()["municipio"]["activo"] is True
        assert client.post("/api/municipios", headers=h, json={"codigo": "25286", "nombre": "Otro"}).status_code == 400
        assert client.post("/api/municipios", headers=h, json={"codigo": "1", "nombre": "funza"}).status_code == 400
        assert client.post("/api/municipios", headers=h, json={"codigo": "", "nombre": ""}).status_code == 400

    def test_obtener_actualizar_y_estado(self, client, datos):
        h = _admin(datos)
        mid = datos.madrid.id
        assert client.get(f"/api/municipios/{mid}", headers=h).status_code == 200
        assert client.get("/api/municipios/9999", headers=h).status_code == 404
        r = client.put(f"/api/municipios/{mid}", headers=h, json={"codigo": "NEW", "nombre": "Madrid Nuevo"})
        assert r.get_json()["municipio"]["nombre"] == "Madrid Nuevo"
        assert client.put(f"/api/municipios/{mid}", headers=h, json={"nombre": "Facatativa"}).status_code == 400
        assert client.put(f"/api/municipios/{mid}", headers=h, json={"codigo": "25269"}).status_code == 400
        assert client.put("/api/municipios/9999", headers=h, json={"nombre": "X"}).status_code == 400
        assert client.patch(f"/api/municipios/{mid}/estado", headers=h, json={"activo": False}).get_json()["municipio"]["activo"] is False
        assert client.patch(f"/api/municipios/{mid}/estado", headers=h, json={"activo": "x"}).status_code == 400
        assert client.patch("/api/municipios/9999/estado", headers=h, json={"activo": True}).status_code == 400


class TestOrganismos:
    def test_listar_con_filtros(self, client, datos):
        h = _admin(datos)
        assert len(client.get("/api/organismos", headers=h).get_json()["organismos"]) == 3
        assert len(client.get("/api/organismos?q=cruz", headers=h).get_json()["organismos"]) == 1
        assert len(client.get("/api/organismos?estado=inactivo", headers=h).get_json()["organismos"]) == 1
        assert len(client.get("/api/organismos?estado=activo", headers=h).get_json()["organismos"]) == 2

    def test_crear_con_municipios(self, client, datos):
        h = _admin(datos)
        r = client.post("/api/organismos", headers=h, json={
            "codigo": "POL", "nombre": "Policia", "tipo": " Seguridad ", "municipios": [datos.madrid.id, datos.madrid.id]})
        d = r.get_json()["organismo"]
        assert r.status_code == 201 and d["tipo"] == "Seguridad" and [m["nombre"] for m in d["municipios"]] == ["Madrid"]

    def test_crear_validaciones(self, client, datos):
        h = _admin(datos)
        post = lambda c: client.post("/api/organismos", headers=h, json=c)
        assert post({"codigo": "", "nombre": ""}).status_code == 400
        assert post({"codigo": "bom", "nombre": "Nuevo"}).status_code == 400
        assert post({"codigo": "NEW", "nombre": "bomberos"}).status_code == 400
        assert post({"codigo": "NEW", "nombre": "Nuevo", "municipios": [9999]}).status_code == 400

    def test_obtener_actualizar_estado_y_municipios(self, client, datos):
        h = _admin(datos)
        oid = datos.bomberos.id
        assert client.get(f"/api/organismos/{oid}", headers=h).status_code == 200
        assert client.get("/api/organismos/9999", headers=h).status_code == 404
        r = client.put(f"/api/organismos/{oid}", headers=h, json={"codigo": "BMB", "nombre": "Bomberos Voluntarios", "tipo": ""})
        d = r.get_json()["organismo"]
        assert (d["codigo"], d["nombre"], d["tipo"]) == ("BMB", "Bomberos Voluntarios", None)
        assert client.put(f"/api/organismos/{oid}", headers=h, json={"nombre": "Cruz Roja"}).status_code == 400
        assert client.put(f"/api/organismos/{oid}", headers=h, json={"codigo": "CRC"}).status_code == 400
        assert client.put("/api/organismos/9999", headers=h, json={"nombre": "X"}).status_code == 400
        assert client.patch(f"/api/organismos/{oid}/estado", headers=h, json={"activo": False}).get_json()["organismo"]["activo"] is False
        assert client.patch(f"/api/organismos/{oid}/estado", headers=h, json={"activo": 1}).status_code == 400
        assert client.patch("/api/organismos/9999/estado", headers=h, json={"activo": True}).status_code == 400
        r = client.put(f"/api/organismos/{oid}/municipios", headers=h, json={"municipios": [datos.madrid.id]})
        assert [m["nombre"] for m in r.get_json()["organismo"]["municipios"]] == ["Madrid"]
        assert client.put(f"/api/organismos/{oid}/municipios", headers=h, json={"municipios": "no"}).status_code == 400
        assert client.put(f"/api/organismos/{oid}/municipios", headers=h, json={"municipios": [9999]}).status_code == 400
        assert client.put("/api/organismos/9999/municipios", headers=h, json={"municipios": []}).status_code == 400
