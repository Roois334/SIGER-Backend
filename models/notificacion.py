from extensions import db


class Notificacion(db.Model):
    """HU-15: aviso para un usuario cuando cambia algo relevante en una emergencia."""
    __tablename__ = "notificaciones"

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False, index=True)
    reporte_id = db.Column(db.Integer, db.ForeignKey("reportes.id", ondelete="CASCADE"), nullable=True)
    tipo = db.Column(db.String(30), nullable=False)       # evento: reporte_nuevo, asignado, en_atencion...
    titulo = db.Column(db.String(150), nullable=False)
    mensaje = db.Column(db.String(300), nullable=False)
    leida = db.Column(db.Boolean, nullable=False, default=False)
    fecha_creacion = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)

    usuario = db.relationship("User")
    reporte = db.relationship("Reporte")
