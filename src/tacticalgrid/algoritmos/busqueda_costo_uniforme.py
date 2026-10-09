"""Busqueda de costo uniforme sobre el contrato comun de problemas."""

import heapq
from itertools import count

from tacticalgrid.juego.estado import EstadoJuego
from tacticalgrid.juego.problema import Problema

from .instrumentacion import MedidorBusqueda, Nodo, expandir
from .resultado_busqueda import ResultadoBusqueda


def busqueda_costo_uniforme(problema: Problema) -> ResultadoBusqueda:
    """Encuentra una solucion de costo acumulado minimo mediante una cola de prioridad.

    Purpose: explorar primero el nodo vigente con menor costo acumulado y devolver una solucion optima para
    costos de transicion positivos, usando las metricas comunes de E4.1.
    Preconditions: problema implementa el contrato Problema; sus estados son hashables y sus costos de
    transicion son positivos.
    Postconditions: devuelve la solucion de costo acumulado minimo o un resultado de fracaso si la frontera se
    agota; conserva el problema y sus estados sin modificaciones. Una mejora estricta se inserta nuevamente y
    cuenta como estado generado; una entrada obsoleta conserva su lugar en el tamano fisico de la frontera hasta
    extraerse, pero se descarta sin comprobar objetivo ni contar una expansion.
    Complexity: O(E * U log U + (V + E) log E + d * U) temporal y O((V + E) * U + d) espacial en el peor
    caso, donde V son estados alcanzables, E transiciones examinadas, U unidades por EstadoJuego y d la
    profundidad de la solucion. Ademas de las operaciones de la cola, cada transicion reconstruye y canoniza
    un EstadoJuego en O(U log U), su procesamiento en conjuntos o diccionarios calcula un hash O(U), y la
    reconstruccion final consulta la posicion en cada uno de los d estados en O(d * U). La frontera puede
    conservar reinserciones y entradas obsoletas.
    AI usage: Yes.
    AI intervention: Codex implemento UCS, la gestion de mejoras y entradas obsoletas, su integracion con E4.1,
    las pruebas automatizadas y esta documentacion.
    Student validation: pendiente de revision del equipo; Codex ejecuto las pruebas automatizadas especificas y
    la suite del proyecto indicadas en la historia E5.1.
    """
    medidor = MedidorBusqueda("UCS")
    raiz = Nodo(problema.estado_inicial)
    desempate = count()
    frontera: list[tuple[int | float, int, Nodo]] = [(raiz.costo_acumulado, next(desempate), raiz)]
    mejores_costos: dict[EstadoJuego, int | float] = {raiz.estado: raiz.costo_acumulado}
    medidor.registrar_generado()
    medidor.observar_frontera(len(frontera))

    while frontera:
        costo_extraido, _, nodo = heapq.heappop(frontera)
        medidor.observar_frontera(len(frontera))
        if costo_extraido != mejores_costos[nodo.estado]:
            continue
        if problema.es_objetivo(nodo.estado):
            return medidor.finalizar(problema, nodo)

        for hijo in expandir(problema, nodo, medidor):
            mejor_anterior = mejores_costos.get(hijo.estado)
            if mejor_anterior is not None and hijo.costo_acumulado >= mejor_anterior:
                continue
            mejores_costos[hijo.estado] = hijo.costo_acumulado
            heapq.heappush(frontera, (hijo.costo_acumulado, next(desempate), hijo))
            medidor.registrar_generado()
            medidor.observar_frontera(len(frontera))

    return medidor.finalizar(problema, None)
