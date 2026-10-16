"""Pruebas de E8.4: Minimax con poda alfa-beta."""

import json
from pathlib import Path

import pytest

from tacticalgrid.algoritmos.alfa_beta import alfa_beta
from tacticalgrid.algoritmos.minimax import minimax
from tacticalgrid.algoritmos.utilidad import EvaluadorUtilidad
from tacticalgrid.escenario.cargador import cargar_escenario
from tacticalgrid.escenario.escenario import Escenario, Posicion
from tacticalgrid.juego.accion import INTERCEPTAR
from tacticalgrid.juego.estado import EstadoJuego, crear_estado_inicial
from tacticalgrid.juego.reglas import es_accion_valida
from tacticalgrid.juego.unidad import Unidad

CARPETA_ESCENARIOS = Path(__file__).resolve().parents[2] / "escenarios"
ESCENARIOS_REALES = ["ejemplo_enunciado.json", "recurso_en_transporte.json", "campo_20x20.json"]


def _cargar(tmp_path, contenido: dict, nombre: str = "escenario.json") -> Escenario:
    ruta = tmp_path / nombre
    ruta.write_text(json.dumps(contenido), encoding="utf-8")
    return cargar_escenario(ruta)


@pytest.fixture
def pasillo(tmp_path) -> Escenario:
    """Pasillo 1x8 de camino con recurso en (0, 1), A1 en (0, 3) y B1 en (0, 6).

    Solo pesa ``carrera_recurso`` (peso 1): cada hoja vale distancia(B1, recurso) - distancia(A1, recurso).
    Arbol a profundidad 2 (MAX = A; orden de acciones: izquierda antes que derecha), calculado a mano:

    - a1: A1 -> (0, 2), distancia de A1 = 1.
        B1 -> (0, 5): 4 - 1 = 3.   B1 -> (0, 7): 6 - 1 = 5.   MIN = 3.   alfa = 3.
    - a2: A1 -> (0, 4), distancia de A1 = 3.
        B1 -> (0, 5): 4 - 3 = 1 <= alfa (3): MIN ya no puede superar 3, se poda B1 -> (0, 7).
    Minimax evalua 4 hojas y genera 7 nodos; alfa-beta evalua 3, genera 6 y poda 1 rama. Ambos eligen a1 con valor 3.
    """
    return _cargar(
        tmp_path,
        {
            "version": "1.0",
            "mapa": {"filas": 1, "columnas": 8},
            "tipos_terreno": {"camino": {"costo": 1, "transitable": True}},
            "terreno": [["camino"] * 8],
            "bases": {"A": {"fila": 0, "columna": 0}, "B": {"fila": 0, "columna": 7}},
            "recurso": {"fila": 0, "columna": 1},
            "unidades": [
                {"id": "A1", "bando": "A", "tipo": "estandar", "fila": 0, "columna": 3},
                {"id": "B1", "bando": "B", "tipo": "estandar", "fila": 0, "columna": 6},
            ],
            "turno": "A",
            "juego": {
                "portador_recurso": None,
                "profundidad_maxima_minimax": 2,
                "pesos_utilidad": {
                    "posesion": 0,
                    "entrega": 0,
                    "carrera_recurso": 1,
                    "amenaza": 0,
                    "bloqueo": 0,
                    "movilidad": 0,
                },
            },
        },
    )


def _destinos(resultado) -> dict[Posicion, float]:
    return {accion.accion.destino: valor for accion, valor in resultado.valores_raiz}


# --- Arbol calculado a mano ----------------------------------------------------------------------------------------

def test_pasillo_minimax_explora_todo_el_arbol(pasillo) -> None:
    resultado = minimax(pasillo, crear_estado_inicial(pasillo), 2)

    assert _destinos(resultado) == {Posicion(0, 2): 3, Posicion(0, 4): 1}
    assert resultado.accion_seleccionada.accion.destino == Posicion(0, 2)
    assert (resultado.nodos_generados, resultado.nodos_evaluados, resultado.nodos_podados) == (7, 4, 0)


def test_pasillo_alfa_beta_poda_una_rama_y_elige_lo_mismo(pasillo) -> None:
    resultado = alfa_beta(pasillo, crear_estado_inicial(pasillo), 2)

    assert resultado.algoritmo == "ALFA_BETA"
    assert resultado.accion_seleccionada.accion.destino == Posicion(0, 2)
    assert resultado.valor == 3
    assert (resultado.nodos_generados, resultado.nodos_evaluados, resultado.nodos_podados) == (6, 3, 1)
    assert resultado.profundidad_alcanzada == 2
    # a1 tiene valor exacto; a2 solo tiene una cota superior (1): su valor real es <= 1 y no puede ganarle a 3.
    assert _destinos(resultado) == {Posicion(0, 2): 3, Posicion(0, 4): 1}
    assert resultado.cotas_raiz == (False, True)


