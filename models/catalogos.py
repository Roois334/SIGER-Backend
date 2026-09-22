from extensions import db


class Rol(db.Model):
    __tablename__ = "roles"
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(40), unique=True, nullable=False)
    descripcion = db.Column(db.String(150))


class Municipio(db.Model):
    __tablename__ = "municipios"
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(80), unique=True, nullable=False)