"""Contrato comun de resultados que reportan todos los algoritmos de busqueda."""

from dataclasses import dataclass

from tacticalgrid.escenario.escenario import Posicion
from tacticalgrid.juego.accion import Accion


@dataclass(frozen=True)
class ResultadoBusqueda:
    """Metricas y camino de una busqueda, equivalentes a la estructura de resultados del enunciado.

    ``camino`` incluye la posicion inicial y la final; ``acciones`` conserva las transiciones aplicadas para
    que la verificacion de soluciones pueda comprobar cada movimiento y recalcular el costo. Si no hay
    solucion, ``camino`` y ``acciones`` quedan vacios y ``costo`` es ``None``.
    """

    algoritmo: str
    exito: bool
    camino: tuple[Posicion, ...]
    costo: int | float | None
    estados_generados: int
    estados_expandidos: int
    maximo_frontera: int
    tiempo_segundos: float = 0.0
    acciones: tuple[Accion, ...] = ()

    @property
    def longitud(self) -> int:
        """Numero de movimientos del camino (0 si no hay solucion o si el inicio ya era objetivo)."""
        return len(self.acciones)

    def a_diccionario(self) -> dict[str, object]:
        """Exporta el resultado con las claves del ejemplo del enunciado, mas ``longitud`` y ``tiempo_segundos``.

        Proposito: ofrecer a la interfaz, a los logs y a los experimentos (E10.3) una estructura identica para
        todos los algoritmos, serializable directamente con ``json.dumps``.
        Precondiciones: ninguna.
        Postcondiciones: devuelve un diccionario nuevo; ``camino`` se expresa como lista de pares
        ``[fila, columna]`` como en el enunciado. No modifica el resultado.
        Complejidad: O(L) temporal y espacial, donde L es la longitud del camino.
        Uso de IA: Si.
        Intervencion de IA: Claude (Opus 5.5) propuso la implementacion y su documentacion en E4.1.
        Validacion del estudiante: cubierto por las pruebas de tests/algoritmos/test_resultado_busqueda.py, que
        comparan la salida con las claves del enunciado y la serializan a JSON.
        """
        return {
            "algoritmo": self.algoritmo,
            "exito": self.exito,
            "camino": [[posicion.fila, posicion.columna] for posicion in self.camino],
            "costo": self.costo,
            "estados_generados": self.estados_generados,
            "estados_expandidos": self.estados_expandidos,
            "maximo_frontera": self.maximo_frontera,
            "longitud": self.longitud,
            "tiempo_segundos": self.tiempo_segundos,
        }
