"""Beam Search (busqueda en haz) con ancho k configurable sobre problemas de navegacion.

Decisiones de diseno:

- La busqueda avanza por niveles. En cada nivel se expanden todos los nodos del haz, se reunen sus hijos como
  candidatos y solo se conservan los ``k`` mejores; el resto se descarta y no se recuerda.
- Los candidatos se ordenan por ``f(n) = g(n) + h(n)``, con la heuristica Manhattan de E6.1 por defecto. Los empates
  se resuelven por orden de generacion, por lo que el resultado es determinista.
- Un estado que ya entro en algun haz no vuelve a entrar (evita ciclos). Un estado descartado si puede volver a
  aparecer por otro camino en un nivel posterior.
- El objetivo se comprueba al formar cada haz: si alguno de sus nodos es objetivo, se devuelve el de menor ``f``.
- Metricas (convencion de E4.1): un estado es *generado* cuando entra en el haz, que es la frontera; los candidatos
  descartados por la poda del haz no cuentan. Por eso el maximo de frontera nunca supera ``k``.
- Beam Search no es completo ni optimo: con ``k`` pequeno puede descartar el camino que despues habria convenido y
  terminar sin solucion o con una mas costosa. Eso es justamente lo que se quiere observar con k = 1, 2, 4, 8.
- Casos extremos: con ``k = 1`` se comporta como una busqueda voraz que solo sigue al mejor candidato de cada nivel;
  con ``k`` mayor que cualquier nivel no se poda nada y se comporta como BFS (menor numero de movimientos), eligiendo
  entre los objetivos de ese nivel el de menor ``f``. Por eso aumentar ``k`` no siempre baja el costo: el ordenamiento
  por ``g + h`` solo decide que candidatos sobreviven dentro de cada nivel.
"""

from collections.abc import Callable, Mapping
from dataclasses import dataclass

from tacticalgrid.juego.estado import EstadoJuego
from tacticalgrid.juego.problema import ProblemaNavegacion

from .busqueda_a_estrella import heuristica_manhattan
from .instrumentacion import MedidorBusqueda, Nodo, es_valor_finito, expandir
from .resultado_busqueda import ResultadoBusqueda

Heuristica = Callable[[ProblemaNavegacion, EstadoJuego], int | float]

CLAVE_ANCHO_HAZ = "k"


@dataclass(frozen=True)
class NivelHaz:
    """Registro de un nivel de Beam Search: candidatos conservados y descartados, cada uno con su ``f = g + h``.

    Ambas tuplas estan ordenadas por ``f`` (y por orden de generacion en empates). El nivel 0 es el haz inicial,
    que solo contiene la raiz. Sirve para analizar en que nivel se pierde un camino (E7.2) y para visualizar la
    exploracion, sin que el algoritmo dependa de quien lo observa.
    """

    nivel: int
    conservados: tuple[tuple[int | float, Nodo], ...]
    descartados: tuple[tuple[int | float, Nodo], ...]


def validar_ancho_haz(k: object) -> int:
    """Comprueba que ``k`` sea un ancho de haz valido y lo devuelve.

    Purpose: rechazar con un mensaje claro cualquier ancho que no permita ejecutar Beam Search, tanto si llega
    como argumento como si se lee del escenario.
    Preconditions: ninguna; ``k`` puede tener cualquier tipo.
    Postconditions: devuelve ``k`` si es un entero (no booleano) mayor o igual que 1; en otro caso lanza
    ``ValueError`` indicando el valor recibido.
    Complexity: O(1) temporal y espacial.
    AI usage: Yes.
    AI intervention: Claude (Opus 5.5) propuso la implementacion y su documentacion en E7.1.
    Student validation: el estudiante reviso y valido el codigo; ademas, las pruebas de
    tests/algoritmos/test_busqueda_haz.py comprueban que se rechazan 0, negativos, booleanos, decimales y textos.
    """
    if isinstance(k, bool) or not isinstance(k, int) or k < 1:
        raise ValueError(f"El ancho del haz k debe ser un entero mayor o igual que 1 y se recibio {k!r}.")
    return k


