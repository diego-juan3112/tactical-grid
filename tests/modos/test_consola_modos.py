"""Pruebas de E10.1 en la consola: ``main.py`` ejecuta el modo que pide ``prueba`` sin cambios de codigo."""

import json
import os
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
CARPETA_ESCENARIOS = RAIZ / "escenarios"


def _ejecutar_main(*argumentos: str):
    return subprocess.run(
        [sys.executable, "-B", str(RAIZ / "main.py"), *argumentos],
        cwd=RAIZ,
        env=os.environ | {"PYTHONIOENCODING": "utf-8"},
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )


def _escenario_con(tmp_path, base: str, cambios_prueba: dict | None = None, cambios_juego: dict | None = None) -> str:
    contenido = json.loads((CARPETA_ESCENARIOS / base).read_text(encoding="utf-8"))
    if cambios_prueba is not None:
        contenido["prueba"] = cambios_prueba
    if cambios_juego is not None:
        contenido["juego"].update(cambios_juego)
    ruta = tmp_path / "escenario.json"
    ruta.write_text(json.dumps(contenido), encoding="utf-8")
    return str(ruta)


# --- El modo se toma del JSON --------------------------------------------------------------------------------------

def test_modo_busqueda_del_json_usa_ucs_por_defecto() -> None:
    salida = _ejecutar_main("escenarios/campo_20x20.json")

    assert salida.returncode == 0, salida.stderr
    assert "MODO: busqueda" in salida.stdout
    assert "ALGORITMO: UCS" in salida.stdout
    assert "Costo acumulado: 34" in salida.stdout


def test_modo_busqueda_usa_el_algoritmo_del_json(tmp_path) -> None:
    ruta = _escenario_con(
        tmp_path,
        "ejemplo_enunciado.json",
        {"modo": "busqueda", "unidad_inicio": "A1", "objetivo": {"fila": 3, "columna": 2}, "algoritmo": "a_estrella"},
    )

    salida = _ejecutar_main(ruta)

    assert salida.returncode == 0, salida.stderr
    assert "ALGORITMO: A_ESTRELLA" in salida.stdout


def test_modo_busqueda_beam_usa_k_del_json(tmp_path) -> None:
    ruta = _escenario_con(
        tmp_path,
        "ejemplo_enunciado.json",
        {"modo": "busqueda", "unidad_inicio": "A1", "objetivo": {"fila": 3, "columna": 2}, "algoritmo": "beam", "k": 2},
    )

    salida = _ejecutar_main(ruta)

    assert salida.returncode == 0, salida.stderr
    assert "BEAM SEARCH (K=2)" in salida.stdout


def test_modo_adversarial_del_json_selecciona_una_accion_con_alfa_beta() -> None:
    salida = _ejecutar_main("escenarios/decision_adversarial.json")

    assert salida.returncode == 0, salida.stderr
    assert "MODO: adversarial" in salida.stdout
    assert "ALGORITMO: ALFA_BETA" in salida.stdout
    assert "Profundidad máxima: 4" in salida.stdout
    assert "Acción seleccionada: A3 (2, 1) -> (2, 2)" in salida.stdout


def test_modo_adversarial_usa_el_algoritmo_del_json(tmp_path) -> None:
    ruta = _escenario_con(tmp_path, "decision_adversarial.json", {"modo": "adversarial", "algoritmo": "minimax"})

    salida = _ejecutar_main(ruta, "--profundidad", "2")

    assert salida.returncode == 0, salida.stderr
    assert "ALGORITMO: MINIMAX" in salida.stdout


def test_modo_partida_del_json_juega_por_turnos_hasta_el_limite(tmp_path) -> None:
    ruta = _escenario_con(
        tmp_path, "recurso_en_transporte.json", {"modo": "partida", "max_turnos": 3}, {"profundidad_maxima_minimax": 2}
    )

    salida = _ejecutar_main(ruta)

    assert salida.returncode == 0, salida.stderr
    texto = salida.stdout
    assert "MODO: partida" in texto
    assert "Turno 1 | A |" in texto and "Turno 2 | B |" in texto and "Turno 3 | A |" in texto
    assert "Turno 4" not in texto
    assert "Resultado: límite de 3 jugadas alcanzado sin ganador" in texto


def test_modo_partida_termina_con_un_ganador() -> None:
    salida = _ejecutar_main("escenarios/estado_compuesto_portador.json", "--modo", "partida")

    assert salida.returncode == 0, salida.stderr
    assert "Resultado: victoria de A en 9 jugadas" in salida.stdout


# --- La consola puede sobrescribir el JSON -------------------------------------------------------------------------

def test_modo_y_turnos_desde_la_consola() -> None:
    salida = _ejecutar_main(
        "escenarios/campo_20x20.json", "--modo", "partida", "--turnos", "2", "--profundidad", "2", "--algoritmo", "minimax"
    )

    assert salida.returncode == 0, salida.stderr
    assert "MODO: partida" in salida.stdout
    assert "Algoritmo de ambos bandos: minimax" in salida.stdout
    assert "Resultado: límite de 2 jugadas alcanzado sin ganador" in salida.stdout


def test_algoritmo_explicito_conserva_el_comportamiento_anterior() -> None:
    """recurso_en_transporte declara modo partida, pero --algoritmo minimax sigue evaluando el estado (E8.3)."""
    salida = _ejecutar_main("escenarios/recurso_en_transporte.json", "--algoritmo", "minimax", "--profundidad", "2")

    assert salida.returncode == 0, salida.stderr
    assert "ALGORITMO: MINIMAX" in salida.stdout
    assert "Acción seleccionada: A1 (0, 2) -> (0, 3) [proteger_zona]" in salida.stdout


def test_modo_adversarial_sobre_un_escenario_de_busqueda() -> None:
    salida = _ejecutar_main("escenarios/campo_20x20.json", "--modo", "adversarial", "--profundidad", "2")

    assert salida.returncode == 0, salida.stderr
    assert "ALGORITMO: ALFA_BETA" in salida.stdout


# --- Errores claros ------------------------------------------------------------------------------------------------

def test_combinacion_incompatible_de_modo_y_algoritmo() -> None:
    salida = _ejecutar_main("escenarios/campo_20x20.json", "--modo", "partida", "--algoritmo", "bfs")

    assert salida.returncode == 1
    assert "no se puede usar en el modo 'partida'" in salida.stderr


def test_prueba_invalida_en_el_json(tmp_path) -> None:
    ruta = _escenario_con(tmp_path, "ejemplo_enunciado.json", {"modo": "torneo"})

    salida = _ejecutar_main(ruta)

    assert salida.returncode == 1
    assert "prueba.modo" in salida.stderr


def test_busqueda_sin_unidad_ni_objetivo_explica_que_falta() -> None:
    salida = _ejecutar_main("escenarios/decision_adversarial.json", "--modo", "busqueda")

    assert salida.returncode == 1
    assert "--unidad" in salida.stderr


def test_a_estrella_reproduce_la_heuristica_hto_desde_argumentos_registrados() -> None:
    salida = _ejecutar_main(
        "escenarios/ruta_corta_vs_economica.json",
        "--modo",
        "busqueda",
        "--algoritmo",
        "a_estrella",
        "--unidad",
        "A1",
        "--objetivo",
        "2",
        "8",
        "--heuristica",
        "hto",
        "--json",
    )

    assert salida.returncode == 0, salida.stderr
    registro = json.loads(salida.stdout)
    assert registro["parametros"]["heuristica"] == "hto"
    assert "--heuristica hto" in registro["comando"]
    assert registro["resultados"][0]["algoritmo"] == "A_ESTRELLA"
