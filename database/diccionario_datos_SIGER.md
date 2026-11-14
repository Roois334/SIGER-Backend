# Diccionario de datos – SIGER

Base de datos PostgreSQL. Generado a partir de `database/siger_db.sql` y `models/`.

**Convenciones:** PK = clave primaria · FK = clave foránea · UQ = valor único · Nulo = SI significa que el campo es opcional.

## Tablas

| Tabla | Descripción |
|---|---|
| `roles` | Perfiles de acceso del sistema. |
| `municipios` | Municipios de la Sabana de Occidente que cubre el sistema. |
| `organismos` | Entidades de atención de emergencias (Bomberos, Cruz Roja, Policía, etc.). |
| `organismo_municipio` | Tabla intermedia (N:M): en qué municipios opera cada organismo. |
| `usuarios` | Personas que usan el sistema (ciudadanos, gestores, organismos y administradores). |
| `password_resets` | Enlaces de un solo uso para recuperar la contraseña. |
| `reportes` | Reportes de emergencia hechos por ciudadanos; tabla central del sistema. |
| `evidencias` | Archivos (fotos/videos) adjuntos a un reporte. |
| `reporte_apoyo` | Tabla intermedia (N:M): organismos de apoyo de una emergencia (el principal está en reportes.organismo_id). |
| `reporte_historial` | Bitácora de cada cambio importante de un reporte. |
| `notificaciones` | Avisos para un usuario cuando cambia algo en una emergencia (HU-15). |

## roles

Perfiles de acceso del sistema.

| Campo | Tipo | Nulo | Clave | Referencia | Defecto | Descripción |
|---|---|---|---|---|---|---|
| `id` | SERIAL (INTEGER) | NO | PK |  | autoincremental | Identificador del rol. |
| `nombre` | VARCHAR(40) | NO | UQ |  |  | Nombre del rol: ciudadano, gestor_municipal, organismo_atencion, administrador. |
| `descripcion` | VARCHAR(150) | SI |  |  |  | Explicación de lo que puede hacer el rol. |

## municipios

Municipios de la Sabana de Occidente que cubre el sistema.

| Campo | Tipo | Nulo | Clave | Referencia | Defecto | Descripción |
|---|---|---|---|---|---|---|
| `id` | SERIAL (INTEGER) | NO | PK |  | autoincremental | Identificador del municipio. |
| `codigo` | VARCHAR(20) | NO | UQ |  |  | Código corto (FAC, MAD, MOS, FUN, BOJ, ROS, SUB, ZIP). |
| `nombre` | VARCHAR(80) | NO | UQ |  |  | Nombre del municipio. |
| `activo` | BOOLEAN | NO |  |  | true | Indica si el municipio está habilitado. |
| `fecha_creacion` | TIMESTAMP | SI |  |  | now() | Fecha de creación del registro. |
| `fecha_actualizacion` | TIMESTAMP | SI |  |  | now() | Fecha de la última modificación (se actualiza sola). |

## organismos

Entidades de atención de emergencias (Bomberos, Cruz Roja, Policía, etc.).

| Campo | Tipo | Nulo | Clave | Referencia | Defecto | Descripción |
|---|---|---|---|---|---|---|
| `id` | SERIAL (INTEGER) | NO | PK |  | autoincremental | Identificador del organismo. |
| `codigo` | VARCHAR(20) | NO | UQ |  |  | Código corto (BOM, CRC, DEF, POL, SAL, TRA, GRD, SSP, CAR). |
| `nombre` | VARCHAR(120) | NO | UQ |  |  | Nombre del organismo. |
| `tipo` | VARCHAR(60) | SI |  |  |  | Categoría: Bomberos, Socorro, Seguridad, Salud, Transito, Gestion del riesgo, Servicios publicos, Ambiental. |
| `activo` | BOOLEAN | NO |  |  | true | Indica si el organismo está habilitado. |
| `fecha_creacion` | TIMESTAMP | SI |  |  | now() | Fecha de creación del registro. |
| `fecha_actualizacion` | TIMESTAMP | SI |  |  | now() | Fecha de la última modificación. |

## organismo_municipio

Tabla intermedia (N:M): en qué municipios opera cada organismo.

| Campo | Tipo | Nulo | Clave | Referencia | Defecto | Descripción |
|---|---|---|---|---|---|---|
| `organismo_id` | INTEGER | NO | PK, FK | organismos.id |  | Organismo. |
| `municipio_id` | INTEGER | NO | PK, FK | municipios.id |  | Municipio donde opera. |

## usuarios

Personas que usan el sistema (ciudadanos, gestores, organismos y administradores).

