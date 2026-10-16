"""Pruebas de E10.3: registro reproducible de experimentos con la estructura del enunciado."""

import json
import os
import shlex
import subprocess
import sys
from pathlib import Path

import pytest

from tacticalgrid.escenario.cargador import cargar_escenario
from tacticalgrid.modos.registro import (
    CLAVES_ENUNCIADO_ADVERSARIAL,
    CLAVES_ENUNCIADO_BUSQUEDA,
    FORMATO,
    RegistroExperimento,
    serializar,
    sin_tiempos,
)

RAIZ = Path(__file__).resolve().parents[2]
CARPETA_ESCENARIOS = RAIZ / "escenarios"


def _ejecutar(*argumentos: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-B", str(RAIZ / "main.py"), *argumentos],
        cwd=RAIZ,
        env=os.environ | {"PYTHONIOENCODING": "utf-8"},
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )


def _registro(*argumentos: str) -> dict:
    salida = _ejecutar(*argumentos, "--json")
    assert salida.returncode == 0, salida.stderr
    # Con --json la salida estandar es solo el JSON: debe poder leerse completa.
    return json.loads(salida.stdout)


# --- Estructura del enunciado en cada modo ------------------------------------------------------------------------

def test_busqueda_tiene_la_estructura_del_enunciado() -> None:
    registro = _registro("escenarios/ruta_corta_vs_economica.json", "--algoritmo", "ucs")

    assert registro["formato"] == FORMATO
    assert registro["modo"] == "busqueda"
    (resultado,) = registro["resultados"]
    assert set(CLAVES_ENUNCIADO_BUSQUEDA) <= set(resultado)
    assert resultado["algoritmo"] == "UCS"
    assert resultado["camino"][0] == [2, 0] and resultado["camino"][-1] == [2, 8]
    assert (resultado["costo"], resultado["estados_generados"], resultado["estados_expandidos"]) == (12, 22, 19)


def test_comparaciones_y_beam_registran_un_resultado_por_algoritmo() -> None:
    ambos = _registro("escenarios/ruta_corta_vs_economica.json", "--algoritmo", "ambos")
    beam = _registro("escenarios/campo_20x20.json", "--algoritmo", "beam", "--k", "1", "2", "4", "8")

    assert [r["algoritmo"] for r in ambos["resultados"]] == ["BFS", "UCS"]
    assert [r["algoritmo"] for r in beam["resultados"]] == [f"BEAM_SEARCH_K{k}" for k in (1, 2, 4, 8)]
    assert beam["parametros"]["k"] == [1, 2, 4, 8]
    assert [r["exito"] for r in beam["resultados"]] == [False, False, True, True]


def test_adversarial_tiene_las_metricas_del_enunciado() -> None:
    registro = _registro(
        "escenarios/recurso_en_transporte.json", "--modo", "adversarial", "--algoritmo", "minimax", "--profundidad", "2"
    )

    (resultado,) = registro["resultados"]
    assert set(CLAVES_ENUNCIADO_ADVERSARIAL) <= set(resultado)
    assert resultado["accion_seleccionada"]["destino"] == [0, 3]
    assert resultado["nodos_generados"] == 80
    assert registro["parametros"]["profundidad"] == 2
    assert registro["parametros"]["pesos_utilidad"]["amenaza"] == 60


def test_partida_registra_cada_jugada() -> None:
    registro = _registro("escenarios/recurso_en_transporte.json", "--modo", "partida", "--profundidad", "1", "--turnos", "5")

    assert registro["modo"] == "partida"
    assert registro["parametros"]["max_turnos"] == 5
    (partida,) = registro["resultados"]
    assert len(partida["turnos"]) == 5


def test_parametros_resueltos_desde_el_campo_prueba() -> None:
    """Sin argumentos, el modo, la unidad y el objetivo salen del JSON y quedan escritos en el registro."""
    registro = _registro("escenarios/campo_20x20.json")

    assert registro["modo"] == "busqueda"
    assert registro["parametros"] == {"algoritmo": "ucs", "unidad": "A1", "objetivo": [9, 10]}


# --- Reproducibilidad ---------------------------------------------------------------------------------------------

@pytest.mark.parametrize(
    "argumentos",
    [
        ("escenarios/campo_20x20.json",),
        ("escenarios/campo_20x20.json", "--algoritmo", "beam", "--k", "2", "4"),
        ("escenarios/recurso_en_transporte.json", "--modo", "adversarial", "--algoritmo", "alfa_beta", "--profundidad", "3"),
        ("escenarios/recurso_en_transporte.json", "--modo", "partida", "--profundidad", "1", "--turnos", "4"),
    ],
    ids=["busqueda_del_json", "beam", "alfa_beta", "partida"],
)
def test_el_comando_registrado_reproduce_los_mismos_resultados(argumentos) -> None:
    original = _registro(*argumentos)

    comando = shlex.split(original["comando"])
    assert comando[:2] == ["python", "main.py"]
    repetido = _registro(*comando[2:])

    assert sin_tiempos(repetido) == sin_tiempos(original)


