"""Perfil propio y administracion de usuarios."""
import io
import os

from tests.conftest import JPG, PASSWORD, PNG, cabeceras
from models.user import User


class TestPerfil:
    def test_obtener_mi_perfil(self, client, datos):
        u = datos.usuario(email="yo@correo.com")
        r = client.get("/api/usuarios/me", headers=cabeceras(u))
        assert r.status_code == 200 and r.get_json()["usuario"]["email"] == "yo@correo.com"
        assert r.headers["Cache-Control"] == "no-store"

    def test_actualizar_datos(self, client, datos):
        u = datos.usuario()
        r = client.put("/api/usuarios/me", headers=cabeceras(u), json={
            "nombre": "Maria", "apellido": "Lopez", "municipio": "Madrid",
            "tipo_documento": "CC", "documento": "9876543210", "telefono": "3109876543"})
        assert r.status_code == 200
        d = r.get_json()["usuario"]
        assert (d["nombre"], d["municipio"], d["documento"], d["telefono"]) == ("Maria", "Madrid", "9876543210", "3109876543")

    def test_actualizar_valida(self, client, datos):
        u = datos.usuario()
        h = cabeceras(u)
        assert client.put("/api/usuarios/me", headers=h, json={"nombre": "", "apellido": "X"}).status_code == 400
        assert client.put("/api/usuarios/me", headers=h, json={"nombre": "Ana3", "apellido": "Lopez"}).status_code == 400
        assert client.put("/api/usuarios/me", headers=h, json={"nombre": "Ana", "apellido": "Lopez", "municipio": "Inactivo"}).status_code == 400
        assert client.put("/api/usuarios/me", headers=h, json={"nombre": "Ana", "apellido": "Lopez", "telefono": "123"}).status_code == 400

    def test_documento_repetido_en_otro_usuario(self, client, datos):
        datos.usuario(tipo_documento="CC", documento="1111111111")
        u = datos.usuario()
        r = client.put("/api/usuarios/me", headers=cabeceras(u), json={
            "nombre": "Ana", "apellido": "Lopez", "tipo_documento": "CC", "documento": "1111111111"})
        assert r.status_code == 400

    def test_solo_el_ciudadano_cambia_de_municipio(self, client, datos):
        g = datos.usuario("gestor_municipal")
        r = client.put("/api/usuarios/me", headers=cabeceras(g), json={"nombre": "Ana", "apellido": "Lopez", "municipio": "Madrid"})
        assert r.get_json()["usuario"]["municipio"] == "Facatativa"


class TestCambioDeCorreo:
    def test_exige_la_contrasena_actual(self, client, datos):
        u = datos.usuario()
        h = cabeceras(u)
        assert client.put("/api/usuarios/me/email", headers=h, json={"email": "nuevo@correo.com", "password": "Mala.1234"}).status_code == 400
        assert client.put("/api/usuarios/me/email", headers=h, json={"email": "nuevo@correo.com"}).status_code == 400

    def test_cambia_el_correo(self, client, datos):
        u = datos.usuario()
        r = client.put("/api/usuarios/me/email", headers=cabeceras(u), json={"email": "Nuevo@Correo.com", "password": PASSWORD})
        assert r.status_code == 200 and r.get_json()["usuario"]["email"] == "nuevo@correo.com"

    def test_rechaza_el_mismo_o_uno_ocupado(self, client, datos):
        otro = datos.usuario(email="otro@correo.com")
        u = datos.usuario(email="yo@correo.com")
        h = cabeceras(u)
        assert "actual" in client.put("/api/usuarios/me/email", headers=h, json={"email": "yo@correo.com", "password": PASSWORD}).get_json()["error"]
        assert "existe" in client.put("/api/usuarios/me/email", headers=h, json={"email": otro.email, "password": PASSWORD}).get_json()["error"]


