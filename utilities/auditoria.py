from sqlalchemy import text

from extensions import db


def usa_postgresql():
    return db.engine.dialect.name == "postgresql"


def registrar_actor(usuario_id):
    if usuario_id is None or not usa_postgresql():
        return
    db.session.execute(text("SELECT set_config('siger.usuario_actual', :id, true)"), {"id": str(usuario_id)})