| Campo | Tipo | Nulo | Clave | Referencia | Defecto | Descripción |
|---|---|---|---|---|---|---|
| `id` | SERIAL (INTEGER) | NO | PK |  | autoincremental | Identificador del usuario. |
| `nombre` | VARCHAR(80) | NO |  |  |  | Nombres. |
| `apellido` | VARCHAR(80) | NO |  |  |  | Apellidos. |
| `email` | VARCHAR(120) | NO | UQ |  |  | Correo electrónico; se usa para iniciar sesión. |
| `password_hash` | VARCHAR(255) | NO |  |  |  | Contraseña cifrada (hash). Nunca se guarda en texto plano. |
| `rol_id` | INTEGER | NO | FK | roles.id |  | Rol del usuario. |
| `municipio_id` | INTEGER | SI | FK | municipios.id |  | Municipio del usuario (ej. el que gestiona un gestor municipal). |
| `organismo_id` | INTEGER | SI | FK | organismos.id |  | Organismo al que pertenece; solo para rol organismo_atencion. |
| `activo` | BOOLEAN | NO |  |  | true | Si la cuenta está habilitada. |
| `foto_url` | VARCHAR(255) | SI |  |  |  | Ruta/URL de la foto de perfil. |
| `tipo_documento` | VARCHAR(10) | SI |  |  |  | CC, CE, TI o PP. |
| `documento` | VARCHAR(20) | SI |  |  |  | Número de documento de identidad. |
| `telefono` | VARCHAR(20) | SI |  |  |  | Teléfono de contacto. |
| `fecha_creacion` | TIMESTAMP | SI |  |  | now() | Fecha de registro. |
| `fecha_actualizacion` | TIMESTAMP | SI |  |  | now() | Fecha de la última modificación. |

## password_resets

Enlaces de un solo uso para recuperar la contraseña.

| Campo | Tipo | Nulo | Clave | Referencia | Defecto | Descripción |
|---|---|---|---|---|---|---|
| `id` | SERIAL (INTEGER) | NO | PK |  | autoincremental | Identificador. |
| `usuario_id` | INTEGER | NO | FK (índice) | usuarios.id |  | Usuario que pidió la recuperación. |
| `token_hash` | VARCHAR(64) | NO | UQ |  |  | Hash del token enviado por correo (el token real no se guarda). |
| `expira` | TIMESTAMP | NO |  |  |  | Fecha límite de validez del enlace. |
| `usado` | BOOLEAN | NO |  |  | false | Si el enlace ya fue utilizado. |
| `fecha_creacion` | TIMESTAMP | NO |  |  |  | Fecha en que se generó el enlace. |

## reportes

Reportes de emergencia hechos por ciudadanos; tabla central del sistema.

| Campo | Tipo | Nulo | Clave | Referencia | Defecto | Descripción |
|---|---|---|---|---|---|---|
| `id` | SERIAL (INTEGER) | NO | PK |  | autoincremental | Identificador interno. |
| `folio` | VARCHAR(30) | NO | UQ |  |  | Código visible del reporte para seguimiento. |
| `ciudadano_id` | INTEGER | NO | FK | usuarios.id |  | Ciudadano que reporta. |
| `municipio_id` | INTEGER | NO | FK | municipios.id |  | Municipio donde ocurre la emergencia. |
| `tipo` | VARCHAR(60) | NO |  |  |  | Incendio, Inundacion, Accidente de transito, Deslizamiento, Fuga o derrame de sustancias, Emergencia medica, Otro. |
| `prioridad` | VARCHAR(20) | NO |  |  | media | baja, media, alta o critica. Se calcula con tipo, afectados, heridos, vías, área y riesgo. |
| `descripcion` | TEXT | NO |  |  |  | Descripción de lo ocurrido. |
| `direccion` | VARCHAR(200) | NO |  |  |  | Dirección o referencia del lugar. |
| `latitud` | FLOAT | SI |  |  |  | Coordenada geográfica (mapa). |
| `longitud` | FLOAT | SI |  |  |  | Coordenada geográfica (mapa). |
| `afectados` | INTEGER | NO |  |  | 0 | Número de personas afectadas. |
| `heridos` | INTEGER | NO |  |  | 0 | Número de personas heridas. |
| `vias_afectadas` | INTEGER | SI |  |  |  | Número de vías afectadas (variable de prioridad, HU-10). |
| `area_afectada` | INTEGER | SI |  |  |  | Área afectada en metros cuadrados (HU-10). |
| `riesgo_propagacion` | VARCHAR(10) | SI |  |  |  | bajo, medio o alto (HU-10). |
| `estado` | VARCHAR(20) | NO |  |  | pendiente | pendiente → asignado → en_atencion → resuelto → cerrado; o descartado. |
| `organismo_id` | INTEGER | SI | FK | organismos.id |  | Organismo principal asignado. |
| `asignado_por_id` | INTEGER | SI | FK | usuarios.id |  | Gestor que hizo la asignación. |
| `fecha_asignacion` | TIMESTAMP | SI |  |  |  | Fecha de la asignación. |
| `fecha_hora` | TIMESTAMP | NO |  |  | now() | Fecha y hora de la emergencia/reporte. |
| `fecha_creacion` | TIMESTAMP | SI |  |  | now() | Fecha de creación del registro. |
| `fecha_actualizacion` | TIMESTAMP | SI |  |  | now() | Fecha de la última modificación. |

