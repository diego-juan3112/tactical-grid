"""Contrato comun de resultados de busqueda, sin implementar algoritmos aun."""

from dataclasses import dataclass

from tacticalgrid.escenario.escenario import Posicion


@dataclass(frozen=True)
class ResultadoBusqueda:
    """Metricas y camino que los algoritmos de busqueda deberan informar."""

    algoritmo: str
    exito: bool
    camino: tuple[Posicion, ...]
    costo: int | float | None
    estados_generados: int
    estados_expandidos: int
    maximo_frontera: int