def test_pasillo_profundidad_1_no_hay_nada_que_podar(pasillo) -> None:
    estado = crear_estado_inicial(pasillo)

    con_poda = alfa_beta(pasillo, estado, 1)
    sin_poda = minimax(pasillo, estado, 1)

    assert con_poda.nodos_podados == 0
    assert (con_poda.nodos_generados, con_poda.nodos_evaluados) == (sin_poda.nodos_generados, sin_poda.nodos_evaluados)
    assert con_poda.accion_seleccionada == sin_poda.accion_seleccionada


# --- Equivalencia con Minimax sobre escenarios reales --------------------------------------------------------------

@pytest.mark.parametrize("archivo", ESCENARIOS_REALES)
@pytest.mark.parametrize("profundidad", [1, 2, 3])
def test_misma_decision_y_valor_que_minimax(archivo, profundidad) -> None:
    escenario = cargar_escenario(CARPETA_ESCENARIOS / archivo)
    estado = crear_estado_inicial(escenario)

    sin_poda = minimax(escenario, estado, profundidad)
    con_poda = alfa_beta(escenario, estado, profundidad)

    assert con_poda.accion_seleccionada == sin_poda.accion_seleccionada
    assert con_poda.valor == sin_poda.valor
    assert es_accion_valida(escenario, estado, con_poda.accion_seleccionada.accion)
    assert con_poda.nodos_generados <= sin_poda.nodos_generados
    assert con_poda.nodos_evaluados <= sin_poda.nodos_evaluados
    assert con_poda.profundidad_alcanzada <= sin_poda.profundidad_alcanzada


@pytest.mark.parametrize("archivo", ESCENARIOS_REALES)
@pytest.mark.parametrize("profundidad", [2, 3])
def test_valores_de_la_raiz_son_exactos_o_cotas_correctas(archivo, profundidad) -> None:
    escenario = cargar_escenario(CARPETA_ESCENARIOS / archivo)
    estado = crear_estado_inicial(escenario)

    reales = dict(minimax(escenario, estado, profundidad).valores_raiz)
    con_poda = alfa_beta(escenario, estado, profundidad)

    assert len(con_poda.cotas_raiz) == len(con_poda.valores_raiz) == len(reales)
    assert con_poda.cotas_raiz[0] is False
    for (accion, valor), es_cota in zip(con_poda.valores_raiz, con_poda.cotas_raiz):
        if es_cota:
            assert reales[accion] <= valor <= con_poda.valor
        else:
            assert reales[accion] == valor
    elegida = [accion for accion, _ in con_poda.valores_raiz].index(con_poda.accion_seleccionada)
    assert con_poda.cotas_raiz[elegida] is False


@pytest.mark.parametrize("archivo", ["recurso_en_transporte.json", "campo_20x20.json"])
def test_la_poda_reduce_el_trabajo_en_escenarios_reales(archivo) -> None:
    escenario = cargar_escenario(CARPETA_ESCENARIOS / archivo)
    estado = crear_estado_inicial(escenario)

    sin_poda = minimax(escenario, estado, 3)
    con_poda = alfa_beta(escenario, estado, 3)

    assert con_poda.nodos_podados > 0
    assert con_poda.nodos_evaluados < sin_poda.nodos_evaluados
    assert con_poda.nodos_generados < sin_poda.nodos_generados


def test_min_no_esta_en_desventaja(tmp_path) -> None:
    """Reflejar el tablero e intercambiar los bandos da el mismo valor y la misma poda para quien mueve."""
    def contenido(turno: str, unidades: list[tuple[str, int, int]], portador: str) -> dict:
        return {
            "version": "1.0",
            "mapa": {"filas": 5, "columnas": 5},
            "tipos_terreno": {"camino": {"costo": 1, "transitable": True}},
            "terreno": [["camino"] * 5 for _ in range(5)],
            "bases": {"A": {"fila": 0, "columna": 0}, "B": {"fila": 4, "columna": 4}},
            "recurso": {"fila": 2, "columna": 2},
            "unidades": [{"id": i, "bando": i[0], "tipo": "estandar", "fila": f, "columna": c} for i, f, c in unidades],
            "turno": turno,
            "juego": {"portador_recurso": portador},
        }

    original = _cargar(tmp_path, contenido("A", [("A1", 2, 2), ("B1", 1, 1), ("B2", 3, 4)], "A1"), "original.json")
    espejo = _cargar(tmp_path, contenido("B", [("B1", 2, 2), ("A1", 3, 3), ("A2", 1, 0)], "B1"), "espejo.json")

    for profundidad in (1, 2, 3):
        valor_a = alfa_beta(original, crear_estado_inicial(original), profundidad).valor
        valor_b = alfa_beta(espejo, crear_estado_inicial(espejo), profundidad).valor
        assert valor_a == valor_b == minimax(original, crear_estado_inicial(original), profundidad).valor


