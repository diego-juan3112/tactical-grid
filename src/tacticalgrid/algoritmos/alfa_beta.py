"""Minimax con poda alfa-beta (E8.4) sobre las mismas acciones, utilidad y orden que el Minimax de E8.3.

Decisiones de diseno:

- Recorre exactamente el mismo arbol que ``minimax``: mismas ``acciones_tacticas`` en el mismo orden, el mismo
  ``preparar_turno`` antes de expandir (el pase por bloqueo no consume profundidad), el mismo criterio de hoja y
  el mismo evaluador (``preparar_evaluador``). La unica diferencia es que deja de explorar las ramas que ya no
  pueden cambiar la decision.
- ``alfa`` es el mejor valor que MAX ya tiene asegurado en el camino actual y ``beta`` el mejor que MIN tiene
  asegurado. En un nodo MAX, si el mejor valor alcanza ``beta``, MIN nunca permitiria llegar a el y se podan las
  acciones restantes; en un nodo MIN, simetricamente, se poda cuando el valor baja hasta ``alfa``.
- Variante "fail-soft": cuando un nodo se poda devuelve el mejor valor encontrado, que es una cota (superior en
  los nodos MIN que cuelgan de la raiz) del valor real. En la raiz se conserva, como en Minimax, la primera accion
  con valor estrictamente mayor: una accion podada devuelve una cota que no supera al mejor valor ya encontrado,
  asi que nunca reemplaza a la elegida, y ante empate gana la primera. Por eso la decision y el valor coinciden
  con Minimax para la misma profundidad, utilidad y orden de acciones.
- Metricas comparables con E8.3: ``nodos_generados`` cuenta la raiz y cada sucesor creado, ``nodos_evaluados``
  las hojas evaluadas y ``profundidad_alcanzada`` la mayor profundidad visitada. ``nodos_podados`` cuenta las
  ramas evitadas: en cada corte, las acciones hermanas que ya no se exploran (no se crea su sucesor).
"""

import time

from tacticalgrid.escenario.escenario import Escenario
from tacticalgrid.juego.estado import EstadoJuego
from tacticalgrid.juego.partida import preparar_turno
from tacticalgrid.juego.reglas import aplicar_accion, es_terminal
from tacticalgrid.juego.tacticas import acciones_tacticas

from .minimax import ResultadoMinimax, preparar_evaluador, validar_profundidad
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
) -> float:
    """Valor de ``estado`` con poda: exacto si queda dentro de (alfa, beta); si no, una cota del lado del corte."""
    contadores.profundidad_alcanzada = max(contadores.profundidad_alcanzada, profundidad)
    estado = preparar_turno(escenario, estado)
    acciones = () if es_terminal(escenario, estado) else acciones_tacticas(escenario, estado)
    if profundidad == profundidad_maxima or not acciones:
        contadores.evaluados += 1
        return evaluador.evaluar(estado)

    es_max = estado.turno_actual == evaluador.bando_max
    mejor = float("-inf") if es_max else float("inf")
    for indice, accion_tactica in enumerate(acciones):
        sucesor = aplicar_accion(escenario, estado, accion_tactica.accion)
        contadores.generados += 1
        valor = _valor_alfa_beta(
            escenario, evaluador, sucesor, profundidad + 1, profundidad_maxima, alfa, beta, contadores
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
) -> ResultadoMinimax:
    """Elige la misma accion que Minimax para el bando en turno, evitando explorar ramas que no cambian la decision.

    Proposito: implementar Minimax con poda alfa-beta y profundidad limitada, reportando las metricas de E8.3 mas
    los nodos podados, para comparar cuanto trabajo ahorra la poda.
    Precondiciones: ``estado`` es coherente con ``escenario``; ``profundidad_maxima`` es un entero mayor o igual que
    1 (si no, ``ValueError``); si se pasa ``evaluador``, su ``bando_max`` debe ser el bando en turno de ``estado``.
    Postcondiciones: devuelve un ``ResultadoMinimax`` con ``algoritmo="ALFA_BETA"``, la misma accion seleccionada y
    el mismo valor que ``minimax`` con la misma profundidad, utilidad y orden de acciones; nodos generados y
    evaluados menores o iguales que los de Minimax; los nodos podados; la profundidad alcanzada y el tiempo. En
    ``valores_raiz`` el valor de cada accion de la raiz es exacto salvo cuando ``cotas_raiz`` lo marca como cota
    superior (su valor real es menor o igual). Si la raiz es terminal o el bando en turno no puede actuar,
    ``accion_seleccionada`` es ``None``. Toda accion considerada es legal y ``estado`` no se modifica.
    Complejidad: en el peor caso, con el peor orden de acciones, O(b^d) nodos como Minimax; con el mejor orden,
    O(b^(d/2)). Cada nodo cuesta O(U^2) como en Minimax y el espacio es O(d * b) por la recursion.
    Uso de IA: Si.
    Intervencion de IA: Claude (Opus 5.5) propuso el diseno (variante fail-soft, conteo de ramas podadas, marca de
    cotas en la raiz), la implementacion, sus pruebas y esta documentacion en E8.4.
    Validacion del estudiante: Se aprueba la implementacion validada por tests/algoritmos/test_alfa_beta.py,
    que compara con un arbol calculado a mano (pasillo 1x8) y con Minimax en los escenarios del repositorio.
    """
    profundidad_maxima = validar_profundidad(profundidad_maxima)
    inicio = time.perf_counter()
    evaluador = preparar_evaluador(escenario, estado, evaluador)

    contadores = _Contadores()
    raiz = preparar_turno(escenario, estado)
    puede_actuar = not es_terminal(escenario, raiz) and raiz.turno_actual == evaluador.bando_max
    acciones = acciones_tacticas(escenario, raiz) if puede_actuar else ()

    seleccionada = None
    valores_raiz = []
    cotas_raiz = []
    if not acciones:
        valor = _valor_alfa_beta(
            escenario, evaluador, raiz, 0, profundidad_maxima, float("-inf"), float("inf"), contadores
        )
    else:
        # En la raiz MAX nunca poda (beta es infinito): todas sus acciones se generan y valoran.
        valor = float("-inf")
        for accion_tactica in acciones:
            sucesor = aplicar_accion(escenario, raiz, accion_tactica.accion)
            contadores.generados += 1
            valor_accion = _valor_alfa_beta(
                escenario, evaluador, sucesor, 1, profundidad_maxima, valor, float("inf"), contadores
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
    )
