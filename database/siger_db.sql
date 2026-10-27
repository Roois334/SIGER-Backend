-- SIGER: esquema de la base de datos (PostgreSQL) y datos de catalogo
-- Generado el 2026-10-27 con database/exportar_esquema.py
-- No incluye usuarios, reportes ni contrasenas.

-- Tabla municipios
CREATE TABLE IF NOT EXISTS municipios (
	id SERIAL NOT NULL, 
	codigo VARCHAR(20) NOT NULL, 
	nombre VARCHAR(80) NOT NULL, 
	activo BOOLEAN NOT NULL, 
	fecha_creacion TIMESTAMP WITHOUT TIME ZONE DEFAULT now(), 
	fecha_actualizacion TIMESTAMP WITHOUT TIME ZONE DEFAULT now(), 
	PRIMARY KEY (id), 
	UNIQUE (codigo), 
	UNIQUE (nombre)
);

-- Tabla organismos
CREATE TABLE IF NOT EXISTS organismos (
	id SERIAL NOT NULL, 
	codigo VARCHAR(20) NOT NULL, 
	nombre VARCHAR(120) NOT NULL, 
	tipo VARCHAR(60), 
	activo BOOLEAN NOT NULL, 
	fecha_creacion TIMESTAMP WITHOUT TIME ZONE DEFAULT now(), 
	fecha_actualizacion TIMESTAMP WITHOUT TIME ZONE DEFAULT now(), 
	PRIMARY KEY (id), 
	UNIQUE (codigo), 
	UNIQUE (nombre)
);

-- Tabla roles
CREATE TABLE IF NOT EXISTS roles (
	id SERIAL NOT NULL, 
	nombre VARCHAR(40) NOT NULL, 
	descripcion VARCHAR(150), 
	PRIMARY KEY (id), 
	UNIQUE (nombre)
);

-- Tabla organismo_municipio
CREATE TABLE IF NOT EXISTS organismo_municipio (
	organismo_id INTEGER NOT NULL, 
	municipio_id INTEGER NOT NULL, 
	PRIMARY KEY (organismo_id, municipio_id), 
	FOREIGN KEY(organismo_id) REFERENCES organismos (id), 
	FOREIGN KEY(municipio_id) REFERENCES municipios (id)
);

-- Tabla usuarios
CREATE TABLE IF NOT EXISTS usuarios (
	id SERIAL NOT NULL, 
	nombre VARCHAR(80) NOT NULL, 
	apellido VARCHAR(80) NOT NULL, 
	email VARCHAR(120) NOT NULL, 
	password_hash VARCHAR(255) NOT NULL, 
	rol_id INTEGER NOT NULL, 
	municipio_id INTEGER, 
	organismo_id INTEGER, 
	activo BOOLEAN NOT NULL, 
	foto_url VARCHAR(255), 
	tipo_documento VARCHAR(10), 
	documento VARCHAR(20), 
	telefono VARCHAR(20), 
	fecha_creacion TIMESTAMP WITHOUT TIME ZONE DEFAULT now(), 
	fecha_actualizacion TIMESTAMP WITHOUT TIME ZONE DEFAULT now(), 
	PRIMARY KEY (id), 
	UNIQUE (email), 
	FOREIGN KEY(rol_id) REFERENCES roles (id), 
	FOREIGN KEY(municipio_id) REFERENCES municipios (id), 
	FOREIGN KEY(organismo_id) REFERENCES organismos (id)
);

-- Tabla password_resets
CREATE TABLE IF NOT EXISTS password_resets (
	id SERIAL NOT NULL, 
	usuario_id INTEGER NOT NULL, 
	token_hash VARCHAR(64) NOT NULL, 
	expira TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	usado BOOLEAN NOT NULL, 
	fecha_creacion TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(usuario_id) REFERENCES usuarios (id), 
	UNIQUE (token_hash)
);
CREATE INDEX IF NOT EXISTS ix_password_resets_usuario_id ON password_resets (usuario_id);

