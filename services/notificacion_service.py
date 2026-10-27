"""
HU-15 - Notificaciones.

Eventos que generan una notificacion (cada una identifica la emergencia por su folio):

  reporte_nuevo   -> gestores del municipio
  asignado        -> ciudadano que reporto + usuarios del organismo asignado
  reasignado      -> ciudadano + organismo nuevo (y se avisa al organismo anterior)
  en_atencion     -> ciudadano + gestores del municipio
  resuelto        -> ciudadano + gestores del municipio
  devuelto        -> gestores del municipio (el organismo no puede atenderla)
  descartado      -> ciudadano
  cerrado         -> ciudadano
  reclasificado   -> ciudadano + organismo asignado

Mecanismo de entrega: dentro de la plataforma (campana con contador). Ademas, si el
correo esta configurado y NOTIFICAR_CORREO=1 en el .env, el ciudadano recibe un correo.

IMPORTANTE: generar una notificacion NUNCA debe romper la accion principal. Todo
va dentro de try/except: si algo falla se registra en el log y la accion sigue.
"""
import html
import logging
import os

from extensions import db
from models.notificacion import Notificacion
from models.user import User
from models.catalogos import Rol
from utilities.permisos import GESTOR_MUNICIPAL, ORGANISMO_ATENCION
from utilities.fechas import ahora as _ahora

log = logging.getLogger("siger.notificaciones")

LIMITE_LISTA = 50


def _tipo_bonito(tipo):
    return {"Inundacion": "Inundación", "Accidente de transito": "Accidente de tránsito",
            "Emergencia medica": "Emergencia médica"}.get(tipo, tipo)


# --------------------------------------------------------------------- destinatarios

def _gestores(municipio_id):
    return (User.query.join(Rol, User.rol_id == Rol.id)
            .filter(Rol.nombre == GESTOR_MUNICIPAL, User.activo.is_(True), User.municipio_id == municipio_id)
            .all())


def _organismo(organismo_id, municipio_id):
    if not organismo_id:
        return []
    return (User.query.join(Rol, User.rol_id == Rol.id)
            .filter(Rol.nombre == ORGANISMO_ATENCION, User.activo.is_(True),
                    User.organismo_id == organismo_id, User.municipio_id == municipio_id)
            .all())


def _ciudadano(reporte):
    c = reporte.ciudadano
    return [c] if c and c.activo else []


# --------------------------------------------------------------------- nucleo

