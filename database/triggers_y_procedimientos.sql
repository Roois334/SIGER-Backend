-- SIGER: triggers y procedimientos almacenados (PostgreSQL)
--
-- Se ejecuta DESPUES de database/siger_db.sql, sobre la misma base:
--     psql "host=... dbname=siger_db sslmode=require" -f database/triggers_y_procedimientos.sql
-- Se puede ejecutar varias veces: reemplaza lo que ya exista y no borra datos.
--
-- TRIGGERS (se ejecutan solos)
--   1. trg_validar_reporte        reportes            rechaza datos imposibles
--   2. trg_normalizar_usuario     usuarios            correo en minusculas, nombres sin espacios sobrantes
--   3. trg_auditoria_usuarios     usuarios            guarda cada cambio de rol o de estado de una cuenta
--   4. trg_proteger_reportes      reportes            impide borrar emergencias que no esten descartadas
--   5. trg_fecha_actualizacion    reportes, usuarios, municipios, organismos   fecha de ultima modificacion
--
-- PROCEDIMIENTOS ALMACENADOS (se llaman cuando se necesitan)
--   1. fn_resumen_municipio(municipio)              emergencias por estado y prioridad
--   2. fn_tiempo_respuesta(municipio, desde, hasta) minutos promedio en asignar y en resolver
--   3. fn_carga_organismos(municipio)               emergencias activas de cada organismo
--   4. sp_cerrar_reportes_resueltos(dias)           cierra los reportes resueltos hace mas de N dias
--   5. sp_limpiar_tokens_vencidos()                 borra enlaces de recuperacion de contrasena viejos
--
-- NOMBRES (para no confundirlos al verlos en la base):
--   trg_...    el trigger (la regla: "cuando pase X en la tabla Y")
--   trgfn_...  el codigo que ejecuta ese trigger (PostgreSQL lo guarda como una funcion interna)
--   fn_...     procedimiento almacenado que DEVUELVE datos   (se usa con SELECT)
--   sp_...     procedimiento almacenado que HACE una accion  (se usa con CALL)
--
-- En la extension PostgreSQL de VS Code (siger_db > Schemas > public):
--   Functions          los 3 fn_...
--   Procedures         los 2 sp_...
--   Trigger Functions  los 5 trgfn_...
--   Tables > (tabla) > Triggers   cada trigger dentro de su tabla
--   Views > vista_triggers_y_procedimientos   la lista completa de los 5 + 5
--
-- Las fechas de SIGER se guardan en hora de Colombia (UTC-5, sin horario de verano), igual que en la app:
--   (now() AT TIME ZONE 'America/Bogota')::timestamp


-- ===========================================================================
-- TRIGGER 1: validar los datos de un reporte
-- La aplicacion ya valida, pero esto protege la base aunque alguien la modifique
-- por fuera de SIGER (por ejemplo, desde una herramienta de base de datos).
-- ===========================================================================
CREATE OR REPLACE FUNCTION trgfn_validar_reporte()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF NEW.afectados < 0 OR NEW.heridos < 0 THEN
        RAISE EXCEPTION 'Reporte %: afectados y heridos no pueden ser negativos', NEW.folio
            USING ERRCODE = 'check_violation';
    END IF;
    IF NEW.heridos > NEW.afectados THEN
        RAISE EXCEPTION 'Reporte %: hay mas heridos (%) que afectados (%)', NEW.folio, NEW.heridos, NEW.afectados
            USING ERRCODE = 'check_violation';
    END IF;
    IF NEW.estado NOT IN ('pendiente', 'asignado', 'en_atencion', 'resuelto', 'cerrado', 'descartado') THEN
        RAISE EXCEPTION 'Reporte %: estado "%" no valido', NEW.folio, NEW.estado
            USING ERRCODE = 'check_violation';
    END IF;
    IF NEW.prioridad NOT IN ('baja', 'media', 'alta', 'critica') THEN
        RAISE EXCEPTION 'Reporte %: prioridad "%" no valida', NEW.folio, NEW.prioridad
            USING ERRCODE = 'check_violation';
    END IF;
    IF NEW.riesgo_propagacion IS NOT NULL AND NEW.riesgo_propagacion NOT IN ('bajo', 'medio', 'alto') THEN
        RAISE EXCEPTION 'Reporte %: riesgo de propagacion "%" no valido', NEW.folio, NEW.riesgo_propagacion
            USING ERRCODE = 'check_violation';
    END IF;
    IF NEW.vias_afectadas < 0 OR NEW.area_afectada < 0 THEN
        RAISE EXCEPTION 'Reporte %: vias y area afectada no pueden ser negativas', NEW.folio
            USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_validar_reporte ON reportes;
