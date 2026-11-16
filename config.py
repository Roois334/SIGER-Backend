import os
from datetime import timedelta

from sqlalchemy.engine import URL

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def _construir_uri_db():
    url_completa = os.environ.get("DATABASE_URL")
    if url_completa:
        return url_completa

    driver, puerto = "postgresql+psycopg2", "5432"
    query = {"sslmode": os.environ.get("DB_SSLMODE", "require")}
    return URL.create(
        drivername=driver,
        username=os.environ.get("DB_USER", "siger_app"),
        password=os.environ.get("DB_PASSWORD", "CAMBIA_ESTA_CLAVE"),
        host=os.environ.get("DB_HOST", "localhost"),
        port=int(os.environ.get("DB_PORT", puerto)),
        database=os.environ.get("DB_NAME", "siger_db"),
        query=query,
    )


def _opciones_motor(uri):
    if str(uri).startswith("sqlite"):
        return {}
    return {"pool_pre_ping": True, "pool_recycle": 280, "pool_size": 5,
            "connect_args": {"connect_timeout": 15}}


class Config:
    DEBUG = os.environ.get("FLASK_DEBUG", "0") == "1"
    SECRET_KEY = os.environ.get("SECRET_KEY") or ("clave-solo-para-desarrollo" if DEBUG else None)
    if not SECRET_KEY:
        raise RuntimeError("Falta SECRET_KEY en el .env. Define una clave larga y aleatoria.")

    _DATA_DIR = os.environ.get("DATA_DIR")
    UPLOAD_FOLDER = os.path.join(_DATA_DIR, "evidencias") if _DATA_DIR else os.path.join(BASE_DIR, "uploads_privados", "evidencias")
    MAX_CONTENT_LENGTH = 56 * 1024 * 1024
    UPLOAD_FOLDER_PERFILES = os.path.join(_DATA_DIR, "perfiles") if _DATA_DIR else os.path.join(BASE_DIR, "static", "uploads", "perfiles")

    SQLALCHEMY_DATABASE_URI = _construir_uri_db()
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    SQLALCHEMY_ENGINE_OPTIONS = _opciones_motor(SQLALCHEMY_DATABASE_URI)

    FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://127.0.0.1:5001")

    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", SECRET_KEY)
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=max(1, int(os.environ.get("JWT_EXPIRES_MINUTES", "20"))))
