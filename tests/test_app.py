"""Aplicacion completa: rutas basicas, decoradores y configuracion."""
import importlib
import os

import pytest
from werkzeug.exceptions import RequestEntityTooLarge  # noqa: F401

import config
from tests.conftest import PNG, cabeceras
from utilities import decorators


def test_portada(client):
    r = client.get("/")
    assert r.status_code == 200 and "SIGER" in r.get_data(as_text=True)


def test_archivo_demasiado_grande_responde_413_en_json(client, app, monkeypatch):
    monkeypatch.setitem(app.config, "MAX_CONTENT_LENGTH", 10)
    r = client.post("/api/auth/login", data="x" * 100, content_type="application/json")
    assert r.status_code == 413 and "maximo" in r.get_json()["error"]


def test_sirve_la_foto_de_perfil(client, app):
    carpeta = app.config["UPLOAD_FOLDER_PERFILES"]
    os.makedirs(carpeta)
    with open(os.path.join(carpeta, "yo.png"), "wb") as f:
        f.write(PNG)
    assert client.get("/static/uploads/perfiles/yo.png").data == PNG
    assert client.get("/static/uploads/perfiles/no-existe.png").status_code == 404
    assert client.get("/static/uploads/perfiles/../../config.py").status_code in (400, 404)


class TestDecoradores:
    def _llamar(self, app, decorador, usuario=None):
        cuerpo = decorador(lambda: ("ok", 200))
        cabecera = cabeceras(usuario) if usuario else {}
        with app.test_request_context("/", headers=cabecera):
            return cuerpo()

    def test_roles_required(self, app, datos):
        admin = datos.usuario("administrador", municipio=None)
        ciudadano = datos.usuario()
        assert self._llamar(app, decorators.roles_required("administrador"), admin) == ("ok", 200)
        _, codigo = self._llamar(app, decorators.roles_required("administrador"), ciudadano)
        assert codigo == 403

    def test_cuenta_inactiva_o_borrada_no_pasa(self, app, datos):
        inactivo = datos.usuario(activo=False)
        _, codigo = self._llamar(app, decorators.roles_required("ciudadano"), inactivo)
        assert codigo == 401
        _, codigo = self._llamar(app, decorators.permiso_required("reportes.crear"), inactivo)
        assert codigo == 401
        fantasma = datos.usuario()
        h = cabeceras(fantasma)
        datos.db.session.delete(fantasma)
        datos.db.session.commit()
        cuerpo = decorators.login_activo_required(lambda: ("ok", 200))
        with app.test_request_context("/", headers=h):
            assert cuerpo()[1] == 401

    def test_el_rol_se_lee_de_la_base_no_del_token(self, client, datos):
        admin = datos.usuario("administrador", municipio=None)
        h = cabeceras(admin)  # el token se emitio cuando era admin
        admin.rol_id = datos.roles["ciudadano"].id
        datos.db.session.commit()
        assert client.get("/api/usuarios", headers=h).status_code == 403


class TestConfiguracion:
    def _recargar(self):
        return importlib.reload(config)

    def test_uri_desde_variables_con_caracteres_raros(self, monkeypatch):
        monkeypatch.delenv("DATABASE_URL")
        monkeypatch.setenv("DB_PASSWORD", "p@ss:/#word")
        monkeypatch.setenv("DB_HOST", "servidor.postgres.database.azure.com")
        try:
            uri = self._recargar()._construir_uri_db()
            assert uri.host == "servidor.postgres.database.azure.com" and uri.password == "p@ss:/#word"
            assert uri.query["sslmode"] == "require"
        finally:
            monkeypatch.undo()
            self._recargar()

    def test_database_url_tiene_prioridad(self, monkeypatch):
        monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@h/db")
        assert config._construir_uri_db() == "postgresql://u:p@h/db"

    def test_opciones_del_motor_segun_la_base(self):
        assert config._opciones_motor("sqlite://") == {}
        assert config._opciones_motor("postgresql://u:p@h/db")["pool_pre_ping"] is True

    def test_sin_secret_key_no_arranca_salvo_en_depuracion(self, monkeypatch):
        monkeypatch.delenv("SECRET_KEY")
        try:
            with pytest.raises(RuntimeError, match="SECRET_KEY"):
                self._recargar()
            monkeypatch.setenv("FLASK_DEBUG", "1")
            assert self._recargar().Config.SECRET_KEY == "clave-solo-para-desarrollo"
        finally:
            monkeypatch.undo()
            self._recargar()

    def test_la_sesion_dura_minimo_un_minuto(self, monkeypatch):
        monkeypatch.setenv("JWT_EXPIRES_MINUTES", "0")
        try:
            assert self._recargar().Config.JWT_ACCESS_TOKEN_EXPIRES.total_seconds() == 60
        finally:
            monkeypatch.undo()
            self._recargar()

    def test_carpetas_en_data_dir(self, monkeypatch):
        monkeypatch.setenv("DATA_DIR", "/home/data")
        try:
            cfg = self._recargar().Config
            assert cfg.UPLOAD_FOLDER.replace("\\", "/") == "/home/data/evidencias"
            assert cfg.UPLOAD_FOLDER_PERFILES.replace("\\", "/") == "/home/data/perfiles"
        finally:
            monkeypatch.undo()
            self._recargar()
