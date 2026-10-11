"""Busqueda en profundidad sobre el contrato comun de problemas."""

from tacticalgrid.juego.problema import Problema

from .instrumentacion import MedidorBusqueda, Nodo, expandir
from .resultado_busqueda import ResultadoBusqueda


def busqueda_profundidad(problema: Problema) -> ResultadoBusqueda:
    """Encuentra una solucion explorando primero la rama mas profunda mediante una frontera LIFO (pila).

    Proposito: explorar el espacio de estados en profundidad, sin priorizar por cantidad de movimientos ni por
    costo, y devolver el resultado con las metricas comunes de E4.1. Comparte con BFS (E4.2) la deteccion de
    estados repetidos, el momento de la prueba de objetivo y la convencion de conteo, de modo que la unica
    diferencia entre ambos es la disciplina de la frontera: pila en DFS, cola en BFS.
    Precondiciones: ``problema`` implementa el contrato ``Problema`` y sus estados son hashables.
    Postcondiciones: devuelve la primera solucion extraida de la pila, que no es necesariamente la mas corta
    ni la mas barata, o un resultado de fracaso cuando la pila se agota; termina siempre en espacios finitos
    porque cada ``EstadoJuego`` se incorpora a la frontera a lo sumo una vez. Explora primero el primer
    movimiento del orden de ``problema.acciones`` (los hijos se apilan en orden inverso), por lo que el
    resultado es determinista. No modifica los estados recibidos.
    Complejidad: O(V + E) temporal y O(V) espacial para busqueda en grafo, donde V son los estados alcanzables
    y E las transiciones. En el modelo clasico de arbol, con profundidad maxima m y ramificacion b, el tiempo
    es O(b^m) y la memoria de la pila O(b * m); esa cota no aplica aqui, porque al marcar estados al apilarlos
    la pila conserva hermanos pendientes y puede superar la frontera de BFS. Usa una pila explicita, sin
    recursion, para no depender del limite de recursion de Python en mapas grandes.
    Uso de IA: Si.
    Intervencion de IA: Claude (Opus 5.5) propuso la implementacion, sus pruebas y esta documentacion en E4.3,
    siguiendo la estructura de BFS de E4.2.
    Validacion del estudiante: Revisión aprobada gracias a las validaciones en
    tests/algoritmos/test_busqueda_profundidad.py, que incluye un caso calculado a mano en un mapa abierto
    de 3x3 (camino, contadores y maximo de frontera).
    """
    medidor = MedidorBusqueda("DFS")
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