-- Tabla reportes
CREATE TABLE IF NOT EXISTS reportes (
	id SERIAL NOT NULL, 
	folio VARCHAR(30) NOT NULL, 
	ciudadano_id INTEGER NOT NULL, 
	municipio_id INTEGER NOT NULL, 
	tipo VARCHAR(60) NOT NULL, 
	prioridad VARCHAR(20) NOT NULL, 
	descripcion TEXT NOT NULL, 
	direccion VARCHAR(200) NOT NULL, 
	latitud FLOAT, 
	longitud FLOAT, 
	afectados INTEGER NOT NULL, 
	heridos INTEGER NOT NULL, 
	vias_afectadas INTEGER, 
	area_afectada INTEGER, 
	riesgo_propagacion VARCHAR(10), 
	estado VARCHAR(20) NOT NULL, 
	organismo_id INTEGER, 
	asignado_por_id INTEGER, 
	fecha_asignacion TIMESTAMP WITHOUT TIME ZONE, 
	fecha_hora TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
	fecha_creacion TIMESTAMP WITHOUT TIME ZONE DEFAULT now(), 
	fecha_actualizacion TIMESTAMP WITHOUT TIME ZONE DEFAULT now(), 
	PRIMARY KEY (id), 
	UNIQUE (folio), 
	FOREIGN KEY(ciudadano_id) REFERENCES usuarios (id), 
	FOREIGN KEY(municipio_id) REFERENCES municipios (id), 
	FOREIGN KEY(organismo_id) REFERENCES organismos (id), 
	FOREIGN KEY(asignado_por_id) REFERENCES usuarios (id)
);

-- Tabla evidencias
CREATE TABLE IF NOT EXISTS evidencias (
	id SERIAL NOT NULL, 
	reporte_id INTEGER NOT NULL, 
	nombre_archivo VARCHAR(255) NOT NULL, 
	ruta_archivo VARCHAR(300) NOT NULL, 
	fecha_carga TIMESTAMP WITHOUT TIME ZONE DEFAULT now(), 
	PRIMARY KEY (id), 
	FOREIGN KEY(reporte_id) REFERENCES reportes (id)
);

