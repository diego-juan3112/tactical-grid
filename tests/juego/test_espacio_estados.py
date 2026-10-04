"""Pruebas de integracion: la funcion sucesor nunca genera estados invalidos sobre escenarios reales."""

from collections import deque
from pathlib import Path

import pytest

from tacticalgrid.escenario.cargador import cargar_escenario
from tacticalgrid.escenario.escenario import Escenario, Posicion
from tacticalgrid.juego.estado import EstadoJuego, crear_estado_inicial
from tacticalgrid.juego.problema import ProblemaNavegacion
from tacticalgrid.juego.reglas import costo_accion, generar_sucesores

CARPETA_ESCENARIOS = Path(__file__).resolve().parents[2] / "escenarios"


def _verificar_estado(escenario: Escenario, estado: EstadoJuego) -> None:
    for unidad in estado.unidades:
        assert escenario.contiene_posicion(unidad.posicion)
        assert escenario.es_transitable(unidad.posicion)
    identificadores = {unidad.identificador for unidad in estado.unidades}
    # El recurso esta en el mapa o tiene un portador existente, nunca ambas cosas ni ninguna.
    assert (estado.posicion_recurso is None) == (estado.portador_recurso is not None)
    assert estado.portador_recurso is None or estado.portador_recurso in identificadores


@pytest.mark.parametrize(
    ("archivo", "unidad", "objetivo"),
    [("ejemplo_enunciado.json", "A1", Posicion(3, 2)), ("arquitectura_basica.json", "A1", Posicion(19, 19))],
)
def test_exploracion_completa_de_navegacion_solo_genera_estados_validos(archivo, unidad, objetivo) -> None:
    escenario = cargar_escenario(CARPETA_ESCENARIOS / archivo)
    problema = ProblemaNavegacion(escenario, unidad, objetivo)
    visitados = {problema.estado_inicial}
    frontera = deque([problema.estado_inicial])
    objetivo_alcanzado = False

    while frontera:
        estado = frontera.popleft()
        _verificar_estado(escenario, estado)
        objetivo_alcanzado |= problema.es_objetivo(estado)
        for accion in problema.acciones(estado):
            assert abs(accion.origen.fila - accion.destino.fila) + abs(accion.origen.columna - accion.destino.columna) == 1
            assert problema.costo(estado, accion) == escenario.obtener_costo(accion.destino) > 0
            sucesor = problema.resultado(estado, accion)
            assert sucesor.turno_actual == estado.turno_actual
            if sucesor not in visitados:
                visitados.add(sucesor)
                frontera.append(sucesor)

    assert objetivo_alcanzado


def test_partida_por_turnos_genera_sucesores_validos_y_alterna_turno() -> None:
    escenario = cargar_escenario(CARPETA_ESCENARIOS / "ejemplo_enunciado.json")
    nivel = {crear_estado_inicial(escenario)}

    for _ in range(4):
        siguiente = set()
        for estado in nivel:
            for accion, sucesor in generar_sucesores(escenario, estado):
                _verificar_estado(escenario, sucesor)
                assert len({unidad.posicion for unidad in sucesor.unidades}) == len(sucesor.unidades)
                assert sucesor.turno_actual != estado.turno_actual
                assert costo_accion(escenario, accion) > 0
                siguiente.add(sucesor)
        assert siguiente
        nivel = siguiente
