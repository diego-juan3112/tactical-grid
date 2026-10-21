"""Modo ``partida`` (E10.1): ambos bandos juegan por turnos con alfa-beta (o Minimax) desde el estado cargado.

Decisiones de diseño:

- La partida continúa desde el estado del escenario (unidades, turno y portador del JSON); no se reinicia.
- En cada turno se aplica ``preparar_turno`` (E3.1/E1.3): si el bando en turno está bloqueado, el turno pasa al
  adversario, y si ambos lo están la partida termina en empate. El pase se registra en la jugada siguiente.
- El bando en turno decide con el mismo algoritmo, profundidad y orden de acciones que su rival: MAX y MIN son
  roles de cada búsqueda, no capacidades distintas.
- La partida termina con victoria, con empate por bloqueo o al alcanzar ``max_turnos`` jugadas. El límite existe
  porque dos bandos que se custodian mutuamente pueden no terminar nunca; no se agrega una regla de empate por
  repetición, que no forma parte de las reglas del juego.
"""

from dataclasses import dataclass

from tacticalgrid.algoritmos.alfa_beta import alfa_beta
from tacticalgrid.algoritmos.minimax import ResultadoMinimax, minimax, validar_profundidad
from tacticalgrid.algoritmos.orden_acciones import ORDEN_GENERACION, validar_orden
from tacticalgrid.escenario.escenario import Escenario
from tacticalgrid.juego.estado import EstadoJuego
from tacticalgrid.juego.partida import preparar_turno
from tacticalgrid.juego.reglas import EMPATE_BLOQUEO, aplicar_accion, es_terminal, obtener_ganador

from .prueba import ALGORITMOS_ADVERSARIALES, MAX_TURNOS_POR_DEFECTO, validar_max_turnos

DECISORES = {"minimax": minimax, "alfa_beta": alfa_beta}
LIMITE_TURNOS = "limite_turnos"


@dataclass(frozen=True)
class TurnoPartida:
    """Jugada de la partida: bando que jugó, estado de partida, decisión y estado resultante."""

    numero: int
    bando: str
    hubo_pase: bool
    estado_previo: EstadoJuego
    decision: ResultadoMinimax
    estado_resultante: EstadoJuego

    def a_diccionario(self) -> dict[str, object]:
        """Exportar la jugada con las métricas de su decisión, lista para ``json.dumps``."""
        return {
            "numero": self.numero,
            "bando": self.bando,
            "hubo_pase": self.hubo_pase,
            "decision": self.decision.a_diccionario(),
        }


@dataclass(frozen=True)
class ResultadoPartida:
    """Partida completa: configuración, jugadas y resultado (``victoria_A``, ``victoria_B``, empate o límite)."""

    algoritmo: str
    profundidad: int
    orden_acciones: str
    max_turnos: int
    estado_inicial: EstadoJuego
    turnos: tuple[TurnoPartida, ...]
    estado_final: EstadoJuego
    resultado: str

    @property
    def ganador(self) -> str | None:
        """Bando ganador, o ``None`` si la partida terminó en empate o por el límite de turnos."""
        return self.resultado.removeprefix("victoria_") if self.resultado.startswith("victoria_") else None

    def a_diccionario(self) -> dict[str, object]:
        """Exportar la partida y sus jugadas en una estructura serializable con ``json.dumps``."""
        return {
            "algoritmo": self.algoritmo,
            "profundidad": self.profundidad,
            "orden_acciones": self.orden_acciones,
            "max_turnos": self.max_turnos,
            "resultado": self.resultado,
            "ganador": self.ganador,
            "jugadas": len(self.turnos),
            "turnos": [turno.a_diccionario() for turno in self.turnos],
        }


def jugar_partida(
    escenario: Escenario,
    estado: EstadoJuego,
    profundidad: int,
    algoritmo: str = "alfa_beta",
    orden: str = ORDEN_GENERACION,
    max_turnos: int = MAX_TURNOS_POR_DEFECTO,
) -> ResultadoPartida:
    """Continuar la partida por turnos desde ``estado``, con ambos bandos decidiendo con el mismo algoritmo.

    Proposito: implementar el modo ``partida`` del enunciado ("cargar el escenario completo para continuar el juego por
    turnos") de forma determinista y reproducible.
    Precondiciones: ``estado`` es coherente con ``escenario``; ``profundidad`` es un entero mayor o igual que 1;
    ``algoritmo`` es ``minimax`` o ``alfa_beta``; ``orden`` es uno de ``ORDENES``; ``max_turnos`` es un entero mayor o
    igual que 1. En otro caso se lanza ``ValueError`` antes de jugar.
    Postcondiciones: se devuelve un ``ResultadoPartida`` con, a lo sumo, ``max_turnos`` jugadas. Cada jugada es legal en
    su ``estado_previo`` (con el pase por bloqueo ya resuelto) y la decide el bando en turno como MAX. El resultado es
    ``victoria_A`` o ``victoria_B`` si un portador llegó a su base, ``empate_bloqueo`` si ningún bando puede actuar y
    ``limite_turnos`` si se alcanzó el límite sin terminar. Con los mismos datos la partida es siempre la misma.
    ``estado`` no cambia.
    Complejidad: O(T * C), con T jugadas (a lo sumo ``max_turnos``) y C el costo de una decisión: O(b^d) con Minimax y,
    en el peor caso, también con alfa-beta, con b acciones por nodo y d la profundidad.
    Uso de IA: Si.
    Intervencion de IA: Claude (Opus 5.5): diseño (IA contra IA desde el estado cargado, registro de pases y límite de
    turnos sin regla de repetición), implementación y pruebas (E10.1).
    Validacion del estudiante: pruebas de tests/modos/test_partida_automatica.py: partida calculada a mano con pases por
    bloqueo, legalidad de cada jugada con alternancia de bandos, límite de turnos, empate por bloqueo total, misma
    partida con Minimax y alfa-beta, y determinismo.
    """
    profundidad = validar_profundidad(profundidad)
    orden = validar_orden(orden)
    max_turnos = validar_max_turnos(max_turnos)
    if algoritmo not in DECISORES:
        raise ValueError(f"El algoritmo de la partida debe ser uno de {list(ALGORITMOS_ADVERSARIALES)} y se recibio {algoritmo!r}.")

    turnos: list[TurnoPartida] = []
    actual = estado
    while len(turnos) < max_turnos:
        preparado = preparar_turno(escenario, actual)
        if es_terminal(escenario, preparado):
            actual = preparado
            break
        decision = DECISORES[algoritmo](escenario, preparado, profundidad, orden=orden)
        siguiente = aplicar_accion(escenario, preparado, decision.accion_seleccionada.accion)
        turnos.append(
            TurnoPartida(
                numero=len(turnos) + 1,
                bando=preparado.turno_actual,
                hubo_pase=preparado.turno_actual != actual.turno_actual,
                estado_previo=preparado,
                decision=decision,
                estado_resultante=siguiente,
            )
        )
        actual = siguiente

    return ResultadoPartida(
        algoritmo=algoritmo,
        profundidad=profundidad,
        orden_acciones=orden,
        max_turnos=max_turnos,
        estado_inicial=estado,
        turnos=tuple(turnos),
        estado_final=actual,
        resultado=_resultado(escenario, actual),
    )


def _resultado(escenario: Escenario, estado: EstadoJuego) -> str:
    ganador = obtener_ganador(escenario, estado)
    if ganador is not None:
        return f"victoria_{ganador}"
    if estado.estado_partida == EMPATE_BLOQUEO:
        return EMPATE_BLOQUEO
    return LIMITE_TURNOS
