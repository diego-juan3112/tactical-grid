"""Busqueda A* con heuristica Manhattan sobre problemas de navegacion."""

import heapq
from itertools import count

from tacticalgrid.juego.estado import EstadoJuego
from tacticalgrid.juego.problema import ProblemaNavegacion

from .instrumentacion import MedidorBusqueda, Nodo, es_valor_finito, expandir
from .resultado_busqueda import ResultadoBusqueda


def heuristica_manhattan(problema: ProblemaNavegacion, estado: EstadoJuego) -> int | float:
    """Estima el costo restante mediante Manhattan escalada por el menor costo de paso.

    Purpose: proporcionar a A* una cota inferior del costo desde la posicion de la unidad navegante hasta el
    objetivo, sin reducir la identidad compuesta de ``estado`` a esa posicion.
    Preconditions: ``problema`` mueve la unidad una celda ortogonal por transicion; todos sus costos de paso son
    al menos ``problema.costo_minimo_paso``, que es positivo; ``estado`` pertenece al espacio del problema.
    Postconditions: devuelve cero en el objetivo y, en otro caso, la distancia Manhattan multiplicada por la
    cota minima de costo; lanza ``ValueError`` si el producto no es finito. No modifica el problema ni el estado.
    En aritmetica representable es admisible y consistente: cada paso reduce Manhattan a lo sumo en uno y cuesta
    al menos la escala aplicada.
    Complexity: O(U) temporal por localizar la unidad entre las U unidades del estado y O(1) espacial.
    AI usage: Yes.
    AI intervention: Codex implemento la formula, su escalamiento y, durante el cierre de E6.1, la guarda que
    impide propagar un producto no finito.
    Student validation: pendiente de revision humana del equipo.
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


def _calcular_prioridad(problema: ProblemaNavegacion, nodo: Nodo) -> int | float:
    """Calcula ``f(n) = g(n) + h(n)`` y rechaza resultados no finitos.

    Purpose: impedir que A* introduzca prioridades infinitas o NaN en ``heapq``.
    Preconditions: ``nodo.costo_acumulado`` es finito y el nodo pertenece al espacio de ``problema``.
    Postconditions: devuelve la prioridad finita del nodo o lanza ``ValueError`` si la suma excede el rango
    numerico soportado; no modifica el nodo ni el problema.
    Complexity: O(U) temporal por la heuristica y O(1) espacial.
    AI usage: Yes.
    AI intervention: Codex implemento esta guarda durante el cierre del riesgo numerico de E6.1.
    Student validation: pendiente de revision humana del cambio de E6.1.
    """
    estimacion = heuristica_manhattan(problema, nodo.estado)
    try:
        prioridad = nodo.costo_acumulado + estimacion
    except OverflowError as error:
        raise ValueError("La prioridad f(n) excede el rango numerico finito soportado.") from error
    if not es_valor_finito(prioridad):
        raise ValueError("La prioridad f(n) excede el rango numerico finito soportado.")
    return prioridad


def busqueda_a_estrella(problema: ProblemaNavegacion) -> ResultadoBusqueda:
    """Encuentra una solucion de costo minimo priorizando ``g(n) + h(n)``.

    Purpose: ejecutar A* sobre la navegacion con Manhattan escalada y reportar las metricas comunes de E4.1.
    Preconditions: ``problema`` cumple las precondiciones de :func:`heuristica_manhattan`; sus estados son
    hashables y sus costos de transicion son positivos.
    Postconditions: devuelve una solucion de costo acumulado minimo o fracaso si la frontera se agota; lanza
    ``ValueError`` antes de insertar una prioridad o propagar un costo no finito. Conserva estados y problema sin
    modificaciones. Las mejoras estrictas de g se reinsertan y las entradas obsoletas se descartan por su g. La
    finitud evita desbordamientos, pero no elimina el redondeo propio de operaciones representables con ``float``.
    Complexity: O(E * (U log U + U) + (V + E) log E + d * U) temporal y O((V + E) * U + d) espacial en el peor
    caso, donde V son estados alcanzables, E transiciones examinadas, U unidades por estado y d la profundidad de
    la solucion. Incluye transiciones, hashing, evaluaciones heuristicas, cola con reinserciones y reconstruccion.
    AI usage: Yes.
    AI intervention: Codex implemento A*, la prioridad f, la gestion de mejoras y obsoletos, su instrumentacion y
    las guardas de finitud de h y f para E6.1 a partir del patron validado de UCS.
    Student validation: pendiente de revision humana del equipo.
    """
    medidor = MedidorBusqueda("A_ESTRELLA")
    raiz = Nodo(problema.estado_inicial)
    desempate = count()
    prioridad_raiz = _calcular_prioridad(problema, raiz)
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
            prioridad = _calcular_prioridad(problema, hijo)
            heapq.heappush(frontera, (prioridad, next(desempate), hijo))
            medidor.registrar_generado()
            medidor.observar_frontera(len(frontera))

    return medidor.finalizar(problema, None)
