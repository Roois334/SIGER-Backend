from extensions import db


class PasswordReset(db.Model):
    """Enlace de un solo uso para restablecer la contrasena. Se guarda solo el HASH del token."""
    __tablename__ = "password_resets"

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False, index=True)
    token_hash = db.Column(db.String(64), unique=True, nullable=False)
    expira = db.Column(db.DateTime, nullable=False)
    usado = db.Column(db.Boolean, nullable=False, default=False)
    fecha_creacion = db.Column(db.DateTime, nullable=False)
