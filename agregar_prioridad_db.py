"""
Agrega a la tabla reportes las 3 columnas de la HU-10. Se puede ejecutar varias veces.
Ejecutar DENTRO de la carpeta BACKEND:   .\\venv\\Scripts\\python agregar_prioridad_db.py
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
for col, tipo in (("vias_afectadas", "INT NULL"), ("area_afectada", "INT NULL"), ("riesgo_propagacion", "VARCHAR(10) NULL")):
    try:
        cur.execute(f"ALTER TABLE reportes ADD COLUMN {col} {tipo}")
        con.commit()
        print("OK        columna reportes." + col)
    except pymysql.err.MySQLError as e:
        if e.args[0] == 1060:
            print("YA EXISTE columna reportes." + col)
        else:
            print("ERROR    ", col, e)
con.close()