class NotificacionService:

    @staticmethod
    def _crear(destinatarios, reporte, tipo, titulo, mensaje, actor=None):
        """Agrega una notificacion por destinatario (sin repetir y sin avisar a quien hizo el cambio)."""
        vistos = set()
        creadas = []
        for u in destinatarios:
            if u is None or u.id in vistos or (actor is not None and u.id == actor.id):
                continue
            vistos.add(u.id)
            n = Notificacion(
                usuario_id=u.id, reporte_id=reporte.id, tipo=tipo,
                titulo=titulo[:150], mensaje=mensaje[:300],
                leida=False, fecha_creacion=_ahora(),
            )
            db.session.add(n)
            creadas.append((u, n))
        return creadas

    @staticmethod
    def _emitir(reporte, evento, actor, destinos):
        """
        destinos: lista de (destinatarios, titulo, mensaje) para poder personalizar el texto
        segun quien lo recibe. Guarda y confirma; si algo falla, deshace SOLO esto y sigue.
        """
        try:
            creadas = []
            for destinatarios, t, m in destinos:
                creadas += NotificacionService._crear(destinatarios, reporte, evento, t, m, actor)
            db.session.commit()
            NotificacionService._enviar_correos(reporte, creadas)
        except Exception as e:  # nunca tumba la accion principal
            db.session.rollback()
            log.error("No se pudo generar la notificacion '%s' del reporte %s: %s", evento, getattr(reporte, "id", "?"), e)
            print(f"[SIGER] ERROR generando notificacion '{evento}': {e}")

    # --------------------------------------------------------------- correo (opcional)

    @staticmethod
    def _enviar_correos(reporte, creadas):
        if os.environ.get("NOTIFICAR_CORREO", "0") != "1":
            return
        try:
            from utilities.correo import enviar_correo, correo_configurado
            if not correo_configurado():
                return
            for u, n in creadas:
                if u.id != reporte.ciudadano_id:   # solo el ciudadano recibe correo
                    continue
                enviar_correo(
                    u.email, f"SIGER — {n.titulo}",
                    NotificacionService._correo_html(u.nombre, reporte, n),
                    f"Hola {u.nombre},\n\n{n.titulo}\n{n.mensaje}\n\nFolio: {reporte.folio}\n\nSIGER - Sabana de Occidente",
                    imagenes=["logo", "logo_grande"],
                )
        except Exception as e:
            log.error("No se pudo enviar el correo de la notificacion: %s", e)

    @staticmethod
    def _correo_html(nombre, reporte, n):
        f = "'Plus Jakarta Sans','Segoe UI',Helvetica,Arial,sans-serif"
        def esc(texto):
            return html.escape(str(texto or ""))
        return f"""\
<!doctype html><html lang="es" style="color-scheme:dark;"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><meta name="color-scheme" content="dark">
<title>{esc(n.titulo)}</title></head>
<body style="margin:0;padding:0;background:#070b12;" bgcolor="#070b12">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" bgcolor="#070b12"><tr><td align="center" style="padding:34px 14px 40px;">
<table role="presentation" width="560" cellpadding="0" cellspacing="0" style="max-width:560px;width:100%;">
<tr><td style="padding:0 4px 20px;"><table role="presentation" cellpadding="0" cellspacing="0"><tr>
<td width="44"><img src="cid:logo@siger" width="44" height="44" alt="SIGER" style="display:block;border:0;border-radius:13px;"></td>
<td style="padding-left:12px;font-family:{f};"><div style="font:800 19px/1.15 {f};color:#ffffff;">SIGER</div>
<div style="font:600 11px/1.4 {f};color:#57708f;">Sabana de Occidente</div></td></tr></table></td></tr>
<tr><td bgcolor="#101a29" style="background:#101a29;border:1px solid #1b3a5f;border-radius:20px;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0">
<tr><td align="center" bgcolor="#0d1b2e" style="padding:34px 36px 26px;background:#0d1b2e;background-image:linear-gradient(180deg,#12294a 0%,#101a29 100%);border-radius:19px 19px 0 0;">
        <img src="cid:logo_grande@siger" width="132" height="132" alt="SIGER" style="display:block;width:132px;height:132px;border:0;border-radius:50%;box-shadow:0 0 0 6px rgba(33,150,243,.14),0 14px 40px rgba(33,150,243,.35);">
      </td></tr>
<tr><td align="center" style="padding:22px 36px 0;"><table role="presentation" cellpadding="0" cellspacing="0"><tr>
<td style="padding:7px 16px;border-radius:999px;background:#0f2540;border:1px solid #1b3a5f;font:700 12px/1 {f};color:#64B5F6;">Folio {esc(reporte.folio)}</td></tr></table></td></tr>
<tr><td align="center" style="padding:18px 36px 0;"><h1 style="margin:0;font:800 26px/1.25 {f};color:#ffffff;letter-spacing:-.5px;">{esc(n.titulo)}</h1></td></tr>
<tr><td align="center" style="padding:14px 40px 0;"><p style="margin:0 0 8px;font:700 15px/1.5 {f};color:#e3f2fd;">Hola {esc(nombre)},</p>
<p style="margin:0;font:15px/1.7 {f};color:#8fa8c9;">{esc(n.mensaje)}</p></td></tr>
<tr><td style="padding:26px 36px 34px;"><table role="presentation" cellpadding="0" cellspacing="0" width="100%" bgcolor="#0b111c" style="background:#0b111c;border:1px solid #1b3a5f;border-radius:16px;"><tr>
<td width="50%" align="center" style="padding:16px 8px;border-right:1px solid #1b3a5f;"><div style="font:800 17px/1.2 {f};color:#64B5F6;">{esc(_tipo_bonito(reporte.tipo))}</div>
<div style="font:700 10px/1.6 {f};color:#57708f;letter-spacing:1.2px;text-transform:uppercase;">Tipo</div></td>
<td width="50%" align="center" style="padding:16px 8px;"><div style="font:800 17px/1.2 {f};color:#64B5F6;">{esc(reporte.municipio.nombre if reporte.municipio else '—')}</div>
<div style="font:700 10px/1.6 {f};color:#57708f;letter-spacing:1.2px;text-transform:uppercase;">Municipio</div></td></tr></table></td></tr>
</table></td></tr>
<tr><td align="center" style="padding:24px 16px 0;font:12px/1.7 {f};color:#57708f;">Ingresa a SIGER para ver el detalle de tu reporte.</td></tr>
</table></td></tr></table></body></html>"""

    # --------------------------------------------------------------- eventos

    @staticmethod
    def reporte_nuevo(reporte):
        tipo = _tipo_bonito(reporte.tipo)
        NotificacionService._emitir(
            reporte, "reporte_nuevo", None,
            [(_gestores(reporte.municipio_id),
              f"Nueva emergencia: {tipo}",
              f"Se reportó {tipo.lower()} en {reporte.municipio.nombre if reporte.municipio else 'tu municipio'} "
              f"({reporte.direccion}). Folio {reporte.folio}. Está pendiente de revisión.")])

    @staticmethod
    def asignado(reporte, actor, organismo_nuevo, organismo_previo=None):
        tipo = _tipo_bonito(reporte.tipo)
        destinos = [
            (_ciudadano(reporte), "Tu reporte fue aceptado",
             f"Tu reporte {reporte.folio} ({tipo}) fue revisado y asignado a {organismo_nuevo.nombre}."),
            (_organismo(organismo_nuevo.id, reporte.municipio_id), "Nueva emergencia asignada",
             f"El gestor asignó a tu organismo el reporte {reporte.folio}: {tipo} en {reporte.direccion}."),
        ]
        evento = "asignado"
        if organismo_previo is not None and organismo_previo.id != organismo_nuevo.id:
            evento = "reasignado"
            destinos[0] = (destinos[0][0], "Tu reporte fue reasignado",
                           f"Tu reporte {reporte.folio} ahora está a cargo de {organismo_nuevo.nombre}.")
            destinos.append((_organismo(organismo_previo.id, reporte.municipio_id), "Emergencia reasignada",
                             f"El reporte {reporte.folio} fue reasignado a {organismo_nuevo.nombre} y ya no está a cargo de tu organismo."))
        NotificacionService._emitir(reporte, evento, actor, destinos)

    @staticmethod
    def cambio_estado(reporte, actor, accion, comentario=None, organismo=None):
        tipo = _tipo_bonito(reporte.tipo)
        org = (organismo or reporte.organismo).nombre if (organismo or reporte.organismo) else "el organismo"
        f = reporte.folio
        gestores = _gestores(reporte.municipio_id)
        ciu = _ciudadano(reporte)
        if accion == "iniciar":
            evento = "en_atencion"
            destinos = [(ciu, "Tu emergencia está en atención", f"{org} inició la atención de tu reporte {f} ({tipo})."),
                        (gestores, "Atención iniciada", f"{org} inició la atención del reporte {f} ({tipo}).")]
        elif accion == "resolver":
            evento = "resuelto"
            destinos = [(ciu, "Tu emergencia fue resuelta", f"{org} marcó como resuelto tu reporte {f} ({tipo})."),
                        (gestores, "Emergencia resuelta", f"{org} resolvió el reporte {f} ({tipo}). Puedes confirmar el cierre.")]
        elif accion == "devolver":
            evento = "devuelto"
            motivo = f" Motivo: {comentario}" if comentario else ""
            destinos = [(gestores, "Reporte devuelto por el organismo",
                         f"{org} no puede atender el reporte {f} ({tipo}) y lo devolvió.{motivo}")]
        elif accion == "descartar":
            evento = "descartado"
            motivo = f" Motivo: {comentario}" if comentario else ""
            destinos = [(ciu, "Tu reporte fue descartado",
                         f"Tras revisarlo, tu reporte {f} ({tipo}) fue descartado.{motivo}")]
        elif accion == "cerrar":
            evento = "cerrado"
            destinos = [(ciu, "Tu reporte fue cerrado", f"El gestor confirmó el cierre de tu reporte {f} ({tipo}). Gracias por avisar.")]
        else:
            return
        NotificacionService._emitir(reporte, evento, actor, destinos)

    @staticmethod
    def reclasificado(reporte, actor, tipo_anterior):
        nuevo = _tipo_bonito(reporte.tipo)
        ant = _tipo_bonito(tipo_anterior)
        texto = f"El tipo del reporte {reporte.folio} cambió de {ant} a {nuevo}."
        NotificacionService._emitir(
            reporte, "reclasificado", actor,
            [(_ciudadano(reporte), "Se actualizó el tipo de tu emergencia", texto),
             (_organismo(reporte.organismo_id, reporte.municipio_id), "Se actualizó el tipo de una emergencia", texto)])

    # --------------------------------------------------------------- consulta (usuario)

    @staticmethod
    def _dto(n):
        return {
            "id": n.id, "tipo": n.tipo, "titulo": n.titulo, "mensaje": n.mensaje,
            "leida": bool(n.leida), "reporte_id": n.reporte_id,
            "folio": n.reporte.folio if n.reporte else None,
            "fecha_creacion": n.fecha_creacion.isoformat() if n.fecha_creacion else None,
        }

    @staticmethod
    def contar_no_leidas(usuario):
        return Notificacion.query.filter_by(usuario_id=usuario.id, leida=False).count()

    @staticmethod
    def listar(usuario, solo_no_leidas=False, limite=LIMITE_LISTA, antes_id=None):
        q = Notificacion.query.filter_by(usuario_id=usuario.id)
        if solo_no_leidas:
            q = q.filter_by(leida=False)
        if antes_id:
            q = q.filter(Notificacion.id < antes_id)
        limite = max(1, min(int(limite or LIMITE_LISTA), 100))
        filas = q.order_by(Notificacion.id.desc()).limit(limite + 1).all()
        hay_mas = len(filas) > limite
        return {
            "notificaciones": [NotificacionService._dto(n) for n in filas[:limite]],
            "no_leidas": NotificacionService.contar_no_leidas(usuario),
            "hay_mas": hay_mas,
        }

    @staticmethod
    def marcar_leida(notificacion_id, usuario):
        n = Notificacion.query.filter_by(id=notificacion_id, usuario_id=usuario.id).first()
        if not n:
            raise LookupError("Notificación no encontrada")
        if not n.leida:
            n.leida = True
            db.session.commit()
        return NotificacionService._dto(n)

    @staticmethod
    def marcar_todas(usuario):
        Notificacion.query.filter_by(usuario_id=usuario.id, leida=False).update({"leida": True})
        db.session.commit()
