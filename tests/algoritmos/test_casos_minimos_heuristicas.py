"""Pruebas reproducibles de los casos minimos 3 y 4 sobre las implementaciones E6.1 y E6.2.

AI usage: Yes.
AI intervention: Codex integro en estas pruebas las propiedades ya cubiertas por separado para fijar la evidencia
de obstaculo, rodeo y comparacion entre Manhattan, HTO y UCS sin modificar los algoritmos.
Student validation: pendiente de revision y validacion del equipo estudiantil.
"""

from pathlib import Path

from tacticalgrid.algoritmos import busqueda_a_estrella, busqueda_costo_uniforme
from tacticalgrid.algoritmos.heuristica_obstaculos import HeuristicaObstaculos
from tacticalgrid.escenario import Posicion, cargar_escenario
from tacticalgrid.juego import ProblemaNavegacion

CARPETA_ESCENARIOS = Path(__file__).resolve().parents[2] / "escenarios"
RUTA_ESCENARIO = CARPETA_ESCENARIOS / "obstaculo_rodeo.json"
INICIO = Posicion(4, 3)
OBJETIVO = Posicion(1, 3)


def _crear_problema() -> ProblemaNavegacion:
    """Construye la configuracion declarada por el escenario del experimento.

    Purpose: evitar que las variantes comparadas difieran en escenario, unidad u objetivo.
    Preconditions: ``obstaculo_rodeo.json`` existe y cumple el contrato de escenarios.
    Postconditions: devuelve una instancia nueva de ``ProblemaNavegacion`` para A1 y el objetivo del JSON.
    Complexity: O(F*C + U log U + T) temporal y O(F*C + U) espacial por carga y construccion.
    AI usage: Yes.
    AI intervention: Codex implemento esta fabrica de pruebas a partir de la configuracion publica del escenario.
    Student validation: pendiente de revision y validacion del equipo estudiantil.
    """
    escenario = cargar_escenario(RUTA_ESCENARIO)
    prueba = escenario.configuracion_prueba
    assert prueba == {
        "modo": "busqueda",
        "unidad_inicio": "A1",
        "objetivo": {"fila": 1, "columna": 3},
    }
    objetivo = Posicion(prueba["objetivo"]["fila"], prueba["objetivo"]["columna"])
    return ProblemaNavegacion(escenario, prueba["unidad_inicio"], objetivo)


def _validar_solucion(problema: ProblemaNavegacion, resultado) -> None:
    """Reaplica las acciones y contrasta camino, transitabilidad, costo y objetivo.

    Purpose: comprobar la solucion sin confiar solo en las metricas devueltas por el algoritmo.
    Preconditions: ``resultado`` corresponde a una busqueda ejecutada sobre ``problema``.
    Postconditions: confirma que cada paso es legal y transitable, que el costo recalculado coincide y que el
    estado final satisface el objetivo; no modifica el estado inicial.
    Complexity: O(L * (U + A)) temporal y O(1) espacial adicional, con L pasos, U unidades y A acciones legales.
    AI usage: Yes.
    AI intervention: Codex implemento la reaplicacion independiente de la ruta para esta evidencia de integracion.
    Student validation: pendiente de revision y validacion del equipo estudiantil.
    """
    assert resultado.exito
    assert resultado.camino[0] == problema.posicion(problema.estado_inicial)
    assert len(resultado.camino) == resultado.longitud + 1

    estado = problema.estado_inicial
    costo_recalculado = 0
    for indice, accion in enumerate(resultado.acciones, start=1):
        assert accion in problema.acciones(estado)
        assert problema.escenario.es_transitable(accion.destino)
        costo_recalculado += problema.costo(estado, accion)
        estado = problema.resultado(estado, accion)
        assert problema.posicion(estado) == resultado.camino[indice]

    assert costo_recalculado == resultado.costo
    assert problema.es_objetivo(estado)
    assert problema.estado_inicial != estado


def test_caso_minimo_3_el_muro_obliga_a_rodear() -> None:
    problema = _crear_problema()
    inicio = problema.posicion(problema.estado_inicial)
    distancia_manhattan = abs(inicio.fila - problema.objetivo.fila) + abs(
        inicio.columna - problema.objetivo.columna
    )
    heuristica = HeuristicaObstaculos(problema)
    referencia = busqueda_costo_uniforme(problema)

    assert (problema.escenario.filas, problema.escenario.columnas) == (8, 7)
    assert (inicio, problema.objetivo) == (INICIO, OBJETIVO)
    assert distancia_manhattan == 3
    assert not problema.escenario.es_transitable(Posicion(2, 3))
    assert heuristica.distancias[inicio] == 15
    assert (referencia.longitud, referencia.costo) == (15, 16)
    _validar_solucion(problema, referencia)


def test_caso_minimo_4_compara_manhattan_y_hto_con_referencia_ucs() -> None:
    problema_manhattan = _crear_problema()
    problema_hto = _crear_problema()
    problema_ucs = _crear_problema()
    heuristica = HeuristicaObstaculos(problema_hto)

    manhattan = busqueda_a_estrella(problema_manhattan)
    hto = busqueda_a_estrella(problema_hto, heuristica_preparada=heuristica)
    ucs = busqueda_costo_uniforme(problema_ucs)

    assert heuristica.problema is problema_hto
    assert problema_manhattan.estado_inicial == problema_hto.estado_inicial == problema_ucs.estado_inicial
    assert problema_manhattan.objetivo == problema_hto.objetivo == problema_ucs.objetivo == OBJETIVO
    assert manhattan.costo == hto.costo == ucs.costo == 16
    assert manhattan.longitud == hto.longitud == ucs.longitud == 15
    assert (
        manhattan.estados_generados,
        manhattan.estados_expandidos,
        manhattan.maximo_frontera,
    ) == (40, 33, 7)
    assert (hto.estados_generados, hto.estados_expandidos, hto.maximo_frontera) == (38, 26, 12)

    _validar_solucion(problema_manhattan, manhattan)
    _validar_solucion(problema_hto, hto)
    _validar_solucion(problema_ucs, ucs)