class TestCambioDeContrasena:
    def test_cambia_y_la_anterior_deja_de_servir(self, client, datos):
        u = datos.usuario(email="yo@correo.com")
        r = client.put("/api/usuarios/me/password", headers=cabeceras(u), json={"actual": PASSWORD, "nueva": "Nueva.5678"})
        assert r.status_code == 200 and r.headers["Cache-Control"] == "no-store"
        assert client.post("/api/auth/login", json={"email": "yo@correo.com", "password": PASSWORD}).status_code == 401
        assert client.post("/api/auth/login", json={"email": "yo@correo.com", "password": "Nueva.5678"}).status_code == 200

    def test_validaciones(self, client, datos):
        u = datos.usuario()
        h = cabeceras(u)
        put = lambda cuerpo: client.put("/api/usuarios/me/password", headers=h, json=cuerpo)
        assert put({"actual": "Mala.1234", "nueva": "Nueva.5678"}).status_code == 400
        assert put({"actual": PASSWORD, "nueva": "debil"}).status_code == 400
        assert "distinta" in put({"actual": PASSWORD, "nueva": PASSWORD}).get_json()["error"]
        assert put({"nueva": "Nueva.5678"}).status_code == 400


class TestFoto:
    def _subir(self, client, u, contenido, nombre, mime="image/png"):
        return client.post("/api/usuarios/me/foto", headers=cabeceras(u),
                           data={"foto": (io.BytesIO(contenido), nombre, mime)}, content_type="multipart/form-data")

    def test_sube_reemplaza_y_quita(self, client, datos, app):
        u = datos.usuario()
        r = self._subir(client, u, PNG, "a.png")
        assert r.status_code == 200
        primera = r.get_json()["usuario"]["foto_url"]
        carpeta = app.config["UPLOAD_FOLDER_PERFILES"]
        assert os.listdir(carpeta) == [os.path.basename(primera)]
        segunda = self._subir(client, u, JPG, "b.jpg", "image/jpeg").get_json()["usuario"]["foto_url"]
        assert os.listdir(carpeta) == [os.path.basename(segunda)]  # la anterior se borro
        r = client.delete("/api/usuarios/me/foto", headers=cabeceras(u))
        assert r.status_code == 200 and r.get_json()["usuario"]["foto_url"] is None
        assert os.listdir(carpeta) == []

    def test_quitar_sin_foto_no_falla(self, client, datos):
        u = datos.usuario()
        assert client.delete("/api/usuarios/me/foto", headers=cabeceras(u)).status_code == 200

    def test_rechazos(self, client, datos):
        u = datos.usuario()
        assert client.post("/api/usuarios/me/foto", headers=cabeceras(u)).status_code == 400
        assert self._subir(client, u, PNG, "a.exe").status_code == 400
        assert self._subir(client, u, b"no soy una imagen", "a.png").status_code == 400  # firma falsa
        assert self._subir(client, u, b"", "a.png").status_code == 400
        assert self._subir(client, u, PNG + b"0" * (5 * 1024 * 1024), "a.png").status_code == 400