def ancho_haz_desde_prueba(configuracion_prueba: Mapping[str, object] | None) -> int | None:
    """Lee el ancho ``k`` opcional del campo ``prueba`` de un escenario ya cargado.

    Purpose: permitir cambiar ``k`` editando el JSON del escenario (``"prueba": {"k": 4, ...}``), sin modificar
    codigo. La capa de algoritmos no abre archivos: recibe la configuracion ya cargada por la capa de escenario.
    Preconditions: ``configuracion_prueba`` es ``Escenario.configuracion_prueba`` (un mapeo o ``None``).
    Postconditions: devuelve ``None`` si no hay configuracion o si no declara ``k``; devuelve ``k`` si es valido;
    lanza ``ValueError`` (ver :func:`validar_ancho_haz`) si ``k`` esta declarado con un valor invalido.
    Complexity: O(1) temporal y espacial.
    AI usage: Yes.
    AI intervention: Claude (Opus 5.5) propuso la implementacion, el nombre del campo propio ``k`` y su
    documentacion en E7.1.
    Student validation: el estudiante reviso y valido el codigo; ademas, las pruebas de
    tests/algoritmos/test_busqueda_haz.py cargan escenarios con y sin ``k`` y comprueban que cambiar ``k`` en el
    JSON cambia la exploracion.
    """
    if configuracion_prueba is None or CLAVE_ANCHO_HAZ not in configuracion_prueba:
        return None
    return validar_ancho_haz(configuracion_prueba[CLAVE_ANCHO_HAZ])


def _evaluar(problema: ProblemaNavegacion, nodo: Nodo, heuristica: Heuristica) -> int | float:
    """Calcula ``f(n) = g(n) + h(n)`` para ordenar candidatos y rechaza resultados no finitos.

    Purpose: dar a todos los candidatos de un nivel un criterio de comparacion que combina el costo ya pagado
    (leido del JSON a traves de ``expandir``) y la estimacion del costo restante.
    Preconditions: ``nodo.costo_acumulado`` es finito y ``heuristica`` devuelve un numero para ``nodo.estado``.
    Postconditions: devuelve la evaluacion finita del nodo o lanza ``ValueError`` si la heuristica o la suma no
    son finitas; no modifica el nodo ni el problema.
    Complexity: O(H) temporal, donde H es el costo de la heuristica (O(U) para Manhattan), y O(1) espacial.
    AI usage: Yes.
    AI intervention: Claude (Opus 5.5) la implemento en E7.1 siguiendo las guardas de finitud que Codex introdujo
    en A* (E6.1).
    Student validation: el estudiante reviso y valido el codigo; ademas, lo cubren las pruebas de
    tests/algoritmos/test_busqueda_haz.py, incluida la que usa una heuristica que devuelve infinito.
    """
    estimacion = heuristica(problema, nodo.estado)
    if not es_valor_finito(estimacion):
        raise ValueError("La heuristica de Beam Search devolvio un valor no finito.")
    try:
        evaluacion = nodo.costo_acumulado + estimacion
    except OverflowError as error:
        raise ValueError("La evaluacion f(n) de Beam Search excede el rango numerico finito soportado.") from error
    if not es_valor_finito(evaluacion):
        raise ValueError("La evaluacion f(n) de Beam Search excede el rango numerico finito soportado.")
    return evaluacion


