# SIGER – Backend

**Sistema de Gestión de Emergencias Regional (Sabana de Occidente).** API REST en Flask que atiende al
frontend de SIGER: usuarios, municipios, organismos de atención,
reportes de emergencia, asignación, seguimiento, mapa público, estadísticas y recuperación de contraseña.

> El frontend y el backend son dos aplicaciones independientes. Primero se levanta el backend (puerto 5000)
> y después el frontend (puerto 5001).

## Tecnologías

Python 3.12 · Flask 3 · Flask-JWT-Extended · Flask-SQLAlchemy / SQLAlchemy 2 · psycopg2 · Flask-CORS · python-dotenv · PostgreSQL (Azure Database for PostgreSQL). También funciona con MySQL / MariaDB (PyMySQL).

## Estructura

```
BACKEND/
├── app.py                 # crea la app, registra los blueprints
├── config.py              # configuración desde variables de entorno (.env)
├── extensions.py          # instancia de SQLAlchemy
├── controllers/           # rutas HTTP (auth, usuarios, catálogos, reportes)
├── services/              # lógica de negocio y reglas (reporte_service.py es el núcleo)
├── models/                # tablas (SQLAlchemy)
├── dtos/                  # objetos que viajan entre capas / hacia el cliente
├── utilities/             # permisos por rol, validaciones, limitador de intentos, correo, prioridad
├── database/              # esquema SQL y script para exportarlo
├── static/correo/         # imágenes de los correos
└── uploads_privados/      # evidencias subidas (no se versiona; se crea sola)
```

Capas: **controllers → services → models/dtos**. Los controladores no tienen reglas de negocio; los servicios no
conocen HTTP.

## Puesta en marcha

### 1. Entorno virtual y dependencias

```powershell
cd BACKEND
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Base de datos

La base del proyecto está en **Azure Database for PostgreSQL** (servidor `siger-pg-2716`, grupo de recursos
`siger-rg`). Para montar una base **nueva** en PostgreSQL, créala vacía (por ejemplo `siger_db`) e impórtale el esquema:

```powershell
psql "host=TU_HOST user=TU_USUARIO dbname=siger_db sslmode=require" -f database/siger_db.sql
```

El archivo `database/siger_db.sql` crea todas las tablas e inserta los datos de catálogo (roles, municipios,
organismos y su relación). **No trae usuarios.** Con una herramienta gráfica (pgAdmin, DBeaver, Azure Data Studio)
basta con ejecutar ese archivo sobre la base vacía. Se puede ejecutar varias veces sin duplicar nada.

Para pasar datos de una base MySQL antigua a PostgreSQL: `python database/migrar_mysql_a_postgres.py URL_MYSQL URL_POSTGRES`.

### 3. Variables de entorno

Copia `.env.example` como `.env` y completa los valores:

```powershell
copy .env.example .env
```

| Variable | Obligatoria | Para qué sirve |
|---|---|---|
| `SECRET_KEY` | Sí | Clave larga y aleatoria. Sin ella el servidor no arranca (salvo en modo depuración). |
| `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME` | Sí | Conexión a la base de datos. |
| `DB_ENGINE` | No | `postgresql` (por defecto) o `mysql`. |
| `DB_SSLMODE` | No | Cifrado de PostgreSQL (por defecto `require`, obligatorio en Azure). |
| `DATA_DIR` | No | Carpeta para evidencias y fotos de perfil (en Azure: `/home/data`). |
| `DATABASE_URL` | No | Alternativa a las `DB_*`: URL completa de SQLAlchemy. |
| `JWT_SECRET_KEY` | No | Clave de los tokens (por defecto usa `SECRET_KEY`). |
| `JWT_EXPIRES_MINUTES` | No | Duración del token en minutos (por defecto 20). |
| `FRONTEND_URL` | No | Dirección del frontend (CORS y enlace del correo de recuperación). |
| `MAIL_USER`, `MAIL_PASSWORD`, `MAIL_NOMBRE`, `MAIL_HOST`, `MAIL_PORT` | No | Envío de correos con Gmail. Sin ellos, el enlace de recuperación se imprime en la consola del backend. |
| `FLASK_DEBUG` | No | `1` activa el modo depuración (solo en desarrollo). |

Genera una `SECRET_KEY` con: `python -c "import secrets; print(secrets.token_hex(32))"`.

### 4. Ejecutar

```powershell
python app.py
```

La API queda en `http://127.0.0.1:5000`. En `/` responde "Hola SIGER-Backend esta funcionando".

### 5. Crear el primer administrador

El registro público siempre crea ciudadanos. Para tener un administrador: regístrate desde el frontend y
luego, en la base de datos, cambia el rol de esa cuenta:

```sql
UPDATE usuarios
SET rol_id = (SELECT id FROM roles WHERE nombre = 'administrador')
WHERE email = 'tu_correo@ejemplo.com';
```

Desde ahí, el administrador crea y asigna roles al resto de usuarios (gestores y organismos) desde el frontend.

## Roles

| Rol | Qué puede hacer |
|---|---|
| `ciudadano` | Registrar emergencias, ver sus reportes y el mapa de emergencias activas de la comunidad (datos recortados, sin información personal). |
| `gestor_municipal` | Ver las emergencias de **su** municipio, aceptarlas y asignarlas a un organismo, evaluar la prioridad, cambiar el tipo, descartar y cerrar; ver estadísticas de su municipio. |
| `organismo_atencion` | Ver solo lo que el gestor asignó a **su** organismo; iniciar la atención, marcar resuelto o devolver el reporte al gestor. |
| `administrador` | Todo lo anterior sin límite de municipio, además de administrar usuarios, municipios y organismos. |

