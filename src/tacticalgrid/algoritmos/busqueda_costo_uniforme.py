"""Búsqueda de costo uniforme sobre el contrato común de problemas."""

import heapq
from itertools import count

from tacticalgrid.juego.estado import EstadoJuego
from tacticalgrid.juego.problema import Problema

from .instrumentacion import MedidorBusqueda, Nodo, ObservadorExpansiones, expandir
from .resultado_busqueda import ResultadoBusqueda


def busqueda_costo_uniforme(
    problema: Problema,
    observador_expansiones: ObservadorExpansiones | None = None,
) -> ResultadoBusqueda:
    """Encontrar una solución de costo acumulado mínimo mediante una cola de prioridad.

    Proposito: expandir primero el nodo vigente con menor costo acumulado y devolver una solución óptima para costos
    de transición positivos, con las métricas comunes de E4.1.
    Precondiciones: ``problema`` implementa el contrato ``Problema``; sus estados son hashables y sus costos de
    transición son positivos.
    Postcondiciones: se devuelve la solución de costo acumulado mínimo, o un resultado de fracaso si la frontera se
    agota; la expansión común lanza ``ValueError`` antes de propagar un costo acumulado no finito. El problema y sus
    estados no cambian. Una mejora estricta se reinserta y cuenta como estado generado; una entrada obsoleta se
    descarta sin comprobar el objetivo ni contar una expansión. La guarda de finitud no elimina el redondeo propio de
    ``float``. El observador opcional recibe solo expansiones vigentes, nunca entradas obsoletas, y no altera las
    prioridades.
    Complejidad: O(E * U log U + (V + E) log E + d * U) temporal y O((V + E) * U + d) espacial en el peor caso, con V
    estados alcanzables, E transiciones examinadas, U unidades por ``EstadoJuego`` y d la profundidad de la solución.
    Además de las operaciones de la cola, cada transición reconstruye y canoniza un ``EstadoJuego`` en O(U log U), su
    uso en conjuntos o diccionarios calcula un hash O(U) y la reconstrucción final consulta la posición en cada estado
    en O(d * U). La traza agrega O(X_t). La frontera puede conservar reinserciones y entradas obsoletas.
    Uso de IA: Si.
    Intervencion de IA: Codex: implementación de UCS, gestión de mejoras y entradas obsoletas e integración con E4.1;
    documentación del fallo controlado ante costos no finitos (E6.1); observador opcional (E9.3).
    Validacion del estudiante: pruebas de tests/algoritmos/test_busqueda_costo_uniforme.py: ruta económica frente a
    la ruta corta de BFS (caso mínimo 2), cambio de ruta al modificar un costo del JSON, rodeo de obstáculos, mejora y
    descarte de entradas obsoletas, costos decimales y objetivo inalcanzable sin modificar el estado.
    """
    medidor = MedidorBusqueda("UCS", observador_expansiones=observador_expansiones)
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
