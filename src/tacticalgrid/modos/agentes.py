"""Partida por turnos entre algoritmos (E9.5): cada bando decide una jugada con su propio algoritmo.

Decisiones de diseño:

- Una llamada a :func:`decidir_jugada` produce una sola jugada del bando en turno sobre el estado vigente; quien la
  consume la aplica con ``aplicar_accion`` y prepara el turno siguiente. Así la partida avanza al ritmo del consumidor.
- Minimax y alfa-beta deciden igual que en el modo ``partida`` de la consola: el bando en turno es MAX y se usan la
  profundidad y el orden de acciones configurados.
- BFS, DFS, UCS, A* y Beam Search resuelven navegaciones de una unidad, así que se les asigna una meta táctica en cada
  turno y se aplica solo el primer paso del camino encontrado:

  1. Si una unidad del bando está junto al portador rival, lo intercepta.
  2. Si el bando lleva el recurso, el portador planea hacia su propia base.
  3. Si el recurso está libre, cada unidad que puede moverse planea hacia él y actúa la de camino de menor costo
     (empate por identificador).
  4. Si el rival lleva el recurso, las unidades planean hacia la celda del portador para alcanzarlo e interceptarlo.

- La planeación usa :class:`ProblemaNavegacionPartida`, que trata como obstáculos las celdas ocupadas, de modo que el
  primer paso es siempre legal. Si ninguna unidad encuentra camino, se aplica la primera acción legal en el orden de
  generación (meta ``respaldo``), que es determinista.
"""

from dataclasses import dataclass

from tacticalgrid.algoritmos.alfa_beta import alfa_beta
from tacticalgrid.algoritmos.busqueda_a_estrella import busqueda_a_estrella
from tacticalgrid.algoritmos.busqueda_anchura import busqueda_anchura
from tacticalgrid.algoritmos.busqueda_costo_uniforme import busqueda_costo_uniforme
from tacticalgrid.algoritmos.busqueda_haz import busqueda_haz, validar_ancho_haz
from tacticalgrid.algoritmos.busqueda_profundidad import busqueda_profundidad
from tacticalgrid.algoritmos.heuristica_obstaculos import HeuristicaObstaculos
from tacticalgrid.algoritmos.instrumentacion import ObservadorExpansiones
from tacticalgrid.algoritmos.minimax import ResultadoMinimax, minimax, validar_profundidad
from tacticalgrid.algoritmos.orden_acciones import ORDEN_GENERACION, validar_orden
from tacticalgrid.algoritmos.resultado_busqueda import ResultadoBusqueda
from tacticalgrid.escenario.escenario import Escenario, Posicion
from tacticalgrid.juego.accion import INTERCEPTAR, MOVER, Accion
from tacticalgrid.juego.estado import EstadoJuego
from tacticalgrid.juego.problema import ProblemaNavegacionPartida
from tacticalgrid.juego.reglas import acciones_validas, buscar_unidad, es_accion_valida, es_terminal

ALGORITMOS_BUSQUEDA_AGENTE = ("bfs", "dfs", "ucs", "astar", "beam")
ALGORITMOS_ADVERSARIALES_AGENTE = ("minimax", "alfa_beta")
ALGORITMOS_AGENTE = ALGORITMOS_BUSQUEDA_AGENTE + ALGORITMOS_ADVERSARIALES_AGENTE
HEURISTICAS_AGENTE = ("manhattan", "hto")
LIMITE_TRAZA_AGENTE = 10_000


@dataclass(frozen=True)
class ConfiguracionAgente:
    """Algoritmo de un bando y sus parámetros: profundidad y orden (adversariales), k (Beam) y heurística (A*)."""

    algoritmo: str
    profundidad: int = 1
    orden: str = ORDEN_GENERACION
    k: int = 4
    heuristica: str = "manhattan"

    def __post_init__(self) -> None:
        """Validar la configuración con los mismos validadores que usan los algoritmos.

        Proposito: rechazar al crearla cualquier configuración con la que un bando no podría decidir.
        Precondiciones: ninguna; los campos pueden tener cualquier valor.
        Postcondiciones: no hay efectos si el algoritmo pertenece a ``ALGORITMOS_AGENTE``, la profundidad es un entero
        mayor o igual que 1, el orden pertenece a ``ORDENES``, k es un ancho de haz válido y la heurística pertenece a
        ``HEURISTICAS_AGENTE``; en otro caso se lanza ``ValueError`` con el valor recibido.
        Complejidad: O(1) temporal y espacial.
        Uso de IA: Si.
        Intervencion de IA: Claude (Opus 5.5): implementación (E9.5).
        Validacion del estudiante: prueba ``test_configuracion_invalida_se_rechaza`` de tests/modos/test_agentes.py.
        """
        if self.algoritmo not in ALGORITMOS_AGENTE:
            raise ValueError(
                f"El algoritmo del bando debe ser uno de {list(ALGORITMOS_AGENTE)} y se recibio {self.algoritmo!r}."
            )
        validar_profundidad(self.profundidad)
        validar_orden(self.orden)
        validar_ancho_haz(self.k)
        if self.heuristica not in HEURISTICAS_AGENTE:
            raise ValueError(
                f"La heuristica debe ser una de {list(HEURISTICAS_AGENTE)} y se recibio {self.heuristica!r}."
            )


