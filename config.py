import os
from datetime import timedelta

from sqlalchemy.engine import URL
from sqlalchemy.pool import NullPool

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


# Motor de base de datos: "postgresql" (Azure) o "mysql" (MySQL/MariaDB local o Filess.io)
DB_ENGINE = os.environ.get("DB_ENGINE", "postgresql").lower()


def _construir_uri_db():
    """
    Arma la URI de conexion desde el .env.
    Usa URL.create para que contrasenas con caracteres raros (@ : / # %)
    no rompan la conexion.
    """
    # Opcion rapida: si defines DATABASE_URL en el .env, se usa tal cual.
    url_completa = os.environ.get("DATABASE_URL")
    if url_completa:
        return url_completa

    if DB_ENGINE == "mysql":
        driver, puerto, query = "mysql+pymysql", "3306", {"charset": "utf8mb4"}
    else:
        # Azure Database for PostgreSQL exige conexion cifrada
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


class Config:
    # Modo depuracion: solo si el .env dice FLASK_DEBUG=1
    DEBUG = os.environ.get("FLASK_DEBUG", "0") == "1"
    # La clave secreta es obligatoria (solo en depuracion se permite una de desarrollo)
    SECRET_KEY = os.environ.get("SECRET_KEY") or ("clave-solo-para-desarrollo" if DEBUG else None)
    if not SECRET_KEY:
        raise RuntimeError("Falta SECRET_KEY en el .env. Define una clave larga y aleatoria.")

    # --- Archivos subidos ---
    # En Azure se define DATA_DIR=/home/data: esa carpeta no se borra al volver a desplegar.
    _DATA_DIR = os.environ.get("DATA_DIR")
    # Evidencias de reportes
    UPLOAD_FOLDER = os.path.join(_DATA_DIR, "evidencias") if _DATA_DIR else os.path.join(BASE_DIR, "uploads_privados", "evidencias")
    MAX_CONTENT_LENGTH = 56 * 1024 * 1024  # 5 evidencias x 10 MB + margen del formulario
    # Fotos de perfil (se sirven en /static/uploads/perfiles/, ver app.py)
    UPLOAD_FOLDER_PERFILES = os.path.join(_DATA_DIR, "perfiles") if _DATA_DIR else os.path.join(BASE_DIR, "static", "uploads", "perfiles")

    # --- Conexion a la base de datos (Azure PostgreSQL o MySQL) ---
    SQLALCHEMY_DATABASE_URI = _construir_uri_db()
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True, "pool_recycle": 280, "pool_size": 5,
                                 "connect_args": {"connect_timeout": 15}}
    if str(SQLALCHEMY_DATABASE_URI).startswith("mysql"):
        # Filess.io (plan gratis) limita las conexiones simultaneas y cierra las inactivas:
        # con MySQL se abre y cierra la conexion en cada peticion.
        SQLALCHEMY_ENGINE_OPTIONS = {"poolclass": NullPool, "connect_args": {"connect_timeout": 15}}

    # --- Recuperacion de contrasena (correo por Gmail) ---
    # Direccion publica del FRONTEND: es la que se pone en el enlace del correo.
    FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://127.0.0.1:5001")

    # --- JWT ---
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", SECRET_KEY)
    # Duracion del token en MINUTOS (por defecto 20). Se cambia con JWT_EXPIRES_MINUTES en el .env.
    # Minimo 1. Nunca pongas 0: en esta libreria 0 significa "no vence nunca".
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=max(1, int(os.environ.get("JWT_EXPIRES_MINUTES", "20"))))
