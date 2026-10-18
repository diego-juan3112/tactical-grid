"""Acciones tacticas adversariales (E8.1): el significado tactico de cada accion legal.

El juego tiene solo dos mecanicas: moverse una celda e interceptar al portador rival adyacente. Las tacticas del
enunciado (avanzar, proteger zona, bloquear posicion, aproximarse al recurso, interceptar al portador) no agregan
mecanicas nuevas: son una clasificacion de esas acciones legales segun la situacion. Asi el espacio de acciones de
Minimax sigue siendo ``acciones_validas`` (legal por construccion y acotado a cinco acciones por unidad), y cada
decision puede explicarse por su tipo tactico.

Reglas de clasificacion, en orden de prioridad (``d`` es la distancia Manhattan):

1. ``interceptar_portador``: la accion es de tipo ``interceptar``.
2. Recurso libre: ``aproximarse_al_recurso`` si el movimiento reduce ``d`` hasta el recurso (incluye recogerlo).
3. Recurso en manos del propio bando:
   - el portador: ``avanzar`` si reduce ``d`` hasta su base;
   - un aliado: ``proteger_zona`` si reduce ``d`` hasta el portador (lo escolta y cubre su zona).
4. Recurso en manos del rival:
   - ``bloquear_posicion`` si el destino queda dentro del rectangulo entre el portador rival y la base rival, es
     decir, sobre alguna de sus rutas mas cortas;
   - ``perseguir_portador`` si no, pero reduce ``d`` hasta el portador rival.
5. ``reposicionar``: cualquier otro movimiento legal.
"""

from dataclasses import dataclass

from tacticalgrid.escenario.escenario import Escenario, Posicion

from .accion import INTERCEPTAR, Accion
from .estado import EstadoJuego
from .recurso import obtener_portador
from .reglas import acciones_validas, buscar_unidad

INTERCEPTAR_PORTADOR = "interceptar_portador"
AVANZAR = "avanzar"
APROXIMARSE_AL_RECURSO = "aproximarse_al_recurso"
PROTEGER_ZONA = "proteger_zona"
BLOQUEAR_POSICION = "bloquear_posicion"
PERSEGUIR_PORTADOR = "perseguir_portador"
REPOSICIONAR = "reposicionar"

TIPOS_TACTICOS = (
    INTERCEPTAR_PORTADOR,
    AVANZAR,
    APROXIMARSE_AL_RECURSO,
    PROTEGER_ZONA,
    BLOQUEAR_POSICION,
    PERSEGUIR_PORTADOR,
    REPOSICIONAR,
)


@dataclass(frozen=True)
class AccionTactica:
    """Accion legal acompanada de su tipo tactico."""

    accion: Accion
    tipo_tactico: str


def _distancia(a: Posicion, b: Posicion) -> int:
    return abs(a.fila - b.fila) + abs(a.columna - b.columna)


def _se_acerca(accion: Accion, referencia: Posicion) -> bool:
    return _distancia(accion.destino, referencia) < _distancia(accion.origen, referencia)


def _dentro_del_rectangulo(posicion: Posicion, esquina_a: Posicion, esquina_b: Posicion) -> bool:
    return (
        min(esquina_a.fila, esquina_b.fila) <= posicion.fila <= max(esquina_a.fila, esquina_b.fila)
        and min(esquina_a.columna, esquina_b.columna) <= posicion.columna <= max(esquina_a.columna, esquina_b.columna)
    )


def clasificar_accion(escenario: Escenario, estado: EstadoJuego, accion: Accion) -> str:
    """Asigna a una accion legal su tipo tactico segun la situacion del recurso y de las unidades.

    Proposito: dar significado tactico (avanzar, proteger zona, bloquear posicion, aproximarse al recurso,
    perseguir o interceptar al portador) a las acciones que consumira Minimax, sin crear mecanicas nuevas.
    Precondiciones: ``accion`` pertenece a ``acciones_validas(escenario, estado)``; las bases vienen del escenario.
    Postcondiciones: devuelve exactamente uno de ``TIPOS_TACTICOS`` aplicando las reglas del modulo en orden de
    prioridad; el resultado depende solo de ``escenario``, ``estado`` y ``accion`` (es determinista) y no modifica
    nada. Es simetrico para A y B: solo usa "propio" y "rival", nunca un bando concreto.
    Complejidad: O(U) temporal para localizar la unidad y al portador, y O(1) espacial.
    Uso de IA: Si.
    Intervencion de IA: Claude (Opus 5.5) propuso el conjunto de tipos, sus reglas geometricas y la implementacion
    en E8.1.
    Validacion del estudiante: el estudiante reviso y valido el codigo; ademas, las pruebas de
    tests/juego/test_tacticas.py cubren cada tipo tactico, la simetria entre bandos y la legalidad de todas las
    acciones clasificadas.
    """
    if accion.tipo == INTERCEPTAR:
        return INTERCEPTAR_PORTADOR
    unidad = buscar_unidad(estado, accion.identificador_unidad)
    portador = obtener_portador(estado)
    if portador is None:
        if estado.posicion_recurso is not None and _se_acerca(accion, estado.posicion_recurso):
            return APROXIMARSE_AL_RECURSO
        return REPOSICIONAR
    if portador.bando == unidad.bando:
        if portador.identificador == unidad.identificador:
            return AVANZAR if _se_acerca(accion, escenario.bases[unidad.bando]) else REPOSICIONAR
        return PROTEGER_ZONA if _se_acerca(accion, portador.posicion) else REPOSICIONAR
    if _dentro_del_rectangulo(accion.destino, portador.posicion, escenario.bases[portador.bando]):
        return BLOQUEAR_POSICION
    if _se_acerca(accion, portador.posicion):
        return PERSEGUIR_PORTADOR
    return REPOSICIONAR


def acciones_tacticas(escenario: Escenario, estado: EstadoJuego) -> tuple[AccionTactica, ...]:
    """Devuelve las acciones legales del bando en turno, cada una con su tipo tactico.

    Proposito: ofrecer a Minimax y alfa-beta (E8.3, E8.4) un espacio de acciones legal y acotado con significado
    tactico, util para explicar decisiones y para experimentar con el orden de las acciones.
    Precondiciones: ``estado`` es coherente con ``escenario``.
    Postcondiciones: devuelve, en el mismo orden que ``acciones_validas``, una ``AccionTactica`` por cada accion
    legal; la tupla esta vacia si la partida termino o el bando esta bloqueado. Toda accion devuelta es legal y a
    lo sumo hay cinco por unidad del bando en turno. No modifica el estado.
    Complejidad: O(A * U) temporal y O(A) espacial, donde A es el numero de acciones legales y U el de unidades.
    Uso de IA: Si.
    Intervencion de IA: Claude (Opus 5.5) propuso e implemento esta consulta en E8.1.
    Validacion del estudiante: el estudiante reviso y valido el codigo; ademas, las pruebas de
    tests/juego/test_tacticas.py exploran partidas sobre los escenarios del repositorio y comprueban que toda accion
    tactica es legal y se puede aplicar.
    """
    return tuple(
        AccionTactica(accion, clasificar_accion(escenario, estado, accion))
        for accion in acciones_validas(escenario, estado)
    )
