"""Búsqueda A* con Manhattan predeterminada y una heurística preparada opcional."""

import heapq
from itertools import count
from typing import Protocol

from tacticalgrid.juego.estado import EstadoJuego
from tacticalgrid.juego.problema import ProblemaNavegacion

from .instrumentacion import MedidorBusqueda, Nodo, ObservadorExpansiones, es_valor_finito, expandir
from .resultado_busqueda import ResultadoBusqueda


class HeuristicaPreparada(Protocol):
    """Contrato mínimo de una heurística ligada a un problema de navegación."""

    problema: ProblemaNavegacion

    def evaluar(self, estado: EstadoJuego) -> int | float: ...


def heuristica_manhattan(problema: ProblemaNavegacion, estado: EstadoJuego) -> int | float:
    """Estimar el costo restante con la distancia Manhattan escalada por el menor costo de paso.

    Proposito: proporcionar a A* una cota inferior del costo desde la posición de la unidad navegante hasta el
    objetivo, sin reducir la identidad compuesta de ``estado`` a esa posición.
    Precondiciones: ``problema`` mueve la unidad una celda ortogonal por transición; todos sus costos de paso son al
    menos ``problema.costo_minimo_paso``, que es positivo; ``estado`` pertenece al espacio del problema.
    Postcondiciones: se devuelve cero en el objetivo y, en otro caso, la distancia Manhattan multiplicada por la cota
    mínima de costo; se lanza ``ValueError`` si el producto no es finito. El problema y el estado no cambian. En
    aritmética representable la estimación es admisible y consistente: cada paso reduce Manhattan a lo sumo en uno y
    cuesta al menos la escala aplicada.
    Complejidad: O(U) temporal por localizar la unidad entre las U unidades del estado y O(1) espacial.
    Uso de IA: Si.
    Intervencion de IA: Codex: fórmula, escalamiento y guarda contra productos no finitos (E6.1).
    Validacion del estudiante: pruebas de tests/algoritmos/test_busqueda_a_estrella.py: distancia escalada, valor cero
    en el objetivo, escala con costo mínimo decimal y fallo controlado cuando el producto desborda.
    """
    actual = problema.posicion(estado)
    distancia = abs(actual.fila - problema.objetivo.fila) + abs(actual.columna - problema.objetivo.columna)
    try:
        estimacion = distancia * problema.costo_minimo_paso
    except OverflowError as error:
        raise ValueError("La heuristica Manhattan excede el rango numerico finito soportado.") from error
    if not es_valor_finito(estimacion):
        raise ValueError("La heuristica Manhattan excede el rango numerico finito soportado.")
    return estimacion


def _calcular_prioridad(
    problema: ProblemaNavegacion,
    nodo: Nodo,
    heuristica_preparada: HeuristicaPreparada | None = None,
) -> int | float:
    """Calcular ``f(n) = g(n) + h(n)`` y rechazar resultados no finitos.

    Proposito: seleccionar Manhattan o la estrategia preparada explícita e impedir que A* introduzca prioridades
    infinitas o NaN en ``heapq``.
    Precondiciones: ``nodo.costo_acumulado`` es finito, el nodo pertenece al espacio de ``problema`` y, si se
    proporciona, ``heuristica_preparada`` está ligada por identidad al mismo problema.
    Postcondiciones: se devuelve la prioridad finita del nodo, o se lanza ``ValueError`` si la suma excede el rango
    numérico soportado o la estimación no es finita; el nodo y el problema no cambian. La estrategia puede extender su
    preparación diferida al evaluar.
    Complejidad: O(C_h) temporal y O(S_h) espacial incremental, con C_h y S_h los costos de una evaluación de la
    heurística elegida; la suma y las validaciones son O(1).
    Uso de IA: Si.
    Intervencion de IA: Codex: guarda numérica (E6.1) y selección entre Manhattan y una estrategia preparada sin
    modificar la fórmula f(n) (E6.2).
    Validacion del estudiante: pruebas de tests/algoritmos/test_busqueda_a_estrella.py: f igual a g más h, rechazo de
    una suma g + h que desborda y de una estimación inyectada no finita.
    """
    if heuristica_preparada is None:
        estimacion = heuristica_manhattan(problema, nodo.estado)
    else:
        estimacion = heuristica_preparada.evaluar(nodo.estado)
    if not es_valor_finito(estimacion):
        raise ValueError("La heuristica seleccionada produjo una estimacion no finita.")
    try:
        prioridad = nodo.costo_acumulado + estimacion
    except OverflowError as error:
        raise ValueError("La prioridad f(n) excede el rango numerico finito soportado.") from error
    if not es_valor_finito(prioridad):
        raise ValueError("La prioridad f(n) excede el rango numerico finito soportado.")
    return prioridad


