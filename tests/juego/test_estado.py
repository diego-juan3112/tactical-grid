"""Pruebas de construccion del estado sin JSON ni Pygame."""

from tacticalgrid.escenario.cargador import cargar_escenario
from tacticalgrid.juego.estado import crear_estado_inicial


def test_estado_inicial_separa_unidades_y_recurso_del_escenario(ruta_escenario_valido) -> None:
    escenario = cargar_escenario(ruta_escenario_valido)

    estado = crear_estado_inicial(escenario)

    assert estado.turno_actual == "A"
    assert estado.portador_recurso is None
    assert estado.posicion_recurso == escenario.recurso
    assert {unidad.identificador for unidad in estado.unidades} == {"A1", "B1"}
