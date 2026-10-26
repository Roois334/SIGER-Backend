import re

MIN_PASSWORD = 8
MAX_PASSWORD = 128
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]{2,}$")


def validar_email(email):
    """Devuelve el correo limpio y en minusculas, o lanza ValueError."""
    email = (email or "").strip().lower()
    if len(email) > 120 or not _EMAIL_RE.match(email):
        raise ValueError("Ingresa un correo valido")
    return email


def validar_password(password, campo="La contrasena"):
    """
    Regla unica de contrasenas (igual a la del formulario): 8 a 128 caracteres,
    con una mayuscula, una minuscula, un numero, un simbolo y sin espacios.
    """
    if not password or len(password) < MIN_PASSWORD:
        raise ValueError(f"{campo} debe tener minimo {MIN_PASSWORD} caracteres")
    if len(password) > MAX_PASSWORD:
        raise ValueError(f"{campo} es demasiado larga")
    if re.search(r"\s", password):
        raise ValueError(f"{campo} no puede tener espacios")
    faltan = []
    if not re.search(r"[A-ZÁÉÍÓÚÜÑ]", password):
        faltan.append("una mayuscula")
    if not re.search(r"[a-záéíóúüñ]", password):
        faltan.append("una minuscula")
    if not re.search(r"\d", password):
        faltan.append("un numero")
    if not re.search(r"[^A-Za-z0-9áéíóúüñÁÉÍÓÚÜÑ\s]", password):
        faltan.append("un simbolo (! @ # $ % & * ...)")
    if faltan:
        raise ValueError(f"{campo} debe incluir " + ", ".join(faltan))
