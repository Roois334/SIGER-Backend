CIUDADANO = "ciudadano"
GESTOR_MUNICIPAL = "gestor_municipal"
ORGANISMO_ATENCION = "organismo_atencion"
ADMINISTRADOR = "administrador"

ROLES_VALIDOS = [CIUDADANO, GESTOR_MUNICIPAL, ORGANISMO_ATENCION, ADMINISTRADOR]

ROLES_CON_ALCANCE_MUNICIPAL = {GESTOR_MUNICIPAL, ORGANISMO_ATENCION}

PERMISOS = {
    "reportes.crear":         {CIUDADANO},
    "reportes.ver_propios":   {CIUDADANO},

    "emergencias.consultar":  {GESTOR_MUNICIPAL, ORGANISMO_ATENCION, ADMINISTRADOR},
    "reportes.asignar":       {GESTOR_MUNICIPAL, ADMINISTRADOR},
    "reportes.atender":       {ORGANISMO_ATENCION},

    "estadisticas.ver":       {GESTOR_MUNICIPAL, ADMINISTRADOR},

    "usuarios.administrar":   {ADMINISTRADOR},
    "catalogos.administrar":  {ADMINISTRADOR},
}


def tiene_permiso(rol, permiso):
    return rol in PERMISOS.get(permiso, set())


def tiene_alcance_municipal(rol):
    return rol in ROLES_CON_ALCANCE_MUNICIPAL
