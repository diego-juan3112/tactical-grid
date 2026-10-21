"""Búsqueda en profundidad sobre el contrato común de problemas."""

from tacticalgrid.juego.problema import Problema

from .instrumentacion import MedidorBusqueda, Nodo, ObservadorExpansiones, expandir
from .resultado_busqueda import ResultadoBusqueda


def busqueda_profundidad(
    problema: Problema,
    observador_expansiones: ObservadorExpansiones | None = None,
) -> ResultadoBusqueda:
    """Encontrar una solución explorando primero la rama más profunda mediante una frontera LIFO (pila).

    Proposito: explorar el espacio de estados en profundidad, sin priorizar por cantidad de movimientos ni por costo,
    y devolver el resultado con las métricas comunes de E4.1. Comparte con BFS (E4.2) la detección de estados
    repetidos, el momento de la prueba de objetivo y la convención de conteo, de modo que la única diferencia entre
    ambos es la disciplina de la frontera: pila en DFS y cola en BFS.
    Precondiciones: ``problema`` implementa el contrato ``Problema`` y sus estados son hashables.
    Postcondiciones: se devuelve la primera solución extraída de la pila, que no es necesariamente la más corta ni la
    más barata, o un resultado de fracaso cuando la pila se agota. La búsqueda termina siempre en espacios finitos,
    porque cada ``EstadoJuego`` entra en la frontera a lo sumo una vez. Se explora primero el primer movimiento del
    orden de ``problema.acciones`` (los hijos se apilan en orden inverso), por lo que el resultado es determinista. Los
    estados recibidos no cambian; el observador opcional recibe solo expansiones reales y no altera el resultado.
    Complejidad: O(V + E) temporal y O(V) espacial en búsqueda en grafo, con V estados alcanzables y E transiciones.
    En el modelo clásico de árbol, con profundidad máxima m y ramificación b, el tiempo es O(b^m) y la memoria de la
    pila O(b * m); esa cota no aplica aquí, porque al marcar los estados al apilarlos la pila conserva hermanos
    pendientes y puede superar la frontera de BFS. La pila es explícita, sin recursión, para no depender del límite de
    recursión de Python en mapas grandes; la traza agrega O(X_t) de memoria.
    Uso de IA: Si.
    Intervencion de IA: Claude (Opus 5.5): implementación, pruebas y documentación con la estructura de BFS de E4.2
    (E4.3). Codex: observador opcional (E9.3).
    Validacion del estudiante: pruebas de tests/algoritmos/test_busqueda_profundidad.py, con un caso calculado a mano
    en un mapa abierto de 3x3 (camino, contadores y máximo de frontera), rodeo de obstáculos y agotamiento de la
    frontera ante un objetivo inalcanzable.
    """
    medidor = MedidorBusqueda("DFS", observador_expansiones=observador_expansiones)
    raiz = Nodo(problema.estado_inicial)
    pila = [raiz]
    descubiertos = {raiz.estado}
    medidor.registrar_generado()
    medidor.observar_frontera(len(pila))

    while pila:
        nodo = pila.pop()
        if problema.es_objetivo(nodo.estado):
            return medidor.finalizar(problema, nodo)

        for hijo in reversed(expandir(problema, nodo, medidor)):
            if hijo.estado in descubiertos:
                continue
            descubiertos.add(hijo.estado)
            pila.append(hijo)
            medidor.registrar_generado()
        medidor.observar_frontera(len(pila))

    return medidor.finalizar(problema, None)
