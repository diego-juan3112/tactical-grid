"""Entidad dinámica de unidad dentro de una partida."""

from dataclasses import dataclass

from tacticalgrid.escenario.escenario import Posicion


@dataclass(frozen=True)
class Unidad:
    """Unidad del juego con identidad, bando, tipo y posición actual."""

    identificador: str
    bando: str
    tipo: str
    posicion: Posicion
