import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from flask import current_app
from werkzeug.security import generate_password_hash, check_password_hash

from extensions import db
from models.user import User
from models.password_reset import PasswordReset
from utilities.correo import enviar_correo
from utilities.validaciones import validar_password

MINUTOS_VALIDEZ = 30
MAX_SOLICITUDES_POR_HORA = 3


def _hash(token):
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _ahora():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _enmascarar(email):
    local, _, dominio = email.partition("@")
    visible = local[:2] if len(local) > 2 else local[:1]
    return f"{visible}{'•' * max(3, len(local) - len(visible))}@{dominio}"


def _correo_html(nombre, enlace, minutos):
    # Mismos colores y formas que la aplicacion web (tema oscuro de SIGER).
    # Las imagenes (logo, banner con radar, icono) viajan incrustadas en el correo (cid:).
    fuente = "'Plus Jakarta Sans','Segoe UI',Helvetica,Arial,sans-serif"
    return f"""\
<!doctype html>
<html lang="es" style="color-scheme:dark;supported-color-schemes:dark;">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="dark">
<meta name="supported-color-schemes" content="dark">
<title>Restablece tu contraseña de SIGER</title>
<style>@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@500;700;800&display=swap');</style>
</head>
<body style="margin:0;padding:0;background:#070b12;" bgcolor="#070b12">
<div style="display:none;max-height:0;overflow:hidden;opacity:0;color:#070b12;">Crea una nueva contraseña para tu cuenta de SIGER. El enlace vence en {minutos} minutos.</div>

<table role="presentation" width="100%" cellpadding="0" cellspacing="0" bgcolor="#070b12" style="background:#070b12;">
<tr><td align="center" style="padding:34px 14px 40px;">

<table role="presentation" width="560" cellpadding="0" cellspacing="0" style="max-width:560px;width:100%;">

  <!-- Barra de marca (igual que el menú de la web) -->
  <tr><td style="padding:0 4px 20px;">
    <table role="presentation" cellpadding="0" cellspacing="0"><tr>
      <td width="44" style="width:44px;"><img src="cid:logo@siger" width="44" height="44" alt="SIGER" style="display:block;width:44px;height:44px;border:0;border-radius:13px;"></td>
      <td style="padding-left:12px;font-family:{fuente};">
        <div style="font:800 19px/1.15 {fuente};color:#ffffff;letter-spacing:-.2px;">SIGER</div>
        <div style="font:600 11px/1.4 {fuente};color:#57708f;">Sabana de Occidente</div>
      </td>
    </tr></table>
  </td></tr>

  <!-- Tarjeta -->
  <tr><td bgcolor="#101a29" style="background:#101a29;border:1px solid #1b3a5f;border-radius:20px;">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0">

      <tr><td style="padding:0;line-height:0;font-size:0;border-radius:19px 19px 0 0;">
        <img src="cid:banner@siger" width="558" alt="" style="display:block;width:100%;max-width:558px;height:auto;border:0;border-radius:19px 19px 0 0;">
      </td></tr>

      <tr><td align="center" style="padding:6px 36px 0;">
        <table role="presentation" cellpadding="0" cellspacing="0"><tr>
          <td style="padding:7px 16px;border-radius:999px;background:#0f2540;border:1px solid #1b3a5f;font:700 12px/1 {fuente};color:#64B5F6;">
            <span style="display:inline-block;width:7px;height:7px;border-radius:50%;background:#2196F3;margin-right:8px;vertical-align:1px;"></span>Recuperar contraseña
          </td>
        </tr></table>
      </td></tr>

      <tr><td align="center" style="padding:20px 36px 0;">
        <h1 style="margin:0;font:800 28px/1.2 {fuente};color:#ffffff;letter-spacing:-.6px;">Restablece tu contraseña</h1>
      </td></tr>

      <tr><td align="center" style="padding:14px 40px 0;">
        <p style="margin:0 0 8px;font:700 15px/1.5 {fuente};color:#e3f2fd;">Hola {nombre},</p>
        <p style="margin:0;font:15px/1.7 {fuente};color:#8fa8c9;">
          Recibimos una solicitud para cambiar la contraseña de tu cuenta.
          Pulsa el botón y crea una nueva en menos de un minuto.
        </p>
      </td></tr>

      <!-- Botón (mismo degradado que los botones de la web) -->
      <tr><td align="center" style="padding:28px 36px 0;">
        <table role="presentation" cellpadding="0" cellspacing="0" width="100%" style="max-width:340px;"><tr>
          <td align="center" bgcolor="#1E88E5" style="border-radius:12px;background:#1E88E5;background-image:linear-gradient(135deg,#1E88E5,#64B5F6);box-shadow:0 8px 24px rgba(33,150,243,.38);">
            <a href="{enlace}" target="_blank" style="display:block;padding:15px 24px;font:800 15px/1.2 {fuente};color:#ffffff;text-decoration:none;border-radius:12px;">Crear nueva contraseña</a>
          </td>
        </tr></table>
      </td></tr>

      <!-- Cifras (misma barra que el inicio de la web) -->
      <tr><td style="padding:26px 36px 0;">
        <table role="presentation" cellpadding="0" cellspacing="0" width="100%" bgcolor="#0b111c" style="background:#0b111c;border:1px solid #1b3a5f;border-radius:16px;"><tr>
          <td width="50%" align="center" style="padding:16px 8px;border-right:1px solid #1b3a5f;">
            <div style="font:800 26px/1.1 {fuente};color:#64B5F6;letter-spacing:-.5px;">{minutos}</div>
            <div style="font:700 10px/1.6 {fuente};color:#57708f;letter-spacing:1.2px;text-transform:uppercase;">Minutos de validez</div>
          </td>
          <td width="50%" align="center" style="padding:16px 8px;">
            <div style="font:800 26px/1.1 {fuente};color:#64B5F6;letter-spacing:-.5px;">1</div>
            <div style="font:700 10px/1.6 {fuente};color:#57708f;letter-spacing:1.2px;text-transform:uppercase;">Solo uso</div>
          </td>
        </tr></table>
      </td></tr>

      <!-- Enlace de respaldo -->
      <tr><td style="padding:24px 36px 0;">
        <div style="font:700 11px/1.5 {fuente};color:#8fa8c9;letter-spacing:.8px;text-transform:uppercase;margin-bottom:8px;">¿El botón no funciona?</div>
        <div style="padding:12px 14px;background:#0b111c;border:1px solid #1b3a5f;border-radius:12px;font:12px/1.6 Consolas,Menlo,'Courier New',monospace;word-break:break-all;">
          <a href="{enlace}" target="_blank" style="color:#64B5F6;text-decoration:none;">{enlace}</a>
        </div>
      </td></tr>

      <!-- Aviso (igual que los avisos de la web) -->
      <tr><td style="padding:22px 36px 34px;">
        <table role="presentation" cellpadding="0" cellspacing="0" width="100%" bgcolor="#0f2540" style="background:#0f2540;border:1px solid #1b3a5f;border-radius:14px;"><tr>
          <td width="30" valign="top" style="padding:14px 0 14px 14px;"><img src="cid:ico_escudo@siger" width="22" height="22" alt="" style="display:block;border:0;"></td>
          <td style="padding:13px 16px 13px 10px;font:13px/1.65 {fuente};color:#8fa8c9;">
            <b style="color:#e3f2fd;">¿No fuiste tú?</b> Ignora este correo: tu contraseña seguirá siendo la misma
            y nadie puede cambiarla sin este enlace.
          </td>
        </tr></table>
      </td></tr>

    </table>
  </td></tr>

  <!-- Pie -->
  <tr><td align="center" style="padding:24px 16px 0;font:12px/1.7 {fuente};color:#57708f;">
    SIGER — Sistema de Gestión de Emergencias Regional de la Sabana de Occidente<br>
    Mensaje automático, por favor no respondas a este correo.
  </td></tr>

</table>

</td></tr></table>
</body></html>"""



