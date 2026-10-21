"""Verifica las variantes académicas 20x20 de los casos adversariales 6, 7, 8 y 10."""

from pathlib import Path

import pytest

from tacticalgrid.algoritmos import alfa_beta, comparar_minimax_alfa_beta, minimax
from tacticalgrid.algoritmos.verificador import verificar_decision
from tacticalgrid.algoritmos.utilidad import EvaluadorUtilidad
from tacticalgrid.escenario.cargador import cargar_escenario
from tacticalgrid.juego.estado import crear_estado_inicial

RAIZ = Path(__file__).resolve().parents[2]
ESCENARIOS = RAIZ / "escenarios"


def _cargar(nombre: str):
    escenario = cargar_escenario(ESCENARIOS / nombre)
    return escenario, crear_estado_inicial(escenario)


def _decision(resultado):
    seleccion = resultado.accion_seleccionada
    return (
        seleccion.accion.identificador_unidad,
        seleccion.accion.origen,
        seleccion.accion.destino,
        resultado.valor,
        resultado.nodos_generados,
        resultado.nodos_evaluados,
        resultado.nodos_podados,
    )


ESCENARIOS_20X20 = (
    "caso_06_estado_compuesto_libre_20x20.json",
    "caso_06_estado_compuesto_portador_20x20.json",
    "caso_07_decision_adversarial_20x20.json",
    "caso_08_minimax_alfa_beta_20x20.json",
    "caso_10_profundidad_20x20.json",
)


@pytest.mark.parametrize("nombre", ESCENARIOS_20X20)
def test_escenarios_academicos_tienen_dimensiones_terrenos_y_unidades_validos(nombre):
    escenario, _ = _cargar(nombre)

    assert (escenario.filas, escenario.columnas) == (20, 20)
    assert len({unidad.identificador for unidad in escenario.unidades_iniciales}) == len(escenario.unidades_iniciales)
    assert all(sum(u.bando == bando for u in escenario.unidades_iniciales) >= 3 for bando in ("A", "B"))
    assert all(
        terreno in escenario.tipos_terreno
        and (not escenario.tipos_terreno[terreno].transitable or escenario.tipos_terreno[terreno].costo > 0)
        for fila in escenario.terreno
        for terreno in fila
    )


@pytest.mark.parametrize(
    ("original", "variante"),
    [
        ("estado_compuesto_libre.json", ESCENARIOS_20X20[0]),
        ("estado_compuesto_portador.json", ESCENARIOS_20X20[1]),
    ],
)
def test_caso_6_variante_conserva_estado_utilidad_y_decision(original, variante):
    escenario_original, estado_original = _cargar(original)
    escenario_variante, estado_variante = _cargar(variante)

    assert estado_original == estado_variante
    assert EvaluadorUtilidad(escenario_original, "A").evaluar(estado_original) == EvaluadorUtilidad(
        escenario_variante, "A"
    ).evaluar(estado_variante)
    for profundidad in (1, 2, 3, 4):
        original_resultado = alfa_beta(escenario_original, estado_original, profundidad)
        variante_resultado = alfa_beta(escenario_variante, estado_variante, profundidad)
        assert _decision(original_resultado) == _decision(variante_resultado)
        assert verificar_decision(escenario_variante, estado_variante, variante_resultado).es_valido


def test_caso_6_variante_distingue_portador_y_posiciones_iguales():
    _, libre = _cargar(ESCENARIOS_20X20[0])
    _, portador = _cargar(ESCENARIOS_20X20[1])

    assert libre.unidades == portador.unidades
    assert libre != portador
    assert alfa_beta(*_cargar(ESCENARIOS_20X20[0]), 4).accion_seleccionada != alfa_beta(
        *_cargar(ESCENARIOS_20X20[1]), 4
    ).accion_seleccionada


@pytest.mark.parametrize("profundidad", (1, 2, 3, 4))
def test_caso_7_decision_adversarial_20x20(profundidad):
    escenario_original, estado_original = _cargar("decision_adversarial.json")
    escenario_variante, estado_variante = _cargar(ESCENARIOS_20X20[2])
    original = minimax(escenario_original, estado_original, profundidad)
    variante = minimax(escenario_variante, estado_variante, profundidad)

    assert _decision(original) == _decision(variante)
    destino = variante.accion_seleccionada.accion.destino
    assert (destino.fila, destino.columna) == ((0, 2) if profundidad == 1 else (2, 2))
    assert verificar_decision(escenario_variante, estado_variante, variante).es_valido


def test_caso_8_minimax_alfa_beta_20x20_conserva_poda_efectiva():
    escenario_original, estado_original = _cargar("recurso_en_transporte.json")
    escenario_variante, estado_variante = _cargar(ESCENARIOS_20X20[3])
    original = comparar_minimax_alfa_beta(escenario_original, estado_original, 4)
    variante = comparar_minimax_alfa_beta(escenario_variante, estado_variante, 4)

    assert original.misma_accion and original.mismo_valor
    assert variante.misma_accion and variante.mismo_valor
    assert _decision(original.minimax) == _decision(variante.minimax)
    assert _decision(original.alfa_beta) == _decision(variante.alfa_beta)
    assert variante.alfa_beta.nodos_podados > 0
    assert verificar_decision(escenario_variante, estado_variante, variante.minimax).es_valido
    assert verificar_decision(escenario_variante, estado_variante, variante.alfa_beta).es_valido


@pytest.mark.parametrize("profundidad", (1, 2, 3, 4))
def test_caso_10_profundidad_20x20_conserva_efectos_y_metricas(profundidad):
    escenario_original, estado_original = _cargar("recurso_en_transporte.json")
    escenario_variante, estado_variante = _cargar(ESCENARIOS_20X20[4])
    minimax_original = minimax(escenario_original, estado_original, profundidad)
    minimax_variante = minimax(escenario_variante, estado_variante, profundidad)
    alfa_original = alfa_beta(escenario_original, estado_original, profundidad)
    alfa_variante = alfa_beta(escenario_variante, estado_variante, profundidad)

    assert _decision(minimax_original) == _decision(minimax_variante)
    assert _decision(alfa_original) == _decision(alfa_variante)
    assert verificar_decision(escenario_variante, estado_variante, minimax_variante).es_valido
    assert verificar_decision(escenario_variante, estado_variante, alfa_variante).es_valido