CREATE TRIGGER trg_validar_reporte
    BEFORE INSERT OR UPDATE ON reportes
    FOR EACH ROW EXECUTE FUNCTION trgfn_validar_reporte();


-- ===========================================================================
-- TRIGGER 2: normalizar los datos de un usuario
-- Evita cuentas duplicadas como "Juan@Correo.com" y "juan@correo.com".
-- ===========================================================================
CREATE OR REPLACE FUNCTION trgfn_normalizar_usuario()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.email := lower(btrim(NEW.email));
    NEW.nombre := regexp_replace(btrim(NEW.nombre), '\s+', ' ', 'g');
    NEW.apellido := regexp_replace(btrim(NEW.apellido), '\s+', ' ', 'g');
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_normalizar_usuario ON usuarios;
CREATE TRIGGER trg_normalizar_usuario
    BEFORE INSERT OR UPDATE OF email, nombre, apellido ON usuarios
    FOR EACH ROW EXECUTE FUNCTION trgfn_normalizar_usuario();


-- ===========================================================================
-- TRIGGER 3: auditoria de cuentas
-- Cada vez que cambia el rol de un usuario o se activa/desactiva su cuenta, queda
-- un registro con el valor anterior, el nuevo, la fecha y quien lo hizo.
-- "modificado_por" lo informa el backend con set_config('siger.usuario_actual', ...).
-- ===========================================================================
CREATE TABLE IF NOT EXISTS auditoria_usuarios (
    id              SERIAL PRIMARY KEY,
    usuario_id      INTEGER NOT NULL REFERENCES usuarios (id) ON DELETE CASCADE,
    campo           VARCHAR(20) NOT NULL,          -- 'rol' o 'activo'
    valor_anterior  VARCHAR(60),
    valor_nuevo     VARCHAR(60),
    modificado_por  INTEGER REFERENCES usuarios (id) ON DELETE SET NULL,
    usuario_bd      VARCHAR(63) NOT NULL DEFAULT current_user,
    fecha           TIMESTAMP NOT NULL DEFAULT (now() AT TIME ZONE 'America/Bogota')::timestamp
);
CREATE INDEX IF NOT EXISTS idx_auditoria_usuarios_usuario ON auditoria_usuarios (usuario_id, fecha);

CREATE OR REPLACE FUNCTION trgfn_auditoria_usuarios()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    v_actor INTEGER := NULLIF(current_setting('siger.usuario_actual', true), '')::INTEGER;
BEGIN
    IF NEW.rol_id IS DISTINCT FROM OLD.rol_id THEN
        INSERT INTO auditoria_usuarios (usuario_id, campo, valor_anterior, valor_nuevo, modificado_por)
        VALUES (NEW.id, 'rol',
                (SELECT nombre FROM roles WHERE id = OLD.rol_id),
                (SELECT nombre FROM roles WHERE id = NEW.rol_id),
                v_actor);
    END IF;
    IF NEW.activo IS DISTINCT FROM OLD.activo THEN
        INSERT INTO auditoria_usuarios (usuario_id, campo, valor_anterior, valor_nuevo, modificado_por)
        VALUES (NEW.id, 'activo',
                CASE WHEN OLD.activo THEN 'activa' ELSE 'inactiva' END,
                CASE WHEN NEW.activo THEN 'activa' ELSE 'inactiva' END,
                v_actor);
    END IF;
    RETURN NULL;  -- trigger AFTER: el valor de retorno no se usa
END;
$$;

DROP TRIGGER IF EXISTS trg_auditoria_usuarios ON usuarios;
CREATE TRIGGER trg_auditoria_usuarios
    AFTER UPDATE OF rol_id, activo ON usuarios
    FOR EACH ROW
    WHEN (OLD.rol_id IS DISTINCT FROM NEW.rol_id OR OLD.activo IS DISTINCT FROM NEW.activo)
    EXECUTE FUNCTION trgfn_auditoria_usuarios();


-- ===========================================================================
-- TRIGGER 4: proteger el historial de emergencias
-- Una emergencia real nunca debe desaparecer. Solo se pueden borrar las descartadas.
-- ===========================================================================
CREATE OR REPLACE FUNCTION trgfn_proteger_reportes()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF OLD.estado <> 'descartado' THEN
        RAISE EXCEPTION 'No se puede borrar el reporte % (estado %): solo se borran reportes descartados',
            OLD.folio, OLD.estado
            USING ERRCODE = 'restrict_violation';
    END IF;
    RETURN OLD;
END;
$$;

