"""Beam Search (búsqueda en haz) con ancho k configurable sobre problemas de navegación.

Decisiones de diseño:

- La búsqueda avanza por niveles. En cada nivel se expanden todos los nodos del haz, se reúnen sus hijos como
  candidatos y solo se conservan los ``k`` mejores; el resto se descarta y no se recuerda.
- Los candidatos se ordenan por ``f(n) = g(n) + h(n)``, con la heurística Manhattan de E6.1 por defecto. Los empates
  se resuelven por orden de generación, de modo que el resultado es determinista.
- Un estado que ya entró en algún haz no vuelve a entrar, lo que evita ciclos. Un estado descartado sí puede
  reaparecer por otro camino en un nivel posterior.
- El objetivo se comprueba al formar cada haz: si alguno de sus nodos es objetivo, se devuelve el de menor ``f``.
- Métricas (convención de E4.1): un estado es *generado* cuando entra en el haz, que actúa como frontera; los
  candidatos descartados por la poda no cuentan. Por eso el máximo de frontera nunca supera ``k``.
- Beam Search no es completo ni óptimo: con ``k`` pequeño puede descartar el camino que después habría convenido y
  terminar sin solución o con una más costosa. Ese efecto es el que se observa con k = 1, 2, 4, 8.
- Casos extremos: con ``k = 1`` equivale a una búsqueda voraz que solo sigue al mejor candidato de cada nivel; con
  ``k`` mayor que cualquier nivel no se poda nada y equivale a BFS (menor número de movimientos), eligiendo entre los
  objetivos de ese nivel el de menor ``f``. Por eso aumentar ``k`` no siempre reduce el costo: el ordenamiento por
  ``g + h`` solo decide qué candidatos sobreviven dentro de cada nivel.
"""

from collections.abc import Callable, Mapping
from dataclasses import dataclass

from tacticalgrid.juego.estado import EstadoJuego
from tacticalgrid.juego.problema import ProblemaNavegacion

from .busqueda_a_estrella import heuristica_manhattan
from .instrumentacion import MedidorBusqueda, Nodo, ObservadorExpansiones, es_valor_finito, expandir
from .resultado_busqueda import ResultadoBusqueda

Heuristica = Callable[[ProblemaNavegacion, EstadoJuego], int | float]

CLAVE_ANCHO_HAZ = "k"


@dataclass(frozen=True)
class NivelHaz:
    """Registro de un nivel de Beam Search: candidatos conservados y descartados, cada uno con su ``f = g + h``.

    Ambas tuplas están ordenadas por ``f`` y, en empates, por orden de generación. El nivel 0 es el haz inicial, que
    solo contiene la raíz. Permite identificar en qué nivel se pierde un camino (E7.2) y visualizar la exploración sin
    que el algoritmo dependa de quien lo observa.
    """

    nivel: int
    conservados: tuple[tuple[int | float, Nodo], ...]
    descartados: tuple[tuple[int | float, Nodo], ...]


def validar_ancho_haz(k: object) -> int:
    """Comprobar que ``k`` sea un ancho de haz válido y devolverlo.

    Proposito: rechazar con un mensaje claro cualquier ancho que no permita ejecutar Beam Search, tanto si llega como
    argumento como si se lee del escenario.
    Precondiciones: ninguna; ``k`` puede tener cualquier tipo.
    Postcondiciones: se devuelve ``k`` si es un entero (no booleano) mayor o igual que 1; en otro caso se lanza
    ``ValueError`` con el valor recibido.
    Complejidad: O(1) temporal y espacial.
    Uso de IA: Si.
    Intervencion de IA: Claude (Opus 5.5): implementación y documentación (E7.1).
    Validacion del estudiante: prueba ``test_k_invalido_se_rechaza_con_mensaje_claro`` de
    tests/algoritmos/test_busqueda_haz.py: rechazo de 0, negativos, booleanos, decimales y textos.
    """
    if isinstance(k, bool) or not isinstance(k, int) or k < 1:
        raise ValueError(f"El ancho del haz k debe ser un entero mayor o igual que 1 y se recibio {k!r}.")
    return k


def ancho_haz_desde_prueba(configuracion_prueba: Mapping[str, object] | None) -> int | None:
    """Leer el ancho ``k`` opcional del campo ``prueba`` de un escenario ya cargado.

    Proposito: permitir cambiar ``k`` editando el JSON del escenario (``"prueba": {"k": 4, ...}``), sin modificar
    código. La capa de algoritmos no abre archivos: recibe la configuración ya cargada por la capa de escenario.
    Precondiciones: ``configuracion_prueba`` es ``Escenario.configuracion_prueba`` (un mapeo o ``None``).
    Postcondiciones: se devuelve ``None`` si no hay configuración o si no declara ``k``, y ``k`` si es válido; se lanza
    ``ValueError`` (ver :func:`validar_ancho_haz`) si ``k`` está declarado con un valor inválido.
    Complejidad: O(1) temporal y espacial.
    Uso de IA: Si.
    Intervencion de IA: Claude (Opus 5.5): implementación, nombre del campo propio ``k`` y documentación (E7.1).
    Validacion del estudiante: pruebas de tests/algoritmos/test_busqueda_haz.py: lectura de ``k`` desde el JSON,
    ``None`` sin ``k``, rechazo de un ``k`` inválido y cambio de la exploración al modificar ``k`` en el JSON.
    """
    if configuracion_prueba is None or CLAVE_ANCHO_HAZ not in configuracion_prueba:
        return None
    return validar_ancho_haz(configuracion_prueba[CLAVE_ANCHO_HAZ])


