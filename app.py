from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from config import Config
from extensions import db
from controllers.auth_controller import auth_bp

app = Flask(__name__)
app.config.from_object(Config)
CORS(app)

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///temporal.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["JWT_SECRET_KEY"] = app.config["SECRET_KEY"]

db.init_app(app)
jwt = JWTManager(app)
app.register_blueprint(auth_bp)


@app.route("/")
def home():
    return "Hola SIGER-Backend esta funcionando"


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