def busqueda_a_estrella(
    problema: ProblemaNavegacion,
    *,
    heuristica_preparada: HeuristicaPreparada | None = None,
    observador_expansiones: ObservadorExpansiones | None = None,
) -> ResultadoBusqueda:
    """Encontrar una solución de costo mínimo priorizando ``g(n) + h(n)``.

    Proposito: ejecutar A* con Manhattan por defecto o con una heurística preparada explícita y reportar las métricas
    comunes de E4.1 sin duplicar la exploración.
    Precondiciones: ``problema`` cumple las precondiciones de :func:`heuristica_manhattan`; sus estados son hashables y
    sus costos de transición son positivos. La estrategia opcional se construyó externamente para esta misma instancia
    de ``problema``; su costo de preparación corresponde al llamador.
    Postcondiciones: se devuelve una solución de costo acumulado mínimo cuando la heurística elegida conserva las
    condiciones de optimalidad de A*, o fracaso si la frontera se agota. Se lanza ``ValueError`` antes de crear la
    frontera si la estrategia pertenece a otro problema, o antes de insertar una prioridad no finita. Los estados y el
    problema no cambian. Las mejoras estrictas de g se reinsertan y las entradas obsoletas se descartan por su g. Las
    evaluaciones y extensiones diferidas de la estrategia ocurren durante la búsqueda. La guarda de finitud no elimina
    el redondeo propio de ``float``. El observador opcional recibe las expansiones vigentes y no altera prioridades,
    reinserciones ni desempates.
    Complejidad: O(E * (T_s + C_h) + (V + E) log E + d * U) temporal y O((V + E) * U + d + S_h) espacial en el peor
    caso, más O(X_t) espacial para la traza; V son estados, E transiciones, T_s el costo de generar una transición,
    C_h y S_h los costos de la heurística, U las unidades y d la profundidad. No incluye construir la heurística.
    Uso de IA: Si.
    Intervencion de IA: Codex: A*, prioridad f, gestión de mejoras y entradas obsoletas, instrumentación y guardas de
    finitud (E6.1); heurística inyectable (E6.2); observador opcional (E9.3).
    Validacion del estudiante: pruebas de tests/algoritmos/test_busqueda_a_estrella.py (costo igual al óptimo de UCS,
    reinserción por mejora estricta, identidad del estado compuesto, meta inalcanzable, estrategia inyectada y valores
    no finitos) y de tests/algoritmos/test_casos_minimos_heuristicas.py (casos mínimos 3 y 4).
    """
    if heuristica_preparada is not None and heuristica_preparada.problema is not problema:
        raise ValueError(
            "La heuristica preparada pertenece a otro ProblemaNavegacion; "
            "construya una estrategia para la misma instancia recibida por A*."
        )

    medidor = MedidorBusqueda("A_ESTRELLA", observador_expansiones=observador_expansiones)
    raiz = Nodo(problema.estado_inicial)
    desempate = count()
    prioridad_raiz = _calcular_prioridad(problema, raiz, heuristica_preparada)
    frontera: list[tuple[int | float, int, Nodo]] = [(prioridad_raiz, next(desempate), raiz)]
    mejores_costos: dict[EstadoJuego, int | float] = {raiz.estado: raiz.costo_acumulado}
    medidor.registrar_generado()
    medidor.observar_frontera(len(frontera))

    while frontera:
        _, _, nodo = heapq.heappop(frontera)
        medidor.observar_frontera(len(frontera))
        if nodo.costo_acumulado != mejores_costos[nodo.estado]:
            continue
        if problema.es_objetivo(nodo.estado):
            return medidor.finalizar(problema, nodo)

        for hijo in expandir(problema, nodo, medidor):
            mejor_anterior = mejores_costos.get(hijo.estado)
            if mejor_anterior is not None and hijo.costo_acumulado >= mejor_anterior:
                continue
            mejores_costos[hijo.estado] = hijo.costo_acumulado
            prioridad = _calcular_prioridad(problema, hijo, heuristica_preparada)
            heapq.heappush(frontera, (prioridad, next(desempate), hijo))
            medidor.registrar_generado()
            medidor.observar_frontera(len(frontera))

    return medidor.finalizar(problema, None)
