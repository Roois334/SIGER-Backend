from dotenv import load_dotenv
load_dotenv()

from flask import Flask, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from config import Config
from extensions import db
from controllers.auth_controller import auth_bp
from controllers.user_controller import user_bp
import models.password_reset  # noqa: F401  (registra la tabla password_resets)

app = Flask(__name__)
app.config.from_object(Config)
CORS(app, origins=[Config.FRONTEND_URL, "http://localhost:5001", "http://127.0.0.1:5001"])

# La estructura de la base (tablas, triggers y datos de catalogo) sale de database/siger_db.sql.
# Por eso aqui NO se hace db.create_all(). Si cambias un modelo, actualiza la base y
# vuelve a exportar el esquema con database/exportar_esquema.py.
db.init_app(app)
jwt = JWTManager(app)
app.register_blueprint(auth_bp)
app.register_blueprint(user_bp)

from controllers.catalogo_controller import municipio_bp, organismo_bp
# ... después de app.register_blueprint(user_bp):
app.register_blueprint(municipio_bp)
app.register_blueprint(organismo_bp)

from controllers.reporte_controller import reporte_bp
app.register_blueprint(reporte_bp)

@app.errorhandler(413)
def archivo_demasiado_grande(e):
    return jsonify({"error": "Los archivos superan el tamano maximo permitido"}), 413


@app.route("/")
def home():
    return "Hola SIGER-Backend esta funcionando"


if __name__ == "__main__":
    app.run(debug=Config.DEBUG)