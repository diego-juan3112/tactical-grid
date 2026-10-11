"""Pruebas de E8.3: Minimax con profundidad limitada."""

import json
from pathlib import Path

import pytest

from tacticalgrid.algoritmos.minimax import minimax, profundidad_desde_configuracion
from tacticalgrid.algoritmos.utilidad import EvaluadorUtilidad
from tacticalgrid.escenario.cargador import cargar_escenario
from tacticalgrid.escenario.escenario import Escenario, Posicion
from tacticalgrid.juego.accion import INTERCEPTAR
from tacticalgrid.juego.estado import EstadoJuego, crear_estado_inicial
from tacticalgrid.juego.reglas import es_accion_valida
from tacticalgrid.juego.unidad import Unidad

CARPETA_ESCENARIOS = Path(__file__).resolve().parents[2] / "escenarios"


def _cargar(tmp_path, contenido: dict, nombre: str = "escenario.json") -> Escenario:
    ruta = tmp_path / nombre
    ruta.write_text(json.dumps(contenido), encoding="utf-8")
    return cargar_escenario(ruta)


@pytest.fixture
def corredor(tmp_path) -> Escenario:
    """Corredor 1x4 de camino: base A en (0, 0), A1 en (0, 1), recurso en (0, 2), B1 sobre su base en (0, 3).

    Arbol calculado a mano (MAX = A, pesos por defecto):

    - A1 -> (0, 2) recoge el recurso. Profundidad 1: posesion 100, entrega -4, amenaza -60 (B1 adyacente),
      movilidad +1 => 37. Profundidad 2: la unica respuesta de B1 es interceptar desde su base => victoria B = -10000.
    - A1 -> (0, 0) retrocede. Profundidad 1: carrera 2 * (1 - 2) = -2, movilidad 0 => -2. Profundidad 2: B1 recoge
      el recurso en (0, 2): posesion -100, entrega +2 => -98. Profundidad 3: A1 avanza a (0, 1) junto al portador
      B1: posesion -100, entrega +2, amenaza +60 => -38.
    """
    return _cargar(
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
            "juego": {"portador_recurso": None, "profundidad_maxima_minimax": 2},
        },
    )


def _destinos(resultado) -> dict[Posicion, float]:
    return {accion.accion.destino: valor for accion, valor in resultado.valores_raiz}


# --- Arbol calculado a mano ----------------------------------------------------------------------------------------

def test_profundidad_1_cae_en_la_trampa_del_recurso(corredor) -> None:
    resultado = minimax(corredor, crear_estado_inicial(corredor), 1)

    assert _destinos(resultado) == {Posicion(0, 0): -2, Posicion(0, 2): 37}
    assert resultado.accion_seleccionada.accion.destino == Posicion(0, 2)
    assert resultado.accion_seleccionada.tipo_tactico == "aproximarse_al_recurso"
    assert resultado.valor == 37
    assert (resultado.nodos_generados, resultado.nodos_evaluados, resultado.profundidad_alcanzada) == (3, 2, 1)


def test_profundidad_2_preve_la_intercepcion_y_retrocede(corredor) -> None:
    resultado = minimax(corredor, crear_estado_inicial(corredor), 2)

    assert _destinos(resultado) == {Posicion(0, 0): -98, Posicion(0, 2): -10_000}
    assert resultado.accion_seleccionada.accion.destino == Posicion(0, 0)
    assert resultado.valor == -98
    # Raiz + 2 jugadas de A + 1 respuesta de B a cada una; las 2 hojas estan a profundidad 2.
    assert (resultado.nodos_generados, resultado.nodos_evaluados, resultado.profundidad_alcanzada) == (5, 2, 2)
    assert resultado.nodos_podados == 0


