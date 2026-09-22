from extensions import db


class Reporte(db.Model):
    __tablename__ = "reportes"

    id = db.Column(db.Integer, primary_key=True)
    folio = db.Column(db.String(30), unique=True, nullable=False)

    ciudadano_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False)
    municipio_id = db.Column(db.Integer, db.ForeignKey("municipios.id"), nullable=False)

    tipo = db.Column(db.String(60), nullable=False)
    descripcion = db.Column(db.Text, nullable=False)
    direccion = db.Column(db.String(200), nullable=False)
    latitud = db.Column(db.Float, nullable=True)
    longitud = db.Column(db.Float, nullable=True)
    afectados = db.Column(db.Integer, nullable=False, default=0)

    estado = db.Column(db.String(20), nullable=False, default="pendiente")

    fecha_hora = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)
    fecha_creacion = db.Column(db.DateTime, server_default=db.func.now())
    fecha_actualizacion = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())

    ciudadano = db.relationship("User")
    municipio = db.relationship("Municipio")
    evidencias = db.relationship(
        "Evidencia", backref="reporte", cascade="all, delete-orphan", lazy=True
    )


class Evidencia(db.Model):
    __tablename__ = "evidencias"

    id = db.Column(db.Integer, primary_key=True)
    reporte_id = db.Column(db.Integer, db.ForeignKey("reportes.id"), nullable=False)
    nombre_archivo = db.Column(db.String(255), nullable=False)
    ruta_archivo = db.Column(db.String(300), nullable=False)
    fecha_carga = db.Column(db.DateTime, server_default=db.func.now())