"""Pruebas de E3.2: recoger y transportar el recurso, y victoria al entregarlo en la base propia."""

from dataclasses import replace
from pathlib import Path

import pytest

from tacticalgrid.escenario.cargador import cargar_escenario
from tacticalgrid.escenario.escenario import Posicion
from tacticalgrid.juego.accion import Accion
from tacticalgrid.juego.estado import EstadoJuego, crear_estado_inicial
from tacticalgrid.juego.recurso import (
    bando_que_entrego_recurso,
    obtener_portador,
    posicion_del_recurso,
    recoger_recurso,
)
from tacticalgrid.juego.reglas import aplicar_accion, es_terminal
from tacticalgrid.juego.unidad import Unidad

ESCENARIO_ENUNCIADO = Path(__file__).resolve().parents[2] / "escenarios" / "ejemplo_enunciado.json"


def _estado(
    unidades: tuple[Unidad, ...],
    recurso: Posicion | None = Posicion(1, 1),
    portador: str | None = None,
    turno: str = "A",
) -> EstadoJuego:
    return EstadoJuego(unidades=unidades, turno_actual=turno, posicion_recurso=recurso, portador_recurso=portador)


def _mover(escenario, estado: EstadoJuego, identificador: str, destino: Posicion) -> EstadoJuego:
    origen = next(unidad.posicion for unidad in estado.unidades if unidad.identificador == identificador)
    return aplicar_accion(escenario, estado, Accion(identificador, origen, destino))


@pytest.fixture
def escenario(ruta_escenario_valido):
    # Mapa 2x3: fila 0 = camino, muro, camino; fila 1 = camino x3. Base A (0,0), base B (1,2).
    return cargar_escenario(ruta_escenario_valido)


def test_unidad_recoge_el_recurso_al_llegar_a_su_celda(escenario) -> None:
    estado = _estado((Unidad("A1", "A", "estandar", Posicion(1, 0)), Unidad("B1", "B", "estandar", Posicion(1, 2))))

    sucesor = _mover(escenario, estado, "A1", Posicion(1, 1))

    assert sucesor.portador_recurso == "A1"
    assert sucesor.posicion_recurso is None
    assert obtener_portador(sucesor).identificador == "A1"


def test_pasar_cerca_del_recurso_no_lo_recoge(escenario) -> None:
    estado = _estado((Unidad("A1", "A", "estandar", Posicion(0, 0)), Unidad("B1", "B", "estandar", Posicion(1, 2))))

    sucesor = _mover(escenario, estado, "A1", Posicion(1, 0))

    assert sucesor.portador_recurso is None
    assert sucesor.posicion_recurso == Posicion(1, 1)
    assert obtener_portador(sucesor) is None


def test_el_recurso_viaja_con_su_portador(escenario) -> None:
    estado = _estado(
        (Unidad("A1", "A", "estandar", Posicion(1, 1)), Unidad("B1", "B", "estandar", Posicion(1, 2))),
        recurso=None,
        portador="A1",
    )

    assert posicion_del_recurso(estado) == Posicion(1, 1)
    sucesor = _mover(escenario, estado, "A1", Posicion(1, 0))

    assert sucesor.portador_recurso == "A1"
    assert sucesor.posicion_recurso is None
    assert posicion_del_recurso(sucesor) == Posicion(1, 0)


def test_posicion_del_recurso_libre_es_la_declarada_en_el_estado() -> None:
    estado = _estado((Unidad("A1", "A", "estandar", Posicion(0, 0)),), recurso=Posicion(1, 1))

    assert posicion_del_recurso(estado) == Posicion(1, 1)


def test_un_bando_gana_al_llevar_el_recurso_a_su_propia_base(escenario) -> None:
    estado = _estado(
        (Unidad("A1", "A", "estandar", Posicion(1, 0)), Unidad("B1", "B", "estandar", Posicion(1, 2))),
        recurso=None,
        portador="A1",
    )

    sucesor = _mover(escenario, estado, "A1", Posicion(0, 0))

    assert bando_que_entrego_recurso(escenario, sucesor) == "A"
    assert sucesor.estado_partida == "victoria_A"
    assert es_terminal(escenario, sucesor)


