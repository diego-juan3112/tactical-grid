"""Minimax con poda alfa-beta (E8.4) sobre las mismas acciones, utilidad y orden que el Minimax de E8.3.

Decisiones de diseño:

- Recorre exactamente el mismo árbol que ``minimax``: mismas ``acciones_tacticas`` en el mismo orden, el mismo
  ``preparar_turno`` antes de expandir (el pase por bloqueo no consume profundidad), el mismo criterio de hoja y el
  mismo evaluador (``preparar_evaluador``). La única diferencia es que deja de explorar las ramas que ya no pueden
  cambiar la decisión.
- ``alfa`` es el mejor valor que MAX ya tiene asegurado en el camino actual y ``beta`` el mejor que tiene asegurado
  MIN. En un nodo MAX, si el mejor valor alcanza ``beta``, MIN nunca permitiría llegar a él y se podan las acciones
  restantes; en un nodo MIN, de forma simétrica, se poda cuando el valor baja hasta ``alfa``.
- Variante *fail-soft*: un nodo podado devuelve el mejor valor encontrado, que es una cota del valor real (superior
  en los nodos MIN que cuelgan de la raíz). En la raíz se conserva, como en Minimax, la primera acción con valor
  estrictamente mayor: una acción podada devuelve una cota que no supera al mejor valor ya encontrado, por lo que
  nunca reemplaza a la elegida, y ante empate gana la primera. Así, la decisión y el valor coinciden con Minimax
  para la misma profundidad, utilidad y orden de acciones.
- Métricas comparables con E8.3: ``nodos_generados`` cuenta la raíz y cada sucesor creado, ``nodos_evaluados`` las
  hojas evaluadas y ``profundidad_alcanzada`` la mayor profundidad visitada. ``nodos_podados`` cuenta las ramas
  evitadas: en cada corte, las acciones hermanas que ya no se exploran y cuyo sucesor no se crea.
"""

import time

from tacticalgrid.escenario.escenario import Escenario
from tacticalgrid.juego.estado import EstadoJuego
from tacticalgrid.juego.partida import preparar_turno
from tacticalgrid.juego.reglas import aplicar_accion, es_terminal
from tacticalgrid.juego.tacticas import acciones_tacticas

from .minimax import ResultadoMinimax, preparar_evaluador, validar_profundidad
from .orden_acciones import ORDEN_GENERACION, ordenar_acciones, validar_orden
from .utilidad import EvaluadorUtilidad


class _Contadores:
    def __init__(self) -> None:
        self.generados = 1
        self.evaluados = 0
        self.podados = 0
        self.profundidad_alcanzada = 0


def _valor_alfa_beta(
    escenario: Escenario,
    evaluador: EvaluadorUtilidad,
    estado: EstadoJuego,
    profundidad: int,
    profundidad_maxima: int,
    alfa: float,
    beta: float,
    contadores: _Contadores,
    orden: str,
) -> float:
    """Calcular recursivamente el valor de ``estado`` con poda alfa-beta (variante fail-soft).

    Proposito: resolver el núcleo de alfa-beta: recorrer el mismo árbol que ``_valor_minimax`` y dejar de explorar los
    hijos restantes de un nodo en cuanto su valor ya no puede cambiar la decisión de un ancestro.
    Precondiciones: las mismas de ``_valor_minimax``; además, ``alfa`` es el mejor valor que MAX ya tiene asegurado en
    el camino actual y ``beta`` el mejor que tiene MIN (en la raíz, menos y más infinito).
    Postcondiciones: si el valor real del nodo queda dentro de (``alfa``, ``beta``), se devuelve exacto; si no, se
    devuelve una cota del lado del corte (fail-soft): en un nodo MIN cortado, un valor menor o igual que ``alfa`` que
    es cota superior del real; en un nodo MAX cortado, uno mayor o igual que ``beta``. En cada corte,
    ``contadores.podados`` aumenta en las acciones hermanas que ya no se exploran. Las hojas, el pase de turno, el
    conteo de generados y evaluados y la profundidad alcanzada se tratan igual que en Minimax. ``estado`` no cambia.
    Complejidad: O(b^(d-p)) nodos con el peor orden de acciones, igual que Minimax, y O(b^((d-p)/2)) con el mejor
    orden; cada nodo cuesta O(U^2). Espacio O(d) por la recursión.
    Uso de IA: Si.
    Intervencion de IA: Claude (Opus 5.5): implementación con variante fail-soft y conteo de ramas podadas (E8.4),
    parámetro ``orden`` (E8.6) y documentación (E11.1).
    Validacion del estudiante: pruebas de tests/algoritmos/test_alfa_beta.py con el árbol del pasillo 1x8 calculado a
    mano y la comparación con Minimax en los escenarios del repositorio (valores de la raíz exactos o cotas correctas),
    y pruebas de tests/algoritmos/test_orden_acciones.py.
    """
    contadores.profundidad_alcanzada = max(contadores.profundidad_alcanzada, profundidad)
    estado = preparar_turno(escenario, estado)
    acciones = () if es_terminal(escenario, estado) else ordenar_acciones(acciones_tacticas(escenario, estado), orden)
    if profundidad == profundidad_maxima or not acciones:
        contadores.evaluados += 1
        return evaluador.evaluar(estado)

    es_max = estado.turno_actual == evaluador.bando_max
    mejor = float("-inf") if es_max else float("inf")
    for indice, accion_tactica in enumerate(acciones):
        sucesor = aplicar_accion(escenario, estado, accion_tactica.accion)
        contadores.generados += 1
        valor = _valor_alfa_beta(
            escenario, evaluador, sucesor, profundidad + 1, profundidad_maxima, alfa, beta, contadores, orden
        )
        if es_max:
            mejor = max(mejor, valor)
            alfa = max(alfa, mejor)
        else:
            mejor = min(mejor, valor)
            beta = min(beta, mejor)
        if alfa >= beta:
            contadores.podados += len(acciones) - indice - 1
            break
    return mejor


