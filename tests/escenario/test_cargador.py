"""Pruebas de carga y consultas de la capa de escenario."""

from tacticalgrid.escenario.cargador import cargar_escenario
from tacticalgrid.escenario.escenario import Posicion


def test_carga_escenario_valido_y_consulta_propiedades(ruta_escenario_valido) -> None:
    escenario = cargar_escenario(ruta_escenario_valido)

    assert escenario.filas == 2
    assert escenario.contiene_posicion(Posicion(1, 2))
    assert not escenario.contiene_posicion(Posicion(2, 0))
    assert not escenario.es_transitable(Posicion(0, 1))
    assert escenario.obtener_costo(Posicion(1, 0)) == 2
