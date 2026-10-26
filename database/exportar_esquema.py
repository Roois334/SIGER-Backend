"""
Exporta el ESQUEMA de la base de SIGER (tablas y triggers) y los datos de CATALOGO
(roles, municipios, organismos y su relacion) a database/siger_db.sql.
NO exporta usuarios, reportes ni contrasenas.

Uso (desde la carpeta BACKEND, con el .env configurado):
    python database/exportar_esquema.py
"""
import datetime
import os
import re
import sys

import pymysql
from dotenv import load_dotenv

AQUI = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(AQUI, "..", ".env"))
SALIDA = os.path.join(AQUI, "siger_db.sql")
TABLAS_CON_DATOS = ["roles", "municipios", "organismos", "organismo_municipio"]


def main():
    try:
        con = pymysql.connect(
            host=os.environ["DB_HOST"], port=int(os.environ.get("DB_PORT", "3306")),
            user=os.environ["DB_USER"], password=os.environ["DB_PASSWORD"],
            database=os.environ["DB_NAME"], connect_timeout=15, charset="utf8mb4",
        )
    except KeyError as e:
        sys.exit(f"Falta la variable {e} en el .env")
    cur = con.cursor()

    cur.execute("SHOW FULL TABLES WHERE Table_type = 'BASE TABLE'")
    tablas = sorted(f[0] for f in cur.fetchall())

    out = [
        "-- SIGER: esquema de la base de datos y datos de catalogo",
        f"-- Generado el {datetime.date.today().isoformat()} con database/exportar_esquema.py",
        "-- No incluye usuarios, reportes ni contrasenas.",
        "SET NAMES utf8mb4;",
        "SET FOREIGN_KEY_CHECKS = 0;",
        "",
    ]
    for t in tablas:
        cur.execute(f"SHOW CREATE TABLE `{t}`")
        ddl = cur.fetchone()[1]
        ddl = re.sub(r" AUTO_INCREMENT=\d+", "", ddl)
        ddl = ddl.replace("CREATE TABLE", "CREATE TABLE IF NOT EXISTS", 1)
        out += [f"-- Tabla {t}", ddl + ";", ""]

    for t in TABLAS_CON_DATOS:
        if t not in tablas:
            continue
        cur.execute(f"SELECT * FROM `{t}`")
        columnas = [d[0] for d in cur.description]
        filas = cur.fetchall()
        if not filas:
            continue
        out.append(f"-- Datos de {t} ({len(filas)} filas)")
        cols = ", ".join(f"`{c}`" for c in columnas)
        for fila in filas:
            valores = ", ".join(con.escape(v) for v in fila)
            out.append(f"INSERT IGNORE INTO `{t}` ({cols}) VALUES ({valores});")
        out.append("")

    try:
        cur.execute("SHOW TRIGGERS")
        triggers = [r[0] for r in cur.fetchall()]
        for nombre in triggers:
            cur.execute(f"SHOW CREATE TRIGGER `{nombre}`")
            sql = cur.fetchone()[2]
            sql = re.sub(r"DEFINER=`[^`]*`@`[^`]*`\s*", "", sql)
            out += [f"-- Trigger {nombre}", "DELIMITER $$", sql + "$$", "DELIMITER ;", ""]
    except pymysql.err.MySQLError as e:
        out.append(f"-- (No se pudieron leer los triggers: {e})")

    out.append("SET FOREIGN_KEY_CHECKS = 1;")
    with open(SALIDA, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(out) + "\n")
    con.close()
    print(f"OK: {len(tablas)} tablas exportadas -> {SALIDA}")
    for t in TABLAS_CON_DATOS:
        if t in tablas:
            print("   con datos:", t)


if __name__ == "__main__":
    main()
