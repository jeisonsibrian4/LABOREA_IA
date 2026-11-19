"""
LABOREA IA - Control de la cuota de Gemini (plan gratuito).

El límite del plan gratis es de PEDIDOS por minuto (y por día). Este módulo:
  - espera un rato (en vez de fallar) cuando se llenó el minuto;
  - bloquea los envíos cuando Google responde 429;
  - avisa con CuotaAgotada para que la app responda igual en "modo reglas" (sin IA).
Es código puro (sin Gemini ni FastAPI), así que se prueba solo.
"""

import threading
import time
from collections import deque
from typing import Callable


class CuotaAgotada(Exception):
    def __init__(self, segundos: float = 60.0):
        super().__init__("Cuota de Gemini agotada (reintentar en %.0f s)" % segundos)
        self.segundos = segundos


class ControlCuota:
    """Ventana deslizante de 60 s: nunca manda más de `rpm` pedidos por minuto."""

    def __init__(self, rpm: int = 4, max_espera: float = 6.0,
                 reloj: Callable[[], float] = time.monotonic,
                 dormir: Callable[[float], None] = time.sleep):
        self.rpm = max(1, int(rpm))
        self.max_espera = float(max_espera)
        self._reloj, self._dormir = reloj, dormir
        self._envios: deque = deque()
        self._bloqueado_hasta = 0.0
        self._lock = threading.Lock()

    def bloquear_por(self, segundos: float) -> None:
        """Después de un 429: no mandar nada durante `segundos`."""
        with self._lock:
            self._bloqueado_hasta = max(self._bloqueado_hasta, self._reloj() + max(0.0, segundos))

    def reservar(self) -> float:
        """Bloquea hasta que haya un lugar libre. Devuelve los segundos esperados.
        Si habría que esperar más de `max_espera`, lanza CuotaAgotada."""
        esperado = 0.0
        while True:
            with self._lock:
                ahora = self._reloj()
                while self._envios and ahora - self._envios[0] >= 60.0:
                    self._envios.popleft()
                espera = 0.0
                if self._bloqueado_hasta > ahora:
                    espera = self._bloqueado_hasta - ahora
                elif len(self._envios) >= self.rpm:
                    espera = 60.0 - (ahora - self._envios[0])
                if espera <= 0:
                    self._envios.append(ahora)
                    return esperado
                if esperado + espera > self.max_espera:
                    raise CuotaAgotada(espera)
            self._dormir(espera)
            esperado += espera
