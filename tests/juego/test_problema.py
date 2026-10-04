"""Pruebas del problema de navegacion compartido por los algoritmos de busqueda."""

from pathlib import Path

import pytest

from tacticalgrid.escenario.cargador import cargar_escenario
from tacticalgrid.escenario.escenario import Posicion
from tacticalgrid.juego.accion import Accion
from tacticalgrid.juego.problema import ProblemaNavegacion

EJEMPLO_ENUNCIADO = Path(__file__).resolve().parents[2] / "escenarios" / "ejemplo_enunciado.json"


@pytest.fixture
def problema() -> ProblemaNavegacion:
    return ProblemaNavegacion(cargar_escenario(EJEMPLO_ENUNCIADO), "A1", Posicion(3, 2))


def test_acciones_de_navegacion_solo_mueven_la_unidad_indicada(problema) -> None:
    # A1 en (0, 1): arriba fuera del mapa, abajo muro; izquierda camino y derecha pasto.
    assert problema.acciones(problema.estado_inicial) == (
        Accion("A1", Posicion(0, 1), Posicion(0, 0)),
        Accion("A1", Posicion(0, 1), Posicion(0, 2)),
    )


def test_resultado_conserva_el_turno_y_mueve_solo_la_unidad(problema) -> None:
    inicial = problema.estado_inicial
    sucesor = problema.resultado(inicial, Accion("A1", Posicion(0, 1), Posicion(0, 2)))

    assert sucesor.turno_actual == inicial.turno_actual
    movidas = set(sucesor.unidades) - set(inicial.unidades)
    assert {unidad.identificador for unidad in movidas} == {"A1"}


def test_navegacion_ignora_unidades_que_ocupan_el_objetivo(problema) -> None:
    # B1 ocupa (3, 2); en modo busqueda el resto de unidades no bloquea el paso.
    estado = problema.estado_inicial
    for destino in (Posicion(0, 0), Posicion(1, 0), Posicion(2, 0), Posicion(2, 1), Posicion(3, 1), Posicion(3, 2)):
        origen = next(unidad.posicion for unidad in estado.unidades if unidad.identificador == "A1")
        estado = problema.resultado(estado, Accion("A1", origen, destino))

    assert problema.es_objetivo(estado)
    assert not problema.es_objetivo(problema.estado_inicial)


def test_costo_de_navegacion_proviene_del_terreno(problema) -> None:
    # (0, 2) es pasto, cuyo costo en el JSON del enunciado es 2.
    assert problema.costo(problema.estado_inicial, Accion("A1", Posicion(0, 1), Posicion(0, 2))) == 2


def test_resultado_rechaza_acciones_invalidas(problema) -> None:
    with pytest.raises(ValueError):
        problema.resultado(problema.estado_inicial, Accion("A1", Posicion(0, 1), Posicion(1, 1)))


def test_problema_rechaza_unidad_inexistente_u_objetivo_fuera_del_mapa() -> None:
    escenario = cargar_escenario(EJEMPLO_ENUNCIADO)

    with pytest.raises(ValueError):
        ProblemaNavegacion(escenario, "Z9", Posicion(0, 0))
    with pytest.raises(ValueError):
        ProblemaNavegacion(escenario, "A1", Posicion(4, 0))
