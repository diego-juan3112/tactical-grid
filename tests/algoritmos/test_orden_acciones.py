"""Pruebas del orden configurable de acciones para Minimax y alfa-beta (E8.6, caso minimo 9)."""

from pathlib import Path

import pytest

from tacticalgrid.algoritmos.alfa_beta import alfa_beta
from tacticalgrid.algoritmos.comparacion_adversarial import comparar_minimax_alfa_beta
from tacticalgrid.algoritmos.minimax import minimax
from tacticalgrid.algoritmos.orden_acciones import (
    ORDEN_GENERACION,
    ORDENES,
    PRIORIDAD_TACTICA,
    orden_desde_configuracion,
    ordenar_acciones,
    validar_orden,
)
from tacticalgrid.escenario.cargador import cargar_escenario
from tacticalgrid.escenario.escenario import Posicion
from tacticalgrid.juego.accion import Accion
from tacticalgrid.juego.estado import crear_estado_inicial
from tacticalgrid.juego.tacticas import TIPOS_TACTICOS, AccionTactica

CARPETA_ESCENARIOS = Path(__file__).resolve().parents[2] / "escenarios"


def _accion(columna: int, tipo: str) -> AccionTactica:
    return AccionTactica(Accion("A1", Posicion(0, 0), Posicion(0, columna)), tipo)


ACCIONES = (
    _accion(1, "reposicionar"),
    _accion(2, "aproximarse_al_recurso"),
    _accion(3, "reposicionar"),
    _accion(4, "interceptar_portador"),
)


def test_los_ordenes_disponibles() -> None:
    assert ORDENES == ("generacion", "inverso", "tactico")
    assert ORDEN_GENERACION == "generacion"


def test_orden_de_generacion_conserva_las_acciones() -> None:
    assert ordenar_acciones(ACCIONES, "generacion") == ACCIONES


def test_orden_inverso_invierte_las_acciones() -> None:
    assert ordenar_acciones(ACCIONES, "inverso") == tuple(reversed(ACCIONES))


def test_orden_tactico_prioriza_por_tipo_y_respeta_la_generacion_en_empates() -> None:
    ordenadas = ordenar_acciones(ACCIONES, "tactico")

    assert [a.tipo_tactico for a in ordenadas] == [
        "interceptar_portador",
        "aproximarse_al_recurso",
        "reposicionar",
        "reposicionar",
    ]
    # Las dos acciones "reposicionar" conservan su orden de generacion (columna 1 antes que 3).
    assert [a.accion.destino.columna for a in ordenadas[2:]] == [1, 3]


def test_la_prioridad_tactica_cubre_todos_los_tipos() -> None:
    assert set(PRIORIDAD_TACTICA) == set(TIPOS_TACTICOS)
    assert PRIORIDAD_TACTICA["interceptar_portador"] == min(PRIORIDAD_TACTICA.values())
    assert PRIORIDAD_TACTICA["reposicionar"] == max(PRIORIDAD_TACTICA.values())


@pytest.mark.parametrize("orden", ["aleatorio", "", None, 3, True])
def test_orden_invalido_se_rechaza(orden) -> None:
    with pytest.raises(ValueError, match="orden de acciones"):
        validar_orden(orden)


def test_orden_se_lee_del_json() -> None:
    assert orden_desde_configuracion({"orden_acciones": "inverso"}) == "inverso"
    assert orden_desde_configuracion({}) is None
    assert orden_desde_configuracion(None) is None
    with pytest.raises(ValueError, match="orden de acciones"):
        orden_desde_configuracion({"orden_acciones": "aleatorio"})


# --- Integracion con Minimax y alfa-beta ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def transporte():
    escenario = cargar_escenario(CARPETA_ESCENARIOS / "recurso_en_transporte.json")
    return escenario, crear_estado_inicial(escenario)


def test_por_defecto_se_usa_el_orden_de_generacion(transporte) -> None:
    escenario, estado = transporte

    explicito = alfa_beta(escenario, estado, 3, orden="generacion")
    por_defecto = alfa_beta(escenario, estado, 3)

    assert por_defecto.orden_acciones == "generacion"
    assert (por_defecto.accion_seleccionada, por_defecto.valor, por_defecto.nodos_podados) == (
        explicito.accion_seleccionada,
        explicito.valor,
        explicito.nodos_podados,
    )


@pytest.mark.parametrize("orden", ORDENES)
def test_con_el_mismo_orden_minimax_y_alfa_beta_deciden_lo_mismo(transporte, orden) -> None:
    escenario, estado = transporte

    sin_poda = minimax(escenario, estado, 3, orden=orden)
    con_poda = alfa_beta(escenario, estado, 3, orden=orden)

    assert con_poda.accion_seleccionada == sin_poda.accion_seleccionada
    assert con_poda.valor == sin_poda.valor
    assert sin_poda.orden_acciones == con_poda.orden_acciones == orden
    assert [a for a, _ in sin_poda.valores_raiz] == [a for a, _ in con_poda.valores_raiz]


def test_el_orden_no_cambia_el_valor_minimax_ni_el_trabajo_de_minimax(transporte) -> None:
    escenario, estado = transporte

    resultados = [minimax(escenario, estado, 3, orden=orden) for orden in ORDENES]

    assert len({r.valor for r in resultados}) == 1
    assert len({(r.nodos_generados, r.nodos_evaluados) for r in resultados}) == 1


def test_el_orden_cambia_la_cantidad_de_poda(transporte) -> None:
    escenario, estado = transporte

    podados = {orden: alfa_beta(escenario, estado, 3, orden=orden).nodos_podados for orden in ORDENES}

    assert len(set(podados.values())) > 1


def test_la_comparacion_aplica_el_orden_a_ambos_algoritmos(transporte) -> None:
    escenario, estado = transporte

    comparacion = comparar_minimax_alfa_beta(escenario, estado, 3, orden="inverso")

    assert comparacion.minimax.orden_acciones == comparacion.alfa_beta.orden_acciones == "inverso"
    assert comparacion.misma_accion and comparacion.mismo_valor
    assert comparacion.a_diccionario()["orden_acciones"] == "inverso"


def test_el_resultado_exporta_el_orden(transporte) -> None:
    escenario, estado = transporte

    assert minimax(escenario, estado, 1, orden="tactico").a_diccionario()["orden_acciones"] == "tactico"


def test_orden_invalido_en_los_algoritmos(transporte) -> None:
    escenario, estado = transporte

    for funcion in (minimax, alfa_beta):
        with pytest.raises(ValueError, match="orden de acciones"):
            funcion(escenario, estado, 2, orden="aleatorio")
