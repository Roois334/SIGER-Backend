import io
import os
import itertools

os.environ["SECRET_KEY"] = "clave-solo-para-pruebas-0123456789abcdef"
os.environ["DATABASE_URL"] = "sqlite://"
os.environ.pop("FLASK_DEBUG", None)
os.environ.pop("DATA_DIR", None)

import pytest
from flask_jwt_extended import create_access_token
from werkzeug.security import generate_password_hash

PASSWORD = "Clave.1234"
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
JPG = b"\xff\xd8\xff\xe0" + b"\x00" * 64
PDF = b"%PDF-1.4\n" + b"\x00" * 32


@pytest.fixture(scope="session")
def app():
    from app import app as flask_app
    flask_app.config.update(TESTING=True)
    return flask_app


@pytest.fixture(autouse=True)
def entorno(app, tmp_path, monkeypatch):
    for variable in ("MAIL_USER", "MAIL_PASSWORD", "NOTIFICAR_CORREO", "FORCE_HTTPS"):
        monkeypatch.delenv(variable, raising=False)
    app.config["UPLOAD_FOLDER"] = str(tmp_path / "evidencias")
    app.config["UPLOAD_FOLDER_PERFILES"] = str(tmp_path / "perfiles")
    from controllers import auth_controller
    auth_controller._limitador_login._fallos.clear()
    from extensions import db
    with app.app_context():
        db.create_all()
        yield
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


class Datos:
    def __init__(self):
        from extensions import db
        from models.catalogos import Rol, Municipio, Organismo
        self.db = db
        self.roles = {n: Rol(nombre=n) for n in
                      ("ciudadano", "gestor_municipal", "organismo_atencion", "administrador")}
        db.session.add_all(self.roles.values())
        self.facatativa = Municipio(codigo="25269", nombre="Facatativa", activo=True)
        self.madrid = Municipio(codigo="25430", nombre="Madrid", activo=True)
        self.inactivo = Municipio(codigo="99999", nombre="Inactivo", activo=False)
        db.session.add_all([self.facatativa, self.madrid, self.inactivo])
        db.session.flush()
        self.bomberos = Organismo(codigo="BOM", nombre="Bomberos", tipo="Emergencias", activo=True)
        self.bomberos.municipios = [self.facatativa]
        self.cruz_roja = Organismo(codigo="CRC", nombre="Cruz Roja", tipo="Socorro", activo=True)
        self.cruz_roja.municipios = [self.facatativa, self.madrid]
        self.defensa = Organismo(codigo="DEF", nombre="Defensa Civil", tipo="Socorro", activo=False)
        self.defensa.municipios = [self.facatativa]
        db.session.add_all([self.bomberos, self.cruz_roja, self.defensa])
        db.session.commit()
        self._n = itertools.count(1)
        self._folio = itertools.count(1)

    def usuario(self, rol="ciudadano", email=None, municipio="facatativa", organismo=None,
                password=PASSWORD, activo=True, **extra):
        from models.user import User
        n = next(self._n)
        mun = getattr(self, municipio) if municipio else None
        u = User(
            nombre=extra.pop("nombre", "Ana"), apellido=extra.pop("apellido", f"Prueba{n}"),
            email=email or f"{rol}{n}@siger.test",
            password_hash=generate_password_hash(password),
            rol_id=self.roles[rol].id, municipio_id=mun.id if mun else None,
            organismo_id=organismo.id if organismo else None, activo=activo, **extra)
        self.db.session.add(u)
        self.db.session.commit()
        return u

    def reporte(self, ciudadano, municipio=None, **extra):
        from models.reporte import Reporte
        from utilities.fechas import ahora
        municipio = municipio or self.facatativa
        valores = dict(
            folio=f"RPT-2026-{next(self._folio):05d}", ciudadano_id=ciudadano.id, municipio_id=municipio.id,
            tipo="Incendio", prioridad="alta", descripcion="Incendio en bodega con mucho humo",
            direccion="Calle 1 # 2-3", afectados=4, heridos=1, estado="pendiente",
            fecha_hora=ahora(), fecha_actualizacion=ahora())
        valores.update(extra)
        r = Reporte(**valores)
        self.db.session.add(r)
        self.db.session.commit()
        return r


@pytest.fixture
def datos(entorno):
    return Datos()


def cabeceras(usuario):
    return {"Authorization": "Bearer " + create_access_token(identity=str(usuario.id))}


@pytest.fixture
def auth():
    return cabeceras


@pytest.fixture
def archivo_png():
    return (io.BytesIO(PNG), "foto.png", "image/png")
