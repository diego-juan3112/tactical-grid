"""Instrumentacion comun para BFS, DFS, UCS, A* y Beam Search: nodos, expansion y metricas.

Convencion de conteo (igual para todos los algoritmos, segun el enunciado):

- **Estado generado:** estado incorporado a la busqueda, es decir, agregado a la frontera. El estado inicial cuenta
  como generado. Un sucesor descartado (por ejemplo, porque ya fue visitado) no cuenta.
- **Estado expandido:** estado cuyos sucesores fueron analizados (cada llamada a :func:`expandir`).
- **Maximo de frontera:** mayor tamano de la frontera observado con :meth:`MedidorBusqueda.observar_frontera`.
- **Tiempo:** segundos transcurridos entre la creacion del medidor y :meth:`MedidorBusqueda.finalizar`.

Uso tipico dentro de un algoritmo::

    medidor = MedidorBusqueda("BFS")
    raiz = Nodo(problema.estado_inicial)
    frontera = deque([raiz]); medidor.registrar_generado(); medidor.observar_frontera(len(frontera))
    while frontera:
        nodo = frontera.popleft()
        if problema.es_objetivo(nodo.estado):
            return medidor.finalizar(problema, nodo)
        for hijo in expandir(problema, nodo, medidor):
            ...  # si se incorpora: frontera.append(hijo); medidor.registrar_generado()
        medidor.observar_frontera(len(frontera))
    return medidor.finalizar(problema, None)
"""

import time
from collections.abc import Callable
from dataclasses import dataclass

from tacticalgrid.juego.accion import Accion
from tacticalgrid.juego.estado import EstadoJuego
from tacticalgrid.juego.problema import Problema

from .resultado_busqueda import ResultadoBusqueda


@dataclass(frozen=True, eq=False)
class Nodo:
    """Nodo del arbol de busqueda: estado, nodo padre, accion que lo produjo, costo acumulado y profundidad.

    La igualdad es por identidad: dos nodos distintos pueden contener el mismo estado (por ejemplo, en DFS o
    cuando UCS encuentra un camino mejor), y cada algoritmo decide como detectar estados repetidos.
    """

    estado: EstadoJuego
    padre: "Nodo | None" = None
    accion: Accion | None = None
    costo_acumulado: int | float = 0
    profundidad: int = 0

    def ruta(self) -> tuple["Nodo", ...]:
        """Devuelve los nodos desde la raiz hasta este nodo, en orden, sin recursion.

        Proposito: reconstruir la solucion siguiendo los enlaces ``padre`` sin riesgo de exceder el limite de
        recursion en caminos largos.
        Precondiciones: la cadena de padres es finita (se construye siempre hacia adelante con :func:`expandir`).
        Postcondiciones: el primer elemento es la raiz y el ultimo es ``self``; no modifica ningun nodo.
        Complejidad: O(d) temporal y espacial, donde d es la profundidad del nodo.
        Uso de IA: Si.
        Intervencion de IA: Claude (Opus 5.5) propuso la implementacion y su documentacion en E4.1.
        Validacion del estudiante: cubierto por las pruebas de tests/algoritmos/test_instrumentacion.py.
        """
        nodos = []
        actual: Nodo | None = self
        while actual is not None:
            nodos.append(actual)
            actual = actual.padre
        return tuple(reversed(nodos))


def expandir(problema: Problema, nodo: Nodo, medidor: "MedidorBusqueda") -> tuple[Nodo, ...]:
    """Genera los nodos hijos de ``nodo`` y registra una expansion en ``medidor``.

    Proposito: concentrar la generacion de sucesores y el calculo de costo acumulado que comparten todos los
    algoritmos de busqueda, para no duplicarlos.
    Precondiciones: ``nodo.estado`` es un estado valido de ``problema``.
    Postcondiciones: incrementa en 1 los estados expandidos; devuelve un hijo por cada accion de
    ``problema.acciones`` en el mismo orden, con ``costo_acumulado`` = costo del padre + ``problema.costo``
    (leido del escenario cargado) y profundidad + 1. No registra estados generados: cada algoritmo lo hace al
    incorporar un hijo a su frontera.
    Complejidad: O(b * T) temporal y O(b) espacial, donde b es el numero de acciones y T el costo de una
    transicion del problema.
    Uso de IA: Si.
    Intervencion de IA: Claude (Opus 5.5) propuso la implementacion y su documentacion en E4.1.
    Validacion del estudiante: cubierto por las pruebas de tests/algoritmos/test_instrumentacion.py, que
    comprueban orden de hijos, costo acumulado desde el JSON y conteo de expansiones.
    """
    medidor.registrar_expandido()
    return tuple(
        Nodo(
            estado=problema.resultado(nodo.estado, accion),
            padre=nodo,
            accion=accion,
            costo_acumulado=nodo.costo_acumulado + problema.costo(nodo.estado, accion),
            profundidad=nodo.profundidad + 1,
        )
        for accion in problema.acciones(nodo.estado)
    )


