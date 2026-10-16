"""Pruebas de E10.1: lectura del campo ``prueba`` del escenario y resolucion del modo a ejecutar."""

import json
from pathlib import Path

import pytest

from tacticalgrid.escenario.cargador import cargar_escenario
from tacticalgrid.escenario.escenario import Posicion
from tacticalgrid.modos.prueba import (
    ALGORITMOS_ADVERSARIALES,
    ALGORITMOS_BUSQUEDA,
    MAX_TURNOS_POR_DEFECTO,
    MODOS,
    ConfiguracionPrueba,
    leer_configuracion_prueba,
    resolver_modo,
)

CARPETA_ESCENARIOS = Path(__file__).resolve().parents[2] / "escenarios"


def _con_prueba(tmp_path, prueba, base: str = "ejemplo_enunciado.json"):
    contenido = json.loads((CARPETA_ESCENARIOS / base).read_text(encoding="utf-8"))
    if prueba is None:
        contenido.pop("prueba", None)
    else:
        contenido["prueba"] = prueba
    ruta = tmp_path / "escenario.json"
    ruta.write_text(json.dumps(contenido), encoding="utf-8")
    return cargar_escenario(ruta)


def test_modos_y_familias_de_algoritmos() -> None:
    assert MODOS == ("busqueda", "partida", "adversarial")
    assert ALGORITMOS_BUSQUEDA == ("bfs", "dfs", "ucs", "a_estrella", "beam")
    assert ALGORITMOS_ADVERSARIALES == ("minimax", "alfa_beta")
    assert MAX_TURNOS_POR_DEFECTO == 50


# --- Lectura de prueba ---------------------------------------------------------------------------------------------

def test_sin_prueba_no_hay_configuracion(tmp_path) -> None:
    assert leer_configuracion_prueba(_con_prueba(tmp_path, None)) is None


def test_lee_la_navegacion_del_ejemplo_del_enunciado() -> None:
    configuracion = leer_configuracion_prueba(cargar_escenario(CARPETA_ESCENARIOS / "ejemplo_enunciado.json"))

    assert configuracion == ConfiguracionPrueba(
        modo="busqueda", unidad="A1", objetivo=Posicion(3, 2), algoritmo=None, max_turnos=None
    )


@pytest.mark.parametrize(
    ("archivo", "modo"),
    [
        ("campo_20x20.json", "busqueda"),
        ("recurso_en_transporte.json", "partida"),
        ("decision_adversarial.json", "adversarial"),
        ("estado_compuesto_libre.json", "adversarial"),
    ],
)
def test_lee_el_modo_de_los_escenarios_del_repositorio(archivo, modo) -> None:
    assert leer_configuracion_prueba(cargar_escenario(CARPETA_ESCENARIOS / archivo)).modo == modo


def test_lee_los_campos_propios_algoritmo_y_max_turnos(tmp_path) -> None:
    busqueda = leer_configuracion_prueba(
        _con_prueba(tmp_path, {"modo": "busqueda", "unidad_inicio": "A1", "objetivo": {"fila": 0, "columna": 0}, "algoritmo": "dfs"})
    )
    partida = leer_configuracion_prueba(_con_prueba(tmp_path, {"modo": "partida", "algoritmo": "minimax", "max_turnos": 7}))

    assert busqueda.algoritmo == "dfs"
    assert (partida.algoritmo, partida.max_turnos) == ("minimax", 7)


@pytest.mark.parametrize(
    ("prueba", "mensaje"),
    [
        ({"modo": "torneo"}, "modo"),
        ({}, "modo"),
        ({"modo": "busqueda", "unidad_inicio": 3}, "unidad_inicio"),
        ({"modo": "busqueda", "objetivo": {"fila": 1}}, "objetivo"),
        ({"modo": "busqueda", "objetivo": [1, 2]}, "objetivo"),
        ({"modo": "busqueda", "algoritmo": "minimax"}, "algoritmo"),
        ({"modo": "adversarial", "algoritmo": "bfs"}, "algoritmo"),
        ({"modo": "partida", "algoritmo": "dfs"}, "algoritmo"),
        ({"modo": "partida", "max_turnos": 0}, "max_turnos"),
        ({"modo": "partida", "max_turnos": True}, "max_turnos"),
    ],
)
def test_prueba_invalida_se_rechaza_con_un_mensaje_claro(tmp_path, prueba, mensaje) -> None:
    with pytest.raises(ValueError, match=mensaje):
        leer_configuracion_prueba(_con_prueba(tmp_path, prueba))


# --- Resolucion del modo -------------------------------------------------------------------------------------------

BUSQUEDA = ConfiguracionPrueba(modo="busqueda")
PARTIDA = ConfiguracionPrueba(modo="partida")
ADVERSARIAL = ConfiguracionPrueba(modo="adversarial")


@pytest.mark.parametrize(
    ("modo_consola", "algoritmo_consola", "configuracion", "esperado"),
    [
        # Sin consola, manda prueba.modo; sin prueba, se busca (comportamiento anterior de la consola).
        (None, None, PARTIDA, "partida"),
        (None, None, ADVERSARIAL, "adversarial"),
        (None, None, None, "busqueda"),
        # Un --algoritmo explicito conserva su comportamiento anterior, aunque el JSON declare otro modo.
        (None, "minimax", PARTIDA, "adversarial"),
        (None, "ucs", ADVERSARIAL, "busqueda"),
        (None, "minimax_alfa_beta", BUSQUEDA, "adversarial"),
        (None, "bfs_dfs", PARTIDA, "busqueda"),
        # --modo tiene prioridad sobre todo.
        ("adversarial", None, BUSQUEDA, "adversarial"),
        ("partida", "alfa_beta", BUSQUEDA, "partida"),
        ("busqueda", "beam", ADVERSARIAL, "busqueda"),
    ],
)
def test_resolver_modo_respeta_la_precedencia(modo_consola, algoritmo_consola, configuracion, esperado) -> None:
    assert resolver_modo(modo_consola, algoritmo_consola, configuracion) == esperado


@pytest.mark.parametrize(
    ("modo_consola", "algoritmo_consola"),
    [("partida", "bfs"), ("partida", "minimax_alfa_beta"), ("busqueda", "minimax"), ("adversarial", "ucs")],
)
def test_combinacion_incompatible_de_modo_y_algoritmo(modo_consola, algoritmo_consola) -> None:
    with pytest.raises(ValueError, match="no se puede usar"):
        resolver_modo(modo_consola, algoritmo_consola, None)