DROP TRIGGER IF EXISTS trg_proteger_reportes ON reportes;
CREATE TRIGGER trg_proteger_reportes
    BEFORE DELETE ON reportes
    FOR EACH ROW EXECUTE FUNCTION trgfn_proteger_reportes();


-- ===========================================================================
-- TRIGGER 5: fecha de ultima modificacion
-- Se actualiza sola en cualquier cambio real de la fila, en hora de Colombia.
-- ===========================================================================
CREATE OR REPLACE FUNCTION trgfn_fecha_actualizacion()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF NEW IS DISTINCT FROM OLD THEN
        NEW.fecha_actualizacion := (now() AT TIME ZONE 'America/Bogota')::timestamp;
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_fecha_actualizacion ON reportes;
CREATE TRIGGER trg_fecha_actualizacion
    BEFORE UPDATE ON reportes
    FOR EACH ROW EXECUTE FUNCTION trgfn_fecha_actualizacion();

DROP TRIGGER IF EXISTS trg_fecha_actualizacion ON usuarios;
CREATE TRIGGER trg_fecha_actualizacion
    BEFORE UPDATE ON usuarios
    FOR EACH ROW EXECUTE FUNCTION trgfn_fecha_actualizacion();

DROP TRIGGER IF EXISTS trg_fecha_actualizacion ON municipios;
CREATE TRIGGER trg_fecha_actualizacion
    BEFORE UPDATE ON municipios
    FOR EACH ROW EXECUTE FUNCTION trgfn_fecha_actualizacion();

DROP TRIGGER IF EXISTS trg_fecha_actualizacion ON organismos;
CREATE TRIGGER trg_fecha_actualizacion
    BEFORE UPDATE ON organismos
    FOR EACH ROW EXECUTE FUNCTION trgfn_fecha_actualizacion();


-- ===========================================================================
-- PROCEDIMIENTO 1: resumen de emergencias de un municipio
-- Una fila por estado, con el total y cuantas hay de cada prioridad.
-- Sin municipio (NULL) = toda la region.
--   SELECT * FROM fn_resumen_municipio(1);
-- ===========================================================================
CREATE OR REPLACE FUNCTION fn_resumen_municipio(p_municipio_id INTEGER DEFAULT NULL)
RETURNS TABLE (estado VARCHAR, total BIGINT, critica BIGINT, alta BIGINT, media BIGINT, baja BIGINT)
LANGUAGE sql
STABLE
AS $$
    SELECT e.estado,
           COUNT(r.id),
           COUNT(r.id) FILTER (WHERE r.prioridad = 'critica'),
           COUNT(r.id) FILTER (WHERE r.prioridad = 'alta'),
           COUNT(r.id) FILTER (WHERE r.prioridad = 'media'),
           COUNT(r.id) FILTER (WHERE r.prioridad = 'baja')
    FROM (VALUES (1, 'pendiente'), (2, 'asignado'), (3, 'en_atencion'),
                 (4, 'resuelto'), (5, 'cerrado'), (6, 'descartado')) AS e (orden, estado)
    LEFT JOIN reportes r
           ON r.estado = e.estado
          AND (p_municipio_id IS NULL OR r.municipio_id = p_municipio_id)
    GROUP BY e.orden, e.estado
    ORDER BY e.orden;
$$;


-- ===========================================================================
-- PROCEDIMIENTO 2: tiempos de respuesta
-- Minutos promedio desde que se reporta hasta la PRIMERA asignacion y hasta que
-- el organismo la marca resuelta. Fechas opcionales (dia completo incluido).
--   SELECT * FROM fn_tiempo_respuesta(1, '2026-01-01', '2026-12-31');
-- ===========================================================================
CREATE OR REPLACE FUNCTION fn_tiempo_respuesta(
    p_municipio_id INTEGER DEFAULT NULL,
    p_desde DATE DEFAULT NULL,
    p_hasta DATE DEFAULT NULL
)
RETURNS TABLE (reportes BIGINT, con_asignacion BIGINT, promedio_asignacion_min NUMERIC,
               con_resolucion BIGINT, promedio_resolucion_min NUMERIC)