class MedidorBusqueda:
    """Acumula las metricas de una ejecucion y construye su :class:`ResultadoBusqueda`."""

    def __init__(self, algoritmo: str, reloj: Callable[[], float] = time.perf_counter) -> None:
        """Inicia el cronometro y los contadores en cero; ``reloj`` permite fijar el tiempo en las pruebas."""
        self.algoritmo = algoritmo
        self._reloj = reloj
        self._inicio = reloj()
        self.estados_generados = 0
        self.estados_expandidos = 0
        self.maximo_frontera = 0

    def registrar_generado(self, cantidad: int = 1) -> None:
        """Cuenta ``cantidad`` estados incorporados a la frontera."""
        self.estados_generados += cantidad

    def registrar_expandido(self) -> None:
        """Cuenta un estado cuyos sucesores fueron analizados."""
        self.estados_expandidos += 1

    def observar_frontera(self, tamano: int) -> None:
        """Actualiza el maximo de frontera con el tamano actual."""
        self.maximo_frontera = max(self.maximo_frontera, tamano)

    def finalizar(self, problema: Problema, nodo_objetivo: Nodo | None) -> ResultadoBusqueda:
        """Detiene el cronometro y construye el resultado comun de la busqueda.

        Proposito: producir para cualquier algoritmo la misma estructura de salida del enunciado.
        Precondiciones: ``nodo_objetivo`` es ``None`` si no hubo solucion, o un nodo cuyo estado satisface
        ``problema.es_objetivo`` y cuya cadena de padres llega al estado inicial.
        Postcondiciones: con solucion, ``camino`` contiene ``problema.posicion`` de cada estado desde el inicial
        hasta el objetivo, ``acciones`` las transiciones aplicadas y ``costo`` el costo acumulado del nodo; sin
        solucion, ``exito`` es falso, el camino y las acciones estan vacios y ``costo`` es ``None``. En ambos
        casos incluye los contadores y el tiempo transcurrido.
        Complejidad: O(d) temporal y espacial, donde d es la profundidad de la solucion.
        Uso de IA: Si.
        Intervencion de IA: Claude (Opus 5.5) propuso la implementacion y su documentacion en E4.1.
        Validacion del estudiante: cubierto por las pruebas de tests/algoritmos/test_instrumentacion.py, que
        ejecutan una busqueda de ejemplo sobre escenarios del repositorio y comprueban camino, costo y metricas.
        """
        tiempo = self._reloj() - self._inicio
        if nodo_objetivo is None:
            return ResultadoBusqueda(
                algoritmo=self.algoritmo,
                exito=False,
                camino=(),
                costo=None,
                estados_generados=self.estados_generados,
                estados_expandidos=self.estados_expandidos,
                maximo_frontera=self.maximo_frontera,
                tiempo_segundos=tiempo,
            )
        ruta = nodo_objetivo.ruta()
        return ResultadoBusqueda(
            algoritmo=self.algoritmo,
            exito=True,
            camino=tuple(problema.posicion(nodo.estado) for nodo in ruta),
            costo=nodo_objetivo.costo_acumulado,
            estados_generados=self.estados_generados,
            estados_expandidos=self.estados_expandidos,
            maximo_frontera=self.maximo_frontera,
            tiempo_segundos=tiempo,
            acciones=tuple(nodo.accion for nodo in ruta[1:] if nodo.accion is not None),
        )