La matriz está en `utilities/permisos.py`; es el único lugar donde se cambia qué puede hacer cada rol.

## Ciclo de vida de una emergencia

```
pendiente → asignado → en_atencion → resuelto → cerrado
     │          │
     │          └── (el organismo la devuelve) → pendiente
     └── descartado (falsa alarma o duplicado)
```

- El ciudadano crea el reporte (**pendiente**). Municipio, tipo, ubicación, descripción, afectados, heridos y evidencias (fotos, video o PDF).
- El gestor lo acepta asignándolo a un organismo del municipio (**asignado**) y puede fijar las variables de prioridad.
- El organismo inicia la atención (**en_atención**) y la marca como **resuelto**.
- El gestor confirma y **cierra** la emergencia.
- Cada cambio queda en `reporte_historial` con autor, fecha y comentario.

**Prioridad (`utilities/prioridad.py`).** Se calcula con puntos: personas afectadas, heridos, vías afectadas,
área afectada (m²) y riesgo de propagación. El tipo de emergencia pone un mínimo (por ejemplo, una fuga nunca baja
de "crítica"). El gestor puede aceptar el cálculo o fijar la prioridad a mano. Los umbrales se ajustan en ese archivo.

## API

Todas las rutas (salvo registro, login y recuperación de contraseña) exigen `Authorization: Bearer <token>`.

| Grupo | Rutas principales |
|---|---|
| `/api/auth` | `POST /register`, `POST /login`, `POST /olvide-password`, `GET /restablecer/<token>`, `POST /restablecer` |
| `/api/usuarios` | `GET /me`, `PUT /me`, `PUT /me/email`, `PUT /me/password`, `POST/DELETE /me/foto`; administración: `GET ""`, `GET/PUT /<id>`, `PATCH /<id>/estado` |
| `/api/municipios` | `GET ""`, `GET /activos`, `POST ""`, `GET/PUT /<id>`, `PATCH /<id>/estado` |
| `/api/organismos` | `GET ""`, `POST ""`, `GET/PUT /<id>`, `PATCH /<id>/estado`, `PUT /<id>/municipios` |
| `/api/reportes` | `POST ""` (crear), `GET ""` (mis reportes), `GET /gestion` (listado con filtros `q, tipo, estado, prioridad, municipio_id, desde, hasta`), `GET /<id>`, `POST /<id>/asignar`, `POST /<id>/estado` (iniciar, resolver, devolver, descartar, cerrar), `POST /<id>/tipo`, `GET /estadisticas`, `GET /publico`, `GET /configuracion`, `GET /evidencias/<id>` |

## Seguridad

- Contraseñas con hash (Werkzeug); mínimo 8 caracteres con letras y números.
- JWT de 2 horas; cada petición vuelve a comprobar en la base que el usuario siga activo y con su rol actual.
- Limitador de intentos de login (5 intentos / 15 min, **en memoria**: con varios procesos habría que usar Redis).
- Permisos por rol y por municipio/organismo validados siempre en el servidor.
- Evidencias en carpeta privada, servidas solo a quien puede ver el reporte; se valida extensión, tipo, firma del archivo y tamaño.
- El mapa público entrega únicamente tipo, prioridad, estado, municipio, fecha y ubicación aproximada (~100 m), de emergencias ya aceptadas por un gestor.
- CORS limitado al frontend. Sin `SECRET_KEY` el servidor no arranca.

## Notas y limitaciones conocidas

- La app se conecta con el usuario administrador del servidor PostgreSQL. En producción conviene crear un usuario solo con `SELECT/INSERT/UPDATE/DELETE`.
- La app no ejecuta `db.create_all()`: la estructura sale de `database/siger_db.sql`. Si cambias un modelo, actualiza la base y vuelve a exportar el esquema.
- Para regenerar el esquema: `python database/exportar_esquema.py` (tablas desde los modelos y catálogos desde la base del `.env`).
- No hay pruebas automáticas todavía; las funciones se probaron manualmente por rol.

## Publicación en Azure

La aplicación está publicada en Azure App Service (plan gratuito F1, grupo de recursos `siger-rg`):

- Sitio: https://siger-frontend-2716.azurewebsites.net
- API: https://siger-backend-2716.azurewebsites.net

**Se publica sola**: cada vez que se sube algo a la rama `main`, GitHub Actions
(`.github/workflows/publicar-azure.yml`) empaqueta el código y lo despliega en `siger-backend-2716`.
El avance se ve en la pestaña **Actions** del repositorio. También se puede lanzar a mano desde ahí
("Run workflow").

- Trabajen en `dev` y pasen los cambios a `main` (pull request) solo cuando estén probados.
- No usa contraseñas: Azure confía en GitHub mediante la identidad administrada `siger-github-deploy`,
  que solo tiene permiso para publicar en las aplicaciones de SIGER.
- Las claves (base de datos, correo, `SECRET_KEY`) **no** están en el repositorio: se configuran en
  Azure, en la aplicación → *Configuración → Variables de entorno*.
