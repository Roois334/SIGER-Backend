import os
from datetime import timedelta

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "clave-secreta-cambiar-en-produccion")
    DEBUG = os.environ.get("FLASK_DEBUG", "1") == "1"

    # --- Evidencias de reportes ---
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads", "evidencias")
    MAX_CONTENT_LENGTH = 20 * 1024 * 1024  # 20 MB por peticion

    # --- Conexion a MySQL ---
    DB_USER = os.environ.get("DB_USER", "siger_app")
    DB_PASSWORD = os.environ.get("DB_PASSWORD", "CAMBIA_ESTA_CLAVE")
    DB_HOST = os.environ.get("DB_HOST", "localhost")
    DB_PORT = os.environ.get("DB_PORT", "3306")
    DB_NAME = os.environ.get("DB_NAME", "siger_db")

    SQLALCHEMY_DATABASE_URI = (
        f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # --- JWT ---
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", SECRET_KEY)
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=int(os.environ.get("JWT_EXPIRES_HOURS", "2")))