from datetime import timedelta

from tests.conftest import PASSWORD, cabeceras
from models.password_reset import PasswordReset
from models.user import User
from services import recuperacion_service as rec
from services.recuperacion_service import RecuperacionService


def _registro(datos, **cambios):
    cuerpo = {"nombre": "Laura", "apellido": "Gomez", "email": "laura@correo.com", "password": PASSWORD,
              "municipio": "Facatativa", "tipo_documento": "CC", "documento": "1234567890",
              "telefono": "3001234567"}
    cuerpo.update(cambios)
    return cuerpo


class TestRegistro:
    def test_crea_un_ciudadano_y_devuelve_token(self, client, datos):
        r = client.post("/api/auth/register", json=_registro(datos))
        assert r.status_code == 201
        cuerpo = r.get_json()
        assert cuerpo["token"]
        assert cuerpo["usuario"]["rol"] == "ciudadano"
        assert "password" not in str(cuerpo).lower().replace("password_hash", "")
        usuario = User.query.filter_by(email="laura@correo.com").one()
        assert usuario.password_hash != PASSWORD

    def test_ignora_un_rol_enviado_por_el_cliente(self, client, datos):
        r = client.post("/api/auth/register", json=_registro(datos, rol="administrador"))
        assert r.get_json()["usuario"]["rol"] == "ciudadano"

    def test_correo_repetido(self, client, datos):
        datos.usuario(email="laura@correo.com")
        r = client.post("/api/auth/register", json=_registro(datos))
        assert r.status_code == 400 and "correo" in r.get_json()["error"]

    def test_documento_repetido(self, client, datos):
        datos.usuario(tipo_documento="CC", documento="1234567890")
        r = client.post("/api/auth/register", json=_registro(datos))
        assert r.status_code == 400 and "documento" in r.get_json()["error"]

    def test_municipio_invalido(self, client, datos):
        assert client.post("/api/auth/register", json=_registro(datos, municipio="Inactivo")).status_code == 400

    def test_sin_municipio_es_valido(self, client, datos):
        assert client.post("/api/auth/register", json=_registro(datos, municipio=None)).status_code == 201

    def test_password_debil(self, client, datos):
        r = client.post("/api/auth/register", json=_registro(datos, password="debil"))
        assert r.status_code == 400

    def test_cuerpo_vacio(self, client, datos):
        assert client.post("/api/auth/register", data="no es json").status_code == 400


class TestLogin:
    def test_correcto(self, client, datos):
        datos.usuario(email="ok@correo.com")
        r = client.post("/api/auth/login", json={"email": " OK@correo.com ", "password": PASSWORD})
        assert r.status_code == 200
        assert r.get_json()["usuario"]["email"] == "ok@correo.com"
        assert r.get_json()["token"]

    def test_la_respuesta_nunca_incluye_la_contrasena_ni_su_hash(self, client, datos):
        datos.usuario(email="ok@correo.com")
        texto = client.post("/api/auth/login", json={"email": "ok@correo.com", "password": PASSWORD}).get_data(as_text=True)
        assert PASSWORD not in texto and "pbkdf2" not in texto and "scrypt" not in texto

    def test_la_respuesta_de_login_no_se_guarda_en_cache(self, client, datos):
        r = client.post("/api/auth/login", json={"email": "x@y.com", "password": "mal"})
        assert r.headers["Cache-Control"] == "no-store"

    def test_mismo_mensaje_si_no_existe_o_la_clave_es_mala(self, client, datos):
        datos.usuario(email="ok@correo.com")
        a = client.post("/api/auth/login", json={"email": "ok@correo.com", "password": "Otra.1234"})
        b = client.post("/api/auth/login", json={"email": "nadie@correo.com", "password": PASSWORD})
        assert a.status_code == b.status_code == 401
        assert a.get_json() == b.get_json()

    def test_cuenta_inactiva_no_entra(self, client, datos):
        datos.usuario(email="off@correo.com", activo=False)
        assert client.post("/api/auth/login", json={"email": "off@correo.com", "password": PASSWORD}).status_code == 401

    def test_sin_contrasena_o_con_tipo_raro_no_rompe(self, client, datos):
        datos.usuario(email="ok@correo.com")
        for cuerpo in ({"email": "ok@correo.com"}, {"email": "ok@correo.com", "password": 123},
                       {"email": "ok@correo.com", "password": "x" * 500}, {}):
            assert client.post("/api/auth/login", json=cuerpo).status_code == 401

    def test_bloquea_tras_cinco_fallos(self, client, datos):
        datos.usuario(email="ok@correo.com")
        for _ in range(5):
            assert client.post("/api/auth/login", json={"email": "ok@correo.com", "password": "Mala.1234"}).status_code == 401
        r = client.post("/api/auth/login", json={"email": "ok@correo.com", "password": PASSWORD})
        assert r.status_code == 429 and "minuto" in r.get_json()["error"]