def _evaluar(problema: ProblemaNavegacion, nodo: Nodo, heuristica: Heuristica) -> int | float:
    """Calcular ``f(n) = g(n) + h(n)`` para ordenar candidatos y rechazar resultados no finitos.

    Proposito: dar a todos los candidatos de un nivel un criterio de comparación que combina el costo ya pagado (leído
    del JSON a través de ``expandir``) y la estimación del costo restante.
    Precondiciones: ``nodo.costo_acumulado`` es finito y ``heuristica`` devuelve un número para ``nodo.estado``.
    Postcondiciones: se devuelve la evaluación finita del nodo, o se lanza ``ValueError`` si la heurística o la suma no
    son finitas; el nodo y el problema no cambian.
    Complejidad: O(H) temporal, con H el costo de la heurística (O(U) para Manhattan), y O(1) espacial.
    Uso de IA: Si.
    Intervencion de IA: Claude (Opus 5.5): implementación con las guardas de finitud que Codex introdujo en A* (E7.1).
    Validacion del estudiante: prueba ``test_heuristica_no_finita_se_rechaza`` de tests/algoritmos/test_busqueda_haz.py.
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
    observador_expansiones: ObservadorExpansiones | None = None,
) -> ResultadoBusqueda:
    """Buscar una solución conservando en cada nivel solo los ``k`` candidatos de menor ``g + h``.

    Proposito: implementar Beam Search con memoria limitada para estudiar cómo el ancho ``k`` cambia la exploración y la
    solución, con las métricas comunes de E4.1.
    Precondiciones: ``k`` es un entero mayor o igual que 1 (si no, ``ValueError``); ``problema`` cumple las
    precondiciones de ``heuristica`` (por defecto, las de :func:`heuristica_manhattan`); sus estados son hashables y
    sus costos de transición son positivos y finitos.
    Postcondiciones: se devuelve el primer nodo objetivo que entra en un haz (el de menor ``f`` si hay varios), o un
    resultado de fracaso si el haz queda vacío. El algoritmo del resultado es ``BEAM_SEARCH_K<k>``. Cada haz tiene a lo
    sumo ``k`` nodos, ningún estado entra dos veces en un haz y el máximo de frontera es menor o igual que ``k``. No se
    garantiza costo mínimo ni encontrar solución cuando existe; si ``k`` supera el tamaño de todos los niveles, la
    solución tiene el mínimo número de movimientos, como BFS. El problema no cambia. ``observador`` recibe un
    :class:`NivelHaz` por el haz inicial y por cada nivel formado, en orden, sin alterar el resultado ni las métricas.
    ``observador_expansiones`` recibe cada nodo del haz cuyos sucesores se analizan y es independiente del observador
    de niveles.
    Complejidad: con profundidad de exploración d, factor de ramificación b y U unidades por estado, cada nivel expande
    a lo sumo k nodos y evalúa a lo sumo k * b candidatos: O(d * k * b * (T + U + log(k * b))) temporal, con T el costo
    de una transición, y O(k * b + V_h + d) espacial, con V_h los estados que entraron en algún haz (conjunto de
    visitados) y d la longitud del camino; la traza agrega O(X_t).
    Uso de IA: Si.
    Intervencion de IA: Claude (Opus 5.5): diseño por niveles, criterio f = g + h, convención de métricas para el haz,
    implementación y documentación (E7.1); ``observador`` de niveles (E7.2). Codex: observador común de expansiones
    (E9.3).
    Validacion del estudiante: pruebas de tests/algoritmos/test_busqueda_haz.py: k = 1, 2, 4 y 8 reproducibles, haz
    estrecho que descarta la solución, aumento de k sin reducción de costo, longitud de BFS sin poda, objetivo
    inalcanzable y observador de niveles sin alterar el resultado; caso mínimo 5 en
    tests/algoritmos/test_caso_minimo_5.py.
    """
    k = validar_ancho_haz(k)
    medidor = MedidorBusqueda(f"BEAM_SEARCH_K{k}", observador_expansiones=observador_expansiones)
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

        # Candidatos del siguiente nivel, sin repetir estado: si dos caminos llegan al mismo estado, se conserva
        # el de menor f y, en empate, el generado primero.
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
