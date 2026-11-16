import logging
import os
import smtplib
import ssl
import threading
from email.message import EmailMessage
from email.utils import formataddr

log = logging.getLogger("siger.correo")

SMTP_HOST = os.environ.get("MAIL_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("MAIL_PORT", "587"))


def correo_configurado():
    return bool(os.environ.get("MAIL_USER") and os.environ.get("MAIL_PASSWORD"))


CARPETA_IMAGENES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static", "correo")


def _enviar(destino, asunto, html, texto, imagenes=None):
    usuario = os.environ.get("MAIL_USER")
    clave = (os.environ.get("MAIL_PASSWORD") or "").replace(" ", "")
    nombre = os.environ.get("MAIL_NOMBRE", "SIGER")

    msg = EmailMessage()
    msg["Subject"] = asunto
    msg["From"] = formataddr((nombre, usuario))
    msg["To"] = destino
    msg.set_content(texto)
    msg.add_alternative(html, subtype="html")

    cuerpo_html = msg.get_body(("html",))
    for cid in (imagenes or []):
        ruta = os.path.join(CARPETA_IMAGENES, cid + ".png")
        if os.path.exists(ruta):
            with open(ruta, "rb") as f:
                cuerpo_html.add_related(f.read(), maintype="image", subtype="png", cid=f"<{cid}@siger>")

    contexto = ssl.create_default_context()
    contexto.check_hostname = True
    contexto.verify_mode = ssl.CERT_REQUIRED
    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=20) as s:
            s.starttls(context=contexto)
            s.login(usuario, clave)
            s.send_message(msg)
        log.info("Correo enviado a %s", destino)
    except Exception as e:
        log.error("No se pudo enviar el correo a %s: %s", destino, e)
        print(f"[SIGER] ERROR enviando correo a {destino}: {e}")


def enviar_correo(destino, asunto, html, texto, enlace_dev=None, imagenes=None):
    if not correo_configurado():
        print("\n[SIGER] Correo NO configurado (MAIL_USER / MAIL_PASSWORD). Modo desarrollo.")
        print(f"[SIGER] Para: {destino}\n[SIGER] Asunto: {asunto}\n[SIGER] Enlace: {enlace_dev}\n")
        return
    threading.Thread(target=_enviar, args=(destino, asunto, html, texto, imagenes), daemon=True).start()