LANGUAGE sql
STABLE
AS $$
    WITH base AS (
        SELECT r.id, r.fecha_hora,
               (SELECT MIN(h.fecha) FROM reporte_historial h
                 WHERE h.reporte_id = r.id AND h.accion = 'asignar') AS asignado,
               (SELECT MIN(h.fecha) FROM reporte_historial h
                 WHERE h.reporte_id = r.id AND h.accion = 'resolver') AS resuelto
        FROM reportes r
        WHERE (p_municipio_id IS NULL OR r.municipio_id = p_municipio_id)
          AND (p_desde IS NULL OR r.fecha_hora >= p_desde)
          AND (p_hasta IS NULL OR r.fecha_hora < p_hasta + 1)
    )
    SELECT COUNT(*),
           COUNT(*) FILTER (WHERE asignado >= fecha_hora),
           ROUND(AVG(EXTRACT(EPOCH FROM asignado - fecha_hora) / 60)
                 FILTER (WHERE asignado >= fecha_hora), 1),
           COUNT(*) FILTER (WHERE resuelto >= fecha_hora),
           ROUND(AVG(EXTRACT(EPOCH FROM resuelto - fecha_hora) / 60)
                 FILTER (WHERE resuelto >= fecha_hora), 1)
    FROM base;
$$;


-- ===========================================================================
-- PROCEDIMIENTO 3: carga de trabajo de los organismos
-- Emergencias activas (asignadas o en atencion) de cada organismo activo, como
-- responsable principal y como apoyo. Ayuda al gestor a decidir a quien asignar.
--   SELECT * FROM fn_carga_organismos(1);
-- ===========================================================================
CREATE OR REPLACE FUNCTION fn_carga_organismos(p_municipio_id INTEGER DEFAULT NULL)
RETURNS TABLE (organismo_id INTEGER, organismo VARCHAR, principales BIGINT, de_apoyo BIGINT, total_activas BIGINT)
LANGUAGE sql
STABLE
AS $$
    WITH activos AS (
        SELECT r.id, r.organismo_id
        FROM reportes r
        WHERE r.estado IN ('asignado', 'en_atencion')
          AND (p_municipio_id IS NULL OR r.municipio_id = p_municipio_id)
    ),
    conteo AS (
        SELECT o.id, o.nombre,
               (SELECT COUNT(*) FROM activos a WHERE a.organismo_id = o.id) AS principales,
               (SELECT COUNT(*) FROM activos a
                  JOIN reporte_apoyo ra ON ra.reporte_id = a.id
                 WHERE ra.organismo_id = o.id) AS de_apoyo
        FROM organismos o
        WHERE o.activo
          AND (p_municipio_id IS NULL OR EXISTS (
                SELECT 1 FROM organismo_municipio om
                 WHERE om.organismo_id = o.id AND om.municipio_id = p_municipio_id))
    )
    SELECT id, nombre, principales, de_apoyo, principales + de_apoyo
    FROM conteo
    ORDER BY principales + de_apoyo DESC, nombre;
$$;


