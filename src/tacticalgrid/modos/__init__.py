"""Modos de prueba del enunciado (E10.1): busqueda, partida y adversarial.

Capa de orquestacion: interpreta el campo ``prueba`` del escenario y ejecuta el modo pedido usando las capas de
escenario, juego y algoritmos. No abre archivos ni conoce Pygame; la consola y la interfaz la consumen.
"""

from .partida_automatica import ResultadoPartida, TurnoPartida, jugar_partida
from .prueba import (
    ALGORITMOS_ADVERSARIALES,
    ALGORITMOS_BUSQUEDA,
    MAX_TURNOS_POR_DEFECTO,
    MODOS,
    ConfiguracionPrueba,
    leer_configuracion_prueba,
    resolver_modo,
    validar_max_turnos,
)

__all__ = [
    "ALGORITMOS_ADVERSARIALES",
    "ALGORITMOS_BUSQUEDA",
    "MAX_TURNOS_POR_DEFECTO",
    "MODOS",
    "ConfiguracionPrueba",
    "ResultadoPartida",
    "TurnoPartida",
    "jugar_partida",
    "leer_configuracion_prueba",
    "resolver_modo",
    "validar_max_turnos",
]
