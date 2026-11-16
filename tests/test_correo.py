"""Envio de correos (SMTP simulado: nunca se contacta a Gmail)."""
import threading

import utilities.correo as correo


class _SMTPFalso:
    instancias = []

    def __init__(self, host, port, timeout=None):
        self.host, self.port, self.eventos = host, port, []
        _SMTPFalso.instancias.append(self)

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def starttls(self, context=None):
        self.eventos.append("tls")

    def login(self, usuario, clave):
        self.eventos.append(("login", usuario, clave))

    def send_message(self, msg):
        self.eventos.append(("mensaje", msg))


def _configurar(monkeypatch):
    monkeypatch.setenv("MAIL_USER", "siger@gmail.com")
    monkeypatch.setenv("MAIL_PASSWORD", "abcd efgh ijkl mnop")
    _SMTPFalso.instancias.clear()
    monkeypatch.setattr(correo.smtplib, "SMTP", _SMTPFalso)


def test_configurado_solo_con_usuario_y_clave(monkeypatch):
    assert not correo.correo_configurado()
    monkeypatch.setenv("MAIL_USER", "a@b.com")
    assert not correo.correo_configurado()
    monkeypatch.setenv("MAIL_PASSWORD", "x")
    assert correo.correo_configurado()


def test_sin_configurar_imprime_el_enlace_y_no_envia(capsys, monkeypatch):
    monkeypatch.setattr(correo.smtplib, "SMTP", lambda *a, **k: (_ for _ in ()).throw(AssertionError("no debe conectar")))
    correo.enviar_correo("ana@x.com", "Asunto", "<p>hola</p>", "hola", enlace_dev="http://enlace")
    salida = capsys.readouterr().out
    assert "http://enlace" in salida and "ana@x.com" in salida


def test_envia_con_tls_y_clave_sin_espacios(monkeypatch):
    _configurar(monkeypatch)
    correo._enviar("ana@x.com", "Asunto", "<p>hola</p>", "hola", imagenes=["logo", "no_existe"])
    smtp = _SMTPFalso.instancias[0]
    assert smtp.eventos[0] == "tls"
    assert smtp.eventos[1] == ("login", "siger@gmail.com", "abcdefghijklmnop")
    msg = smtp.eventos[2][1]
    assert msg["To"] == "ana@x.com" and msg["Subject"] == "Asunto"


def test_un_fallo_de_smtp_no_se_propaga(monkeypatch, capsys):
    _configurar(monkeypatch)
    monkeypatch.setattr(correo.smtplib, "SMTP", lambda *a, **k: (_ for _ in ()).throw(OSError("sin red")))
    correo._enviar("ana@x.com", "Asunto", "<p>hola</p>", "hola")
    assert "ERROR enviando correo" in capsys.readouterr().out


def test_enviar_correo_lo_hace_en_segundo_plano(monkeypatch):
    _configurar(monkeypatch)
    hilos = []
    original = threading.Thread

    class _Hilo(original):
        def __init__(self, *a, **k):
            super().__init__(*a, **k)
            hilos.append(self)

    monkeypatch.setattr(correo.threading, "Thread", _Hilo)
    correo.enviar_correo("ana@x.com", "Asunto", "<p>hola</p>", "hola")
    hilos[0].join(timeout=5)
    assert _SMTPFalso.instancias and hilos[0].daemon
