from extensions import db


class User(db.Model):
    __tablename__ = "usuarios"

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(80), nullable=False)
    apellido = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    rol_id = db.Column(db.Integer, db.ForeignKey("roles.id"), nullable=False)
    municipio_id = db.Column(db.Integer, db.ForeignKey("municipios.id"), nullable=True)
    activo = db.Column(db.Boolean, nullable=False, default=True)
    foto_url = db.Column(db.String(255), nullable=True)
    fecha_creacion = db.Column(db.DateTime, server_default=db.func.now())
    fecha_actualizacion = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())

    rol = db.relationship("Rol")
    municipio = db.relationship("Municipio")