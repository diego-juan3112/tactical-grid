"""Casos minimos 6 a 10 (E8.6): estado compuesto, decision adversarial, Minimax vs. alfa-beta, orden y profundidad.

Cada prueba fija una afirmacion de docs/casos-minimos-adversariales.md con datos deterministas (conteos, acciones y
valores; nunca tiempos), para que el analisis deje de ser valido si cambian los algoritmos, las reglas, la utilidad
o los escenarios.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from tacticalgrid.algoritmos import (
    ORDENES,
    EvaluadorUtilidad,
    alfa_beta,
    comparar_minimax_alfa_beta,
    minimax,
)
from tacticalgrid.escenario.cargador import cargar_escenario
from tacticalgrid.escenario.escenario import Posicion
from tacticalgrid.juego.estado import crear_estado_inicial
from tacticalgrid.juego.reglas import es_accion_valida

RAIZ = Path(__file__).resolve().parents[2]
CARPETA_ESCENARIOS = RAIZ / "escenarios"
ESCENARIOS_DE_LOS_CASOS = (
    "estado_compuesto_libre.json",
    "estado_compuesto_portador.json",
    "decision_adversarial.json",
    "recurso_en_transporte.json",
)


def _cargar(archivo: str):
    escenario = cargar_escenario(CARPETA_ESCENARIOS / archivo)
    return escenario, crear_estado_inicial(escenario)


def _jugada(resultado) -> tuple[str, Posicion, Posicion, str]:
    accion = resultado.accion_seleccionada
    return (
        accion.accion.identificador_unidad,
        accion.accion.origen,
        accion.accion.destino,
        accion.tipo_tactico,
    )


# --- Reglas comunes a los escenarios de los casos ------------------------------------------------------------------

@pytest.mark.parametrize("archivo", ESCENARIOS_DE_LOS_CASOS)
def test_los_escenarios_de_los_casos_respetan_las_reglas_del_enunciado(archivo) -> None:
    escenario, _ = _cargar(archivo)

    for bando in ("A", "B"):
        assert sum(unidad.bando == bando for unidad in escenario.unidades_iniciales) >= 3


@pytest.mark.parametrize("archivo", ESCENARIOS_DE_LOS_CASOS[:3])
def test_los_escenarios_nuevos_declaran_el_modo_adversarial(archivo) -> None:
    escenario, _ = _cargar(archivo)

    assert escenario.configuracion_prueba == {"modo": "adversarial"}


# --- Caso 6: estado compuesto --------------------------------------------------------------------------------------

def test_caso_6_misma_posicion_fisica_estados_distintos() -> None:
    _, libre = _cargar("estado_compuesto_libre.json")
    _, portador = _cargar("estado_compuesto_portador.json")

    assert libre.unidades == portador.unidades
    assert (libre.portador_recurso, libre.posicion_recurso) == (None, Posicion(2, 4))
    assert (portador.portador_recurso, portador.posicion_recurso) == ("A1", None)
    assert libre != portador
    assert len({libre, portador}) == 2


def test_caso_6_la_utilidad_distingue_los_dos_estados() -> None:
    escenario_libre, libre = _cargar("estado_compuesto_libre.json")
    escenario_portador, portador = _cargar("estado_compuesto_portador.json")

    desglose_libre = EvaluadorUtilidad(escenario_libre, "A").desglosar(libre)
    desglose_portador = EvaluadorUtilidad(escenario_portador, "A").desglosar(portador)

    assert sum(desglose_libre.values()) == 4
    assert desglose_libre["carrera_recurso"] == 4 and desglose_libre["posesion"] == 0
    assert sum(desglose_portador.values()) == 92
    assert (desglose_portador["posesion"], desglose_portador["entrega"]) == (100, -8)


@pytest.mark.parametrize("profundidad", [1, 2, 3, 4])
def test_caso_6_la_misma_posicion_lleva_a_decisiones_distintas(profundidad) -> None:
    escenario_libre, libre = _cargar("estado_compuesto_libre.json")
    escenario_portador, portador = _cargar("estado_compuesto_portador.json")

    sin_portador = alfa_beta(escenario_libre, libre, profundidad)
    con_portador = alfa_beta(escenario_portador, portador, profundidad)

    assert _jugada(sin_portador) == ("A1", Posicion(2, 2), Posicion(2, 3), "aproximarse_al_recurso")
    assert _jugada(con_portador) == ("A1", Posicion(2, 2), Posicion(1, 2), "avanzar")


# --- Caso 7: la mejor decision no es avanzar directo al recurso ----------------------------------------------------

@pytest.fixture(scope="module")
def decision():
    return _cargar("decision_adversarial.json")


def _valor_de(resultado, destino: Posicion, unidad: str = "A1") -> float:
    return next(
        valor
        for accion, valor in resultado.valores_raiz
        if accion.accion.identificador_unidad == unidad and accion.accion.destino == destino
    )


def test_caso_7_con_profundidad_1_tomar_el_recurso_parece_lo_mejor(decision) -> None:
    escenario, estado = decision

    resultado = minimax(escenario, estado, 1)

    assert _jugada(resultado) == ("A1", Posicion(0, 1), Posicion(0, 2), "aproximarse_al_recurso")
    assert resultado.valor == 37


@pytest.mark.parametrize(("profundidad", "valor"), [(2, -37), (3, 37), (4, -39)])
def test_caso_7_mirando_la_respuesta_de_b_minimax_no_toma_el_recurso(decision, profundidad, valor) -> None:
    escenario, estado = decision

    resultado = minimax(escenario, estado, profundidad)

    assert _valor_de(resultado, Posicion(0, 2)) == -10_000
    assert resultado.accion_seleccionada.accion.destino != Posicion(0, 2)
    assert _jugada(resultado) == ("A3", Posicion(2, 1), Posicion(2, 2), "aproximarse_al_recurso")
    assert resultado.valor == valor


def test_caso_7_retroceder_solo_parece_aceptable_hasta_profundidad_3(decision) -> None:
    escenario, estado = decision

    valores = [_valor_de(minimax(escenario, estado, d), Posicion(0, 0)) for d in (1, 2, 3, 4)]

    assert valores == [-2, -98, -38, -10_000]


# --- Caso 8: Minimax vs. alfa-beta ---------------------------------------------------------------------------------

@pytest.fixture(scope="module")
def transporte():
    return _cargar("recurso_en_transporte.json")


@pytest.mark.parametrize(
    ("profundidad", "minimax_gen_ev", "alfa_beta_gen_ev_pod"),
    [
        (1, (9, 8), (9, 8, 0)),
        (2, (80, 71), (40, 31, 40)),
        (3, (662, 582), (238, 191, 148)),
        (4, (5900, 5238), (787, 600, 907)),
    ],
)
def test_caso_8_misma_accion_y_menos_trabajo(transporte, profundidad, minimax_gen_ev, alfa_beta_gen_ev_pod) -> None:
    escenario, estado = transporte

    comparacion = comparar_minimax_alfa_beta(escenario, estado, profundidad)

    assert comparacion.misma_accion and comparacion.mismo_valor
    assert es_accion_valida(escenario, estado, comparacion.alfa_beta.accion_seleccionada.accion)
    assert (comparacion.minimax.nodos_generados, comparacion.minimax.nodos_evaluados) == minimax_gen_ev
    assert (
        comparacion.alfa_beta.nodos_generados,
        comparacion.alfa_beta.nodos_evaluados,
        comparacion.alfa_beta.nodos_podados,
    ) == alfa_beta_gen_ev_pod


def test_caso_8_el_ahorro_crece_con_la_profundidad(transporte) -> None:
    escenario, estado = transporte

    ahorros = [
        comparar_minimax_alfa_beta(escenario, estado, d).reduccion_porcentual("nodos_evaluados") for d in (1, 2, 3, 4)
    ]

    assert ahorros[0] == 0
    assert ahorros == sorted(ahorros)
    assert ahorros[-1] > 85


def test_caso_8_arbol_calculado_a_mano_del_pasillo(pasillo) -> None:
    comparacion = comparar_minimax_alfa_beta(pasillo, crear_estado_inicial(pasillo), 2)

    assert (comparacion.minimax.nodos_generados, comparacion.minimax.nodos_evaluados) == (7, 4)
    assert (
        comparacion.alfa_beta.nodos_generados,
        comparacion.alfa_beta.nodos_evaluados,
        comparacion.alfa_beta.nodos_podados,
    ) == (6, 3, 1)
    assert comparacion.misma_accion and comparacion.alfa_beta.valor == 3


# --- Caso 9: orden de acciones -------------------------------------------------------------------------------------

@pytest.mark.parametrize(
    ("orden", "gen_ev_pod", "jugada"),
    [
        ("generacion", (787, 600, 907), ("A1", Posicion(0, 2), Posicion(0, 3), "proteger_zona")),
        ("inverso", (962, 721, 1115), ("A2", Posicion(3, 3), Posicion(4, 3), "reposicionar")),
        ("tactico", (587, 428, 843), ("A1", Posicion(0, 2), Posicion(0, 3), "proteger_zona")),
    ],
)
def test_caso_9_el_orden_cambia_la_poda_pero_no_el_valor(transporte, orden, gen_ev_pod, jugada) -> None:
    escenario, estado = transporte

    comparacion = comparar_minimax_alfa_beta(escenario, estado, 4, orden=orden)
    resultado = comparacion.alfa_beta

    assert (resultado.nodos_generados, resultado.nodos_evaluados, resultado.nodos_podados) == gen_ev_pod
    assert _jugada(resultado) == jugada
    assert resultado.valor == 72
    assert comparacion.misma_accion and comparacion.mismo_valor


def test_caso_9_con_otro_orden_se_elige_otra_accion_del_mismo_valor(transporte) -> None:
    escenario, estado = transporte

    raiz = dict(minimax(escenario, estado, 4).valores_raiz)
    generacion = alfa_beta(escenario, estado, 4, orden="generacion").accion_seleccionada
    inverso = alfa_beta(escenario, estado, 4, orden="inverso").accion_seleccionada

    assert generacion != inverso
    assert raiz[generacion] == raiz[inverso] == max(raiz.values())


def test_caso_9_el_orden_no_cambia_el_trabajo_de_minimax(transporte) -> None:
    escenario, estado = transporte

    trabajos = {(r.nodos_generados, r.nodos_evaluados, r.valor) for r in (minimax(escenario, estado, 3, orden=o) for o in ORDENES)}

    assert trabajos == {(662, 582, 76)}


def test_caso_9_nodos_podados_no_mide_el_ahorro(transporte) -> None:
    """El orden tactico evalua menos hojas que el de generacion, pero cuenta menos ramas podadas."""
    escenario, estado = transporte

    generacion = alfa_beta(escenario, estado, 4, orden="generacion")
    tactico = alfa_beta(escenario, estado, 4, orden="tactico")

    assert tactico.nodos_evaluados < generacion.nodos_evaluados
    assert tactico.nodos_podados < generacion.nodos_podados


@pytest.mark.parametrize("archivo", ["recurso_en_transporte.json", "campo_20x20.json"])
@pytest.mark.parametrize("profundidad", [3, 4])
def test_caso_9_el_orden_tactico_es_el_que_menos_evalua(archivo, profundidad) -> None:
    escenario, estado = _cargar(archivo)

    evaluados = {orden: alfa_beta(escenario, estado, profundidad, orden=orden).nodos_evaluados for orden in ORDENES}

    assert evaluados["tactico"] == min(evaluados.values())


# --- Caso 10: profundidad ------------------------------------------------------------------------------------------

@pytest.mark.parametrize(
    ("profundidad", "jugada", "valor"),
    [
        (1, ("A2", Posicion(3, 3), Posicion(2, 3), "avanzar"), 74),
        (2, ("A1", Posicion(0, 2), Posicion(0, 3), "proteger_zona"), 72),
        (3, ("A2", Posicion(3, 3), Posicion(4, 3), "reposicionar"), 76),
        (4, ("A1", Posicion(0, 2), Posicion(0, 3), "proteger_zona"), 72),
    ],
)
def test_caso_10_la_decision_cambia_con_la_profundidad(transporte, profundidad, jugada, valor) -> None:
    escenario, estado = transporte

    resultado = alfa_beta(escenario, estado, profundidad)

    assert _jugada(resultado) == jugada
    assert resultado.valor == valor
    assert resultado.profundidad_alcanzada == profundidad


def test_caso_10_el_trabajo_crece_exponencialmente(transporte) -> None:
    escenario, estado = transporte

    generados = [minimax(escenario, estado, d).nodos_generados for d in (1, 2, 3, 4)]

    assert generados == [9, 80, 662, 5900]
    # Cada nivel multiplica el arbol por un factor de ramificacion efectivo cercano a 8 (las acciones de la raiz).
    assert all(7 <= siguiente / anterior <= 10 for anterior, siguiente in zip(generados, generados[1:]))


def test_caso_10_las_profundidades_impares_son_optimistas_para_max(transporte) -> None:
    """Con profundidad impar la ultima jugada mirada es de MAX; con par, de MIN."""
    escenario, estado = transporte

    valores = [alfa_beta(escenario, estado, d).valor for d in (1, 2, 3, 4)]

    assert valores == [74, 72, 76, 72]
    assert min(valores[0], valores[2]) > max(valores[1], valores[3])


# --- Reproducibilidad por consola ----------------------------------------------------------------------------------

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


def test_consola_permite_cambiar_el_orden_sin_tocar_codigo() -> None:
    salida = _ejecutar_main(
        "escenarios/recurso_en_transporte.json", "--algoritmo", "alfa_beta", "--profundidad", "4", "--orden", "inverso"
    )

    assert salida.returncode == 0, salida.stderr
    assert "Orden de acciones: inverso" in salida.stdout
    assert "Nodos podados: 1115" in salida.stdout
    assert "Acción seleccionada: A2 (3, 3) -> (4, 3) [reposicionar]" in salida.stdout


def test_consola_lee_el_orden_del_json(tmp_path) -> None:
    contenido = json.loads((CARPETA_ESCENARIOS / "recurso_en_transporte.json").read_text(encoding="utf-8"))
    contenido["juego"]["orden_acciones"] = "tactico"
    ruta = tmp_path / "orden_tactico.json"
    ruta.write_text(json.dumps(contenido), encoding="utf-8")

    salida = _ejecutar_main(str(ruta), "--algoritmo", "minimax_alfa_beta", "--profundidad", "4")

    assert salida.returncode == 0, salida.stderr
    assert "Orden de acciones: tactico" in salida.stdout
    assert "428" in salida.stdout


def test_consola_rechaza_un_orden_invalido_del_json(tmp_path) -> None:
    contenido = json.loads((CARPETA_ESCENARIOS / "recurso_en_transporte.json").read_text(encoding="utf-8"))
    contenido["juego"]["orden_acciones"] = "aleatorio"
    ruta = tmp_path / "orden_invalido.json"
    ruta.write_text(json.dumps(contenido), encoding="utf-8")

    salida = _ejecutar_main(str(ruta), "--algoritmo", "alfa_beta")

    assert salida.returncode == 1
    assert "orden de acciones" in salida.stderr
