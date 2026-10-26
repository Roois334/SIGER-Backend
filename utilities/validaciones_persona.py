import re

TIPOS_DOCUMENTO = {
    "CC": "Cedula de ciudadania",
    "CE": "Cedula de extranjeria",
    "TI": "Tarjeta de identidad",
    "PP": "Pasaporte",
}


_LETRAS = "A-Za-zÁÉÍÓÚÜÑáéíóúüñ"
_NOMBRE_RE = re.compile(rf"^[{_LETRAS}]+(?:[ '\-][{_LETRAS}]+)*$")


def validar_nombre(valor, campo="El nombre"):
    """Nombres y apellidos: solo letras (con tildes y n), espacios, apostrofe y guion. Devuelve el texto limpio."""
    valor = re.sub(r"\s+", " ", (valor or "").strip())
    if not valor:
        raise ValueError(f"{campo} es obligatorio")
    if len(valor) < 2:
        raise ValueError(f"{campo} debe tener al menos 2 letras")
    if len(valor) > 80:
        raise ValueError(f"{campo} no puede superar 80 caracteres")
    if not _NOMBRE_RE.match(valor):
        raise ValueError(f"{campo} solo puede tener letras")
    return valor


def validar_documento(tipo, numero):
    """Devuelve (tipo, numero) limpios o lanza ValueError."""
    tipo = (tipo or "").strip().upper()
    if tipo not in TIPOS_DOCUMENTO:
        raise ValueError("Selecciona el tipo de documento")
    numero = re.sub(r"[\s.\-]", "", numero or "").upper()
    if not numero:
        raise ValueError("El numero de documento es obligatorio")
    if tipo == "PP":
        if not re.fullmatch(r"[A-Z0-9]{5,15}", numero):
            raise ValueError("El pasaporte debe tener entre 5 y 15 letras o numeros")
    elif not re.fullmatch(r"\d{5,12}", numero):
        raise ValueError("El numero de documento debe tener entre 5 y 12 digitos")
    return tipo, numero


def validar_telefono(telefono):
    """Celular colombiano (3XXXXXXXXX) o fijo con indicativo (60XXXXXXXX). Devuelve 10 digitos."""
    digitos = re.sub(r"[\s\-()]", "", telefono or "")
    if digitos.startswith("+57"):
        digitos = digitos[3:]
    elif digitos.startswith("57") and len(digitos) == 12:
        digitos = digitos[2:]
    if not re.fullmatch(r"(3\d{9}|60\d{8})", digitos):
        raise ValueError("Ingresa un telefono valido de 10 digitos (ej. 3001234567)")
    return digitos