def alfa_beta(
    escenario: Escenario,
    estado: EstadoJuego,
    profundidad_maxima: int,
    evaluador: EvaluadorUtilidad | None = None,
    orden: str = ORDEN_GENERACION,
) -> ResultadoMinimax:
    """Elegir la misma acción que Minimax para el bando en turno sin explorar ramas que no cambian la decisión.

    Proposito: implementar Minimax con poda alfa-beta y profundidad limitada, con las métricas de E8.3 más los nodos
    podados, para comparar cuánto trabajo ahorra la poda.
    Precondiciones: ``estado`` es coherente con ``escenario``; ``profundidad_maxima`` es un entero mayor o igual que 1
    (si no, ``ValueError``); si se pasa ``evaluador``, su ``bando_max`` es el bando en turno de ``estado``.
    Postcondiciones: se devuelve un ``ResultadoMinimax`` con ``algoritmo="ALFA_BETA"``, la misma acción seleccionada y
    el mismo valor que ``minimax`` con la misma profundidad, utilidad y orden de acciones; nodos generados y evaluados
    menores o iguales que los de Minimax; los nodos podados, la profundidad alcanzada y el tiempo. En ``valores_raiz``
    el valor de cada acción de la raíz es exacto, salvo cuando ``cotas_raiz`` lo marca como cota superior (su valor
    real es menor o igual). Si la raíz es terminal o el bando en turno no puede actuar, ``accion_seleccionada`` es
    ``None``. Toda acción considerada es legal y ``estado`` no cambia.
    Complejidad: con el peor orden de acciones, O(b^d) nodos como Minimax; con el mejor orden, O(b^(d/2)). Cada nodo
    cuesta O(U^2), como en Minimax, y el espacio es O(d * b) por la recursión.
    Uso de IA: Si.
    Intervencion de IA: Claude (Opus 5.5): diseño (variante fail-soft, conteo de ramas podadas, marca de cotas en la
    raíz), implementación, pruebas y documentación (E8.4); parámetro ``orden``, por defecto ``generacion``, para
    estudiar su efecto sobre la poda (E8.6).
    Validacion del estudiante: pruebas de tests/algoritmos/test_alfa_beta.py: árbol del pasillo 1x8 calculado a mano,
    misma decisión y valor que Minimax en los escenarios del repositorio, valores de la raíz exactos o cotas correctas
    y reducción del trabajo en escenarios reales.
    """
    profundidad_maxima = validar_profundidad(profundidad_maxima)
    orden = validar_orden(orden)
    inicio = time.perf_counter()
    evaluador = preparar_evaluador(escenario, estado, evaluador)

    contadores = _Contadores()
    raiz = preparar_turno(escenario, estado)
    puede_actuar = not es_terminal(escenario, raiz) and raiz.turno_actual == evaluador.bando_max
    acciones = ordenar_acciones(acciones_tacticas(escenario, raiz), orden) if puede_actuar else ()

    seleccionada = None
    valores_raiz = []
    cotas_raiz = []
    if not acciones:
        valor = _valor_alfa_beta(
            escenario, evaluador, raiz, 0, profundidad_maxima, float("-inf"), float("inf"), contadores, orden
        )
    else:
        # En la raíz MAX nunca poda (beta es infinito): todas sus acciones se generan y se valoran.
        valor = float("-inf")
        for accion_tactica in acciones:
            sucesor = aplicar_accion(escenario, raiz, accion_tactica.accion)
            contadores.generados += 1
            valor_accion = _valor_alfa_beta(
                escenario, evaluador, sucesor, 1, profundidad_maxima, valor, float("inf"), contadores, orden
            )
            valores_raiz.append((accion_tactica, valor_accion))
            cotas_raiz.append(seleccionada is not None and valor_accion <= valor)
            if seleccionada is None or valor_accion > valor:
                seleccionada, valor = accion_tactica, valor_accion

    return ResultadoMinimax(
        algoritmo="ALFA_BETA",
        bando_max=evaluador.bando_max,
        profundidad_maxima=profundidad_maxima,
        accion_seleccionada=seleccionada,
        valor=valor,
        nodos_generados=contadores.generados,
        nodos_evaluados=contadores.evaluados,
        nodos_podados=contadores.podados,
        profundidad_alcanzada=contadores.profundidad_alcanzada,
        tiempo_segundos=time.perf_counter() - inicio,
        valores_raiz=tuple(valores_raiz),
        cotas_raiz=tuple(cotas_raiz),
        orden_acciones=orden,
    )
