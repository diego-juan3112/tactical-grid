"""Busqueda A* con Manhattan predeterminada y una heuristica preparada opcional."""

import heapq
from itertools import count
from typing import Protocol

from tacticalgrid.juego.estado import EstadoJuego
from tacticalgrid.juego.problema import ProblemaNavegacion

from .instrumentacion import MedidorBusqueda, Nodo, es_valor_finito, expandir
from .resultado_busqueda import ResultadoBusqueda


class HeuristicaPreparada(Protocol):
    """Contrato minimo de una heuristica ligada a un problema de navegacion."""

    problema: ProblemaNavegacion

    def evaluar(self, estado: EstadoJuego) -> int | float: ...


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


def _calcular_prioridad(
    problema: ProblemaNavegacion,
    nodo: Nodo,
    heuristica_preparada: HeuristicaPreparada | None = None,
) -> int | float:
    """Calcula ``f(n) = g(n) + h(n)`` y rechaza resultados no finitos.

    Purpose: seleccionar Manhattan o la estrategia preparada explicita e impedir que A* introduzca prioridades
    infinitas o NaN en ``heapq``.
    Preconditions: ``nodo.costo_acumulado`` es finito, el nodo pertenece al espacio de ``problema`` y, si se
    proporciona, ``heuristica_preparada`` esta ligada por identidad al mismo problema.
    Postconditions: devuelve la prioridad finita del nodo o lanza ``ValueError`` si la suma excede el rango
    numerico soportado o la estimacion no es finita; no modifica el nodo ni el problema. La estrategia puede
    extender su preparacion diferida al evaluar.
    Complexity: O(C_h) temporal y O(S_h) espacial incremental, donde C_h y S_h corresponden a una evaluacion de
    la heuristica elegida; la suma y las validaciones son O(1).
    AI usage: Yes.
    AI intervention: Codex implemento en E6.1 la guarda numerica y en E6.2 incorporo la seleccion entre Manhattan
    y una estrategia preparada sin modificar la formula f(n).
    Student validation: pendiente de revision humana del equipo.
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
) -> ResultadoBusqueda:
    """Encuentra una solucion de costo minimo priorizando ``g(n) + h(n)``.

    Purpose: ejecutar A* con Manhattan por defecto o una heuristica preparada explicita y reportar las metricas
    comunes de E4.1 sin duplicar la exploracion.
    Preconditions: ``problema`` cumple las precondiciones de :func:`heuristica_manhattan`; sus estados son
    hashables y sus costos de transicion son positivos. La estrategia opcional fue construida externamente para
    esta misma instancia de ``problema``; su costo de preparacion corresponde al llamador.
    Postconditions: devuelve una solucion de costo acumulado minimo cuando la heuristica elegida conserva las
    condiciones de optimalidad de A*, o fracaso si la frontera se agota; lanza ``ValueError`` antes de crear la
    frontera si la estrategia pertenece a otro problema, o antes de insertar una prioridad no finita. Conserva
    estados y problema sin modificaciones. Las mejoras estrictas de g se reinsertan y las entradas obsoletas se
    descartan por su g. Las evaluaciones y extensiones diferidas de la estrategia ocurren durante la busqueda. La
    finitud no elimina el redondeo propio de ``float``.
    Complexity: O(E * (T_s + C_h) + (V + E) log E + d * U) temporal y O((V + E) * U + d + S_h) espacial en el
    peor caso, donde V son estados, E transiciones, T_s el costo de generar una transicion, C_h y S_h los costos de
    evaluar la heuristica elegida, U las unidades y d la profundidad. No incluye construir la estrategia externa.
    AI usage: Yes.
    AI intervention: Codex implemento A*, la prioridad f, la gestion de mejoras y obsoletos, su instrumentacion y
    las guardas de finitud para E6.1; en E6.2 agrego la inyeccion opcional y la validacion de identidad.
    Student validation: pendiente de revision humana del equipo.
    """
    if heuristica_preparada is not None and heuristica_preparada.problema is not problema:
        raise ValueError(
            "La heuristica preparada pertenece a otro ProblemaNavegacion; "
            "construya una estrategia para la misma instancia recibida por A*."
        )

    medidor = MedidorBusqueda("A_ESTRELLA")
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
