"""Instrumentación común para BFS, DFS, UCS, A* y Beam Search: nodos, expansión y métricas.

Convención de conteo, igual para todos los algoritmos según el enunciado:

- **Estado generado:** estado incorporado a la búsqueda, es decir, agregado a la frontera. El estado inicial cuenta
  como generado. Un sucesor descartado (por ejemplo, porque ya fue visitado) no cuenta.
- **Estado expandido:** estado cuyos sucesores fueron analizados (cada llamada a :func:`expandir`).
- **Máximo de frontera:** mayor tamaño de la frontera observado con :meth:`MedidorBusqueda.observar_frontera`.
- **Tiempo:** segundos transcurridos entre la creación del medidor y :meth:`MedidorBusqueda.finalizar`.

Uso dentro de un algoritmo::

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

import math
import time
from collections.abc import Callable
from dataclasses import dataclass

from tacticalgrid.escenario.escenario import Posicion
from tacticalgrid.juego.accion import Accion
from tacticalgrid.juego.estado import EstadoJuego
from tacticalgrid.juego.problema import Problema

from .resultado_busqueda import ResultadoBusqueda


@dataclass(frozen=True, eq=False)
class Nodo:
    """Nodo del árbol de búsqueda: estado, nodo padre, acción que lo produjo, costo acumulado y profundidad.

    La igualdad es por identidad: dos nodos distintos pueden contener el mismo estado (por ejemplo, en DFS o cuando UCS
    encuentra un camino mejor), y cada algoritmo decide cómo detectar estados repetidos.
    """

    estado: EstadoJuego
    padre: "Nodo | None" = None
    accion: Accion | None = None
    costo_acumulado: int | float = 0
    profundidad: int = 0

    def ruta(self) -> tuple["Nodo", ...]:
        """Devolver los nodos desde la raíz hasta este nodo, en orden y sin recursión.

        Proposito: reconstruir la solución siguiendo los enlaces ``padre`` sin riesgo de exceder el límite de recursión
        en caminos largos.
        Precondiciones: la cadena de padres es finita; se construye siempre hacia adelante con :func:`expandir`.
        Postcondiciones: el primer elemento es la raíz y el último es ``self``; ningún nodo cambia.
        Complejidad: O(d) temporal y espacial, con d la profundidad del nodo.
        Uso de IA: Si.
        Intervencion de IA: Claude (Opus 5.5): implementación y documentación (E4.1).
        Validacion del estudiante: prueba ``test_nodo_ruta_va_de_la_raiz_al_nodo`` de
        tests/algoritmos/test_instrumentacion.py.
        """
        nodos = []
        actual: Nodo | None = self
        while actual is not None:
            nodos.append(actual)
            actual = actual.padre
        return tuple(reversed(nodos))


@dataclass(frozen=True)
class EventoExpansion:
    """Estado completo y proyección espacial de una expansión real, en su orden de observación."""

    orden: int
    estado: EstadoJuego
    posicion: Posicion


@dataclass(frozen=True)
class TrazaExpansiones:
    """Instantánea inmutable de los eventos almacenados y del alcance real de la traza."""

    eventos: tuple[EventoExpansion, ...]
    total_expansiones: int
    limite: int
    truncada: bool

    @property
    def posiciones_unicas(self) -> tuple[Posicion, ...]:
        """Proyectar los eventos guardados a posiciones únicas conservando el primer orden observado.

        Proposito: ofrecer al renderizador una vista espacial sin tratar como equivalentes la posición y el estado.
        Precondiciones: los eventos conservan el orden asignado por el observador.
        Postcondiciones: se devuelve cada posición una vez; los eventos originales no cambian ni se descartan.
        Complejidad: O(X_t) temporal y espacial para X_t eventos almacenados.
        Uso de IA: Si.
        Intervencion de IA: Codex: proyección estable (E9.3).
        Validacion del estudiante: prueba ``test_observador_registra_expansion_real_en_orden_y_con_identidad_completa``
        de tests/algoritmos/test_instrumentacion.py, con estados distintos en una misma celda.
        """
        return tuple(dict.fromkeys(evento.posicion for evento in self.eventos))


class ObservadorExpansiones:
    """Captura opcional y acotada de los estados realmente expandidos."""

    def __init__(self, limite: int = 10_000) -> None:
        """Configurar el máximo de eventos conservados.

        Proposito: limitar la memoria dedicada a la visualización sin alterar el total real de expansiones.
        Precondiciones: ``limite`` es un entero mayor o igual que cero.
        Postcondiciones: el observador queda vacío; un límite cero registra solo el total y el truncamiento.
        Complejidad: O(1) temporal y espacial.
        Uso de IA: Si.
        Intervencion de IA: Codex: diseño e implementación de la captura acotada (E9.3).
        Validacion del estudiante: pruebas de tests/algoritmos/test_instrumentacion.py: traza parcial con límite sin
        pérdida del total y traza vacía con observador activo.
        """
        if type(limite) is not int or limite < 0:
            raise ValueError("El limite de la traza debe ser un entero mayor o igual que cero.")
        self._limite = limite
        self._eventos: list[EventoExpansion] = []
        self._total = 0

    def observar(self, estado: EstadoJuego, posicion: Posicion) -> None:
        """Registrar una expansión sin modificar el estado observado.

        Proposito: conservar la identidad compuesta, la posición y el orden de cada expansión hasta el límite
        configurado.
        Precondiciones: ``estado`` es el del nodo entregado a ``expandir`` y ``posicion`` es su proyección en el
        problema.
        Postcondiciones: el total aumenta siempre; el evento se almacena solo si queda capacidad.
        Complejidad: O(1) temporal y O(1) espacial por evento almacenado.
        Uso de IA: Si.
        Intervencion de IA: Codex: registro exacto en el punto común de expansión (E9.3).
        Validacion del estudiante: pruebas de tests/algoritmos/test_instrumentacion.py: identidad completa, orden de
        observación y truncamiento.
        """
        orden = self._total
        self._total += 1
        if len(self._eventos) < self._limite:
            self._eventos.append(EventoExpansion(orden, estado, posicion))

    def finalizar(self) -> TrazaExpansiones:
        """Construir la instantánea inmutable que consume el resultado.

        Proposito: separar la captura mutable de la traza pública e indicar si el límite omitió eventos.
        Precondiciones: las observaciones previas se registraron con ``observar``.
        Postcondiciones: se conservan el orden, el total y el límite; ``truncada`` es verdadera solo si faltan eventos.
        Complejidad: O(X_t) temporal y espacial para copiar X_t eventos almacenados.
        Uso de IA: Si.
        Intervencion de IA: Codex: cierre de la traza (E9.3).
        Validacion del estudiante: pruebas de tests/algoritmos/test_instrumentacion.py: trazas vacías, trazas limitadas
        y ausencia de traza sin observador.
        """
        return TrazaExpansiones(
            eventos=tuple(self._eventos),
            total_expansiones=self._total,
            limite=self._limite,
            truncada=self._total > len(self._eventos),
        )


def es_valor_finito(valor: object) -> bool:
    """Indicar si un valor puede usarse con seguridad en la aritmética de costos.

    Proposito: centralizar la comprobación numérica que impide propagar infinitos o NaN en las búsquedas.
    Precondiciones: ``valor`` es el resultado o un operando de una operación de costo.
    Postcondiciones: se devuelve ``True`` solo para enteros o flotantes no booleanos que ``math.isfinite`` confirma
    como finitos; cualquier tipo o magnitud no soportada devuelve ``False`` sin propagar excepciones.
    Complejidad: O(1) temporal y espacial.
    Uso de IA: Si.
    Intervencion de IA: Codex: guarda común durante el cierre del riesgo numérico de E6.1.
    Validacion del estudiante: pruebas de tests/algoritmos/test_busqueda_a_estrella.py y
    tests/algoritmos/test_busqueda_haz.py: rechazo de costos, heurísticas y prioridades no finitos.
    """
    if isinstance(valor, bool) or not isinstance(valor, (int, float)):
        return False
    try:
        return math.isfinite(valor)
    except (OverflowError, TypeError, ValueError):
        return False


def expandir(problema: Problema, nodo: Nodo, medidor: "MedidorBusqueda") -> tuple[Nodo, ...]:
    """Generar los nodos hijos de ``nodo`` y registrar una expansión en ``medidor``.

    Proposito: concentrar la generación de sucesores y el cálculo del costo acumulado que comparten todos los
    algoritmos de búsqueda.
    Precondiciones: ``nodo.estado`` es un estado válido de ``problema``.
    Postcondiciones: los estados expandidos aumentan en 1 y el observador opcional recibe el estado y su posición. Se
    devuelve un hijo por cada acción de ``problema.acciones``, en el mismo orden, con ``costo_acumulado`` igual al costo
    del padre más ``problema.costo`` (leído del escenario cargado) y profundidad + 1. Se lanza ``ValueError`` si la suma
    no es finita o excede el rango numérico soportado. Los estados generados no se registran aquí: cada algoritmo los
    cuenta al incorporar un hijo.
    Complejidad: O(b * T) temporal y O(b) espacial, con b el número de acciones y T el costo de una transición del
    problema.
    Uso de IA: Si.
    Intervencion de IA: Claude (Opus 5.5): implementación y documentación (E4.1). Codex: rechazo controlado de
    acumulaciones no finitas (E6.1).
    Validacion del estudiante: prueba ``test_expandir_genera_hijos_en_orden_con_costo_del_json_y_cuenta_una_expansion``
    de tests/algoritmos/test_instrumentacion.py y prueba de desbordamiento de la acumulación en
    tests/algoritmos/test_busqueda_a_estrella.py.
    """
    medidor.registrar_expandido(nodo.estado, problema.posicion(nodo.estado))
    hijos = []
    for accion in problema.acciones(nodo.estado):
        estado = problema.resultado(nodo.estado, accion)
        costo_paso = problema.costo(nodo.estado, accion)
        try:
            costo_acumulado = nodo.costo_acumulado + costo_paso
        except OverflowError as error:
            raise ValueError("El costo acumulado excede el rango numerico finito soportado.") from error
        if not es_valor_finito(costo_acumulado):
            raise ValueError("El costo acumulado excede el rango numerico finito soportado.")
        hijos.append(
            Nodo(
                estado=estado,
                padre=nodo,
                accion=accion,
                costo_acumulado=costo_acumulado,
                profundidad=nodo.profundidad + 1,
            )
        )
    return tuple(hijos)


class MedidorBusqueda:
    """Acumulador de las métricas de una ejecución que construye su :class:`ResultadoBusqueda`."""

    def __init__(
        self,
        algoritmo: str,
        reloj: Callable[[], float] = time.perf_counter,
        observador_expansiones: ObservadorExpansiones | None = None,
    ) -> None:
        """Preparar la medición de una búsqueda con el cronómetro en marcha y los contadores en cero.

        Proposito: que todos los algoritmos de búsqueda midan generados, expandidos, máximo de frontera y tiempo con la
        misma convención de E4.1.
        Precondiciones: ``algoritmo`` es el nombre con el que se reporta el resultado; ``reloj`` devuelve segundos
        crecientes (por defecto ``time.perf_counter``; las pruebas pueden fijarlo).
        Postcondiciones: el medidor queda con los tres contadores en 0, el instante de inicio tomado de ``reloj`` y, si
        se recibe, el observador de expansiones de E9.3, que no altera las métricas.
        Complejidad: O(1) temporal y espacial.
        Uso de IA: Si.
        Intervencion de IA: Claude (Opus 5.5): implementación (E4.1) y documentación (E11.1). Codex: observador de
        expansiones (E9.3).
        Validacion del estudiante: pruebas de tests/algoritmos/test_instrumentacion.py, que construyen medidores con un
        reloj fijo y con observador.
        """
        self.algoritmo = algoritmo
        self._reloj = reloj
        self._inicio = reloj()
        self.estados_generados = 0
        self.estados_expandidos = 0
        self.maximo_frontera = 0
        self._observador_expansiones = observador_expansiones

    def registrar_generado(self, cantidad: int = 1) -> None:
        """Contar ``cantidad`` estados incorporados a la frontera."""
        self.estados_generados += cantidad

    def registrar_expandido(self, estado: EstadoJuego, posicion: Posicion) -> None:
        """Contar un estado cuyos sucesores fueron analizados."""
        self.estados_expandidos += 1
        if self._observador_expansiones is not None:
            self._observador_expansiones.observar(estado, posicion)

    def observar_frontera(self, tamano: int) -> None:
        """Actualizar el máximo de frontera con el tamaño actual."""
        self.maximo_frontera = max(self.maximo_frontera, tamano)

    def finalizar(self, problema: Problema, nodo_objetivo: Nodo | None) -> ResultadoBusqueda:
        """Detener el cronómetro y construir el resultado común de la búsqueda.

        Proposito: producir para cualquier algoritmo la misma estructura de salida del enunciado.
        Precondiciones: ``nodo_objetivo`` es ``None`` si no hubo solución, o un nodo cuyo estado satisface
        ``problema.es_objetivo`` y cuya cadena de padres llega al estado inicial.
        Postcondiciones: con solución, ``camino`` contiene ``problema.posicion`` de cada estado desde el inicial hasta
        el objetivo, ``acciones`` las transiciones aplicadas y ``costo`` el costo acumulado del nodo; sin solución,
        ``exito`` es falso, el camino y las acciones quedan vacíos y ``costo`` es ``None``. En ambos casos se incluyen
        los contadores, el tiempo y la instantánea del observador opcional.
        Complejidad: O(d + X_t) temporal y espacial, con d la profundidad y X_t los eventos almacenados.
        Uso de IA: Si.
        Intervencion de IA: Claude (Opus 5.5): implementación (E4.1). Codex: traza opcional (E9.3).
        Validacion del estudiante: pruebas de tests/algoritmos/test_instrumentacion.py: resultado exitoso coherente con
        el problema, misma estructura para dos estrategias, objetivo en un muro sin solución e inicio que ya es
        objetivo.
        """
        tiempo = self._reloj() - self._inicio
        traza = self._observador_expansiones.finalizar() if self._observador_expansiones is not None else None
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
                traza_expansiones=traza,
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
            traza_expansiones=traza,
        )
