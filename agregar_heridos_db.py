"""
Agrega la columna "heridos" a la tabla reportes. Se puede ejecutar varias veces sin problema.
Ejecutar DENTRO de la carpeta BACKEND:   .\\venv\\Scripts\\python agregar_heridos_db.py
"""
import os
import pymysql
from dotenv import load_dotenv

load_dotenv()
con = pymysql.connect(
    host=os.environ["DB_HOST"], port=int(os.environ.get("DB_PORT", "3306")),
    user=os.environ["DB_USER"], password=os.environ["DB_PASSWORD"],
    database=os.environ["DB_NAME"], connect_timeout=15,
)
cur = con.cursor()
try:
    cur.execute("ALTER TABLE reportes ADD COLUMN heridos INT NOT NULL DEFAULT 0")
    con.commit()
    print("OK        columna reportes.heridos creada (los reportes anteriores quedan en 0)")
except pymysql.err.MySQLError as e:
    if e.args[0] == 1060:
        print("YA EXISTE columna reportes.heridos")
    else:
        print("ERROR    ", e)
cur.execute("SELECT COUNT(*) FROM reportes")
print("Reportes en la base:", cur.fetchone()[0])
con.close()
