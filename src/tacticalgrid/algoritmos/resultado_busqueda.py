"""Contrato común de resultados que reportan todos los algoritmos de búsqueda."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from tacticalgrid.escenario.escenario import Posicion
from tacticalgrid.juego.accion import Accion

if TYPE_CHECKING:
    from .instrumentacion import TrazaExpansiones


@dataclass(frozen=True)
class ResultadoBusqueda:
    """Métricas y camino de una búsqueda, equivalentes a la estructura de resultados del enunciado.

    ``camino`` incluye las posiciones inicial y final; ``acciones`` conserva las transiciones aplicadas, para que la
    verificación de soluciones compruebe cada movimiento y recalcule el costo. Sin solución, ``camino`` y ``acciones``
    quedan vacíos y ``costo`` es ``None``. ``traza_expansiones`` es opcional y solo contiene eventos reales cuando el
    llamador activa su observador.
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
    traza_expansiones: "TrazaExpansiones | None" = None

    @property
    def longitud(self) -> int:
        """Número de movimientos del camino: 0 si no hay solución o si el inicio ya era el objetivo."""
        return len(self.acciones)

    def a_diccionario(self) -> dict[str, object]:
        """Exportar el resultado con las claves del ejemplo del enunciado, más ``longitud`` y ``tiempo_segundos``.

        Proposito: ofrecer a la interfaz, a los registros y a los experimentos (E10.3) una estructura idéntica para
        todos los algoritmos, serializable directamente con ``json.dumps``.
        Precondiciones: ninguna.
        Postcondiciones: se devuelve un diccionario nuevo, con ``camino`` como lista de pares ``[fila, columna]`` igual
        que en el enunciado. El resultado no cambia.
        Complejidad: O(L) temporal y espacial, con L la longitud del camino.
        Uso de IA: Si.
        Intervencion de IA: Claude (Opus 5.5): implementación y documentación (E4.1).
        Validacion del estudiante: pruebas de tests/algoritmos/test_resultado_busqueda.py: claves del enunciado,
        serialización a JSON y resultado sin solución.
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