class RecuperacionService:
    @staticmethod
    def solicitar(email):
        """
        Crea un enlace de un solo uso y lo envia al correo. NUNCA revela si el correo existe:
        el que llama siempre responde lo mismo.
        """
        email = (email or "").strip().lower()
        if not email or "@" not in email:
            raise ValueError("Escribe tu correo electronico")

        user = User.query.filter_by(email=email, activo=True).first()
        if not user:
            return

        hace_una_hora = _ahora() - timedelta(hours=1)
        recientes = PasswordReset.query.filter(
            PasswordReset.usuario_id == user.id, PasswordReset.fecha_creacion >= hace_una_hora
        ).count()
        if recientes >= MAX_SOLICITUDES_POR_HORA:
            return  # silencioso: evita que alguien llene el buzon de otra persona

        # Los enlaces anteriores quedan invalidados
        PasswordReset.query.filter_by(usuario_id=user.id, usado=False).update({"usado": True})

        token = secrets.token_urlsafe(32)
        db.session.add(PasswordReset(
            usuario_id=user.id, token_hash=_hash(token),
            expira=_ahora() + timedelta(minutes=MINUTOS_VALIDEZ), usado=False, fecha_creacion=_ahora(),
        ))
        db.session.commit()

        base = current_app.config.get("FRONTEND_URL", "http://127.0.0.1:5001").rstrip("/")
        enlace = f"{base}/restablecer/{token}"
        texto = (f"Hola {user.nombre},\n\nPara crear una nueva contraseña en SIGER abre este enlace "
                 f"(vence en {MINUTOS_VALIDEZ} minutos y se usa una sola vez):\n{enlace}\n\n"
                 "Si no fuiste tú, ignora este mensaje.")
        enviar_correo(user.email, "Restablece tu contraseña de SIGER",
                      _correo_html(user.nombre, enlace, MINUTOS_VALIDEZ), texto, enlace_dev=enlace,
                      imagenes=["logo", "banner", "ico_escudo"])

    @staticmethod
    def _buscar_valido(token):
        if not token:
            return None
        pr = PasswordReset.query.filter_by(token_hash=_hash(token)).first()
        if not pr or pr.usado or pr.expira < _ahora():
            return None
        return pr

    @staticmethod
    def validar(token):
        pr = RecuperacionService._buscar_valido(token)
        if not pr:
            raise ValueError("El enlace no es valido o ya vencio")
        user = User.query.get(pr.usuario_id)
        if not user or not user.activo:
            raise ValueError("El enlace no es valido o ya vencio")
        return {"email": _enmascarar(user.email), "minutos": max(1, int((pr.expira - _ahora()).total_seconds() // 60))}

    @staticmethod
    def restablecer(token, nueva):
        pr = RecuperacionService._buscar_valido(token)
        if not pr:
            raise ValueError("El enlace no es valido o ya vencio. Pide uno nuevo")
        user = User.query.get(pr.usuario_id)
        if not user or not user.activo:
            raise ValueError("El enlace no es valido o ya vencio. Pide uno nuevo")
        validar_password(nueva)
        if check_password_hash(user.password_hash, nueva):
            raise ValueError("Elige una contrasena distinta a la actual")

        user.password_hash = generate_password_hash(nueva)
        PasswordReset.query.filter_by(usuario_id=user.id, usado=False).update({"usado": True})
        db.session.commit()
