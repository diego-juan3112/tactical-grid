"""Pruebas de E8.5: metricas comparables de Minimax y alfa-beta sobre el mismo estado y profundidad."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from tacticalgrid.algoritmos.alfa_beta import alfa_beta
from tacticalgrid.algoritmos.comparacion_adversarial import METRICAS_COMPARABLES, comparar_minimax_alfa_beta
from tacticalgrid.algoritmos.minimax import minimax
from tacticalgrid.escenario.cargador import cargar_escenario
from tacticalgrid.escenario.escenario import Posicion
from tacticalgrid.juego.estado import EstadoJuego, crear_estado_inicial
from tacticalgrid.juego.unidad import Unidad

RAIZ = Path(__file__).resolve().parents[2]
CARPETA_ESCENARIOS = RAIZ / "escenarios"

# Los 7 datos que exige la issue E8.5, con los nombres de campo de ResultadoMinimax.
CAMPOS_EXIGIDOS = {
    "nodos_generados",
    "nodos_evaluados",
    "nodos_podados",
    "profundidad_alcanzada",
    "tiempo_segundos",
    "accion_seleccionada",
    "valor",
}


def test_las_metricas_comparables_son_las_siete_que_exige_la_issue() -> None:
    assert {campo for _, campo in METRICAS_COMPARABLES} == CAMPOS_EXIGIDOS
    assert len(METRICAS_COMPARABLES) == 7


def test_pasillo_calculado_a_mano(pasillo) -> None:
    comparacion = comparar_minimax_alfa_beta(pasillo, crear_estado_inicial(pasillo), 2)

    assert comparacion.minimax.algoritmo == "MINIMAX"
    assert comparacion.alfa_beta.algoritmo == "ALFA_BETA"
    assert (comparacion.minimax.nodos_generados, comparacion.alfa_beta.nodos_generados) == (7, 6)
    assert (comparacion.minimax.nodos_evaluados, comparacion.alfa_beta.nodos_evaluados) == (4, 3)
    assert (comparacion.minimax.nodos_podados, comparacion.alfa_beta.nodos_podados) == (0, 1)
    assert comparacion.misma_accion and comparacion.mismo_valor
    assert comparacion.alfa_beta.accion_seleccionada.accion.destino == Posicion(0, 2)
    # Reduccion = 1 - alfa_beta / minimax, en porcentaje.
    assert comparacion.reduccion_porcentual("nodos_evaluados") == pytest.approx(25.0)
    assert comparacion.reduccion_porcentual("nodos_generados") == pytest.approx(100 / 7)


@pytest.mark.parametrize("archivo", ["ejemplo_enunciado.json", "recurso_en_transporte.json", "campo_20x20.json"])
@pytest.mark.parametrize("profundidad", [1, 2, 3])
def test_coincide_con_ejecutar_cada_algoritmo_por_separado(archivo, profundidad) -> None:
    escenario = cargar_escenario(CARPETA_ESCENARIOS / archivo)
    estado = crear_estado_inicial(escenario)

    comparacion = comparar_minimax_alfa_beta(escenario, estado, profundidad)
    sin_poda = minimax(escenario, estado, profundidad)
    con_poda = alfa_beta(escenario, estado, profundidad)

    for _, campo in METRICAS_COMPARABLES:
        if campo == "tiempo_segundos":
            continue
        assert getattr(comparacion.minimax, campo) == getattr(sin_poda, campo)
        assert getattr(comparacion.alfa_beta, campo) == getattr(con_poda, campo)
    assert comparacion.misma_accion and comparacion.mismo_valor
    assert comparacion.minimax.profundidad_maxima == comparacion.alfa_beta.profundidad_maxima == profundidad
    assert comparacion.minimax.bando_max == comparacion.alfa_beta.bando_max == estado.turno_actual


def test_a_diccionario_expone_las_siete_metricas_de_ambos_y_es_json(pasillo) -> None:
    datos = comparar_minimax_alfa_beta(pasillo, crear_estado_inicial(pasillo), 2).a_diccionario()

    assert CAMPOS_EXIGIDOS <= set(datos["minimax"]) and CAMPOS_EXIGIDOS <= set(datos["alfa_beta"])
    assert datos["profundidad_maxima"] == 2
    assert datos["bando_max"] == "A"
    assert datos["misma_accion"] is True and datos["mismo_valor"] is True
    assert datos["reduccion_porcentual"]["nodos_evaluados"] == pytest.approx(25.0)
    assert set(datos["reduccion_porcentual"]) == {"nodos_generados", "nodos_evaluados", "tiempo_segundos"}
    json.dumps(datos)


def test_reduccion_solo_aplica_a_metricas_de_trabajo(pasillo) -> None:
    comparacion = comparar_minimax_alfa_beta(pasillo, crear_estado_inicial(pasillo), 2)

    with pytest.raises(ValueError, match="no admite reduccion"):
        comparacion.reduccion_porcentual("valor")


def test_raiz_terminal_ambos_sin_accion(pasillo) -> None:
    ganado = EstadoJuego(
        unidades=(Unidad("A1", "A", "estandar", Posicion(0, 0)), Unidad("B1", "B", "estandar", Posicion(0, 6))),
        turno_actual="A",
        posicion_recurso=None,
        portador_recurso="A1",
        estado_partida="victoria_A",
    )

    comparacion = comparar_minimax_alfa_beta(pasillo, ganado, 3)

    assert comparacion.minimax.accion_seleccionada is None and comparacion.alfa_beta.accion_seleccionada is None
    assert comparacion.misma_accion and comparacion.mismo_valor
    assert comparacion.a_diccionario()["minimax"]["accion_seleccionada"] is None


@pytest.mark.parametrize("profundidad", [0, -1, True, 2.5, "3", None])
def test_profundidad_invalida_se_rechaza(pasillo, profundidad) -> None:
    with pytest.raises(ValueError, match="profundidad maxima de Minimax"):
        comparar_minimax_alfa_beta(pasillo, crear_estado_inicial(pasillo), profundidad)


# --- Consola -------------------------------------------------------------------------------------------------------

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


def test_consola_muestra_la_tabla_comparativa_con_las_siete_metricas() -> None:
    salida = _ejecutar_main(
        "escenarios/recurso_en_transporte.json", "--algoritmo", "minimax_alfa_beta", "--profundidad", "2"
    )

    assert salida.returncode == 0, salida.stderr
    texto = salida.stdout
    assert "COMPARACIÓN MINIMAX vs. ALFA-BETA" in texto
    for etiqueta, _ in METRICAS_COMPARABLES:
        assert etiqueta in texto
    assert "Nodos generados" in texto and "80" in texto and "40" in texto
    assert "A1 (0, 2) -> (0, 3)" in texto
    assert "Misma acción: Sí" in texto
    assert "Mismo valor: Sí" in texto


def test_consola_comparacion_usa_la_profundidad_del_json(tmp_path) -> None:
    contenido = json.loads((CARPETA_ESCENARIOS / "ejemplo_enunciado.json").read_text(encoding="utf-8"))
    contenido["juego"]["profundidad_maxima_minimax"] = 1
    ruta = tmp_path / "profundidad_1.json"
    ruta.write_text(json.dumps(contenido), encoding="utf-8")

    salida = _ejecutar_main(str(ruta), "--algoritmo", "minimax_alfa_beta")

    assert salida.returncode == 0, salida.stderr
    assert "Profundidad máxima: 1" in salida.stdout
