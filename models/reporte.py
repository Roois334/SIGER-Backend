from extensions import db


class Reporte(db.Model):
    __tablename__ = "reportes"

    id = db.Column(db.Integer, primary_key=True)
    folio = db.Column(db.String(30), unique=True, nullable=False)

    ciudadano_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False)
    municipio_id = db.Column(db.Integer, db.ForeignKey("municipios.id"), nullable=False)

    tipo = db.Column(db.String(60), nullable=False)
    prioridad = db.Column(db.String(20), nullable=False, default="media")
    descripcion = db.Column(db.Text, nullable=False)
    direccion = db.Column(db.String(200), nullable=False)
    latitud = db.Column(db.Float, nullable=True)
    longitud = db.Column(db.Float, nullable=True)
    afectados = db.Column(db.Integer, nullable=False, default=0)
    heridos = db.Column(db.Integer, nullable=False, default=0)
    # HU-10: variables que el gestor evalua para calcular la prioridad
    vias_afectadas = db.Column(db.Integer, nullable=True)
    area_afectada = db.Column(db.Integer, nullable=True)  # metros cuadrados
    riesgo_propagacion = db.Column(db.String(10), nullable=True)  # bajo / medio / alto

    # pendiente -> asignado -> en_atencion -> resuelto   (o descartado)
    estado = db.Column(db.String(20), nullable=False, default="pendiente")

    # Asignacion: el gestor acepta el reporte y lo asigna a un organismo
    organismo_id = db.Column(db.Integer, db.ForeignKey("organismos.id"), nullable=True)
    asignado_por_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=True)
    fecha_asignacion = db.Column(db.DateTime, nullable=True)

    fecha_hora = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)
    fecha_creacion = db.Column(db.DateTime, server_default=db.func.now())
    fecha_actualizacion = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())

    ciudadano = db.relationship("User", foreign_keys=[ciudadano_id])
    asignado_por = db.relationship("User", foreign_keys=[asignado_por_id])
    municipio = db.relationship("Municipio")
    organismo = db.relationship("Organismo")
    evidencias = db.relationship(
        "Evidencia", backref="reporte", cascade="all, delete-orphan", lazy=True
    )
    historial = db.relationship(
        "ReporteHistorial", backref="reporte", cascade="all, delete-orphan",
        order_by="ReporteHistorial.fecha, ReporteHistorial.id", lazy=True
    )


class Evidencia(db.Model):
    __tablename__ = "evidencias"

    id = db.Column(db.Integer, primary_key=True)
    reporte_id = db.Column(db.Integer, db.ForeignKey("reportes.id"), nullable=False)
    nombre_archivo = db.Column(db.String(255), nullable=False)
    ruta_archivo = db.Column(db.String(300), nullable=False)
    fecha_carga = db.Column(db.DateTime, server_default=db.func.now())


class ReporteHistorial(db.Model):
    """Cada cambio importante del reporte (asignacion, inicio de atencion, etc.)."""
    __tablename__ = "reporte_historial"

    id = db.Column(db.Integer, primary_key=True)
    reporte_id = db.Column(db.Integer, db.ForeignKey("reportes.id"), nullable=False)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=True)
    accion = db.Column(db.String(20), nullable=False)   # asignar, reasignar, iniciar, resolver, devolver, descartar
    estado_anterior = db.Column(db.String(20), nullable=True)
    estado_nuevo = db.Column(db.String(20), nullable=False)
    comentario = db.Column(db.String(300), nullable=True)
    fecha = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)

    usuario = db.relationship("User")
