import os
from datetime import timedelta

from sqlalchemy.engine import URL

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def _construir_uri_db():
    """
    Arma la URI de conexion a MySQL/MariaDB (local o Filess.io) desde el .env.
    Usa URL.create para que contrasenas con caracteres raros (@ : / # %)
    no rompan la conexion.
    """
    # Opcion rapida: si defines DATABASE_URL en el .env, se usa tal cual.
    url_completa = os.environ.get("DATABASE_URL")
    if url_completa:
        return url_completa

    return URL.create(
        drivername="mysql+pymysql",
        username=os.environ.get("DB_USER", "siger_app"),
        password=os.environ.get("DB_PASSWORD", "CAMBIA_ESTA_CLAVE"),
        host=os.environ.get("DB_HOST", "localhost"),
        port=int(os.environ.get("DB_PORT", "3306")),
        database=os.environ.get("DB_NAME", "siger_db"),
        query={"charset": "utf8mb4"},
    )


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "clave-secreta-cambiar-en-produccion")
    DEBUG = os.environ.get("FLASK_DEBUG", "1") == "1"

    # --- Evidencias de reportes ---
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads_privados", "evidencias")
    MAX_CONTENT_LENGTH = 20 * 1024 * 1024  # 20 MB por peticion

    # --- Fotos de perfil ---
    UPLOAD_FOLDER_PERFILES = os.path.join(BASE_DIR, "static", "uploads", "perfiles")

    # --- Conexion a la base de datos (Filess.io / MySQL) ---
    SQLALCHEMY_DATABASE_URI = _construir_uri_db()
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Filess.io (plan gratis) limita las conexiones simultaneas y las cierra
    # cuando estan inactivas. Con esto el pool es pequeño y se "revive" solo.
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,   # prueba la conexion antes de usarla
        "pool_recycle": 280,     # renueva conexiones viejas (segundos)
    }
    if str(SQLALCHEMY_DATABASE_URI).startswith("mysql"):
        SQLALCHEMY_ENGINE_OPTIONS.update({
            "pool_size": 3,
            "max_overflow": 0,
            "connect_args": {"connect_timeout": 15},
        })

    # --- JWT ---
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", SECRET_KEY)
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=int(os.environ.get("JWT_EXPIRES_HOURS", "2")))