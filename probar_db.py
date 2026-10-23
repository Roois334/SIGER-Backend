from dotenv import load_dotenv
load_dotenv()
import os, pymysql

print("Host:", os.environ.get("DB_HOST"), "Puerto:", os.environ.get("DB_PORT"))
print("Usuario:", os.environ.get("DB_USER"), "BD:", os.environ.get("DB_NAME"))
print("Hay contraseña:", bool(os.environ.get("DB_PASSWORD")))

try:
    c = pymysql.connect(
        host=os.environ["DB_HOST"],
        port=int(os.environ["DB_PORT"]),
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        database=os.environ["DB_NAME"],
        connect_timeout=15,
    )
    print("CONEXION OK")
    c.close()
except Exception as e:
    print("ERROR:", e)