def test_profundidad_3_y_hoja_terminal_antes_del_limite(corredor) -> None:
    resultado = minimax(corredor, crear_estado_inicial(corredor), 3)

    assert _destinos(resultado) == {Posicion(0, 0): -38, Posicion(0, 2): -10_000}
    assert resultado.valor == -38
    # La victoria de B es una hoja a profundidad 2 (terminal): no se expande aunque el limite sea 3.
    assert (resultado.nodos_generados, resultado.nodos_evaluados, resultado.profundidad_alcanzada) == (6, 2, 3)


def test_profundidad_maxima_se_lee_del_json(corredor) -> None:
    profundidad = profundidad_desde_configuracion(corredor.configuracion_juego)

    assert profundidad == 2
    assert minimax(corredor, crear_estado_inicial(corredor), profundidad).accion_seleccionada.accion.destino == Posicion(
        0, 0
    )


# --- Propiedades sobre escenarios reales ---------------------------------------------------------------------------

@pytest.mark.parametrize("archivo", ["ejemplo_enunciado.json", "recurso_en_transporte.json", "campo_20x20.json"])
@pytest.mark.parametrize("profundidad", [1, 2, 3])
def test_accion_legal_valor_y_metricas_coherentes(archivo, profundidad) -> None:
    escenario = cargar_escenario(CARPETA_ESCENARIOS / archivo)
    estado = crear_estado_inicial(escenario)

    resultado = minimax(escenario, estado, profundidad)

    assert es_accion_valida(escenario, estado, resultado.accion_seleccionada.accion)
    valores = [valor for _, valor in resultado.valores_raiz]
    assert resultado.valor == max(valores)
    # Ante empate se elige la primera accion con el mejor valor.
    assert resultado.valores_raiz[valores.index(max(valores))][0] == resultado.accion_seleccionada
    assert resultado.profundidad_alcanzada == profundidad
    assert resultado.nodos_generados > resultado.nodos_evaluados >= len(valores)
    assert resultado.nodos_podados == 0
    assert resultado.tiempo_segundos >= 0


@pytest.mark.parametrize("archivo", ["ejemplo_enunciado.json", "recurso_en_transporte.json"])
def test_mas_profundidad_genera_mas_nodos(archivo) -> None:
    escenario = cargar_escenario(CARPETA_ESCENARIOS / archivo)
    estado = crear_estado_inicial(escenario)

    generados = [minimax(escenario, estado, d).nodos_generados for d in (1, 2, 3)]

    assert generados == sorted(generados) and len(set(generados)) == 3


@pytest.mark.parametrize("archivo", sorted(p.name for p in CARPETA_ESCENARIOS.glob("*.json")))
def test_todos_los_escenarios_declaran_una_profundidad_valida(archivo) -> None:
    escenario = cargar_escenario(CARPETA_ESCENARIOS / archivo)

    assert profundidad_desde_configuracion(escenario.configuracion_juego) == 4


def test_min_no_esta_en_desventaja(tmp_path) -> None:
    """Reflejar el tablero e intercambiar los bandos da el mismo valor para quien mueve: MAX y MIN son roles."""
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
        valor_a = minimax(original, crear_estado_inicial(original), profundidad).valor
        valor_b = minimax(espejo, crear_estado_inicial(espejo), profundidad).valor
        assert valor_a == valor_b


# --- Casos borde y validaciones ------------------------------------------------------------------------------------

def test_raiz_terminal_no_selecciona_accion(corredor) -> None:
    ganado = EstadoJuego(
        unidades=(Unidad("A1", "A", "estandar", Posicion(0, 0)), Unidad("B1", "B", "estandar", Posicion(0, 3))),
        turno_actual="A",
        posicion_recurso=None,
        portador_recurso="A1",
        estado_partida="victoria_A",
    )

    resultado = minimax(corredor, ganado, 3)

    assert resultado.accion_seleccionada is None
    assert resultado.valor == 10_000
    assert (resultado.nodos_generados, resultado.nodos_evaluados, resultado.profundidad_alcanzada) == (1, 1, 0)


