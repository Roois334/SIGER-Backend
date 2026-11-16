"""
Seguridad del transporte (HTTPS) y cabeceras de proteccion.

Por que existe: la contrasena viaja en el cuerpo de la peticion de login. Eso es normal en
cualquier sitio web; lo que la protege es que el canal este CIFRADO (HTTPS/TLS). Sin HTTPS,
cualquiera en la red puede leerla. Este modulo:

  1. Rechaza el trafico que llego por HTTP (detras de Azure el proxy avisa con X-Forwarded-Proto).
     - GET/HEAD: redirige a la misma direccion en HTTPS.
     - Otros metodos (POST con la contrasena): se RECHAZAN con 426 sin procesarlos, porque
       redirigir un POST ya significa que la contrasena viajo en claro una vez.
  2. Envia HSTS para que el navegador use siempre HTTPS con este sitio.
  3. Marca como "no-store" las respuestas sensibles (login, contrasena) para que ningun
     navegador ni proxy las guarde en cache.
  4. Agrega cabeceras basicas (nosniff, X-Frame-Options, Referrer-Policy).

En local (sin proxy no hay cabecera X-Forwarded-Proto) no se bloquea nada.
FORCE_HTTPS=0 en el entorno desactiva el rechazo (solo para depuracion).
"""
import os

from flask import request, redirect, jsonify

HSTS = "max-age=31536000; includeSubDomains"
HOSTS_LOCALES = {"localhost", "127.0.0.1", "::1", "[::1]"}


def es_host_local(host):
    """True para localhost / 127.0.0.1 (con o sin puerto)."""
    host = (host or "").strip().lower()
    if host.startswith("["):  # IPv6 entre corchetes
        return host.split("]")[0] + "]" in HOSTS_LOCALES
    return host.split(":")[0] in HOSTS_LOCALES


def protocolo_cliente(req):
    """Protocolo que uso el cliente: la cabecera del proxy tiene prioridad sobre el esquema local."""
    cabecera = (req.headers.get("X-Forwarded-Proto") or "").split(",")[0].strip().lower()
    return cabecera or req.scheme


def llego_por_http(req):
    """
    True solo si SABEMOS que el cliente uso HTTP: el proxy lo dice de forma explicita.
    Sin cabecera (ejecucion local o llamadas internas) no se asume nada.
    """
    return (req.headers.get("X-Forwarded-Proto") or "").split(",")[0].strip().lower() == "http"


def url_https(url):
    """Convierte http://... en https://... (si ya es https, la deja igual)."""
    return "https://" + url[len("http://"):] if url.lower().startswith("http://") else url


def aplicar_seguridad(app, rutas_sensibles=()):
    """
    Registra los controles en la app Flask.
    rutas_sensibles: prefijos de ruta cuyas respuestas llevan 'Cache-Control: no-store'.
    """
    sensibles = tuple(rutas_sensibles)

    @app.before_request
    def exigir_https():
        if os.environ.get("FORCE_HTTPS", "1") == "0" or not llego_por_http(request):
            return None
        if request.method in ("GET", "HEAD"):
            return redirect(url_https(request.url), code=301)
        # POST/PUT/...: NO se procesa; el dato ya viajo sin cifrar, hay que avisar al cliente
        return jsonify({"error": "Esta direccion solo acepta conexiones seguras (HTTPS)"}), 426

    @app.after_request
    def cabeceras_seguridad(resp):
        resp.headers.setdefault("X-Content-Type-Options", "nosniff")
        resp.headers.setdefault("X-Frame-Options", "DENY")
        resp.headers.setdefault("Referrer-Policy", "same-origin")
        if protocolo_cliente(request) == "https":
            resp.headers.setdefault("Strict-Transport-Security", HSTS)
        if sensibles and request.path.startswith(sensibles):
            resp.headers["Cache-Control"] = "no-store"
            resp.headers.setdefault("Pragma", "no-cache")
        return resp

    return app
