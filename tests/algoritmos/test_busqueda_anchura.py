"""Pruebas de E4.2 sobre escenarios reales de navegacion."""

import json
from pathlib import Path

from tacticalgrid.algoritmos import busqueda_anchura
from tacticalgrid.escenario.cargador import cargar_escenario
from tacticalgrid.escenario.escenario import Posicion
from tacticalgrid.juego.problema import ProblemaNavegacion

CARPETA_ESCENARIOS = Path(__file__).resolve().parents[2] / "escenarios"


def _problema(archivo: str, objetivo: Posicion) -> ProblemaNavegacion:
    escenario = cargar_escenario(CARPETA_ESCENARIOS / archivo)
    return ProblemaNavegacion(escenario, "A1", objetivo)


def test_objetivo_inicial_reporta_raiz_sin_expandir() -> None:
    problema = _problema("ruta_corta_vs_economica.json", Posicion(2, 0))

    resultado = busqueda_anchura(problema)

    assert resultado.exito
    assert resultado.camino == (Posicion(2, 0),)
    assert resultado.acciones == ()
    assert resultado.longitud == 0
    assert resultado.costo == 0
    assert (resultado.estados_generados, resultado.estados_expandidos, resultado.maximo_frontera) == (1, 0, 1)


def test_ruta_directa_reconstruye_accion_y_costo() -> None:
    problema = _problema("ruta_corta_vs_economica.json", Posicion(2, 1))

    resultado = busqueda_anchura(problema)

    assert resultado.exito
    assert resultado.camino == (Posicion(2, 0), Posicion(2, 1))
    assert len(resultado.acciones) == resultado.longitud == 1
    assert resultado.acciones[0].origen == resultado.camino[0]
    assert resultado.acciones[0].destino == resultado.camino[-1]
    assert resultado.costo == 7
    assert (resultado.estados_generados, resultado.estados_expandidos, resultado.maximo_frontera) == (6, 3, 3)


def test_bfs_elige_dos_movimientos_costosos_sobre_ruta_larga_barata(tmp_path) -> None:
    contenido = {
        "version": "1.0",
        "mapa": {"filas": 3, "columnas": 3},
        "tipos_terreno": {
            "camino": {"costo": 1, "transitable": True},
            "pantano": {"costo": 7, "transitable": True},
        },
        "terreno": [
            ["camino", "camino", "camino"],
            ["camino", "pantano", "camino"],
            ["camino", "camino", "camino"],
        ],
        "bases": {"A": {"fila": 0, "columna": 0}, "B": {"fila": 2, "columna": 2}},
        "recurso": {"fila": 0, "columna": 2},
        "unidades": [{"id": "A1", "bando": "A", "tipo": "estandar", "fila": 1, "columna": 0}],
        "turno": "A",
        "juego": {"portador_recurso": None},
        "prueba": {"modo": "busqueda", "unidad_inicio": "A1", "objetivo": {"fila": 1, "columna": 2}},
    }
    ruta_escenario = tmp_path / "costo_vs_movimientos.json"
    ruta_escenario.write_text(json.dumps(contenido), encoding="utf-8")
    problema = ProblemaNavegacion(cargar_escenario(ruta_escenario), "A1", Posicion(1, 2))

    resultado = busqueda_anchura(problema)

    assert resultado.exito
    assert resultado.longitud == 2
    assert resultado.costo == 8
    assert len(resultado.camino) == len(resultado.acciones) + 1
    assert resultado.camino[0] == Posicion(1, 0)
    assert resultado.camino[-1] == Posicion(1, 2)
    assert problema.escenario.obtener_costo(Posicion(1, 1)) + problema.escenario.obtener_costo(Posicion(1, 2)) == 8
    ruta_alternativa = (Posicion(0, 0), Posicion(0, 1), Posicion(0, 2), Posicion(1, 2))
    costo_alternativo = sum(problema.escenario.obtener_costo(posicion) for posicion in ruta_alternativa)
    assert len(ruta_alternativa) == 4 > resultado.longitud
    assert costo_alternativo == 4 < resultado.costo
    assert (resultado.estados_generados, resultado.estados_expandidos, resultado.maximo_frontera) == (9, 6, 3)


def test_obstaculo_obliga_a_rodear_y_bfs_reconstruye_todo_el_camino() -> None:
    problema = _problema("obstaculo_rodeo.json", Posicion(1, 3))

    resultado = busqueda_anchura(problema)

    assert resultado.exito
    assert resultado.longitud == 15
    assert len(resultado.camino) == len(resultado.acciones) + 1
    assert resultado.camino[0] == Posicion(4, 3)
    assert resultado.camino[-1] == Posicion(1, 3)
    assert resultado.costo == sum(problema.costo(problema.estado_inicial, accion) for accion in resultado.acciones)
    assert (resultado.estados_generados, resultado.estados_expandidos, resultado.maximo_frontera) == (41, 38, 7)


def test_ciclos_y_ramas_convergentes_se_descartan_y_la_frontera_se_agota() -> None:
    problema = _problema("ejemplo_enunciado.json", Posicion(1, 1))
    estado_inicial = problema.estado_inicial
    escenario = problema.escenario

    resultado = busqueda_anchura(problema)

    assert not resultado.exito
    assert resultado.camino == resultado.acciones == ()
    assert resultado.costo is None
    assert (resultado.estados_generados, resultado.estados_expandidos, resultado.maximo_frontera) == (29, 29, 8)
    assert problema.estado_inicial is estado_inicial
    assert problema.escenario is escenario


def test_misma_busqueda_es_determinista_y_funciona_en_dimensiones_distintas() -> None:
    for archivo, objetivo in (
        ("ruta_corta_vs_economica.json", Posicion(2, 8)),
        ("campo_20x20.json", Posicion(9, 10)),
    ):
        problema = _problema(archivo, objetivo)
        primero = busqueda_anchura(problema)
        segundo = busqueda_anchura(problema)

        assert (primero.exito, primero.camino, primero.acciones, primero.costo, primero.longitud,
                primero.estados_generados, primero.estados_expandidos, primero.maximo_frontera) == (
            segundo.exito, segundo.camino, segundo.acciones, segundo.costo, segundo.longitud,
            segundo.estados_generados, segundo.estados_expandidos, segundo.maximo_frontera,
        )
        assert primero.camino[0] == problema.posicion(problema.estado_inicial)
        assert primero.camino[-1] == objetivo