def test_dos_ejecuciones_solo_difieren_en_el_tiempo() -> None:
    argumentos = ("escenarios/ruta_corta_vs_economica.json", "--algoritmo", "ambos")

    primera, segunda = _registro(*argumentos), _registro(*argumentos)

    assert sin_tiempos(primera) == sin_tiempos(segunda)
    assert all("tiempo_segundos" in r for r in primera["resultados"])


def test_la_huella_identifica_el_contenido_del_escenario(tmp_path) -> None:
    contenido = (CARPETA_ESCENARIOS / "ruta_corta_vs_economica.json").read_text(encoding="utf-8")
    copia = tmp_path / "copia.json"
    copia.write_text(contenido, encoding="utf-8")
    cambiado = tmp_path / "cambiado.json"
    cambiado.write_text(contenido.replace('"pantano": {"costo": 7', '"pantano": {"costo": 15'), encoding="utf-8")

    original = _registro("escenarios/ruta_corta_vs_economica.json", "--algoritmo", "ucs")
    huella_copia = _registro(str(copia), "--algoritmo", "ucs")["escenario"]["huella_sha256"]
    huella_cambiada = _registro(str(cambiado), "--algoritmo", "ucs")["escenario"]["huella_sha256"]

    assert huella_copia == original["escenario"]["huella_sha256"]
    assert huella_cambiada != original["escenario"]["huella_sha256"]
    assert len(huella_copia) == 64


# --- Verificacion y export ----------------------------------------------------------------------------------------

def test_registro_incluye_la_verificacion_si_se_pide() -> None:
    con = _registro("escenarios/ruta_corta_vs_economica.json", "--algoritmo", "ambos", "--verificar")
    sin = _registro("escenarios/ruta_corta_vs_economica.json", "--algoritmo", "ambos")

    assert con["verificacion"]["valida"] is True
    assert [r["sujeto"] for r in con["verificacion"]["reportes"]] == ["BFS (busqueda)", "UCS (busqueda)"]
    assert con["comando"].endswith("--verificar")
    assert "verificacion" not in sin


def test_exportar_guarda_el_archivo_y_conserva_el_texto(tmp_path) -> None:
    destino = tmp_path / "resultado.json"

    salida = _ejecutar("escenarios/ruta_corta_vs_economica.json", "--algoritmo", "ucs", "--exportar", str(destino))

    assert salida.returncode == 0, salida.stderr
    assert "ALGORITMO: UCS" in salida.stdout  # el texto habitual se sigue mostrando
    assert f"exportado a {destino}" in salida.stdout
    exportado = json.loads(destino.read_text(encoding="utf-8"))
    assert sin_tiempos(exportado) == sin_tiempos(_registro("escenarios/ruta_corta_vs_economica.json", "--algoritmo", "ucs"))


def test_exportar_a_una_carpeta_inexistente_explica_el_error(tmp_path) -> None:
    salida = _ejecutar("escenarios/ruta_corta_vs_economica.json", "--exportar", str(tmp_path / "no" / "existe.json"))

    assert salida.returncode == 1
    assert "No se pudo exportar" in salida.stderr


def test_sin_opciones_no_cambia_la_salida_de_texto() -> None:
    salida = _ejecutar("escenarios/ruta_corta_vs_economica.json", "--algoritmo", "ucs")

    assert salida.returncode == 0
    assert "ALGORITMO: UCS" in salida.stdout
    assert '"formato"' not in salida.stdout


# --- Unidades del registro ----------------------------------------------------------------------------------------

def test_serializar_conserva_cualquier_contenido() -> None:
    documento = {
        "camino": [[2, 0], [2, 1]],
        "texto": 'detalle con, comas [corchetes] y "comillas"',
        "lista": ["a, b", "c]"],
        "anidado": [{"x": [1, 2]}, {"y": None}],
        "vacio": {},
    }

    texto = serializar(documento)

    assert json.loads(texto) == documento
    assert '"camino": [[2, 0], [2, 1]]' in texto


def test_comando_omite_parametros_que_no_son_opciones_de_consola() -> None:
    registro = RegistroExperimento(
        archivo="escenarios/mi mapa.json",
        huella_sha256="0" * 64,
        escenario=cargar_escenario(CARPETA_ESCENARIOS / "ejemplo_enunciado.json"),
    )
    registro.definir("adversarial", algoritmo="minimax", profundidad=3, pesos_utilidad={"amenaza": 0}, k=None)

    assert registro.parametros == {"algoritmo": "minimax", "profundidad": 3, "pesos_utilidad": {"amenaza": 0}}
    assert registro.comando() == "python main.py 'escenarios/mi mapa.json' --modo adversarial --algoritmo minimax --profundidad 3"
