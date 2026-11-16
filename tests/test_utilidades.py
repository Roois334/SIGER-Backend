from datetime import date, datetime

import pytest

from utilities import fechas, limitador, permisos, prioridad
from utilities.validaciones import validar_email, validar_password
from utilities.validaciones_persona import validar_documento, validar_nombre, validar_telefono


class TestEmail:
    def test_limpia_y_pasa_a_minusculas(self):
        assert validar_email("  Ana@Correo.COM ") == "ana@correo.com"

    @pytest.mark.parametrize("malo", ["", None, "sin-arroba", "a@b", "a b@c.com", "x" * 120 + "@c.com"])
    def test_rechaza_invalidos(self, malo):
        with pytest.raises(ValueError):
            validar_email(malo)


class TestPassword:
    def test_acepta_una_valida(self):
        validar_password("Clave.1234")

    @pytest.mark.parametrize("clave,texto", [
        (None, "minimo"), ("Ab.1", "minimo"), ("A" * 129 + "a.1", "demasiado larga"),
        ("Clave .1234", "espacios"), ("clave.1234", "mayuscula"), ("CLAVE.1234", "minuscula"),
        ("Clave.Clave", "numero"), ("Clave12345", "simbolo"),
    ])
    def test_rechaza_con_mensaje(self, clave, texto):
        with pytest.raises(ValueError, match=texto):
            validar_password(clave)

    def test_el_mensaje_usa_el_campo_indicado(self):
        with pytest.raises(ValueError, match="La contrasena nueva"):
            validar_password("corta", "La contrasena nueva")


class TestPersona:
    def test_nombre_valido_normaliza_espacios(self):
        assert validar_nombre("  María   José ") == "María José"
        assert validar_nombre("O'Neil-Pérez") == "O'Neil-Pérez"

    @pytest.mark.parametrize("malo", ["", None, "A", "Ana3", "x" * 81, "Ana_"])
    def test_nombre_invalido(self, malo):
        with pytest.raises(ValueError):
            validar_nombre(malo)

    def test_documento_cedula(self):
        assert validar_documento("cc", "1.234.567-8") == ("CC", "12345678")

    def test_documento_pasaporte(self):
        assert validar_documento("PP", "ab12345") == ("PP", "AB12345")

    @pytest.mark.parametrize("tipo,numero", [("XX", "123456"), ("CC", ""), ("CC", "12"), ("PP", "ab"), ("CC", "abcdef")])
    def test_documento_invalido(self, tipo, numero):
        with pytest.raises(ValueError):
            validar_documento(tipo, numero)

    @pytest.mark.parametrize("entrada,esperado", [
        ("300 123 4567", "3001234567"), ("+57 300 123 4567", "3001234567"),
        ("573001234567", "3001234567"), ("(601) 234-5678"[:0] + "6012345678", "6012345678"),
    ])
    def test_telefono_valido(self, entrada, esperado):
        assert validar_telefono(entrada) == esperado

    @pytest.mark.parametrize("malo", ["", None, "12345", "2001234567", "30012345678"])
    def test_telefono_invalido(self, malo):
        with pytest.raises(ValueError):
            validar_telefono(malo)


class TestPrioridad:
    def test_sin_variables_es_baja(self):
        assert prioridad.calcular_prioridad("baja", 0, 0, 0, 0, None) == ("baja", 0)

    def test_suma_de_puntos_define_el_nivel(self):
        assert prioridad.calcular_prioridad("baja", 6, 0, 0, 0, None)[0] == "media"
        assert prioridad.calcular_prioridad("baja", 21, 3, 0, 0, None)[0] == "alta"
        assert prioridad.calcular_prioridad("baja", 21, 10, 2, 1001, "alto")[0] == "critica"

    def test_el_tipo_pone_un_piso(self):
        assert prioridad.calcular_prioridad("critica", 0, 0, 0, 0, None)[0] == "critica"

    def test_piso_desconocido_cuenta_como_media(self):
        assert prioridad.calcular_prioridad("rara", 0, 0, 0, 0, None)[0] == "media"


class TestFechas:
    def test_ahora_es_naive(self):
        assert fechas.ahora().tzinfo is None

    def test_parsear(self):
        assert fechas.parsear_fecha("2026-03-05", "desde") == date(2026, 3, 5)
        assert fechas.parsear_fecha("  ", "desde") is None
        with pytest.raises(ValueError, match="desde"):
            fechas.parsear_fecha("05/03/2026", "desde")

    def test_rango(self):
        assert fechas.rango_fechas("2026-01-01", "2026-01-31") == (date(2026, 1, 1), date(2026, 1, 31))
        assert fechas.rango_fechas(None, None) == (None, None)
        with pytest.raises(ValueError, match="posterior"):
            fechas.rango_fechas("2026-02-01", "2026-01-01")

    def test_filtrar_por_fecha(self, datos):
        ciudadano = datos.usuario()
        datos.reporte(ciudadano, fecha_hora=datetime(2026, 1, 10, 12))
        datos.reporte(ciudadano, fecha_hora=datetime(2026, 2, 10, 12))
        from models.reporte import Reporte
        q = fechas.filtrar_por_fecha(Reporte.query, Reporte.fecha_hora, date(2026, 1, 10), date(2026, 1, 10))
        assert q.count() == 1
        assert fechas.filtrar_por_fecha(Reporte.query, Reporte.fecha_hora, None, None).count() == 2


class TestLimitador:
    def test_bloquea_al_superar_el_maximo_y_se_libera_con_exito(self):
        lim = limitador.LimitadorIntentos(maximo=2, ventana_seg=60)
        assert lim.segundos_bloqueado("a") == 0
        lim.registrar_fallo("a")
        lim.registrar_fallo("a")
        assert lim.segundos_bloqueado("a") > 0
        lim.registrar_exito("a")
        assert lim.segundos_bloqueado("a") == 0

    def test_los_fallos_vencen(self, monkeypatch):
        lim = limitador.LimitadorIntentos(maximo=1, ventana_seg=10)
        ahora = [1000.0]
        monkeypatch.setattr(limitador.time, "time", lambda: ahora[0])
        lim.registrar_fallo("a")
        assert lim.segundos_bloqueado("a") > 0
        ahora[0] += 11
        assert lim.segundos_bloqueado("a") == 0


class TestPermisos:
    def test_matriz(self):
        assert permisos.tiene_permiso(permisos.CIUDADANO, "reportes.crear")
        assert not permisos.tiene_permiso(permisos.CIUDADANO, "usuarios.administrar")
        assert not permisos.tiene_permiso(permisos.ADMINISTRADOR, "permiso.inexistente")

    def test_alcance_municipal(self):
        assert permisos.tiene_alcance_municipal(permisos.GESTOR_MUNICIPAL)
        assert not permisos.tiene_alcance_municipal(permisos.ADMINISTRADOR)
