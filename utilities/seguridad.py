import os

from flask import request, redirect, jsonify

HSTS = "max-age=31536000; includeSubDomains"
HOSTS_LOCALES = {"localhost", "127.0.0.1", "::1", "[::1]"}


def es_host_local(host):
    host = (host or "").strip().lower()
    if host.startswith("["):
        return host.split("]")[0] + "]" in HOSTS_LOCALES
    return host.split(":")[0] in HOSTS_LOCALES


def protocolo_cliente(req):
    cabecera = (req.headers.get("X-Forwarded-Proto") or "").split(",")[0].strip().lower()
    return cabecera or req.scheme


def llego_por_http(req):
    return (req.headers.get("X-Forwarded-Proto") or "").split(",")[0].strip().lower() == "http"


def url_https(url):
    return "https://" + url[len("http://"):] if url.lower().startswith("http://") else url


def aplicar_seguridad(app, rutas_sensibles=()):
    sensibles = tuple(rutas_sensibles)

    @app.before_request
    def exigir_https():
        if os.environ.get("FORCE_HTTPS", "1") == "0" or not llego_por_http(request):
            return None
        if request.method in ("GET", "HEAD"):
            return redirect(url_https(request.url), code=301)
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
