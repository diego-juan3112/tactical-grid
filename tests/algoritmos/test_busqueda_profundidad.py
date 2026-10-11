"""Pruebas de E4.3: DFS sobre el contrato comun de problemas y las metricas de E4.1."""

import json
from pathlib import Path

from tacticalgrid.algoritmos import busqueda_anchura, busqueda_profundidad
from tacticalgrid.escenario.cargador import cargar_escenario
from tacticalgrid.escenario.escenario import Posicion
from tacticalgrid.juego.problema import ProblemaNavegacion

CARPETA_ESCENARIOS = Path(__file__).resolve().parents[2] / "escenarios"


def _problema(archivo: str, objetivo: Posicion) -> ProblemaNavegacion:
    escenario = cargar_escenario(CARPETA_ESCENARIOS / archivo)
    return ProblemaNavegacion(escenario, "A1", objetivo)


def _problema_abierto_3x3(tmp_path, objetivo: Posicion) -> ProblemaNavegacion:
    contenido = {
        "version": "1.0",
        "mapa": {"filas": 3, "columnas": 3},
        "tipos_terreno": {"camino": {"costo": 1, "transitable": True}},
        "terreno": [["camino"] * 3 for _ in range(3)],
        "bases": {"A": {"fila": 0, "columna": 0}, "B": {"fila": 2, "columna": 2}},
        "recurso": {"fila": 1, "columna": 1},
        "unidades": [{"id": "A1", "bando": "A", "tipo": "estandar", "fila": 0, "columna": 0}],
        "turno": "A",
        "juego": {"portador_recurso": None},
    }
    ruta = tmp_path / "abierto_3x3.json"
    ruta.write_text(json.dumps(contenido), encoding="utf-8")
    return ProblemaNavegacion(cargar_escenario(ruta), "A1", objetivo)


def _verificar_camino_valido(problema: ProblemaNavegacion, resultado) -> None:
    escenario = problema.escenario
    assert resultado.camino[0] == problema.posicion(problema.estado_inicial)
    assert resultado.camino[-1] == problema.objetivo
    assert len(resultado.camino) == len(resultado.acciones) + 1 == resultado.longitud + 1
    for origen, destino in zip(resultado.camino, resultado.camino[1:]):
        assert abs(origen.fila - destino.fila) + abs(origen.columna - destino.columna) == 1
        assert escenario.es_transitable(destino)
    assert resultado.costo == sum(escenario.obtener_costo(posicion) for posicion in resultado.camino[1:])


def test_objetivo_inicial_reporta_raiz_sin_expandir() -> None:
    problema = _problema("ruta_corta_vs_economica.json", Posicion(2, 0))

    resultado = busqueda_profundidad(problema)

    assert resultado.algoritmo == "DFS"
    assert resultado.exito
    assert resultado.camino == (Posicion(2, 0),)
    assert resultado.acciones == ()
    assert resultado.costo == 0
    assert (resultado.estados_generados, resultado.estados_expandidos, resultado.maximo_frontera) == (1, 0, 1)


def test_dfs_profundiza_por_el_primer_movimiento_y_no_garantiza_el_camino_mas_corto(tmp_path) -> None:
    # Orden de movimientos: arriba, abajo, izquierda, derecha. Desde (0, 0) DFS baja primero por la columna 0
    # y llega a (0, 2) dando la vuelta al mapa, mientras BFS llega en dos movimientos.
    problema = _problema_abierto_3x3(tmp_path, Posicion(0, 2))

    dfs = busqueda_profundidad(problema)
    bfs = busqueda_anchura(problema)

    assert dfs.camino == (
        Posicion(0, 0), Posicion(1, 0), Posicion(2, 0), Posicion(2, 1),
        Posicion(2, 2), Posicion(1, 2), Posicion(0, 2),
    )
    assert dfs.longitud == 6 and dfs.costo == 6
    assert (dfs.estados_generados, dfs.estados_expandidos, dfs.maximo_frontera) == (9, 6, 3)
    assert bfs.longitud == 2
    _verificar_camino_valido(problema, dfs)


def test_obstaculo_dfs_encuentra_un_camino_valido_que_rodea_la_barrera() -> None:
    problema = _problema("obstaculo_rodeo.json", Posicion(1, 3))

    resultado = busqueda_profundidad(problema)

    assert resultado.exito
    _verificar_camino_valido(problema, resultado)
    assert resultado.longitud >= busqueda_anchura(problema).longitud


def test_dfs_funciona_en_dimensiones_distintas_y_es_determinista() -> None:
    for archivo, objetivo in (
        ("ruta_corta_vs_economica.json", Posicion(2, 8)),
        ("campo_20x20.json", Posicion(9, 10)),
    ):
        problema = _problema(archivo, objetivo)
        primero = busqueda_profundidad(problema)
        segundo = busqueda_profundidad(problema)

        assert primero.exito
        _verificar_camino_valido(problema, primero)
        assert (primero.camino, primero.acciones, primero.costo, primero.estados_generados,
                primero.estados_expandidos, primero.maximo_frontera) == (
            segundo.camino, segundo.acciones, segundo.costo, segundo.estados_generados,
            segundo.estados_expandidos, segundo.maximo_frontera,
        )


def test_objetivo_inalcanzable_agota_la_frontera_sin_ciclos_infinitos() -> None:
    # (1, 1) es muro en el ejemplo del enunciado: ningun camino llega y DFS debe terminar.
    problema = _problema("ejemplo_enunciado.json", Posicion(1, 1))
    estado_inicial = problema.estado_inicial

    resultado = busqueda_profundidad(problema)
    bfs = busqueda_anchura(problema)

    assert not resultado.exito
    assert resultado.camino == resultado.acciones == ()
    assert resultado.costo is None
    # Con estados descubiertos, DFS y BFS visitan exactamente el mismo conjunto alcanzable.
    assert resultado.estados_generados == resultado.estados_expandidos == bfs.estados_generados
    assert problema.estado_inicial is estado_inicial
