-- SIGER: esquema de la base de datos y datos de catalogo
-- Generado el 2026-10-25 con database/exportar_esquema.py
-- No incluye usuarios, reportes ni contrasenas.
SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- Tabla evidencias
CREATE TABLE IF NOT EXISTS `evidencias` (
  `id` int NOT NULL AUTO_INCREMENT,
  `reporte_id` int NOT NULL,
  `nombre_archivo` varchar(255) COLLATE utf8mb4_general_ci NOT NULL,
  `ruta_archivo` varchar(300) COLLATE utf8mb4_general_ci NOT NULL,
  `fecha_carga` datetime DEFAULT (now()),
  PRIMARY KEY (`id`),
  KEY `reporte_id` (`reporte_id`),
  CONSTRAINT `evidencias_ibfk_1` FOREIGN KEY (`reporte_id`) REFERENCES `reportes` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- Tabla municipios
CREATE TABLE IF NOT EXISTS `municipios` (
  `id` int NOT NULL AUTO_INCREMENT,
  `codigo` varchar(20) COLLATE utf8mb4_general_ci NOT NULL,
  `nombre` varchar(80) COLLATE utf8mb4_general_ci NOT NULL,
  `activo` tinyint(1) NOT NULL,
  `fecha_creacion` datetime DEFAULT (now()),
  `fecha_actualizacion` datetime DEFAULT (now()),
  PRIMARY KEY (`id`),
  UNIQUE KEY `codigo` (`codigo`),
  UNIQUE KEY `nombre` (`nombre`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- Tabla organismo_municipio
CREATE TABLE IF NOT EXISTS `organismo_municipio` (
  `organismo_id` int NOT NULL,
  `municipio_id` int NOT NULL,
  PRIMARY KEY (`organismo_id`,`municipio_id`),
  KEY `municipio_id` (`municipio_id`),
  CONSTRAINT `organismo_municipio_ibfk_1` FOREIGN KEY (`organismo_id`) REFERENCES `organismos` (`id`),
  CONSTRAINT `organismo_municipio_ibfk_2` FOREIGN KEY (`municipio_id`) REFERENCES `municipios` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- Tabla organismos
CREATE TABLE IF NOT EXISTS `organismos` (
  `id` int NOT NULL AUTO_INCREMENT,
  `codigo` varchar(20) COLLATE utf8mb4_general_ci NOT NULL,
  `nombre` varchar(120) COLLATE utf8mb4_general_ci NOT NULL,
  `tipo` varchar(60) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `activo` tinyint(1) NOT NULL,
  `fecha_creacion` datetime DEFAULT (now()),
  `fecha_actualizacion` datetime DEFAULT (now()),
  PRIMARY KEY (`id`),
  UNIQUE KEY `codigo` (`codigo`),
  UNIQUE KEY `nombre` (`nombre`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- Tabla password_resets
CREATE TABLE IF NOT EXISTS `password_resets` (
  `id` int NOT NULL AUTO_INCREMENT,
  `usuario_id` int NOT NULL,
  `token_hash` varchar(64) NOT NULL,
  `expira` datetime NOT NULL,
  `usado` tinyint(1) NOT NULL DEFAULT '0',
  `fecha_creacion` datetime NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `token_hash` (`token_hash`),
  KEY `idx_pr_usuario` (`usuario_id`),
  CONSTRAINT `fk_pr_usuario` FOREIGN KEY (`usuario_id`) REFERENCES `usuarios` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Tabla reporte_apoyo
CREATE TABLE IF NOT EXISTS `reporte_apoyo` (
  `reporte_id` int NOT NULL,
  `organismo_id` int NOT NULL,
  `fecha` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`reporte_id`,`organismo_id`),
  KEY `fk_apoyo_organismo` (`organismo_id`),
  CONSTRAINT `fk_apoyo_organismo` FOREIGN KEY (`organismo_id`) REFERENCES `organismos` (`id`),
  CONSTRAINT `fk_apoyo_reporte` FOREIGN KEY (`reporte_id`) REFERENCES `reportes` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Tabla reporte_historial
CREATE TABLE IF NOT EXISTS `reporte_historial` (
  `id` int NOT NULL AUTO_INCREMENT,
  `reporte_id` int NOT NULL,
  `usuario_id` int DEFAULT NULL,
  `accion` varchar(20) NOT NULL,
  `estado_anterior` varchar(20) DEFAULT NULL,
  `estado_nuevo` varchar(20) NOT NULL,
  `comentario` varchar(300) DEFAULT NULL,
  `fecha` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_historial_reporte` (`reporte_id`),
  KEY `fk_historial_usuario` (`usuario_id`),
  CONSTRAINT `fk_historial_reporte` FOREIGN KEY (`reporte_id`) REFERENCES `reportes` (`id`),
  CONSTRAINT `fk_historial_usuario` FOREIGN KEY (`usuario_id`) REFERENCES `usuarios` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Tabla reportes
CREATE TABLE IF NOT EXISTS `reportes` (
  `id` int NOT NULL AUTO_INCREMENT,
  `folio` varchar(30) COLLATE utf8mb4_general_ci NOT NULL,
  `ciudadano_id` int NOT NULL,
  `municipio_id` int NOT NULL,
  `tipo` varchar(60) COLLATE utf8mb4_general_ci NOT NULL,
  `prioridad` varchar(20) COLLATE utf8mb4_general_ci NOT NULL,
  `descripcion` text COLLATE utf8mb4_general_ci NOT NULL,
  `direccion` varchar(200) COLLATE utf8mb4_general_ci NOT NULL,
  `latitud` float DEFAULT NULL,
  `longitud` float DEFAULT NULL,
  `afectados` int NOT NULL,
  `estado` varchar(20) COLLATE utf8mb4_general_ci NOT NULL DEFAULT 'pendiente',
  `fecha_hora` datetime NOT NULL DEFAULT (now()),
  `fecha_creacion` datetime DEFAULT (now()),
  `fecha_actualizacion` datetime DEFAULT (now()),
  `organismo_id` int DEFAULT NULL,
  `asignado_por_id` int DEFAULT NULL,
  `fecha_asignacion` datetime DEFAULT NULL,
  `heridos` int NOT NULL DEFAULT '0',
  `vias_afectadas` int DEFAULT NULL,
  `area_afectada` int DEFAULT NULL,
  `riesgo_propagacion` varchar(10) COLLATE utf8mb4_general_ci DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `folio` (`folio`),
  KEY `ciudadano_id` (`ciudadano_id`),
  KEY `municipio_id` (`municipio_id`),
  KEY `fk_reportes_organismo` (`organismo_id`),
  KEY `fk_reportes_asignado_por` (`asignado_por_id`),
  KEY `idx_reportes_estado` (`estado`),
  KEY `idx_reportes_fecha` (`fecha_hora`),
  CONSTRAINT `fk_reportes_asignado_por` FOREIGN KEY (`asignado_por_id`) REFERENCES `usuarios` (`id`),
  CONSTRAINT `fk_reportes_organismo` FOREIGN KEY (`organismo_id`) REFERENCES `organismos` (`id`),
  CONSTRAINT `reportes_ibfk_1` FOREIGN KEY (`ciudadano_id`) REFERENCES `usuarios` (`id`),
  CONSTRAINT `reportes_ibfk_2` FOREIGN KEY (`municipio_id`) REFERENCES `municipios` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- Tabla roles
CREATE TABLE IF NOT EXISTS `roles` (
  `id` int NOT NULL AUTO_INCREMENT,
  `nombre` varchar(40) COLLATE utf8mb4_general_ci NOT NULL,
  `descripcion` varchar(150) COLLATE utf8mb4_general_ci DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `nombre` (`nombre`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- Tabla usuarios
CREATE TABLE IF NOT EXISTS `usuarios` (
  `id` int NOT NULL AUTO_INCREMENT,
  `nombre` varchar(80) COLLATE utf8mb4_general_ci NOT NULL,
  `apellido` varchar(80) COLLATE utf8mb4_general_ci NOT NULL,
  `email` varchar(120) COLLATE utf8mb4_general_ci NOT NULL,
  `password_hash` varchar(255) COLLATE utf8mb4_general_ci NOT NULL,
  `rol_id` int NOT NULL,
  `municipio_id` int DEFAULT NULL,
  `activo` tinyint(1) NOT NULL,
  `foto_url` varchar(255) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `fecha_creacion` datetime DEFAULT (now()),
  `fecha_actualizacion` datetime DEFAULT (now()),
  `organismo_id` int DEFAULT NULL,
  `tipo_documento` varchar(10) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `documento` varchar(20) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `telefono` varchar(20) COLLATE utf8mb4_general_ci DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `email` (`email`),
  UNIQUE KEY `uq_usuarios_documento` (`tipo_documento`,`documento`),
  KEY `rol_id` (`rol_id`),
  KEY `municipio_id` (`municipio_id`),
  KEY `fk_usuarios_organismo` (`organismo_id`),
  CONSTRAINT `fk_usuarios_organismo` FOREIGN KEY (`organismo_id`) REFERENCES `organismos` (`id`),
  CONSTRAINT `usuarios_ibfk_1` FOREIGN KEY (`rol_id`) REFERENCES `roles` (`id`),
  CONSTRAINT `usuarios_ibfk_2` FOREIGN KEY (`municipio_id`) REFERENCES `municipios` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- Datos de roles (4 filas)
INSERT IGNORE INTO `roles` (`id`, `nombre`, `descripcion`) VALUES (1, 'ciudadano', 'Usuario que reporta emergencias');
INSERT IGNORE INTO `roles` (`id`, `nombre`, `descripcion`) VALUES (2, 'gestor_municipal', 'Gestiona emergencias de su municipio');
INSERT IGNORE INTO `roles` (`id`, `nombre`, `descripcion`) VALUES (3, 'organismo_atencion', 'Bomberos, Cruz Roja, Defensa Civil, Policia, etc.');
INSERT IGNORE INTO `roles` (`id`, `nombre`, `descripcion`) VALUES (4, 'administrador', 'Administra el sistema por completo');

-- Datos de municipios (8 filas)
INSERT IGNORE INTO `municipios` (`id`, `codigo`, `nombre`, `activo`, `fecha_creacion`, `fecha_actualizacion`) VALUES (1, 'FAC', 'Facatativa', 1, '2026-09-21 22:11:10', '2026-09-21 22:11:10');
INSERT IGNORE INTO `municipios` (`id`, `codigo`, `nombre`, `activo`, `fecha_creacion`, `fecha_actualizacion`) VALUES (2, 'MAD', 'Madrid', 1, '2026-09-21 22:11:10', '2026-09-21 22:11:10');
INSERT IGNORE INTO `municipios` (`id`, `codigo`, `nombre`, `activo`, `fecha_creacion`, `fecha_actualizacion`) VALUES (3, 'MOS', 'Mosquera', 1, '2026-09-21 22:11:10', '2026-09-21 22:11:10');
INSERT IGNORE INTO `municipios` (`id`, `codigo`, `nombre`, `activo`, `fecha_creacion`, `fecha_actualizacion`) VALUES (4, 'FUN', 'Funza', 1, '2026-09-21 22:11:10', '2026-09-21 22:11:10');
INSERT IGNORE INTO `municipios` (`id`, `codigo`, `nombre`, `activo`, `fecha_creacion`, `fecha_actualizacion`) VALUES (5, 'BOJ', 'Bojaca', 1, '2026-09-21 22:11:10', '2026-10-23 02:37:24');
INSERT IGNORE INTO `municipios` (`id`, `codigo`, `nombre`, `activo`, `fecha_creacion`, `fecha_actualizacion`) VALUES (6, 'ROS', 'El Rosal', 1, '2026-09-21 22:11:10', '2026-09-21 22:11:10');
INSERT IGNORE INTO `municipios` (`id`, `codigo`, `nombre`, `activo`, `fecha_creacion`, `fecha_actualizacion`) VALUES (7, 'SUB', 'Subachoque', 1, '2026-09-21 22:11:10', '2026-09-21 22:11:10');
INSERT IGNORE INTO `municipios` (`id`, `codigo`, `nombre`, `activo`, `fecha_creacion`, `fecha_actualizacion`) VALUES (8, 'ZIP', 'Zipacon', 1, '2026-09-21 22:11:10', '2026-09-21 22:11:10');

-- Datos de organismos (9 filas)
INSERT IGNORE INTO `organismos` (`id`, `codigo`, `nombre`, `tipo`, `activo`, `fecha_creacion`, `fecha_actualizacion`) VALUES (1, 'BOM', 'Bomberos', 'Bomberos', 1, '2026-10-10 20:58:44', '2026-10-10 20:58:44');
INSERT IGNORE INTO `organismos` (`id`, `codigo`, `nombre`, `tipo`, `activo`, `fecha_creacion`, `fecha_actualizacion`) VALUES (2, 'CRC', 'Cruz Roja Colombiana', 'Socorro', 1, '2026-10-10 20:58:44', '2026-10-10 20:58:44');
INSERT IGNORE INTO `organismos` (`id`, `codigo`, `nombre`, `tipo`, `activo`, `fecha_creacion`, `fecha_actualizacion`) VALUES (3, 'DEF', 'Defensa Civil Colombiana', 'Socorro', 1, '2026-10-10 20:58:44', '2026-10-10 20:58:44');
INSERT IGNORE INTO `organismos` (`id`, `codigo`, `nombre`, `tipo`, `activo`, `fecha_creacion`, `fecha_actualizacion`) VALUES (4, 'POL', 'Policia Nacional', 'Seguridad', 1, '2026-10-10 20:58:44', '2026-10-10 20:58:44');
INSERT IGNORE INTO `organismos` (`id`, `codigo`, `nombre`, `tipo`, `activo`, `fecha_creacion`, `fecha_actualizacion`) VALUES (5, 'SAL', 'Secretaria de Salud y Ambulancias', 'Salud', 1, '2026-10-10 20:58:44', '2026-10-10 20:58:44');
INSERT IGNORE INTO `organismos` (`id`, `codigo`, `nombre`, `tipo`, `activo`, `fecha_creacion`, `fecha_actualizacion`) VALUES (6, 'TRA', 'Transito y Transporte', 'Transito', 1, '2026-10-10 20:58:44', '2026-10-10 20:58:44');
INSERT IGNORE INTO `organismos` (`id`, `codigo`, `nombre`, `tipo`, `activo`, `fecha_creacion`, `fecha_actualizacion`) VALUES (7, 'GRD', 'Gestion del Riesgo', 'Gestion del riesgo', 1, '2026-10-10 20:58:44', '2026-10-10 20:58:44');
INSERT IGNORE INTO `organismos` (`id`, `codigo`, `nombre`, `tipo`, `activo`, `fecha_creacion`, `fecha_actualizacion`) VALUES (8, 'SSP', 'Empresas de Servicios Publicos', 'Servicios publicos', 1, '2026-10-10 20:58:44', '2026-10-10 20:58:44');
INSERT IGNORE INTO `organismos` (`id`, `codigo`, `nombre`, `tipo`, `activo`, `fecha_creacion`, `fecha_actualizacion`) VALUES (9, 'CAR', 'Autoridad Ambiental CAR', 'Ambiental', 1, '2026-10-10 20:58:44', '2026-10-10 20:58:44');

-- Datos de organismo_municipio (72 filas)
INSERT IGNORE INTO `organismo_municipio` (`organismo_id`, `municipio_id`) VALUES (1, 1);
INSERT IGNORE INTO `organismo_municipio` (`organismo_id`, `municipio_id`) VALUES (2, 1);
INSERT IGNORE INTO `organismo_municipio` (`organismo_id`, `municipio_id`) VALUES (3, 1);
INSERT IGNORE INTO `organismo_municipio` (`organismo_id`, `municipio_id`) VALUES (4, 1);
INSERT IGNORE INTO `organismo_municipio` (`organismo_id`, `municipio_id`) VALUES (5, 1);
INSERT IGNORE INTO `organismo_municipio` (`organismo_id`, `municipio_id`) VALUES (6, 1);
INSERT IGNORE INTO `organismo_municipio` (`organismo_id`, `municipio_id`) VALUES (7, 1);
INSERT IGNORE INTO `organismo_municipio` (`organismo_id`, `municipio_id`) VALUES (8, 1);
INSERT IGNORE INTO `organismo_municipio` (`organismo_id`, `municipio_id`) VALUES (9, 1);
INSERT IGNORE INTO `organismo_municipio` (`organismo_id`, `municipio_id`) VALUES (1, 2);
INSERT IGNORE INTO `organismo_municipio` (`organismo_id`, `municipio_id`) VALUES (2, 2);
INSERT IGNORE INTO `organismo_municipio` (`organismo_id`, `municipio_id`) VALUES (3, 2);
INSERT IGNORE INTO `organismo_municipio` (`organismo_id`, `municipio_id`) VALUES (4, 2);
INSERT IGNORE INTO `organismo_municipio` (`organismo_id`, `municipio_id`) VALUES (5, 2);
INSERT IGNORE INTO `organismo_municipio` (`organismo_id`, `municipio_id`) VALUES (6, 2);
INSERT IGNORE INTO `organismo_municipio` (`organismo_id`, `municipio_id`) VALUES (7, 2);
INSERT IGNORE INTO `organismo_municipio` (`organismo_id`, `municipio_id`) VALUES (8, 2);
INSERT IGNORE INTO `organismo_municipio` (`organismo_id`, `municipio_id`) VALUES (9, 2);
INSERT IGNORE INTO `organismo_municipio` (`organismo_id`, `municipio_id`) VALUES (1, 3);
INSERT IGNORE INTO `organismo_municipio` (`organismo_id`, `municipio_id`) VALUES (2, 3);
INSERT IGNORE INTO `organismo_municipio` (`organismo_id`, `municipio_id`) VALUES (3, 3);
INSERT IGNORE INTO `organismo_municipio` (`organismo_id`, `municipio_id`) VALUES (4, 3);
INSERT IGNORE INTO `organismo_municipio` (`organismo_id`, `municipio_id`) VALUES (5, 3);
INSERT IGNORE INTO `organismo_municipio` (`organismo_id`, `municipio_id`) VALUES (6, 3);
INSERT IGNORE INTO `organismo_municipio` (`organismo_id`, `municipio_id`) VALUES (7, 3);
INSERT IGNORE INTO `organismo_municipio` (`organismo_id`, `municipio_id`) VALUES (8, 3);
INSERT IGNORE INTO `organismo_municipio` (`organismo_id`, `municipio_id`) VALUES (9, 3);
INSERT IGNORE INTO `organismo_municipio` (`organismo_id`, `municipio_id`) VALUES (1, 4);
INSERT IGNORE INTO `organismo_municipio` (`organismo_id`, `municipio_id`) VALUES (2, 4);
INSERT IGNORE INTO `organismo_municipio` (`organismo_id`, `municipio_id`) VALUES (3, 4);
INSERT IGNORE INTO `organismo_municipio` (`organismo_id`, `municipio_id`) VALUES (4, 4);
INSERT IGNORE INTO `organismo_municipio` (`organismo_id`, `municipio_id`) VALUES (5, 4);
INSERT IGNORE INTO `organismo_municipio` (`organismo_id`, `municipio_id`) VALUES (6, 4);
INSERT IGNORE INTO `organismo_municipio` (`organismo_id`, `municipio_id`) VALUES (7, 4);
INSERT IGNORE INTO `organismo_municipio` (`organismo_id`, `municipio_id`) VALUES (8, 4);
INSERT IGNORE INTO `organismo_municipio` (`organismo_id`, `municipio_id`) VALUES (9, 4);
INSERT IGNORE INTO `organismo_municipio` (`organismo_id`, `municipio_id`) VALUES (1, 5);
INSERT IGNORE INTO `organismo_municipio` (`organismo_id`, `municipio_id`) VALUES (2, 5);
INSERT IGNORE INTO `organismo_municipio` (`organismo_id`, `municipio_id`) VALUES (3, 5);
INSERT IGNORE INTO `organismo_municipio` (`organismo_id`, `municipio_id`) VALUES (4, 5);
INSERT IGNORE INTO `organismo_municipio` (`organismo_id`, `municipio_id`) VALUES (5, 5);
INSERT IGNORE INTO `organismo_municipio` (`organismo_id`, `municipio_id`) VALUES (6, 5);
INSERT IGNORE INTO `organismo_municipio` (`organismo_id`, `municipio_id`) VALUES (7, 5);
INSERT IGNORE INTO `organismo_municipio` (`organismo_id`, `municipio_id`) VALUES (8, 5);
INSERT IGNORE INTO `organismo_municipio` (`organismo_id`, `municipio_id`) VALUES (9, 5);
INSERT IGNORE INTO `organismo_municipio` (`organismo_id`, `municipio_id`) VALUES (1, 6);
INSERT IGNORE INTO `organismo_municipio` (`organismo_id`, `municipio_id`) VALUES (2, 6);
INSERT IGNORE INTO `organismo_municipio` (`organismo_id`, `municipio_id`) VALUES (3, 6);
INSERT IGNORE INTO `organismo_municipio` (`organismo_id`, `municipio_id`) VALUES (4, 6);
INSERT IGNORE INTO `organismo_municipio` (`organismo_id`, `municipio_id`) VALUES (5, 6);
INSERT IGNORE INTO `organismo_municipio` (`organismo_id`, `municipio_id`) VALUES (6, 6);
INSERT IGNORE INTO `organismo_municipio` (`organismo_id`, `municipio_id`) VALUES (7, 6);
INSERT IGNORE INTO `organismo_municipio` (`organismo_id`, `municipio_id`) VALUES (8, 6);
INSERT IGNORE INTO `organismo_municipio` (`organismo_id`, `municipio_id`) VALUES (9, 6);
INSERT IGNORE INTO `organismo_municipio` (`organismo_id`, `municipio_id`) VALUES (1, 7);
INSERT IGNORE INTO `organismo_municipio` (`organismo_id`, `municipio_id`) VALUES (2, 7);
INSERT IGNORE INTO `organismo_municipio` (`organismo_id`, `municipio_id`) VALUES (3, 7);
INSERT IGNORE INTO `organismo_municipio` (`organismo_id`, `municipio_id`) VALUES (4, 7);
INSERT IGNORE INTO `organismo_municipio` (`organismo_id`, `municipio_id`) VALUES (5, 7);
INSERT IGNORE INTO `organismo_municipio` (`organismo_id`, `municipio_id`) VALUES (6, 7);
INSERT IGNORE INTO `organismo_municipio` (`organismo_id`, `municipio_id`) VALUES (7, 7);
INSERT IGNORE INTO `organismo_municipio` (`organismo_id`, `municipio_id`) VALUES (8, 7);
INSERT IGNORE INTO `organismo_municipio` (`organismo_id`, `municipio_id`) VALUES (9, 7);
INSERT IGNORE INTO `organismo_municipio` (`organismo_id`, `municipio_id`) VALUES (1, 8);
INSERT IGNORE INTO `organismo_municipio` (`organismo_id`, `municipio_id`) VALUES (2, 8);
INSERT IGNORE INTO `organismo_municipio` (`organismo_id`, `municipio_id`) VALUES (3, 8);
INSERT IGNORE INTO `organismo_municipio` (`organismo_id`, `municipio_id`) VALUES (4, 8);
INSERT IGNORE INTO `organismo_municipio` (`organismo_id`, `municipio_id`) VALUES (5, 8);
INSERT IGNORE INTO `organismo_municipio` (`organismo_id`, `municipio_id`) VALUES (6, 8);
INSERT IGNORE INTO `organismo_municipio` (`organismo_id`, `municipio_id`) VALUES (7, 8);
INSERT IGNORE INTO `organismo_municipio` (`organismo_id`, `municipio_id`) VALUES (8, 8);
INSERT IGNORE INTO `organismo_municipio` (`organismo_id`, `municipio_id`) VALUES (9, 8);

SET FOREIGN_KEY_CHECKS = 1;