## evidencias

Archivos (fotos/videos) adjuntos a un reporte.

| Campo | Tipo | Nulo | Clave | Referencia | Defecto | Descripción |
|---|---|---|---|---|---|---|
| `id` | SERIAL (INTEGER) | NO | PK |  | autoincremental | Identificador. |
| `reporte_id` | INTEGER | NO | FK | reportes.id |  | Reporte al que pertenece. |
| `nombre_archivo` | VARCHAR(255) | NO |  |  |  | Nombre original del archivo. |
| `ruta_archivo` | VARCHAR(300) | NO |  |  |  | Ruta donde se guardó (carpeta uploads_privados). |
| `fecha_carga` | TIMESTAMP | SI |  |  | now() | Fecha en que se subió. |

## reporte_apoyo

Tabla intermedia (N:M): organismos de apoyo de una emergencia (el principal está en reportes.organismo_id).

| Campo | Tipo | Nulo | Clave | Referencia | Defecto | Descripción |
|---|---|---|---|---|---|---|
| `reporte_id` | INTEGER | NO | PK, FK | reportes.id |  | Reporte. |
| `organismo_id` | INTEGER | NO | PK, FK | organismos.id |  | Organismo de apoyo. |
| `fecha` | TIMESTAMP | SI |  |  | now() | Fecha en que se agregó el apoyo. |

## reporte_historial

Bitácora de cada cambio importante de un reporte.

| Campo | Tipo | Nulo | Clave | Referencia | Defecto | Descripción |
|---|---|---|---|---|---|---|
| `id` | SERIAL (INTEGER) | NO | PK |  | autoincremental | Identificador. |
| `reporte_id` | INTEGER | NO | FK | reportes.id |  | Reporte afectado. |
| `usuario_id` | INTEGER | SI | FK | usuarios.id |  | Usuario que realizó la acción. |
| `accion` | VARCHAR(20) | NO |  |  |  | asignar, reasignar, iniciar, resolver, devolver, descartar, cerrar, apoyo, reclasificar. |
| `estado_anterior` | VARCHAR(20) | SI |  |  |  | Estado antes del cambio. |
| `estado_nuevo` | VARCHAR(20) | NO |  |  |  | Estado después del cambio. |
| `comentario` | VARCHAR(300) | SI |  |  |  | Observación de quien hizo la acción. |
| `fecha` | TIMESTAMP | NO |  |  | now() | Fecha y hora del cambio. |

## notificaciones

Avisos para un usuario cuando cambia algo en una emergencia (HU-15).

| Campo | Tipo | Nulo | Clave | Referencia | Defecto | Descripción |
|---|---|---|---|---|---|---|
| `id` | SERIAL (INTEGER) | NO | PK |  | autoincremental | Identificador. |
| `usuario_id` | INTEGER | NO | FK (índice) | usuarios.id |  | Usuario que recibe el aviso. |
| `reporte_id` | INTEGER | SI | FK | reportes.id (ON DELETE CASCADE) |  | Reporte relacionado; si se borra el reporte, se borra el aviso. |
| `tipo` | VARCHAR(30) | NO |  |  |  | Evento: reporte_nuevo, asignado, en_atencion, etc. |
| `titulo` | VARCHAR(150) | NO |  |  |  | Título del aviso. |
| `mensaje` | VARCHAR(300) | NO |  |  |  | Texto del aviso. |
| `leida` | BOOLEAN | NO |  |  | false | Si el usuario ya la leyó. |
| `fecha_creacion` | TIMESTAMP | NO |  |  | now() | Fecha del aviso. |

## Relaciones

```
roles 1──N usuarios
municipios 1──N usuarios
organismos 1──N usuarios
municipios N──M organismos        (organismo_municipio)
usuarios 1──N reportes            (ciudadano_id)
usuarios 1──N reportes            (asignado_por_id)
municipios 1──N reportes
organismos 1──N reportes          (organismo principal)
reportes N──M organismos          (reporte_apoyo)
reportes 1──N evidencias
reportes 1──N reporte_historial
usuarios 1──N reporte_historial
usuarios 1──N notificaciones
reportes 1──N notificaciones
usuarios 1──N password_resets
```
