from dotenv import load_dotenv
load_dotenv()

from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from config import Config
from extensions import db
from controllers.auth_controller import auth_bp
from controllers.user_controller import user_bp
from controllers.catalogo_controller import municipio_bp, organismo_bp
from controllers.reporte_controller import reporte_bp
from controllers.notificacion_controller import notificacion_bp
from controllers.publico_controller import publico_bp
from controllers.estadistica_controller import estadistica_bp
import models.password_reset  # noqa: F401  (registra la tabla password_resets)
import models.notificacion  # noqa: F401  (registra la tabla notificaciones)

app = Flask(__name__)
app.config.from_object(Config)
CORS(app, origins=[Config.FRONTEND_URL, "http://localhost:5001", "http://127.0.0.1:5001"])

# La estructura de la base (tablas, triggers y datos de catalogo) sale de database/siger_db.sql.
# Por eso aqui NO se hace db.create_all(). Si cambias un modelo, actualiza la base y
# vuelve a exportar el esquema con database/exportar_esquema.py.
db.init_app(app)
JWTManager(app)
for blueprint in (auth_bp, user_bp, municipio_bp, organismo_bp, reporte_bp,
                  notificacion_bp, publico_bp, estadistica_bp):
    app.register_blueprint(blueprint)

@app.route("/static/uploads/perfiles/<path:nombre>")
def foto_perfil(nombre):
    """Las fotos de perfil viven en UPLOAD_FOLDER_PERFILES (en Azure, fuera del codigo desplegado)."""
    return send_from_directory(app.config["UPLOAD_FOLDER_PERFILES"], nombre)


@app.errorhandler(413)
def archivo_demasiado_grande(e):
    return jsonify({"error": "Los archivos superan el tamano maximo permitido"}), 413


@app.route("/")
def home():
    return "Hola SIGER-Backend esta funcionando"


if __name__ == "__main__":
    app.run(debug=Config.DEBUG)