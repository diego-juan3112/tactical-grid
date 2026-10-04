"""Representacion de las acciones que transforman un estado del juego."""

from dataclasses import dataclass

from tacticalgrid.escenario.escenario import Posicion

# Orden fijo (arriba, abajo, izquierda, derecha) en que se generan los movimientos de cada unidad. Fija el orden
# de los sucesores, que afecta a DFS y a la poda alfa-beta; no contiene posiciones ni costos de ningun mapa.
DESPLAZAMIENTOS: tuple[tuple[int, int], ...] = ((-1, 0), (1, 0), (0, -1), (0, 1))


@dataclass(frozen=True)
class Accion:
    """Movimiento de una unidad hacia una celda ortogonalmente adyacente."""

    identificador_unidad: str
    origen: Posicion
    destino: Posicion