def test_intercepcion_inmediata_es_la_decision_del_rival(corredor) -> None:
    """Si B esta en turno junto al portador A1 y sobre su base, interceptar le da la victoria."""
    estado = EstadoJuego(
        unidades=(Unidad("A1", "A", "estandar", Posicion(0, 2)), Unidad("B1", "B", "estandar", Posicion(0, 3))),
        turno_actual="B",
        posicion_recurso=None,
        portador_recurso="A1",
    )

    resultado = minimax(corredor, estado, 2)

    assert resultado.bando_max == "B"
    assert resultado.accion_seleccionada.accion.tipo == INTERCEPTAR
    assert resultado.valor == 10_000


@pytest.mark.parametrize("profundidad", [0, -1, True, 2.5, "3", None])
def test_profundidad_invalida_se_rechaza(corredor, profundidad) -> None:
    with pytest.raises(ValueError, match="profundidad maxima de Minimax"):
        minimax(corredor, crear_estado_inicial(corredor), profundidad)


def test_profundidad_invalida_en_el_json_se_rechaza(tmp_path, corredor) -> None:
    with pytest.raises(ValueError, match="se recibio 0"):
        profundidad_desde_configuracion({"profundidad_maxima_minimax": 0})
    assert profundidad_desde_configuracion({}) is None
    assert profundidad_desde_configuracion(None) is None


def test_evaluador_debe_tener_como_max_al_bando_en_turno(corredor) -> None:
    with pytest.raises(ValueError, match="bando MAX"):
        minimax(corredor, crear_estado_inicial(corredor), 2, evaluador=EvaluadorUtilidad(corredor, "B"))


def test_a_diccionario_tiene_las_metricas_del_enunciado(corredor) -> None:
    datos = minimax(corredor, crear_estado_inicial(corredor), 2).a_diccionario()

    assert {
        "nodos_generados",
        "nodos_evaluados",
        "nodos_podados",
        "profundidad_alcanzada",
        "tiempo_segundos",
        "accion_seleccionada",
        "valor",
    } <= set(datos)
    assert datos["accion_seleccionada"] == {
        "unidad": "A1",
        "tipo": "mover",
        "origen": [0, 1],
        "destino": [0, 0],
        "tactica": "reposicionar",
    }
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


def test_consola_usa_la_profundidad_indicada() -> None:
    salida = _ejecutar_main("escenarios/recurso_en_transporte.json", "--algoritmo", "minimax", "--profundidad", "2")

    assert salida.returncode == 0, salida.stderr
    assert "Profundidad máxima: 2" in salida.stdout
    assert "Acción seleccionada: A1 (0, 2) -> (0, 3) [proteger_zona]" in salida.stdout
    assert "Nodos generados: 80" in salida.stdout
    assert "<== elegida" in salida.stdout


def test_consola_usa_la_profundidad_del_json(tmp_path) -> None:
    contenido = json.loads((CARPETA_ESCENARIOS / "ejemplo_enunciado.json").read_text(encoding="utf-8"))
    contenido["juego"]["profundidad_maxima_minimax"] = 1
    ruta = tmp_path / "profundidad_1.json"
    ruta.write_text(json.dumps(contenido), encoding="utf-8")

    salida = _ejecutar_main(str(ruta), "--algoritmo", "minimax")

    assert salida.returncode == 0, salida.stderr
    assert "Profundidad máxima: 1" in salida.stdout


def test_consola_sin_profundidad_explica_como_configurarla(tmp_path) -> None:
    contenido = json.loads((CARPETA_ESCENARIOS / "ejemplo_enunciado.json").read_text(encoding="utf-8"))
    del contenido["juego"]["profundidad_maxima_minimax"]
    ruta = tmp_path / "sin_profundidad.json"
    ruta.write_text(json.dumps(contenido), encoding="utf-8")

    salida = _ejecutar_main(str(ruta), "--algoritmo", "minimax")

    assert salida.returncode == 1
    assert "--profundidad" in salida.stderr and "profundidad_maxima_minimax" in salida.stderr
