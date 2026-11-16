import threading
import time


class LimitadorIntentos:
    def __init__(self, maximo=5, ventana_seg=900):
        self.maximo = maximo
        self.ventana = ventana_seg
        self._fallos = {}
        self._lock = threading.Lock()

    def _limpiar(self, clave, ahora):
        vigentes = [t for t in self._fallos.get(clave, []) if ahora - t < self.ventana]
        if vigentes:
            self._fallos[clave] = vigentes
        else:
            self._fallos.pop(clave, None)
        return vigentes

    def segundos_bloqueado(self, clave):
        ahora = time.time()
        with self._lock:
            fallos = self._limpiar(clave, ahora)
            if len(fallos) >= self.maximo:
                return int(self.ventana - (ahora - fallos[0])) + 1
            return 0

    def registrar_fallo(self, clave):
        ahora = time.time()
        with self._lock:
            self._limpiar(clave, ahora)
            self._fallos.setdefault(clave, []).append(ahora)

    def registrar_exito(self, clave):
        with self._lock:
            self._fallos.pop(clave, None)