-- Tabla notificaciones
CREATE TABLE IF NOT EXISTS notificaciones (
	id SERIAL NOT NULL, 
	usuario_id INTEGER NOT NULL, 
	reporte_id INTEGER, 
	tipo VARCHAR(30) NOT NULL, 
	titulo VARCHAR(150) NOT NULL, 
	mensaje VARCHAR(300) NOT NULL, 
	leida BOOLEAN NOT NULL, 
	fecha_creacion TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(usuario_id) REFERENCES usuarios (id), 
	FOREIGN KEY(reporte_id) REFERENCES reportes (id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS ix_notificaciones_usuario_id ON notificaciones (usuario_id);

-- Tabla reporte_apoyo
CREATE TABLE IF NOT EXISTS reporte_apoyo (
	reporte_id INTEGER NOT NULL, 
	organismo_id INTEGER NOT NULL, 
	fecha TIMESTAMP WITHOUT TIME ZONE DEFAULT now(), 
	PRIMARY KEY (reporte_id, organismo_id), 
	FOREIGN KEY(reporte_id) REFERENCES reportes (id), 
	FOREIGN KEY(organismo_id) REFERENCES organismos (id)
);

-- Tabla reporte_historial
CREATE TABLE IF NOT EXISTS reporte_historial (
	id SERIAL NOT NULL, 
	reporte_id INTEGER NOT NULL, 
	usuario_id INTEGER, 
	accion VARCHAR(20) NOT NULL, 
	estado_anterior VARCHAR(20), 
	estado_nuevo VARCHAR(20) NOT NULL, 
	comentario VARCHAR(300), 
	fecha TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(reporte_id) REFERENCES reportes (id), 
	FOREIGN KEY(usuario_id) REFERENCES usuarios (id)
);

-- Datos de municipios (8 filas)
INSERT INTO municipios (id, codigo, nombre, activo, fecha_creacion, fecha_actualizacion) VALUES (1, 'FAC', 'Facatativa', true, '2026-09-21 22:11:10', '2026-09-21 22:11:10') ON CONFLICT DO NOTHING;
INSERT INTO municipios (id, codigo, nombre, activo, fecha_creacion, fecha_actualizacion) VALUES (2, 'MAD', 'Madrid', true, '2026-09-21 22:11:10', '2026-09-21 22:11:10') ON CONFLICT DO NOTHING;
INSERT INTO municipios (id, codigo, nombre, activo, fecha_creacion, fecha_actualizacion) VALUES (3, 'MOS', 'Mosquera', true, '2026-09-21 22:11:10', '2026-09-21 22:11:10') ON CONFLICT DO NOTHING;
INSERT INTO municipios (id, codigo, nombre, activo, fecha_creacion, fecha_actualizacion) VALUES (4, 'FUN', 'Funza', true, '2026-09-21 22:11:10', '2026-09-21 22:11:10') ON CONFLICT DO NOTHING;
INSERT INTO municipios (id, codigo, nombre, activo, fecha_creacion, fecha_actualizacion) VALUES (5, 'BOJ', 'Bojaca', true, '2026-09-21 22:11:10', '2026-10-23 02:37:24') ON CONFLICT DO NOTHING;
INSERT INTO municipios (id, codigo, nombre, activo, fecha_creacion, fecha_actualizacion) VALUES (6, 'ROS', 'El Rosal', true, '2026-09-21 22:11:10', '2026-09-21 22:11:10') ON CONFLICT DO NOTHING;
INSERT INTO municipios (id, codigo, nombre, activo, fecha_creacion, fecha_actualizacion) VALUES (7, 'SUB', 'Subachoque', true, '2026-09-21 22:11:10', '2026-09-21 22:11:10') ON CONFLICT DO NOTHING;
INSERT INTO municipios (id, codigo, nombre, activo, fecha_creacion, fecha_actualizacion) VALUES (8, 'ZIP', 'Zipacon', true, '2026-09-21 22:11:10', '2026-09-21 22:11:10') ON CONFLICT DO NOTHING;
SELECT setval(pg_get_serial_sequence('municipios', 'id'), COALESCE((SELECT MAX(id) FROM municipios), 0) + 1, false);

-- Datos de organismos (9 filas)
INSERT INTO organismos (id, codigo, nombre, tipo, activo, fecha_creacion, fecha_actualizacion) VALUES (1, 'BOM', 'Bomberos', 'Bomberos', true, '2026-10-10 20:58:44', '2026-10-10 20:58:44') ON CONFLICT DO NOTHING;
INSERT INTO organismos (id, codigo, nombre, tipo, activo, fecha_creacion, fecha_actualizacion) VALUES (2, 'CRC', 'Cruz Roja Colombiana', 'Socorro', true, '2026-10-10 20:58:44', '2026-10-10 20:58:44') ON CONFLICT DO NOTHING;
INSERT INTO organismos (id, codigo, nombre, tipo, activo, fecha_creacion, fecha_actualizacion) VALUES (3, 'DEF', 'Defensa Civil Colombiana', 'Socorro', true, '2026-10-10 20:58:44', '2026-10-10 20:58:44') ON CONFLICT DO NOTHING;
INSERT INTO organismos (id, codigo, nombre, tipo, activo, fecha_creacion, fecha_actualizacion) VALUES (4, 'POL', 'Policia Nacional', 'Seguridad', true, '2026-10-10 20:58:44', '2026-10-10 20:58:44') ON CONFLICT DO NOTHING;
INSERT INTO organismos (id, codigo, nombre, tipo, activo, fecha_creacion, fecha_actualizacion) VALUES (5, 'SAL', 'Secretaria de Salud y Ambulancias', 'Salud', true, '2026-10-10 20:58:44', '2026-10-10 20:58:44') ON CONFLICT DO NOTHING;
INSERT INTO organismos (id, codigo, nombre, tipo, activo, fecha_creacion, fecha_actualizacion) VALUES (6, 'TRA', 'Transito y Transporte', 'Transito', true, '2026-10-10 20:58:44', '2026-10-10 20:58:44') ON CONFLICT DO NOTHING;
INSERT INTO organismos (id, codigo, nombre, tipo, activo, fecha_creacion, fecha_actualizacion) VALUES (7, 'GRD', 'Gestion del Riesgo', 'Gestion del riesgo', true, '2026-10-10 20:58:44', '2026-10-10 20:58:44') ON CONFLICT DO NOTHING;
INSERT INTO organismos (id, codigo, nombre, tipo, activo, fecha_creacion, fecha_actualizacion) VALUES (8, 'SSP', 'Empresas de Servicios Publicos', 'Servicios publicos', true, '2026-10-10 20:58:44', '2026-10-10 20:58:44') ON CONFLICT DO NOTHING;
INSERT INTO organismos (id, codigo, nombre, tipo, activo, fecha_creacion, fecha_actualizacion) VALUES (9, 'CAR', 'Autoridad Ambiental CAR', 'Ambiental', true, '2026-10-10 20:58:44', '2026-10-10 20:58:44') ON CONFLICT DO NOTHING;
SELECT setval(pg_get_serial_sequence('organismos', 'id'), COALESCE((SELECT MAX(id) FROM organismos), 0) + 1, false);

-- Datos de roles (4 filas)
INSERT INTO roles (id, nombre, descripcion) VALUES (1, 'ciudadano', 'Usuario que reporta emergencias') ON CONFLICT DO NOTHING;
INSERT INTO roles (id, nombre, descripcion) VALUES (2, 'gestor_municipal', 'Gestiona emergencias de su municipio') ON CONFLICT DO NOTHING;
INSERT INTO roles (id, nombre, descripcion) VALUES (3, 'organismo_atencion', 'Bomberos, Cruz Roja, Defensa Civil, Policia, etc.') ON CONFLICT DO NOTHING;
INSERT INTO roles (id, nombre, descripcion) VALUES (4, 'administrador', 'Administra el sistema por completo') ON CONFLICT DO NOTHING;
SELECT setval(pg_get_serial_sequence('roles', 'id'), COALESCE((SELECT MAX(id) FROM roles), 0) + 1, false);

-- Datos de organismo_municipio (72 filas)
INSERT INTO organismo_municipio (organismo_id, municipio_id) VALUES (1, 1) ON CONFLICT DO NOTHING;
INSERT INTO organismo_municipio (organismo_id, municipio_id) VALUES (2, 1) ON CONFLICT DO NOTHING;
INSERT INTO organismo_municipio (organismo_id, municipio_id) VALUES (3, 1) ON CONFLICT DO NOTHING;
INSERT INTO organismo_municipio (organismo_id, municipio_id) VALUES (4, 1) ON CONFLICT DO NOTHING;
INSERT INTO organismo_municipio (organismo_id, municipio_id) VALUES (5, 1) ON CONFLICT DO NOTHING;
INSERT INTO organismo_municipio (organismo_id, municipio_id) VALUES (6, 1) ON CONFLICT DO NOTHING;
INSERT INTO organismo_municipio (organismo_id, municipio_id) VALUES (7, 1) ON CONFLICT DO NOTHING;
INSERT INTO organismo_municipio (organismo_id, municipio_id) VALUES (8, 1) ON CONFLICT DO NOTHING;
INSERT INTO organismo_municipio (organismo_id, municipio_id) VALUES (9, 1) ON CONFLICT DO NOTHING;
INSERT INTO organismo_municipio (organismo_id, municipio_id) VALUES (1, 2) ON CONFLICT DO NOTHING;
INSERT INTO organismo_municipio (organismo_id, municipio_id) VALUES (2, 2) ON CONFLICT DO NOTHING;
INSERT INTO organismo_municipio (organismo_id, municipio_id) VALUES (3, 2) ON CONFLICT DO NOTHING;
INSERT INTO organismo_municipio (organismo_id, municipio_id) VALUES (4, 2) ON CONFLICT DO NOTHING;
INSERT INTO organismo_municipio (organismo_id, municipio_id) VALUES (5, 2) ON CONFLICT DO NOTHING;
INSERT INTO organismo_municipio (organismo_id, municipio_id) VALUES (6, 2) ON CONFLICT DO NOTHING;
INSERT INTO organismo_municipio (organismo_id, municipio_id) VALUES (7, 2) ON CONFLICT DO NOTHING;
INSERT INTO organismo_municipio (organismo_id, municipio_id) VALUES (8, 2) ON CONFLICT DO NOTHING;
INSERT INTO organismo_municipio (organismo_id, municipio_id) VALUES (9, 2) ON CONFLICT DO NOTHING;
INSERT INTO organismo_municipio (organismo_id, municipio_id) VALUES (1, 3) ON CONFLICT DO NOTHING;
INSERT INTO organismo_municipio (organismo_id, municipio_id) VALUES (2, 3) ON CONFLICT DO NOTHING;
INSERT INTO organismo_municipio (organismo_id, municipio_id) VALUES (3, 3) ON CONFLICT DO NOTHING;
INSERT INTO organismo_municipio (organismo_id, municipio_id) VALUES (4, 3) ON CONFLICT DO NOTHING;
INSERT INTO organismo_municipio (organismo_id, municipio_id) VALUES (5, 3) ON CONFLICT DO NOTHING;
INSERT INTO organismo_municipio (organismo_id, municipio_id) VALUES (6, 3) ON CONFLICT DO NOTHING;
INSERT INTO organismo_municipio (organismo_id, municipio_id) VALUES (7, 3) ON CONFLICT DO NOTHING;
INSERT INTO organismo_municipio (organismo_id, municipio_id) VALUES (8, 3) ON CONFLICT DO NOTHING;
INSERT INTO organismo_municipio (organismo_id, municipio_id) VALUES (9, 3) ON CONFLICT DO NOTHING;
INSERT INTO organismo_municipio (organismo_id, municipio_id) VALUES (1, 4) ON CONFLICT DO NOTHING;
INSERT INTO organismo_municipio (organismo_id, municipio_id) VALUES (2, 4) ON CONFLICT DO NOTHING;
INSERT INTO organismo_municipio (organismo_id, municipio_id) VALUES (3, 4) ON CONFLICT DO NOTHING;
INSERT INTO organismo_municipio (organismo_id, municipio_id) VALUES (4, 4) ON CONFLICT DO NOTHING;
INSERT INTO organismo_municipio (organismo_id, municipio_id) VALUES (5, 4) ON CONFLICT DO NOTHING;
INSERT INTO organismo_municipio (organismo_id, municipio_id) VALUES (6, 4) ON CONFLICT DO NOTHING;
INSERT INTO organismo_municipio (organismo_id, municipio_id) VALUES (7, 4) ON CONFLICT DO NOTHING;
INSERT INTO organismo_municipio (organismo_id, municipio_id) VALUES (8, 4) ON CONFLICT DO NOTHING;
INSERT INTO organismo_municipio (organismo_id, municipio_id) VALUES (9, 4) ON CONFLICT DO NOTHING;
INSERT INTO organismo_municipio (organismo_id, municipio_id) VALUES (1, 5) ON CONFLICT DO NOTHING;
INSERT INTO organismo_municipio (organismo_id, municipio_id) VALUES (2, 5) ON CONFLICT DO NOTHING;
INSERT INTO organismo_municipio (organismo_id, municipio_id) VALUES (3, 5) ON CONFLICT DO NOTHING;
INSERT INTO organismo_municipio (organismo_id, municipio_id) VALUES (4, 5) ON CONFLICT DO NOTHING;
INSERT INTO organismo_municipio (organismo_id, municipio_id) VALUES (5, 5) ON CONFLICT DO NOTHING;
INSERT INTO organismo_municipio (organismo_id, municipio_id) VALUES (6, 5) ON CONFLICT DO NOTHING;
INSERT INTO organismo_municipio (organismo_id, municipio_id) VALUES (7, 5) ON CONFLICT DO NOTHING;
INSERT INTO organismo_municipio (organismo_id, municipio_id) VALUES (8, 5) ON CONFLICT DO NOTHING;
INSERT INTO organismo_municipio (organismo_id, municipio_id) VALUES (9, 5) ON CONFLICT DO NOTHING;
INSERT INTO organismo_municipio (organismo_id, municipio_id) VALUES (1, 6) ON CONFLICT DO NOTHING;
INSERT INTO organismo_municipio (organismo_id, municipio_id) VALUES (2, 6) ON CONFLICT DO NOTHING;
INSERT INTO organismo_municipio (organismo_id, municipio_id) VALUES (3, 6) ON CONFLICT DO NOTHING;
INSERT INTO organismo_municipio (organismo_id, municipio_id) VALUES (4, 6) ON CONFLICT DO NOTHING;
INSERT INTO organismo_municipio (organismo_id, municipio_id) VALUES (5, 6) ON CONFLICT DO NOTHING;
INSERT INTO organismo_municipio (organismo_id, municipio_id) VALUES (6, 6) ON CONFLICT DO NOTHING;
INSERT INTO organismo_municipio (organismo_id, municipio_id) VALUES (7, 6) ON CONFLICT DO NOTHING;
INSERT INTO organismo_municipio (organismo_id, municipio_id) VALUES (8, 6) ON CONFLICT DO NOTHING;
INSERT INTO organismo_municipio (organismo_id, municipio_id) VALUES (9, 6) ON CONFLICT DO NOTHING;
INSERT INTO organismo_municipio (organismo_id, municipio_id) VALUES (1, 7) ON CONFLICT DO NOTHING;
INSERT INTO organismo_municipio (organismo_id, municipio_id) VALUES (2, 7) ON CONFLICT DO NOTHING;
INSERT INTO organismo_municipio (organismo_id, municipio_id) VALUES (3, 7) ON CONFLICT DO NOTHING;
INSERT INTO organismo_municipio (organismo_id, municipio_id) VALUES (4, 7) ON CONFLICT DO NOTHING;
INSERT INTO organismo_municipio (organismo_id, municipio_id) VALUES (5, 7) ON CONFLICT DO NOTHING;
INSERT INTO organismo_municipio (organismo_id, municipio_id) VALUES (6, 7) ON CONFLICT DO NOTHING;
INSERT INTO organismo_municipio (organismo_id, municipio_id) VALUES (7, 7) ON CONFLICT DO NOTHING;
INSERT INTO organismo_municipio (organismo_id, municipio_id) VALUES (8, 7) ON CONFLICT DO NOTHING;
INSERT INTO organismo_municipio (organismo_id, municipio_id) VALUES (9, 7) ON CONFLICT DO NOTHING;
INSERT INTO organismo_municipio (organismo_id, municipio_id) VALUES (1, 8) ON CONFLICT DO NOTHING;
INSERT INTO organismo_municipio (organismo_id, municipio_id) VALUES (2, 8) ON CONFLICT DO NOTHING;
INSERT INTO organismo_municipio (organismo_id, municipio_id) VALUES (3, 8) ON CONFLICT DO NOTHING;
INSERT INTO organismo_municipio (organismo_id, municipio_id) VALUES (4, 8) ON CONFLICT DO NOTHING;
INSERT INTO organismo_municipio (organismo_id, municipio_id) VALUES (5, 8) ON CONFLICT DO NOTHING;
INSERT INTO organismo_municipio (organismo_id, municipio_id) VALUES (6, 8) ON CONFLICT DO NOTHING;
INSERT INTO organismo_municipio (organismo_id, municipio_id) VALUES (7, 8) ON CONFLICT DO NOTHING;
INSERT INTO organismo_municipio (organismo_id, municipio_id) VALUES (8, 8) ON CONFLICT DO NOTHING;
INSERT INTO organismo_municipio (organismo_id, municipio_id) VALUES (9, 8) ON CONFLICT DO NOTHING;