-- ===========================================================================
-- PROCEDIMIENTO 4: cerrar reportes resueltos olvidados
-- Si el organismo marco un reporte como resuelto y el gestor no confirmo el cierre
-- en N dias, se cierra solo. Queda en el historial y se avisa al ciudadano.
--   CALL sp_cerrar_reportes_resueltos(7);
-- ===========================================================================
CREATE OR REPLACE PROCEDURE sp_cerrar_reportes_resueltos(
    p_dias INTEGER DEFAULT 7,
    INOUT p_cerrados INTEGER DEFAULT 0
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_ahora TIMESTAMP := (now() AT TIME ZONE 'America/Bogota')::timestamp;
BEGIN
    IF p_dias IS NULL OR p_dias < 1 THEN
        RAISE EXCEPTION 'Los dias deben ser 1 o mas' USING ERRCODE = 'invalid_parameter_value';
    END IF;

    WITH cerrados AS (
        UPDATE reportes r
           SET estado = 'cerrado'
         WHERE r.estado = 'resuelto'
           AND COALESCE((SELECT MAX(h.fecha) FROM reporte_historial h
                          WHERE h.reporte_id = r.id AND h.accion = 'resolver'),
                        r.fecha_actualizacion) < v_ahora - make_interval(days => p_dias)
        RETURNING r.id, r.folio, r.tipo, r.ciudadano_id
    ),
    historial AS (
        INSERT INTO reporte_historial (reporte_id, usuario_id, accion, estado_anterior, estado_nuevo, comentario, fecha)
        SELECT id, NULL, 'cerrar', 'resuelto', 'cerrado',
               format('Cierre automatico: resuelto hace mas de %s dias sin confirmacion del gestor', p_dias),
               v_ahora
        FROM cerrados
        RETURNING id
    ),
    avisos AS (
        INSERT INTO notificaciones (usuario_id, reporte_id, tipo, titulo, mensaje, leida, fecha_creacion)
        SELECT c.ciudadano_id, c.id, 'cerrado', 'Tu reporte fue cerrado',
               format('Tu reporte %s (%s) se cerro porque ya estaba resuelto. Gracias por avisar.', c.folio, c.tipo),
               false, v_ahora
        FROM cerrados c
        JOIN usuarios u ON u.id = c.ciudadano_id AND u.activo
        RETURNING id
    )
    SELECT COUNT(*) INTO p_cerrados FROM cerrados;
END;
$$;


-- ===========================================================================
-- PROCEDIMIENTO 5: limpiar enlaces de recuperacion de contrasena
-- Borra los enlaces ya usados o vencidos con mas de un dia de antiguedad.
-- (Los del ultimo dia se conservan: la app los cuenta para limitar a 3 solicitudes por hora.)
-- password_resets guarda las fechas en UTC.
--   CALL sp_limpiar_tokens_vencidos();
-- ===========================================================================
CREATE OR REPLACE PROCEDURE sp_limpiar_tokens_vencidos(INOUT p_borrados INTEGER DEFAULT 0)
LANGUAGE plpgsql
AS $$
DECLARE
    v_ahora_utc TIMESTAMP := (now() AT TIME ZONE 'UTC')::timestamp;
BEGIN
    DELETE FROM password_resets
     WHERE (usado OR expira < v_ahora_utc)
       AND fecha_creacion < v_ahora_utc - INTERVAL '1 day';
    GET DIAGNOSTICS p_borrados = ROW_COUNT;
END;
$$;


-- ===========================================================================
-- VISTA: la lista completa de los 5 triggers y los 5 procedimientos almacenados
--   SELECT * FROM vista_triggers_y_procedimientos;
-- ===========================================================================
CREATE OR REPLACE VIEW vista_triggers_y_procedimientos AS
SELECT 'Trigger'::text AS tipo,
       t.trigger_name::text AS nombre,
       string_agg(DISTINCT t.event_object_table::text, ', ') AS tabla,
       CASE t.trigger_name
           WHEN 'trg_validar_reporte'     THEN 'Rechaza datos imposibles en un reporte'
           WHEN 'trg_normalizar_usuario'  THEN 'Correo en minusculas y nombres sin espacios sobrantes'
           WHEN 'trg_auditoria_usuarios'  THEN 'Guarda quien cambio el rol o el estado de una cuenta'
           WHEN 'trg_proteger_reportes'   THEN 'Impide borrar emergencias que no esten descartadas'
           WHEN 'trg_fecha_actualizacion' THEN 'Actualiza la fecha de ultima modificacion'
       END AS descripcion
FROM information_schema.triggers t
WHERE t.trigger_schema = 'public'
GROUP BY t.trigger_name
UNION ALL
SELECT 'Procedimiento almacenado',
       r.routine_name::text,
       CASE r.routine_type WHEN 'FUNCTION' THEN 'devuelve datos (SELECT)' ELSE 'hace una accion (CALL)' END,
       CASE r.routine_name
           WHEN 'fn_resumen_municipio'         THEN 'Emergencias por estado y prioridad'
           WHEN 'fn_tiempo_respuesta'          THEN 'Minutos promedio en asignar y en resolver'
           WHEN 'fn_carga_organismos'          THEN 'Emergencias activas de cada organismo'
           WHEN 'sp_cerrar_reportes_resueltos' THEN 'Cierra los reportes resueltos hace mas de N dias'
           WHEN 'sp_limpiar_tokens_vencidos'   THEN 'Borra enlaces viejos de recuperacion de contrasena'
       END
FROM information_schema.routines r
WHERE r.routine_schema = 'public'
  AND r.routine_name IN ('fn_resumen_municipio', 'fn_tiempo_respuesta', 'fn_carga_organismos',
                         'sp_cerrar_reportes_resueltos', 'sp_limpiar_tokens_vencidos')
ORDER BY 1 DESC, 2;

-- ===========================================================================
-- LIMPIEZA: nombres anteriores de las funciones internas de los triggers
-- (antes se llamaban fn_..., igual que los procedimientos; ahora son trgfn_...)
-- y la antigua funcion de apoyo siger_ahora() (la hora de Colombia ahora va escrita donde se usa)
-- ===========================================================================
ALTER TABLE auditoria_usuarios ALTER COLUMN fecha SET DEFAULT (now() AT TIME ZONE 'America/Bogota')::timestamp;
DROP FUNCTION IF EXISTS siger_ahora();
DROP FUNCTION IF EXISTS fn_validar_reporte();
DROP FUNCTION IF EXISTS fn_normalizar_usuario();
DROP FUNCTION IF EXISTS fn_auditoria_usuarios();
DROP FUNCTION IF EXISTS fn_proteger_reportes();
DROP FUNCTION IF EXISTS fn_fecha_actualizacion();
