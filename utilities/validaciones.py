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
    """Regla unica de contrasenas: 8 a 128 caracteres, con letras y numeros."""
    if not password or len(password) < MIN_PASSWORD:
        raise ValueError(f"{campo} debe tener minimo {MIN_PASSWORD} caracteres")
    if len(password) > MAX_PASSWORD:
        raise ValueError(f"{campo} es demasiado larga")
    if not (re.search(r"[A-Za-z]", password) and re.search(r"\d", password)):
        raise ValueError(f"{campo} debe incluir letras y numeros")
