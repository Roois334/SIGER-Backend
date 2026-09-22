from dotenv import load_dotenv
load_dotenv()

from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from config import Config
from extensions import db
from controllers.auth_controller import auth_bp

app = Flask(__name__)
app.config.from_object(Config)
CORS(app)

# La base de datos (tablas, triggers, procedimientos y el usuario de
# conexion con permisos limitados) se crea con el script .sql.
# El usuario 'siger_app' solo tiene SELECT/INSERT/UPDATE/DELETE/EXECUTE,
# por eso aqui NO se hace db.create_all(): la app no tiene permisos de DDL.
db.init_app(app)
jwt = JWTManager(app)
app.register_blueprint(auth_bp)


@app.route("/")
def home():
    return "Hola SIGER-Backend esta funcionando"


if __name__ == "__main__":
    app.run(debug=Config.DEBUG)