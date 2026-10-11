"""Representacion de las acciones que transforman un estado del juego."""

from dataclasses import dataclass

from tacticalgrid.escenario.escenario import Posicion

# Orden fijo (arriba, abajo, izquierda, derecha) en que se generan los movimientos de cada unidad. Fija el orden
# de los sucesores, que afecta a DFS y a la poda alfa-beta; no contiene posiciones ni costos de ningun mapa.
DESPLAZAMIENTOS: tuple[tuple[int, int], ...] = ((-1, 0), (1, 0), (0, -1), (0, 1))

# Tipos de accion del juego (E8.1). Mover desplaza la unidad a ``destino``. Interceptar no desplaza a nadie: la
# unidad en ``origen`` le quita el recurso al portador rival ubicado en ``destino``, que es una celda adyacente.
MOVER = "mover"
INTERCEPTAR = "interceptar"


@dataclass(frozen=True)
class Accion:
    """Accion de una unidad: moverse a una celda adyacente o interceptar al portador rival adyacente."""

    identificador_unidad: str
    origen: Posicion
    destino: Posicion
    tipo: str = MOVER