@dataclass(frozen=True)
class DecisionAgente:
    """Jugada decidida por el algoritmo de un bando, con la meta perseguida y el resultado que la justifica.

    ``meta`` vale ``interceptar``, ``base``, ``recurso``, ``portador`` o ``respaldo`` para los algoritmos de búsqueda,
    y ``minimax`` para Minimax y alfa-beta. ``busqueda`` contiene el camino planeado y sus métricas cuando la jugada
    proviene de una búsqueda; ``adversarial``, la decisión con sus métricas cuando proviene de Minimax o alfa-beta.
    """

    bando: str
    algoritmo: str
    accion: Accion
    meta: str
    objetivo: Posicion | None = None
    busqueda: ResultadoBusqueda | None = None
    adversarial: ResultadoMinimax | None = None


def decidir_jugada(escenario: Escenario, estado: EstadoJuego, configuracion: ConfiguracionAgente) -> DecisionAgente:
    """Decidir una jugada del bando en turno con el algoritmo configurado.

    Proposito: implementar la partida por turnos entre algoritmos, una jugada por llamada, para que cada bando pueda
    usar cualquiera de los algoritmos del proyecto.
    Precondiciones: ``estado`` es coherente con ``escenario`` y ya pasó por ``preparar_turno``; ``configuracion`` es
    válida.
    Postcondiciones: se devuelve una ``DecisionAgente`` cuya acción es legal en ``estado`` y pertenece al bando en
    turno; con los mismos datos la decisión es siempre la misma. Se lanza ``ValueError`` si el estado es terminal o si
    el bando en turno no tiene acciones. ``estado`` no cambia.
    Complejidad: para Minimax y alfa-beta, la de su búsqueda, O(b^d) en el peor caso; para los algoritmos de búsqueda,
    U_b ejecuciones del algoritmo, una por unidad candidata del bando, más O(A) para revisar las acciones legales.
    Uso de IA: Si.
    Intervencion de IA: Claude (Opus 5.5): diseño de las metas tácticas e implementación (E9.5).
    Validacion del estudiante: pruebas de tests/modos/test_agentes.py: paso hacia el recurso con cada algoritmo de
    búsqueda, unidad de menor costo, portador hacia su base, intercepción, persecución, respaldo sin camino, misma
    acción que Minimax y alfa-beta, jugadas legales sin modificar el estado y determinismo.
    """
    if es_terminal(escenario, estado):
        raise ValueError("La partida esta en un estado terminal: no hay jugadas que decidir.")
    acciones = acciones_validas(escenario, estado)
    if not acciones:
        raise ValueError(f"El bando {estado.turno_actual} no tiene acciones; prepare el turno antes de decidir.")
    if configuracion.algoritmo in ALGORITMOS_ADVERSARIALES_AGENTE:
        return _decidir_adversarial(escenario, estado, configuracion, acciones)
    return _decidir_busqueda(escenario, estado, configuracion, acciones)


def _decidir_adversarial(
    escenario: Escenario,
    estado: EstadoJuego,
    configuracion: ConfiguracionAgente,
    acciones: tuple[Accion, ...],
) -> DecisionAgente:
    """Delegar la jugada en Minimax o alfa-beta con el bando en turno como MAX."""
    funcion = minimax if configuracion.algoritmo == "minimax" else alfa_beta
    resultado = funcion(escenario, estado, configuracion.profundidad, orden=configuracion.orden)
    seleccion = resultado.accion_seleccionada
    accion = seleccion.accion if seleccion is not None else acciones[0]
    return DecisionAgente(estado.turno_actual, configuracion.algoritmo, accion, "minimax", adversarial=resultado)


