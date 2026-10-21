"""Modos de prueba del enunciado (E10.1): búsqueda, partida y adversarial.

Capa de orquestación: interpretar el campo ``prueba`` del escenario y ejecutar el modo pedido con las capas de
escenario, juego y algoritmos. No abre archivos ni depende de Pygame; la consumen la consola y la interfaz.
"""

from .agentes import ALGORITMOS_AGENTE, ConfiguracionAgente, DecisionAgente, decidir_jugada
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
    "ALGORITMOS_AGENTE",
    "ALGORITMOS_BUSQUEDA",
    "MAX_TURNOS_POR_DEFECTO",
    "MODOS",
    "ConfiguracionAgente",
    "ConfiguracionPrueba",
    "DecisionAgente",
    "ResultadoPartida",
    "TurnoPartida",
    "decidir_jugada",
    "jugar_partida",
    "leer_configuracion_prueba",
    "resolver_modo",
    "validar_max_turnos",
]