class TestRecuperacion:
    def _token_para(self, usuario, monkeypatch):
        enviados = []
        monkeypatch.setattr(rec, "enviar_correo", lambda *a, **k: enviados.append(k["enlace_dev"]))
        RecuperacionService.solicitar(usuario.email)
        return enviados[-1].rsplit("/", 1)[1] if enviados else None

    def test_olvide_responde_igual_exista_o_no(self, client, datos, monkeypatch):
        monkeypatch.setattr(rec, "enviar_correo", lambda *a, **k: None)
        datos.usuario(email="ok@correo.com")
        a = client.post("/api/auth/olvide-password", json={"email": "ok@correo.com"})
        b = client.post("/api/auth/olvide-password", json={"email": "nadie@correo.com"})
        assert a.status_code == b.status_code == 200 and a.get_json() == b.get_json()

    def test_olvide_sin_correo(self, client, datos):
        assert client.post("/api/auth/olvide-password", json={"email": "sin-arroba"}).status_code == 400

    def test_flujo_completo(self, client, datos, monkeypatch):
        u = datos.usuario(email="ok@correo.com")
        token = self._token_para(u, monkeypatch)
        info = client.get(f"/api/auth/restablecer/{token}")
        assert info.status_code == 200 and "•" in info.get_json()["email"]
        r = client.post("/api/auth/restablecer", json={"token": token, "nueva": "Nueva.5678"})
        assert r.status_code == 200
        assert client.post("/api/auth/login", json={"email": "ok@correo.com", "password": "Nueva.5678"}).status_code == 200
        assert client.post("/api/auth/restablecer", json={"token": token, "nueva": "Otra.56789"}).status_code == 400
        assert client.get(f"/api/auth/restablecer/{token}").status_code == 410

    def test_el_token_se_guarda_solo_como_hash(self, datos, monkeypatch):
        u = datos.usuario()
        token = self._token_para(u, monkeypatch)
        guardado = PasswordReset.query.one()
        assert token not in guardado.token_hash and len(guardado.token_hash) == 64

    def test_solicitudes_nuevas_invalidan_las_anteriores(self, datos, monkeypatch):
        u = datos.usuario()
        primero = self._token_para(u, monkeypatch)
        self._token_para(u, monkeypatch)
        assert RecuperacionService._buscar_valido(primero) is None

    def test_limite_de_solicitudes_por_hora(self, datos, monkeypatch):
        u = datos.usuario()
        enviados = []
        monkeypatch.setattr(rec, "enviar_correo", lambda *a, **k: enviados.append(1))
        for _ in range(5):
            RecuperacionService.solicitar(u.email)
        assert len(enviados) == rec.MAX_SOLICITUDES_POR_HORA

    def test_enlace_vencido(self, datos, monkeypatch):
        u = datos.usuario()
        token = self._token_para(u, monkeypatch)
        pr = PasswordReset.query.one()
        pr.expira = rec._ahora() - timedelta(minutes=1)
        datos.db.session.commit()
        assert RecuperacionService._buscar_valido(token) is None
        assert RecuperacionService._buscar_valido("") is None
        assert RecuperacionService._buscar_valido("inventado") is None

    def test_no_permite_la_misma_contrasena_ni_una_debil(self, client, datos, monkeypatch):
        u = datos.usuario()
        token = self._token_para(u, monkeypatch)
        assert "distinta" in client.post("/api/auth/restablecer", json={"token": token, "nueva": PASSWORD}).get_json()["error"]
        assert client.post("/api/auth/restablecer", json={"token": token, "nueva": "debil"}).status_code == 400

    def test_cuenta_desactivada_despues_de_pedir_el_enlace(self, client, datos, monkeypatch):
        u = datos.usuario()
        token = self._token_para(u, monkeypatch)
        u.activo = False
        datos.db.session.commit()
        assert client.get(f"/api/auth/restablecer/{token}").status_code == 410
        assert client.post("/api/auth/restablecer", json={"token": token, "nueva": "Nueva.5678"}).status_code == 400

    def test_correo_inexistente_o_inactivo_no_genera_nada(self, datos, monkeypatch):
        datos.usuario(email="off@correo.com", activo=False)
        monkeypatch.setattr(rec, "enviar_correo", lambda *a, **k: (_ for _ in ()).throw(AssertionError("no debe enviar")))
        RecuperacionService.solicitar("off@correo.com")
        RecuperacionService.solicitar("nadie@correo.com")
        assert PasswordReset.query.count() == 0

    def test_enmascarar(self):
        assert rec._enmascarar("ab@x.com").startswith("a•")
        assert rec._enmascarar("abcdef@x.com").startswith("ab")
        assert rec._enmascarar("abcdef@x.com").endswith("@x.com")

    def test_el_correo_html_incluye_el_enlace(self):
        html = rec._correo_html("Ana", "https://sitio/restablecer/abc", 30)
        assert "https://sitio/restablecer/abc" in html and "30" in html


class TestSesion:
    def test_endpoint_protegido_sin_token(self, client, datos):
        assert client.get("/api/usuarios/me").status_code == 401

    def test_token_de_un_usuario_desactivado_deja_de_servir(self, client, datos):
        u = datos.usuario()
        h = cabeceras(u)
        u.activo = False
        datos.db.session.commit()
        r = client.get("/api/usuarios/me", headers=h)
        assert r.status_code == 401
