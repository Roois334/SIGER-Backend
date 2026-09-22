from extensions import db


class Rol(db.Model):
    __tablename__ = "roles"
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(40), unique=True, nullable=False)
    descripcion = db.Column(db.String(150))


# Tabla intermedia para la relacion muchos-a-muchos entre organismos y municipios
organismo_municipio = db.Table(
    "organismo_municipio",
    db.Column("organismo_id", db.Integer, db.ForeignKey("organismos.id"), primary_key=True),
    db.Column("municipio_id", db.Integer, db.ForeignKey("municipios.id"), primary_key=True),
)


class Municipio(db.Model):
    __tablename__ = "municipios"

    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(20), unique=True, nullable=False)
    nombre = db.Column(db.String(80), unique=True, nullable=False)
    activo = db.Column(db.Boolean, nullable=False, default=True)
    fecha_creacion = db.Column(db.DateTime, server_default=db.func.now())
    fecha_actualizacion = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())

    organismos = db.relationship(
        "Organismo", secondary=organismo_municipio, back_populates="municipios"
    )


class Organismo(db.Model):
    __tablename__ = "organismos"

    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(20), unique=True, nullable=False)
    nombre = db.Column(db.String(120), unique=True, nullable=False)
    tipo = db.Column(db.String(60))
    activo = db.Column(db.Boolean, nullable=False, default=True)
    fecha_creacion = db.Column(db.DateTime, server_default=db.func.now())
    fecha_actualizacion = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())

    municipios = db.relationship(
        "Municipio", secondary=organismo_municipio, back_populates="organismos"
    )