import pytest
from flask import Flask, jsonify

from tests.conftest import PASSWORD
from utilities.seguridad import aplicar_seguridad, es_host_local, llego_por_http, protocolo_cliente, url_https

HTTP = {"X-Forwarded-Proto": "http"}
HTTPS = {"X-Forwarded-Proto": "https"}


@pytest.fixture
def mini():
    app = Flask(__name__)
    aplicar_seguridad(app, rutas_sensibles=("/secreto",))

    @app.route("/secreto", methods=["GET", "POST"])
    def secreto():
        return jsonify(ok=True)

    @app.route("/publico", methods=["GET", "POST"])
    def publico():
        return jsonify(ok=True)

    return app.test_client()


class TestAyudas:
    @pytest.mark.parametrize("host,esperado", [
        ("localhost", True), ("localhost:5001", True), ("127.0.0.1:5000", True), ("[::1]:5000", True),
        ("siger.azurewebsites.net", False), ("", False), (None, False), ("localhost.evil.com", False),
    ])
    def test_es_host_local(self, host, esperado):
        assert es_host_local(host) is esperado

    def test_url_https(self):
        assert url_https("http://a.com/x?y=1") == "https://a.com/x?y=1"
        assert url_https("HTTP://a.com") == "https://a.com"
        assert url_https("https://a.com") == "https://a.com"

    def test_protocolo_y_http(self, app):
        with app.test_request_context("/", headers={"X-Forwarded-Proto": "https, http"}):
            from flask import request
            assert protocolo_cliente(request) == "https" and not llego_por_http(request)
        with app.test_request_context("/", headers=HTTP):
            from flask import request
            assert llego_por_http(request)
        with app.test_request_context("/"):
            from flask import request
            assert protocolo_cliente(request) == "http" and not llego_por_http(request)


class TestHttps:
    def test_get_por_http_redirige_a_https(self, mini):
        r = mini.get("/publico?a=1", headers=HTTP)
        assert r.status_code == 301 and r.headers["Location"] == "https://localhost/publico?a=1"

    def test_post_por_http_se_rechaza_sin_procesarlo(self, mini):
        r = mini.post("/secreto", headers=HTTP, json={"password": PASSWORD})
        assert r.status_code == 426 and "HTTPS" in r.get_json()["error"]

    def test_por_https_pasa_y_envia_hsts(self, mini):
        r = mini.post("/publico", headers=HTTPS, json={})
        assert r.status_code == 200 and "max-age=31536000" in r.headers["Strict-Transport-Security"]

    def test_sin_proxy_no_se_bloquea_nada_y_no_hay_hsts(self, mini):
        r = mini.get("/publico")
        assert r.status_code == 200 and "Strict-Transport-Security" not in r.headers

    def test_se_puede_apagar_para_depurar(self, mini, monkeypatch):
        monkeypatch.setenv("FORCE_HTTPS", "0")
        assert mini.post("/secreto", headers=HTTP, json={}).status_code == 200


class TestCabeceras:
    def test_cabeceras_basicas(self, mini):
        h = mini.get("/publico").headers
        assert h["X-Content-Type-Options"] == "nosniff" and h["X-Frame-Options"] == "DENY" and h["Referrer-Policy"] == "same-origin"

    def test_no_store_solo_en_rutas_sensibles(self, mini):
        assert mini.get("/secreto").headers["Cache-Control"] == "no-store"
        assert "Cache-Control" not in mini.get("/publico").headers

    def test_sin_rutas_sensibles_no_toca_la_cache(self):
        app = Flask(__name__)
        aplicar_seguridad(app)
        app.add_url_rule("/x", "x", lambda: "ok")
        assert "Cache-Control" not in app.test_client().get("/x").headers


class TestAplicacionReal:
    def test_login_por_http_nunca_se_procesa(self, client, datos):
        datos.usuario(email="ok@correo.com")
        r = client.post("/api/auth/login", headers=HTTP, json={"email": "ok@correo.com", "password": PASSWORD})
        assert r.status_code == 426 and "token" not in r.get_data(as_text=True)

    def test_login_por_https_funciona_y_no_se_cachea(self, client, datos):
        datos.usuario(email="ok@correo.com")
        r = client.post("/api/auth/login", headers=HTTPS, json={"email": "ok@correo.com", "password": PASSWORD})
        assert r.status_code == 200 and r.headers["Cache-Control"] == "no-store"
        assert "Strict-Transport-Security" in r.headers

    def test_cambio_de_contrasena_no_se_cachea(self, client, datos):
        from tests.conftest import cabeceras
        u = datos.usuario()
        r = client.put("/api/usuarios/me/password", headers={**cabeceras(u), **HTTPS},
                       json={"actual": PASSWORD, "nueva": "Nueva.5678"})
        assert r.headers["Cache-Control"] == "no-store"
