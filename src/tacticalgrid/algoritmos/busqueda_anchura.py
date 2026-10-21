"""Búsqueda en anchura sobre el contrato común de problemas."""

from collections import deque

from tacticalgrid.juego.problema import Problema

from .instrumentacion import MedidorBusqueda, Nodo, ObservadorExpansiones, expandir
from .resultado_busqueda import ResultadoBusqueda


def busqueda_anchura(
    problema: Problema,
    observador_expansiones: ObservadorExpansiones | None = None,
) -> ResultadoBusqueda:
    """Encontrar una solución con la menor cantidad de acciones mediante una frontera FIFO.

    Proposito: explorar por niveles los estados del problema, sin priorizar por costo, y devolver el resultado con las
    métricas comunes de E4.1.
    Precondiciones: ``problema`` implementa el contrato ``Problema`` y sus estados son hashables.
    Postcondiciones: se devuelve la primera solución extraída de la frontera, o un resultado de fracaso cuando la
    frontera se agota; los estados recibidos no cambian. Con un observador, se registran las mismas expansiones que
    cuenta la métrica, sin alterar la frontera, el camino ni los desempates.
    Complejidad: O(V + E) temporal y O(V + X_t) espacial en búsqueda en grafo, con X_t eventos almacenados. En el
    modelo clásico de árbol, explorar hasta la profundidad d con ramificación b cuesta O(b^d).
    Uso de IA: Si.
    Intervencion de IA: Codex: implementación de BFS (E4.2) e inyección opcional del observador (E9.3).
    Validacion del estudiante: pruebas de tests/algoritmos/test_busqueda_anchura.py: objetivo inicial sin expansión,
    reconstrucción de acciones y costo, preferencia por menos movimientos frente a una ruta larga más barata, rodeo de
    obstáculos, descarte de ciclos y ramas convergentes, y determinismo en otras dimensiones.
    """
    medidor = MedidorBusqueda("BFS", observador_expansiones=observador_expansiones)
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