class TestAdministracion:
    def _admin(self, datos):
        return datos.usuario("administrador", municipio=None)

    def test_solo_el_administrador(self, client, datos):
        c = datos.usuario()
        assert client.get("/api/usuarios", headers=cabeceras(c)).status_code == 403
        assert client.get("/api/usuarios").status_code == 401

    def test_listar_con_filtros(self, client, datos):
        admin = self._admin(datos)
        datos.usuario(email="busca@correo.com", nombre="Zacarias")
        datos.usuario("gestor_municipal", activo=False)
        h = cabeceras(admin)
        assert len(client.get("/api/usuarios", headers=h).get_json()["usuarios"]) == 3
        assert len(client.get("/api/usuarios?q=zacar", headers=h).get_json()["usuarios"]) == 1
        assert len(client.get("/api/usuarios?rol=gestor_municipal", headers=h).get_json()["usuarios"]) == 1
        assert len(client.get("/api/usuarios?estado=inactivo", headers=h).get_json()["usuarios"]) == 1
        assert len(client.get("/api/usuarios?estado=activo", headers=h).get_json()["usuarios"]) == 2
        assert client.get("/api/usuarios?rol=inventado", headers=h).status_code == 400

    def test_obtener(self, client, datos):
        admin = self._admin(datos)
        u = datos.usuario()
        assert client.get(f"/api/usuarios/{u.id}", headers=cabeceras(admin)).status_code == 200
        assert client.get("/api/usuarios/9999", headers=cabeceras(admin)).status_code == 404

    def test_actualizar_rol_y_municipio(self, client, datos):
        admin = self._admin(datos)
        u = datos.usuario()
        r = client.put(f"/api/usuarios/{u.id}", headers=cabeceras(admin),
                       json={"rol": "gestor_municipal", "municipio": "Madrid", "nombre": "Nuevo", "email": "n@correo.com"})
        d = r.get_json()["usuario"]
        assert r.status_code == 200 and (d["rol"], d["municipio"], d["nombre"], d["email"]) == ("gestor_municipal", "Madrid", "Nuevo", "n@correo.com")

    def test_organismo_requiere_organismo_y_municipio_que_opere(self, client, datos):
        admin = self._admin(datos)
        u = datos.usuario()
        h = cabeceras(admin)
        put = lambda cuerpo: client.put(f"/api/usuarios/{u.id}", headers=h, json=cuerpo)
        assert put({"rol": "organismo_atencion"}).status_code == 400  # sin organismo
        assert put({"rol": "organismo_atencion", "organismo_id": 9999}).status_code == 400
        assert put({"rol": "organismo_atencion", "organismo_id": "abc"}).status_code == 400
        assert put({"rol": "organismo_atencion", "organismo_id": datos.bomberos.id, "municipio": "Madrid"}).status_code == 400
        ok = put({"rol": "organismo_atencion", "organismo_id": datos.bomberos.id, "municipio": "Facatativa"})
        assert ok.status_code == 200 and ok.get_json()["usuario"]["organismo"] == "Bomberos"
        # al dejar de ser organismo se limpia el organismo
        volver = put({"rol": "ciudadano", "organismo_id": ""})
        assert volver.get_json()["usuario"]["organismo_id"] is None

    def test_gestor_exige_municipio(self, client, datos):
        admin = self._admin(datos)
        u = datos.usuario()
        r = client.put(f"/api/usuarios/{u.id}", headers=cabeceras(admin), json={"rol": "gestor_municipal", "municipio": ""})
        assert r.status_code == 400

    def test_validaciones_de_actualizacion(self, client, datos):
        admin = self._admin(datos)
        otro = datos.usuario(email="otro@correo.com")
        u = datos.usuario()
        h = cabeceras(admin)
        put = lambda uid, cuerpo: client.put(f"/api/usuarios/{uid}", headers=h, json=cuerpo)
        assert put(9999, {"nombre": "Ana"}).status_code == 400
        assert put(u.id, {"rol": "inventado"}).status_code == 400
        assert put(u.id, {"municipio": "Narnia"}).status_code == 400
        assert put(u.id, {"email": otro.email}).status_code == 400
        assert put(admin.id, {"rol": "ciudadano"}).status_code == 400  # no puede quitarse su rol

    def test_cambiar_estado(self, client, datos):
        admin = self._admin(datos)
        u = datos.usuario()
        h = cabeceras(admin)
        assert client.patch(f"/api/usuarios/{u.id}/estado", headers=h, json={"activo": False}).get_json()["usuario"]["activo"] is False
        assert client.patch(f"/api/usuarios/{u.id}/estado", headers=h, json={"activo": "no"}).status_code == 400
        assert client.patch(f"/api/usuarios/{admin.id}/estado", headers=h, json={"activo": False}).status_code == 400
        assert client.patch("/api/usuarios/9999/estado", headers=h, json={"activo": True}).status_code == 400
