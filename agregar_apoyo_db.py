"""
HU-11: crea la tabla reporte_apoyo (organismos de apoyo de cada emergencia).
Se puede ejecutar varias veces sin problema. No toca los datos existentes.
Ejecutar DENTRO de la carpeta BACKEND:   .\\venv\\Scripts\\python agregar_apoyo_db.py
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
    cur.execute("SHOW TABLES LIKE 'reporte_apoyo'")
    existe = cur.fetchone() is not None
    cur.execute(
        "CREATE TABLE IF NOT EXISTS reporte_apoyo ("
        " reporte_id INT NOT NULL,"
        " organismo_id INT NOT NULL,"
        " fecha DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,"
        " PRIMARY KEY (reporte_id, organismo_id),"
        " CONSTRAINT fk_apoyo_reporte FOREIGN KEY (reporte_id) REFERENCES reportes(id) ON DELETE CASCADE,"
        " CONSTRAINT fk_apoyo_organismo FOREIGN KEY (organismo_id) REFERENCES organismos(id)"
        ") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4"
    )
    con.commit()
    print("YA EXISTE tabla reporte_apoyo" if existe else "OK        tabla reporte_apoyo creada")
except pymysql.err.MySQLError as e:
    print("ERROR    ", e)
con.close()
