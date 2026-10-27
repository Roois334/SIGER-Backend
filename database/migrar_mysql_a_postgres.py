"""
Copia TODOS los datos de la base MySQL (Filess.io) a PostgreSQL (Azure).

- Crea las tablas en PostgreSQL a partir de los modelos (si ya existen, no las toca).
- Copia tabla por tabla en orden (primero las que no dependen de otras).
- Ajusta los contadores de id para que los registros nuevos sigan la numeracion.
- NO borra nada de MySQL. Si PostgreSQL ya tiene datos, se detiene sin tocar nada.

Uso (desde la carpeta del backend):
    python database/migrar_mysql_a_postgres.py "mysql+pymysql://usuario:clave@host:3306/base" "postgresql+psycopg2://usuario:clave@host:5432/base?sslmode=require"
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, func, select, text  # noqa: E402

from extensions import db  # noqa: E402
import models.catalogos  # noqa: E402,F401
import models.user  # noqa: E402,F401
import models.reporte  # noqa: E402,F401
import models.notificacion  # noqa: E402,F401
import models.password_reset  # noqa: E402,F401


def main(url_origen, url_destino):
    origen = create_engine(url_origen, connect_args={"connect_timeout": 15})
    destino = create_engine(url_destino, connect_args={"connect_timeout": 15})
    tablas = db.metadata.sorted_tables

    db.metadata.create_all(destino)
    with destino.connect() as con:
        ocupadas = [t.name for t in tablas if con.execute(select(func.count()).select_from(t)).scalar()]
    if ocupadas:
        sys.exit(f"PostgreSQL ya tiene datos en: {', '.join(ocupadas)}. No se copio nada.")

    with origen.connect() as src, destino.begin() as dst:
        for t in tablas:
            filas = [dict(f._mapping) for f in src.execute(select(t))]
            if filas:
                dst.execute(t.insert(), filas)
            print(f"{t.name:22} {len(filas):6} filas")
        # Los id se insertaron a mano: el contador debe seguir desde el mayor
        for t in tablas:
            if "id" in t.c and t.c.id.autoincrement:
                dst.execute(text(
                    f"SELECT setval(pg_get_serial_sequence('{t.name}', 'id'), "
                    f"COALESCE((SELECT MAX(id) FROM {t.name}), 0) + 1, false)"))

    # Comprobacion: mismas filas en las dos bases
    with origen.connect() as src, destino.connect() as dst:
        for t in tablas:
            a = src.execute(select(func.count()).select_from(t)).scalar()
            b = dst.execute(select(func.count()).select_from(t)).scalar()
            if a != b:
                sys.exit(f"ERROR: {t.name} tiene {a} filas en MySQL y {b} en PostgreSQL")
    print("OK: todas las tablas tienen las mismas filas en las dos bases")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
