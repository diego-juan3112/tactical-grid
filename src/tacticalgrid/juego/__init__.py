"""Estado dinamico y reglas del dominio de TacticalGrid."""

from .estado import EstadoJuego, crear_estado_inicial
from .unidad import Unidad

__all__ = ["EstadoJuego", "Unidad", "crear_estado_inicial"]
