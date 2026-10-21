"""Tipos de terreno definidos por un escenario JSON."""

from dataclasses import dataclass


@dataclass(frozen=True)
class TipoTerreno:
    """Propiedades estáticas de un tipo de terreno: costo y transitabilidad."""

    costo: int | float | None
    transitable: bool
