"""Pruebas del contrato de resultados sin ejecutar algoritmos ni Pygame."""

import json

from tacticalgrid.algoritmos.resultado_busqueda import ResultadoBusqueda
from tacticalgrid.escenario.escenario import Posicion
from tacticalgrid.juego.accion import Accion

CLAVES_DEL_ENUNCIADO = {
    "algoritmo",
    "exito",
    "camino",
    "costo",
    "estados_generados",
    "estados_expandidos",
    "maximo_frontera",
}


def _resultado_exitoso() -> ResultadoBusqueda:
    return ResultadoBusqueda(
        algoritmo="A_ESTRELLA",
        exito=True,
        camino=(Posicion(3, 2), Posicion(3, 3), Posicion(4, 3)),
        costo=9,
        estados_generados=42,
        estados_expandidos=21,
        maximo_frontera=13,
        tiempo_segundos=0.25,
        acciones=(
            Accion("A1", Posicion(3, 2), Posicion(3, 3)),
            Accion("A1", Posicion(3, 3), Posicion(4, 3)),
        ),
    )


def test_resultado_busqueda_representa_metricas_sin_conocer_escenario() -> None:
    resultado = _resultado_exitoso()

    assert resultado.algoritmo == "A_ESTRELLA"
    assert resultado.camino[-1] == Posicion(4, 3)
    assert resultado.longitud == 2


def test_a_diccionario_tiene_la_estructura_del_enunciado() -> None:
    datos = _resultado_exitoso().a_diccionario()

    assert CLAVES_DEL_ENUNCIADO <= set(datos)
    assert datos["camino"] == [[3, 2], [3, 3], [4, 3]]
    assert (datos["costo"], datos["estados_generados"], datos["estados_expandidos"], datos["maximo_frontera"]) == (
        9,
        42,
        21,
        13,
    )
    assert datos["longitud"] == 2
    assert datos["tiempo_segundos"] == 0.25


def test_a_diccionario_es_serializable_a_json() -> None:
    texto = json.dumps(_resultado_exitoso().a_diccionario())

    assert json.loads(texto)["algoritmo"] == "A_ESTRELLA"


def test_resultado_sin_solucion_tiene_camino_vacio_y_costo_nulo() -> None:
    resultado = ResultadoBusqueda(
        algoritmo="BFS",
        exito=False,
        camino=(),
        costo=None,
        estados_generados=5,
        estados_expandidos=5,
        maximo_frontera=2,
    )

    assert resultado.longitud == 0
    assert resultado.a_diccionario()["camino"] == []
    assert resultado.a_diccionario()["costo"] is None
