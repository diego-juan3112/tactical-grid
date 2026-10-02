"""Tipos de terreno definidos por un escenario JSON."""

from dataclasses import dataclass


@dataclass(frozen=True)
class TipoTerreno:
    """Propiedades estaticas de un tipo de terreno."""

    costo: int | float | None
    transitable: bool
