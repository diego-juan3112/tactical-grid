"""Pruebas de construccion e identidad del estado sin JSON ni Pygame."""

from tacticalgrid.escenario.cargador import cargar_escenario
from tacticalgrid.escenario.escenario import Posicion
from tacticalgrid.juego.estado import EstadoJuego, crear_estado_inicial
from tacticalgrid.juego.unidad import Unidad


def _crear_unidades() -> tuple[Unidad, Unidad]:
    return (
        Unidad(identificador="A1", bando="A", tipo="estandar", posicion=Posicion(1, 1)),
        Unidad(identificador="B1", bando="B", tipo="estandar", posicion=Posicion(2, 2)),
    )


def _crear_estado(
    unidades: tuple[Unidad, ...] | None = None,
    turno_actual: str = "A",
    portador_recurso: str | None = None,
) -> EstadoJuego:
    return EstadoJuego(
        unidades=unidades or _crear_unidades(),
        turno_actual=turno_actual,
        posicion_recurso=Posicion(0, 1),
        portador_recurso=portador_recurso,
    )


def test_estado_inicial_separa_unidades_y_recurso_del_escenario(ruta_escenario_valido) -> None:
    escenario = cargar_escenario(ruta_escenario_valido)

    estado = crear_estado_inicial(escenario)

    assert estado.turno_actual == "A"
    assert estado.portador_recurso is None
    assert estado.posicion_recurso == escenario.recurso
    assert {unidad.identificador for unidad in estado.unidades} == {"A1", "B1"}


def test_estados_completamente_equivalentes_son_iguales() -> None:
    assert _crear_estado() == _crear_estado()


def test_estados_con_distinto_portador_son_diferentes() -> None:
    assert _crear_estado(portador_recurso="A1") != _crear_estado(portador_recurso=None)


def test_estados_con_distinto_turno_son_diferentes() -> None:
    assert _crear_estado(turno_actual="A") != _crear_estado(turno_actual="B")


def test_estados_con_una_unidad_en_otra_posicion_son_diferentes() -> None:
    unidades = _crear_unidades()
    unidades_movidas = (
        Unidad(identificador="A1", bando="A", tipo="estandar", posicion=Posicion(1, 2)),
        unidades[1],
    )

    assert _crear_estado(unidades=unidades) != _crear_estado(unidades=unidades_movidas)


def test_estados_con_unidades_en_distinto_orden_son_iguales() -> None:
    unidades = _crear_unidades()

    assert _crear_estado(unidades=unidades) == _crear_estado(unidades=(unidades[1], unidades[0]))


def test_estado_juego_es_utilizable_en_un_conjunto() -> None:
    unidades = _crear_unidades()

    assert {_crear_estado(unidades=unidades), _crear_estado(unidades=(unidades[1], unidades[0]))} == {
        _crear_estado(unidades=unidades)
    }
