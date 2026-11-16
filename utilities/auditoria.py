"""
Apoyo a los triggers y procedimientos de PostgreSQL (database/triggers_y_procedimientos.sql).

registrar_actor() le dice a la base QUIEN hace el cambio en la transaccion actual, para que el
trigger trg_auditoria_usuarios lo guarde en auditoria_usuarios.modificado_por. El valor dura solo
hasta el commit. En SQLite (las pruebas) no hay triggers, asi que no hace nada.
"""
from sqlalchemy import text

from extensions import db


def usa_postgresql():
    return db.engine.dialect.name == "postgresql"


def registrar_actor(usuario_id):
    if usuario_id is None or not usa_postgresql():
        return
    db.session.execute(text("SELECT set_config('siger.usuario_actual', :id, true)"), {"id": str(usuario_id)})