# --- Casos borde y validaciones ------------------------------------------------------------------------------------

def test_raiz_terminal_no_selecciona_accion(pasillo) -> None:
    ganado = EstadoJuego(
        unidades=(Unidad("A1", "A", "estandar", Posicion(0, 0)), Unidad("B1", "B", "estandar", Posicion(0, 6))),
        turno_actual="A",
        posicion_recurso=None,
        portador_recurso="A1",
        estado_partida="victoria_A",
    )

    resultado = alfa_beta(pasillo, ganado, 3)

    assert resultado.accion_seleccionada is None
    assert resultado.valor == 10_000
    assert (resultado.nodos_generados, resultado.nodos_evaluados, resultado.nodos_podados) == (1, 1, 0)
    assert resultado.valores_raiz == resultado.cotas_raiz == ()


def test_intercepcion_inmediata_es_la_decision_del_rival(tmp_path) -> None:
    corredor = _cargar(
        tmp_path,
        {
            "version": "1.0",
            "mapa": {"filas": 1, "columnas": 4},
            "tipos_terreno": {"camino": {"costo": 1, "transitable": True}},
            "terreno": [["camino"] * 4],
            "bases": {"A": {"fila": 0, "columna": 0}, "B": {"fila": 0, "columna": 3}},
            "recurso": {"fila": 0, "columna": 2},
            "unidades": [
                {"id": "A1", "bando": "A", "tipo": "estandar", "fila": 0, "columna": 1},
                {"id": "B1", "bando": "B", "tipo": "estandar", "fila": 0, "columna": 3},
            ],
            "turno": "A",
            "juego": {"portador_recurso": None},
        },
    )
    estado = EstadoJuego(
        unidades=(Unidad("A1", "A", "estandar", Posicion(0, 2)), Unidad("B1", "B", "estandar", Posicion(0, 3))),
        turno_actual="B",
        posicion_recurso=None,
        portador_recurso="A1",
    )

    resultado = alfa_beta(corredor, estado, 2)

    assert resultado.bando_max == "B"
    assert resultado.accion_seleccionada.accion.tipo == INTERCEPTAR
    assert resultado.valor == 10_000


@pytest.mark.parametrize("profundidad", [0, -1, True, 2.5, "3", None])
def test_profundidad_invalida_se_rechaza(pasillo, profundidad) -> None:
    with pytest.raises(ValueError, match="profundidad maxima de Minimax"):
        alfa_beta(pasillo, crear_estado_inicial(pasillo), profundidad)


def test_evaluador_debe_tener_como_max_al_bando_en_turno(pasillo) -> None:
    with pytest.raises(ValueError, match="bando MAX"):
        alfa_beta(pasillo, crear_estado_inicial(pasillo), 2, evaluador=EvaluadorUtilidad(pasillo, "B"))


def test_a_diccionario_incluye_los_nodos_podados(pasillo) -> None:
    datos = alfa_beta(pasillo, crear_estado_inicial(pasillo), 2).a_diccionario()

    assert datos["algoritmo"] == "ALFA_BETA"
    assert datos["nodos_podados"] == 1
    json.dumps(datos)


# --- Consola -------------------------------------------------------------------------------------------------------

def _ejecutar_main(*argumentos: str):
    import os
    import subprocess
    import sys

    raiz = Path(__file__).resolve().parents[2]
    return subprocess.run(
        [sys.executable, "-B", str(raiz / "main.py"), *argumentos],
        cwd=raiz,
        env=os.environ | {"PYTHONIOENCODING": "utf-8"},
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )


def test_consola_alfa_beta_elige_lo_mismo_que_minimax_y_reporta_la_poda() -> None:
    salida = _ejecutar_main("escenarios/recurso_en_transporte.json", "--algoritmo", "alfa_beta", "--profundidad", "2")

    assert salida.returncode == 0, salida.stderr
    assert "ALGORITMO: ALFA_BETA" in salida.stdout
    assert "Acción seleccionada: A1 (0, 2) -> (0, 3) [proteger_zona]" in salida.stdout
    assert "Nodos podados:" in salida.stdout
    assert "<== elegida" in salida.stdout


def test_consola_alfa_beta_usa_la_profundidad_del_json(tmp_path) -> None:
    contenido = json.loads((CARPETA_ESCENARIOS / "ejemplo_enunciado.json").read_text(encoding="utf-8"))
    contenido["juego"]["profundidad_maxima_minimax"] = 1
    ruta = tmp_path / "profundidad_1.json"
    ruta.write_text(json.dumps(contenido), encoding="utf-8")

    salida = _ejecutar_main(str(ruta), "--algoritmo", "alfa_beta")

    assert salida.returncode == 0, salida.stderr
    assert "Profundidad máxima: 1" in salida.stdout
