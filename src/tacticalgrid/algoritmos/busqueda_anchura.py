"""Busqueda en anchura sobre el contrato comun de problemas."""

from collections import deque

from tacticalgrid.juego.problema import Problema

from .instrumentacion import MedidorBusqueda, Nodo, expandir
from .resultado_busqueda import ResultadoBusqueda


def busqueda_anchura(problema: Problema) -> ResultadoBusqueda:
    """Encuentra una solucion con la menor cantidad de acciones mediante una frontera FIFO.

    Purpose: explorar por niveles los estados del problema, sin priorizar por costo, y devolver el resultado
    con las metricas comunes de E4.1.
    Preconditions: problema implementa el contrato Problema y sus estados son hashables.
    Postconditions: devuelve la primera solucion extraida de la frontera o un resultado de fracaso cuando esta
    se agota; no modifica los estados recibidos.
    Complexity: O(V + E) temporal y O(V) espacial para busqueda en grafo. En el modelo clasico de arbol de
    busqueda, la exploracion hasta profundidad d con factor de ramificacion b se caracteriza como O(b^d).
    AI usage: Yes.
    AI intervention: Codex implemento BFS, su integracion con E4.1, sus pruebas y esta documentacion.
    Student validation: Se revisó manualmente la implementación de BFS contra los criterios de aceptación de E4.2.
    Se verificó el uso de frontera FIFO, el marcado de estados al descubrirlos, la prevención de ciclos mediante
    el EstadoJuego completo, la comprobación del objetivo al extraer de la frontera, la reconstrucción del camino
    y las acciones, y la semántica de las métricas de E4.1. También se verificó que BFS priorice la cantidad de
    movimientos y no el costo del terreno, aunque el costo real del camino se reporte en ResultadoBusqueda. Se
    ejecutaron las pruebas específicas de BFS, las pruebas de algoritmos y la suite completa.
    """
    medidor = MedidorBusqueda("BFS")
    raiz = Nodo(problema.estado_inicial)
    frontera = deque([raiz])
    descubiertos = {raiz.estado}
    medidor.registrar_generado()
    medidor.observar_frontera(len(frontera))

    while frontera:
        nodo = frontera.popleft()
        if problema.es_objetivo(nodo.estado):
            return medidor.finalizar(problema, nodo)

        for hijo in expandir(problema, nodo, medidor):
            if hijo.estado in descubiertos:
                continue
            descubiertos.add(hijo.estado)
            frontera.append(hijo)
            medidor.registrar_generado()
        medidor.observar_frontera(len(frontera))

    return medidor.finalizar(problema, None)
