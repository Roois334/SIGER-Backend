"""
Exporta el ESQUEMA de la base de SIGER (tablas, a partir de los modelos) y los datos de
CATALOGO (roles, municipios, organismos y su relacion) a database/siger_db.sql (PostgreSQL).
NO exporta usuarios, reportes ni contrasenas.

Uso (desde la carpeta BACKEND, con el .env configurado):
    python database/exportar_esquema.py
"""
import datetime
import os
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(AQUI))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(os.path.join(AQUI, "..", ".env"))

from sqlalchemy import select  # noqa: E402
from sqlalchemy.dialects import postgresql  # noqa: E402
from sqlalchemy.schema import CreateIndex, CreateTable  # noqa: E402

from app import app  # noqa: E402
from extensions import db  # noqa: E402

SALIDA = os.path.join(AQUI, "siger_db.sql")
TABLAS_CON_DATOS = ["roles", "municipios", "organismos", "organismo_municipio"]


def _sql(sentencia):
    return str(sentencia.compile(dialect=postgresql.dialect())).strip()


def main():
    tablas = db.metadata.sorted_tables
    out = [
        "-- SIGER: esquema de la base de datos (PostgreSQL) y datos de catalogo",
        f"-- Generado el {datetime.date.today().isoformat()} con database/exportar_esquema.py",
        "-- No incluye usuarios, reportes ni contrasenas.",
        "",
    ]
    for t in tablas:
        ddl = _sql(CreateTable(t, if_not_exists=True))
        out += [f"-- Tabla {t.name}", ddl + ";"]
        out += [_sql(CreateIndex(i, if_not_exists=True)) + ";" for i in t.indexes]
        out.append("")

    with app.app_context():
        for t in tablas:
            if t.name not in TABLAS_CON_DATOS:
                continue
            filas = db.session.execute(select(t)).mappings().all()
            if not filas:
                continue
            out.append(f"-- Datos de {t.name} ({len(filas)} filas)")
            for fila in filas:
                insert = postgresql.insert(t).values(**fila).on_conflict_do_nothing()
                out.append(str(insert.compile(dialect=postgresql.dialect(),
                                              compile_kwargs={"literal_binds": True})) + ";")
            if "id" in t.c:
                out.append(f"SELECT setval(pg_get_serial_sequence('{t.name}', 'id'), "
                           f"COALESCE((SELECT MAX(id) FROM {t.name}), 0) + 1, false);")
            out.append("")

    with open(SALIDA, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(out) + "\n")
    print(f"OK: {len(tablas)} tablas exportadas -> {SALIDA}")


if __name__ == "__main__":
    main()