def busqueda_haz(
    problema: ProblemaNavegacion,
    k: int,
    heuristica: Heuristica = heuristica_manhattan,
    observador: Callable[["NivelHaz"], None] | None = None,
) -> ResultadoBusqueda:
    """Busca una solucion conservando en cada nivel solo los ``k`` candidatos de menor ``g + h``.

    Purpose: implementar Beam Search con memoria limitada para estudiar como el ancho ``k`` cambia la exploracion
    y la solucion, reportando las metricas comunes de E4.1.
    Preconditions: ``k`` es un entero mayor o igual que 1 (si no, ``ValueError``); ``problema`` cumple las
    precondiciones de ``heuristica`` (por defecto, las de :func:`heuristica_manhattan`); sus estados son hashables
    y sus costos de transicion son positivos y finitos.
    Postconditions: devuelve el primer nodo objetivo que entra en un haz (el de menor ``f`` si hay varios) o un
    resultado de fracaso si el haz queda vacio. El algoritmo del resultado es ``BEAM_SEARCH_K<k>``. Cada haz tiene
    a lo sumo ``k`` nodos, ningun estado entra dos veces en un haz y el maximo de frontera es menor o igual que
    ``k``. No garantiza costo minimo ni encontrar solucion cuando existe; si ``k`` supera el tamano de todos los
    niveles, la solucion tiene el minimo numero de movimientos, como BFS. No modifica el problema. Si se pasa
    ``observador``, se le entrega un :class:`NivelHaz` por el haz inicial y por cada nivel formado, en orden, sin
    alterar el resultado ni las metricas.
    Complexity: con profundidad de exploracion d, factor de ramificacion b y U unidades por estado, cada nivel
    expande a lo sumo k nodos y evalua a lo sumo k * b candidatos: O(d * k * b * (T + U + log(k * b))) temporal,
    donde T es el costo de una transicion, y O(k * b + V_h + d) espacial, donde V_h son los estados que entraron
    en algun haz (conjunto de visitados) y d la longitud del camino reconstruido.
    AI usage: Yes.
    AI intervention: Claude (Opus 5.5) propuso el diseno por niveles, el criterio f = g + h, la convencion de
    metricas para el haz, la implementacion y esta documentacion en E7.1, y agrego en E7.2 el ``observador``
    opcional que permite analizar que candidatos conserva y descarta cada nivel.
    Student validation: el estudiante reviso y valido el codigo; ademas, las pruebas de
    tests/algoritmos/test_busqueda_haz.py ejecutan k = 1, 2, 4 y 8 sobre los escenarios del repositorio y
    verifican la legalidad y el costo de cada solucion, el limite del haz, el caso sin solucion y la coincidencia
    con la longitud de BFS cuando k es suficientemente grande.
    """
    k = validar_ancho_haz(k)
    medidor = MedidorBusqueda(f"BEAM_SEARCH_K{k}")
    raiz = Nodo(problema.estado_inicial)
    haz = [(_evaluar(problema, raiz, heuristica), raiz)]
    en_algun_haz = {raiz.estado}
    nivel = 0
    medidor.registrar_generado()
    medidor.observar_frontera(len(haz))
    if observador is not None:
        observador(NivelHaz(nivel=nivel, conservados=tuple(haz), descartados=()))

    while haz:
        objetivos = [(evaluacion, nodo) for evaluacion, nodo in haz if problema.es_objetivo(nodo.estado)]
        if objetivos:
            return medidor.finalizar(problema, objetivos[0][1])

        # Candidatos del siguiente nivel, sin repetir estado: si dos caminos llegan al mismo estado se conserva
        # el de menor f (y, en empate, el generado primero).
        candidatos: dict[EstadoJuego, tuple[int | float, int, Nodo]] = {}
        orden = 0
        for _, nodo in haz:
            for hijo in expandir(problema, nodo, medidor):
                if hijo.estado in en_algun_haz:
                    continue
                evaluacion = _evaluar(problema, hijo, heuristica)
                anterior = candidatos.get(hijo.estado)
                if anterior is None or evaluacion < anterior[0]:
                    candidatos[hijo.estado] = (evaluacion, orden, hijo)
                orden += 1

        ordenados = sorted(candidatos.values(), key=lambda candidato: (candidato[0], candidato[1]))
        haz = [(evaluacion, hijo) for evaluacion, _, hijo in ordenados[:k]]
        en_algun_haz.update(hijo.estado for _, hijo in haz)
        medidor.registrar_generado(len(haz))
        medidor.observar_frontera(len(haz))
        nivel += 1
        if observador is not None:
            observador(
                NivelHaz(
                    nivel=nivel,
                    conservados=tuple(haz),
                    descartados=tuple((evaluacion, hijo) for evaluacion, _, hijo in ordenados[k:]),
                )
            )

    return medidor.finalizar(problema, None)