def _decidir_busqueda(
    escenario: Escenario,
    estado: EstadoJuego,
    configuracion: ConfiguracionAgente,
    acciones: tuple[Accion, ...],
) -> DecisionAgente:
    """Elegir la meta táctica del bando y aplicar el primer paso del camino de menor costo hacia ella.

    Proposito: dar a los algoritmos de navegación de una unidad un papel en la partida sin modificarlos.
    Precondiciones: ``estado`` no es terminal, ``acciones`` son sus acciones legales y no están vacías.
    Postcondiciones: se devuelve la intercepción si existe; si no, el primer paso legal del camino de menor costo hacia
    la meta del bando (empate por identificador) o, si ninguna unidad encuentra camino, la primera acción legal con
    meta ``respaldo``. ``estado`` no cambia.
    Complejidad: U_b ejecuciones del algoritmo configurado, con U_b las unidades candidatas, más O(A).
    Uso de IA: Si.
    Intervencion de IA: Claude (Opus 5.5): metas tácticas y selección de la unidad (E9.5).
    Validacion del estudiante: pruebas de tests/modos/test_agentes.py sobre cada meta y sobre el respaldo.
    """
    bando = estado.turno_actual
    intercepcion = next((accion for accion in acciones if accion.tipo == INTERCEPTAR), None)
    if intercepcion is not None:
        return DecisionAgente(bando, configuracion.algoritmo, intercepcion, "interceptar", intercepcion.destino)

    con_movimiento = sorted({accion.identificador_unidad for accion in acciones if accion.tipo == MOVER})
    meta, objetivo, candidatas = _meta_del_bando(escenario, estado, con_movimiento)

    mejor: tuple[int | float, str, ResultadoBusqueda] | None = None
    for identificador in candidatas:
        problema = ProblemaNavegacionPartida(escenario, identificador, objetivo, estado)
        resultado = _ejecutar_busqueda(problema, configuracion)
        if not resultado.exito or not resultado.acciones:
            continue
        if not es_accion_valida(escenario, estado, resultado.acciones[0]):
            continue
        if mejor is None or (resultado.costo, identificador) < (mejor[0], mejor[1]):
            mejor = (resultado.costo, identificador, resultado)

    if mejor is None:
        return DecisionAgente(bando, configuracion.algoritmo, acciones[0], "respaldo", objetivo)
    resultado = mejor[2]
    return DecisionAgente(bando, configuracion.algoritmo, resultado.acciones[0], meta, objetivo, busqueda=resultado)


def _meta_del_bando(
    escenario: Escenario,
    estado: EstadoJuego,
    con_movimiento: list[str],
) -> tuple[str, Posicion, list[str]]:
    """Devolver la meta táctica del bando en turno, la celda objetivo y las unidades que planean hacia ella.

    Con el recurso libre, la meta es el recurso para todas las unidades que pueden moverse; si el bando lo lleva, la
    meta es su base y solo planea el portador; si lo lleva el rival, la meta es la celda del portador rival.
    """
    portador = estado.portador_recurso
    if portador is None:
        return "recurso", estado.posicion_recurso, con_movimiento
    unidad_portadora = buscar_unidad(estado, portador)
    if unidad_portadora.bando == estado.turno_actual:
        return "base", escenario.bases[estado.turno_actual], [portador] if portador in con_movimiento else []
    return "portador", unidad_portadora.posicion, con_movimiento


def _ejecutar_busqueda(problema: ProblemaNavegacionPartida, configuracion: ConfiguracionAgente) -> ResultadoBusqueda:
    """Ejecutar el algoritmo de búsqueda configurado sobre ``problema`` con una traza acotada de expansiones."""
    observador = ObservadorExpansiones(LIMITE_TRAZA_AGENTE)
    algoritmo = configuracion.algoritmo
    if algoritmo == "beam":
        return busqueda_haz(problema, configuracion.k, observador_expansiones=observador)
    if algoritmo == "astar":
        heuristica = HeuristicaObstaculos(problema) if configuracion.heuristica == "hto" else None
        return busqueda_a_estrella(problema, heuristica_preparada=heuristica, observador_expansiones=observador)
    funciones = {"bfs": busqueda_anchura, "dfs": busqueda_profundidad, "ucs": busqueda_costo_uniforme}
    return funciones[algoritmo](problema, observador_expansiones=observador)
