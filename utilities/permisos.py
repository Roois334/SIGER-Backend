"""
Matriz central de roles y permisos de SIGER.

Si quieres cambiar QUE puede hacer cada rol, se cambia SOLO aqui.
Los decoradores (utilities/decorators.py) y los servicios leen de este archivo.
"""

CIUDADANO = "ciudadano"
GESTOR_MUNICIPAL = "gestor_municipal"
ORGANISMO_ATENCION = "organismo_atencion"
ADMINISTRADOR = "administrador"

ROLES_VALIDOS = [CIUDADANO, GESTOR_MUNICIPAL, ORGANISMO_ATENCION, ADMINISTRADOR]

# Roles cuyo alcance se limita al municipio que tienen asignado
# (solo ven las emergencias de SU municipio).
ROLES_CON_ALCANCE_MUNICIPAL = {GESTOR_MUNICIPAL, ORGANISMO_ATENCION}

PERMISOS = {
    # --- Ciudadano ---
    "reportes.crear":         {CIUDADANO},
    "reportes.ver_propios":   {CIUDADANO},

    # --- Gestion de emergencias ---
    # Consultar: el gestor ve todo su municipio; el organismo SOLO lo que le asignaron.
    "emergencias.consultar":  {GESTOR_MUNICIPAL, ORGANISMO_ATENCION, ADMINISTRADOR},
    # Aceptar un reporte, asignarlo a un organismo o descartarlo
    "reportes.asignar":       {GESTOR_MUNICIPAL, ADMINISTRADOR},
    # Iniciar atencion, marcar resuelto o devolver un reporte asignado
    "reportes.atender":       {ORGANISMO_ATENCION},

    # --- Estadisticas (HU-17): el gestor ve su municipio; el administrador, todo ---
    "estadisticas.ver":       {GESTOR_MUNICIPAL, ADMINISTRADOR},

    # --- Administracion ---
    "usuarios.administrar":   {ADMINISTRADOR},
    "catalogos.administrar":  {ADMINISTRADOR},
}


def tiene_permiso(rol, permiso):
    return rol in PERMISOS.get(permiso, set())


def tiene_alcance_municipal(rol):
    return rol in ROLES_CON_ALCANCE_MUNICIPAL
