"""Pruebas del contrato de resultados sin ejecutar algoritmos ni Pygame."""

from tacticalgrid.algoritmos.resultado_busqueda import ResultadoBusqueda
from tacticalgrid.escenario.escenario import Posicion


def test_resultado_busqueda_representa_metricas_sin_conocer_escenario() -> None:
    resultado = ResultadoBusqueda(
        algoritmo="BFS",
        exito=True,
        camino=(Posicion(0, 0), Posicion(0, 1)),
        costo=2,
        estados_generados=3,
        estados_expandidos=2,
        maximo_frontera=1,
    )

    assert resultado.algoritmo == "BFS"
    assert resultado.camino[-1] == Posicion(0, 1)