def test_llevar_el_recurso_a_la_base_adversaria_no_da_la_victoria(escenario) -> None:
    estado = _estado(
        (Unidad("A1", "A", "estandar", Posicion(1, 1)), Unidad("B1", "B", "estandar", Posicion(0, 0))),
        recurso=None,
        portador="A1",
    )

    sucesor = _mover(escenario, estado, "A1", Posicion(1, 2))

    assert bando_que_entrego_recurso(escenario, sucesor) is None
    assert sucesor.estado_partida == "en_curso"


def test_el_bando_b_recoge_y_gana_con_las_mismas_reglas(escenario) -> None:
    estado = _estado(
        (Unidad("A1", "A", "estandar", Posicion(0, 0)), Unidad("B1", "B", "estandar", Posicion(1, 2))),
        turno="B",
    )

    recogido = _mover(escenario, estado, "B1", Posicion(1, 1))
    assert recogido.portador_recurso == "B1"

    # Se devuelve el turno a B para probar la entrega: el recurso ya va con B1 y la base B esta en (1, 2).
    entregado = _mover(escenario, replace(recogido, turno_actual="B"), "B1", Posicion(1, 2))

    assert bando_que_entrego_recurso(escenario, entregado) == "B"
    assert entregado.estado_partida == "victoria_B"


def test_recoger_recurso_en_la_propia_base_gana_de_inmediato(escenario) -> None:
    estado = _estado(
        (Unidad("A1", "A", "estandar", Posicion(1, 0)), Unidad("B1", "B", "estandar", Posicion(1, 2))),
        recurso=Posicion(0, 0),
    )

    sucesor = _mover(escenario, estado, "A1", Posicion(0, 0))

    assert sucesor.portador_recurso == "A1"
    assert sucesor.estado_partida == "victoria_A"


def test_recoger_recurso_no_cambia_nada_si_ya_tiene_portador() -> None:
    estado = _estado(
        (Unidad("A1", "A", "estandar", Posicion(1, 1)), Unidad("B1", "B", "estandar", Posicion(1, 2))),
        recurso=None,
        portador="A1",
    )

    assert recoger_recurso(estado, "B1", Posicion(1, 1)) is estado


def test_recoger_recurso_no_cambia_nada_si_el_destino_no_es_la_celda_del_recurso() -> None:
    estado = _estado((Unidad("A1", "A", "estandar", Posicion(0, 0)),), recurso=Posicion(1, 1))

    assert recoger_recurso(estado, "A1", Posicion(1, 0)) is estado


def test_recoger_recurso_no_modifica_el_estado_original() -> None:
    estado = _estado((Unidad("A1", "A", "estandar", Posicion(1, 0)),), recurso=Posicion(1, 1))

    recogido = recoger_recurso(estado, "A1", Posicion(1, 1))

    assert recogido is not estado
    assert estado.portador_recurso is None and estado.posicion_recurso == Posicion(1, 1)


def test_partida_completa_del_enunciado_recoger_transportar_y_ganar() -> None:
    escenario = cargar_escenario(ESCENARIO_ENUNCIADO)
    estado = crear_estado_inicial(escenario)
    ruta_a = [Posicion(0, 2), Posicion(1, 2), Posicion(2, 2), Posicion(1, 2), Posicion(0, 2), Posicion(0, 1), Posicion(0, 0)]
    vaiven_b = [Posicion(3, 1), Posicion(3, 2)]

    for paso, destino in enumerate(ruta_a):
        estado = _mover(escenario, estado, "A1", destino)
        if paso == 2:
            assert estado.portador_recurso == "A1"
            assert posicion_del_recurso(estado) == Posicion(2, 2)
        if not es_terminal(escenario, estado):
            estado = _mover(escenario, estado, "B1", vaiven_b[paso % 2])

    assert estado.estado_partida == "victoria_A"
    assert bando_que_entrego_recurso(escenario, estado) == "A"
    assert posicion_del_recurso(estado) == escenario.bases["A"]
