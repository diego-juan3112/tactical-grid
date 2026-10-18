"""Reglas de transicion de la partida: acciones validas, sucesores, condicion objetivo y costo.

Reglas deterministas definidas en E1.2 y E1.3:

- En cada turno el bando en ``turno_actual`` elige una de sus unidades y la mueve una celda en direccion
  ortogonal (arriba, abajo, izquierda, derecha). No hay movimientos diagonales.
- El destino debe estar dentro del mapa, ser transitable y no estar ocupado por otra unidad (de cualquier bando).
- Si el recurso no tiene portador y una unidad entra en su celda, lo recoge automaticamente.
- El recurso viaja con su portador. Si el portador entra en la base de su propio bando, ese bando gana.
- Tras cada accion el turno pasa al otro bando.
- El costo de una accion es el costo del terreno de la celda destino, leido del escenario cargado.
- Una partida terminada no tiene acciones validas. Una unidad bloqueada no aporta acciones; si todo el bando
  esta bloqueado, se pasa el turno al adversario si puede actuar, o se declara empate si ambos estan bloqueados.
- La intercepcion transfiere el recurso a una unidad adversaria sin eliminar unidades ni cambiar el turno.
- E8.1: una unidad ortogonalmente adyacente al portador rival puede usar su turno para interceptarlo (accion de
  tipo ``interceptar``): no se mueve nadie, el recurso pasa al interceptor y el turno cambia como en cualquier
  accion. Es la unica accion tactica con efecto propio; las demas tacticas son movimientos clasificados.
- La ausencia de ruta es resultado de busqueda y no modifica el estado del juego.
"""

from dataclasses import replace

from tacticalgrid.escenario.escenario import Escenario, Posicion

from .accion import DESPLAZAMIENTOS, INTERCEPTAR, Accion
from .estado import EstadoJuego
from .recurso import bando_que_entrego_recurso, recoger_recurso
from .unidad import Unidad

EN_CURSO = "en_curso"
EMPATE_BLOQUEO = "empate_bloqueo"
BANDOS = ("A", "B")


def obtener_ganador(escenario: Escenario, estado: EstadoJuego) -> str | None:
    """Determina el bando ganador a partir de la informacion del estado.

    Proposito: definir la condicion objetivo de la partida: un bando gana cuando su unidad portadora del
    recurso se encuentra en la base de ese mismo bando.
    Precondiciones: ``estado`` es coherente con ``escenario`` (si hay portador, es una unidad del estado).
    Postcondiciones: devuelve ``"A"`` o ``"B"`` si hay ganador y ``None`` en otro caso; no modifica nada.
    Complejidad: O(U) temporal y O(1) espacial, donde U es el numero de unidades.
    Uso de IA: Si.
    Intervencion de IA: Claude (Opus 5.5) propuso la implementacion y su documentacion a partir del enunciado;
    Claude (Sonnet 5.5) la delego en ``recurso.bando_que_entrego_recurso`` en E3.2, sin cambiar su resultado.
    Validacion del estudiante: el estudiante reviso las reglas frente al enunciado y valido el metodo con
    pytest (tests/juego/test_reglas.py y la exploracion de sucesores en tests/juego/test_espacio_estados.py).
    """
    return bando_que_entrego_recurso(escenario, estado)


def es_terminal(escenario: Escenario, estado: EstadoJuego) -> bool:
    """Indica si hay victoria o empate por bloqueo total.

    Proposito: centralizar el reconocimiento de los resultados terminales de la partida.
    Precondiciones: ``estado`` es coherente con ``escenario``.
    Postcondiciones: devuelve verdadero para una victoria vigente o ``empate_bloqueo``; no modifica el estado.
    Complejidad: O(U) temporal y O(1) espacial, donde U es la cantidad de unidades.
    Uso de IA: Si.
    Intervencion de IA: Codex extendio la condicion existente para reconocer el empate aprobado en E1.3.
    Validacion del estudiante: se reviso manualmente la implementacion contra los criterios de aceptacion de E1.3.
    Se ejecutaron las pruebas especificas de reglas de juego y la suite completa del proyecto; se verificaron los
    casos de bloqueo individual, pase automatico, empate por bloqueo total, intercepcion valida e invalida,
    intercepcion en base propia y preservacion de la inmutabilidad del estado.
    """
    return estado.estado_partida == EMPATE_BLOQUEO or obtener_ganador(escenario, estado) is not None


def generar_movimientos(
    escenario: Escenario, unidad: Unidad, ocupadas: frozenset[Posicion] = frozenset()
) -> tuple[Accion, ...]:
    """Genera los movimientos ortogonales de una unidad permitidos por el escenario.

    Proposito: concentrar en un solo punto la regla de movimiento que comparten la partida y la navegacion.
    Precondiciones: la posicion de ``unidad`` esta dentro del mapa de ``escenario``.
    Postcondiciones: devuelve, en el orden de ``DESPLAZAMIENTOS``, las acciones cuyo destino esta dentro del
    mapa, es transitable segun el JSON y no pertenece a ``ocupadas``. No modifica nada.
    Complejidad: O(1) temporal y espacial (a lo sumo cuatro destinos con consultas O(1)).
    Uso de IA: Si.
    Intervencion de IA: Claude (Opus 5.5) propuso la implementacion y su documentacion.
    Validacion del estudiante: el estudiante reviso las reglas frente al enunciado y valido el metodo con
    pytest (tests/juego/test_reglas.py y la exploracion de sucesores en tests/juego/test_espacio_estados.py).
    """
    acciones = []
    for delta_fila, delta_columna in DESPLAZAMIENTOS:
        destino = Posicion(unidad.posicion.fila + delta_fila, unidad.posicion.columna + delta_columna)
        if escenario.contiene_posicion(destino) and escenario.es_transitable(destino) and destino not in ocupadas:
            acciones.append(Accion(unidad.identificador, unidad.posicion, destino))
    return tuple(acciones)


def generar_intercepcion(estado: EstadoJuego, unidad: Unidad) -> Accion | None:
    """Devuelve la accion de interceptar al portador rival si ``unidad`` puede hacerlo, o ``None``.

    Proposito: definir la condicion espacial que faltaba para usar la intercepcion de E1.3: estar junto al portador.
    Precondiciones: ``unidad`` pertenece a ``estado``; la partida no es terminal (lo comprueba quien la llama).
    Postcondiciones: devuelve ``Accion(unidad.identificador, unidad.posicion, portador.posicion, INTERCEPTAR)`` solo
    si hay portador, es de otro bando y esta a distancia Manhattan 1 de ``unidad``; en otro caso ``None``. No modifica
    nada.
    Complejidad: O(U) temporal para localizar al portador y O(1) espacial.
    Uso de IA: Si.
    Intervencion de IA: Claude (Opus 5.5) propuso la regla de adyacencia y la implemento en E8.1.
    Validacion del estudiante: el estudiante reviso y valido el codigo; ademas, las pruebas de
    tests/juego/test_tacticas.py cubren portador adyacente, no adyacente, aliado, en diagonal y ausencia de
    portador.
    """
    if estado.portador_recurso is None:
        return None
    portador = _buscar_unidad(estado, estado.portador_recurso)
    if portador is None or portador.bando == unidad.bando:
        return None
    distancia = abs(portador.posicion.fila - unidad.posicion.fila) + abs(
        portador.posicion.columna - unidad.posicion.columna
    )
    if distancia != 1:
        return None
    return Accion(unidad.identificador, unidad.posicion, portador.posicion, INTERCEPTAR)


def acciones_validas(escenario: Escenario, estado: EstadoJuego) -> tuple[Accion, ...]:
    """Enumera las acciones legales del bando en turno.

    Proposito: definir el conjunto de acciones validas de la partida, comun a Minimax, alfa-beta y la interfaz.
    Precondiciones: ``estado`` es coherente con ``escenario``.
    Postcondiciones: devuelve una tupla vacia si la partida termino o si todas las unidades del bando en
    turno estan bloqueadas; una unidad bloqueada no impide acciones de sus aliadas. En otro caso, devuelve las
    acciones de cada unidad del bando, recorridas en orden de identificador: primero sus movimientos en el orden
    de ``DESPLAZAMIENTOS`` y, si esta junto al portador rival, la intercepcion (E8.1). No modifica el estado.
    Complejidad: O(U^2) temporal en el peor caso (cada unidad puede localizar al portador) y O(U) espacial; cada
    unidad aporta a lo sumo cinco acciones (cuatro movimientos y una intercepcion).
    Uso de IA: Si.
    Intervencion de IA: Claude (Opus 5.5) propuso la implementacion y su documentacion; en E8.1 agrego la
    intercepcion al final de las acciones de cada unidad.
    Validacion del estudiante: el estudiante reviso las reglas frente al enunciado y valido el metodo con
    pytest (tests/juego/test_reglas.py y la exploracion de sucesores en tests/juego/test_espacio_estados.py).
    """
    if es_terminal(escenario, estado):
        return ()
    ocupadas = frozenset(unidad.posicion for unidad in estado.unidades)
    acciones: list[Accion] = []
    for unidad in estado.unidades:
        if unidad.bando != estado.turno_actual:
            continue
        acciones.extend(generar_movimientos(escenario, unidad, ocupadas))
        intercepcion = generar_intercepcion(estado, unidad)
        if intercepcion is not None:
            acciones.append(intercepcion)
    return tuple(acciones)


def resolver_bloqueo_turno(escenario: Escenario, estado: EstadoJuego) -> EstadoJuego:
    """Aplica el pase automatico o empate cuando el bando activo no tiene acciones.

    Proposito: resolver de manera determinista el bloqueo del bando activo sin generar pases recursivos.
    Precondiciones: ``estado`` es coherente con ``escenario`` y sus unidades representan la situacion actual.
    Postcondiciones: conserva el estado si hay acciones activas o la partida ya termino; pasa el turno una vez
    si solo el adversario puede actuar; si ninguno puede, devuelve un estado con ``empate_bloqueo``. El original
    no se modifica.
    Complejidad: O(U) temporal y espacial, por consultar las acciones de ambos bandos y copiar el estado.
    Uso de IA: Si.
    Intervencion de IA: Codex implemento la transicion conforme a las decisiones aprobadas para E1.3.
    Validacion del estudiante: se reviso manualmente la implementacion contra los criterios de aceptacion de E1.3.
    Se ejecutaron las pruebas especificas de reglas de juego y la suite completa del proyecto; se verificaron los
    casos de bloqueo individual, pase automatico, empate por bloqueo total, intercepcion valida e invalida,
    intercepcion en base propia y preservacion de la inmutabilidad del estado.
    """
    if es_terminal(escenario, estado) or acciones_validas(escenario, estado):
        return estado
    turno_adversario = _otro_bando(estado.turno_actual)
    estado_adversario = replace(estado, turno_actual=turno_adversario)
    if acciones_validas(escenario, estado_adversario):
        return estado_adversario
    return replace(estado, estado_partida=EMPATE_BLOQUEO)


def resolver_intercepcion(
    escenario: Escenario, estado: EstadoJuego, identificador_interceptor: str
) -> EstadoJuego:
    """Transfiere atomicamente el recurso del portador actual a una unidad adversaria.

    Proposito: aplicar la consecuencia de dominio de una intercepcion ya establecida, sin definir su accion espacial.
    Precondiciones: la partida esta en curso, hay un portador existente y el interceptor existe, pertenece al otro
    bando y no es el portador actual.
    Postcondiciones: devuelve un nuevo estado con el interceptor como portador y ``posicion_recurso=None``;
    conserva unidades y turno, y registra la victoria si el nuevo portador esta en su propia base. No muta el estado
    original. Condiciones invalidas lanzan ``ValueError``.
    Complejidad: O(U) temporal y espacial para localizar las unidades y crear el estado inmutable.
    Uso de IA: Si.
    Intervencion de IA: Codex implemento la transferencia atomica conforme a las decisiones aprobadas para E1.3.
    Validacion del estudiante: se reviso manualmente la implementacion contra los criterios de aceptacion de E1.3.
    Se ejecutaron las pruebas especificas de reglas de juego y la suite completa del proyecto; se verificaron los
    casos de bloqueo individual, pase automatico, empate por bloqueo total, intercepcion valida e invalida,
    intercepcion en base propia y preservacion de la inmutabilidad del estado.
    """
    if estado.estado_partida != EN_CURSO or es_terminal(escenario, estado):
        raise ValueError("No se puede interceptar fuera de una partida en curso.")
    if estado.portador_recurso is None:
        raise ValueError("No hay un portador actual del recurso para interceptar.")
    portador = _buscar_unidad(estado, estado.portador_recurso)
    interceptor = _buscar_unidad(estado, identificador_interceptor)
    if portador is None:
        raise ValueError(f"No existe el portador '{estado.portador_recurso}' en el estado.")
    if interceptor is None:
        raise ValueError(f"No existe la unidad interceptora '{identificador_interceptor}' en el estado.")
    if interceptor.identificador == portador.identificador:
        raise ValueError("La unidad portadora actual no puede interceptarse a si misma.")
    if interceptor.bando == portador.bando:
        raise ValueError("La unidad interceptora debe pertenecer al bando contrario al portador.")
    sucesor = replace(estado, portador_recurso=identificador_interceptor, posicion_recurso=None)
    ganador = obtener_ganador(escenario, sucesor)
    if ganador is not None:
        return replace(sucesor, estado_partida=f"victoria_{ganador}")
    return sucesor


def es_accion_valida(escenario: Escenario, estado: EstadoJuego, accion: Accion) -> bool:
    """Comprueba si una accion es legal en el estado dado segun las reglas de la partida.

    Proposito: permitir que la verificacion de soluciones y de decisiones Minimax compruebe legalidad.
    Precondiciones: ``estado`` es coherente con ``escenario``.
    Postcondiciones: devuelve ``True`` solo si ``accion`` pertenece a ``acciones_validas(escenario, estado)``.
    Complejidad: O(U) temporal y espacial.
    Uso de IA: Si.
    Intervencion de IA: Claude (Opus 5.5) propuso la implementacion y su documentacion.
    Validacion del estudiante: el estudiante reviso las reglas frente al enunciado y valido el metodo con
    pytest (tests/juego/test_reglas.py y la exploracion de sucesores en tests/juego/test_espacio_estados.py).
    """
    return accion in acciones_validas(escenario, estado)


def aplicar_accion(escenario: Escenario, estado: EstadoJuego, accion: Accion) -> EstadoJuego:
    """Construye el estado sucesor de la partida al ejecutar una accion valida.

    Proposito: definir la funcion sucesor de la partida por turnos.
    Precondiciones: ``accion`` es valida en ``estado`` (si no, se lanza ``ValueError``).
    Postcondiciones: devuelve un nuevo ``EstadoJuego`` con el turno cedido al otro bando. Si la accion es un
    movimiento, la unidad queda desplazada y el recurso recogido o transportado segun las reglas; si es una
    intercepcion (E8.1), nadie se mueve y el recurso pasa al interceptor mediante ``resolver_intercepcion``.
    ``estado_partida`` queda en ``"victoria_<bando>"`` si se cumplio la condicion objetivo. ``estado`` no se
    modifica.
    Complejidad: O(U) temporal y espacial por la validacion y la copia de la tupla de unidades.
    Uso de IA: Si.
    Intervencion de IA: Claude (Opus 5.5) propuso la implementacion y su documentacion; en E8.1 agrego la
    aplicacion de la intercepcion reutilizando ``resolver_intercepcion`` de E1.3.
    Validacion del estudiante: el estudiante reviso las reglas frente al enunciado y valido el metodo con
    pytest (tests/juego/test_reglas.py, tests/juego/test_tacticas.py y la exploracion de sucesores en
    tests/juego/test_espacio_estados.py).
    """
    if not es_accion_valida(escenario, estado, accion):
        raise ValueError(f"La accion {accion} no es valida en el estado actual.")
    if accion.tipo == INTERCEPTAR:
        sucesor = resolver_intercepcion(escenario, estado, accion.identificador_unidad)
    else:
        sucesor = desplazar_unidad(escenario, estado, accion)
    return replace(sucesor, turno_actual=_otro_bando(estado.turno_actual))


def generar_sucesores(escenario: Escenario, estado: EstadoJuego) -> tuple[tuple[Accion, EstadoJuego], ...]:
    """Devuelve cada accion valida de la partida junto con el estado que produce, en el orden de generacion."""
    return tuple((accion, aplicar_accion(escenario, estado, accion)) for accion in acciones_validas(escenario, estado))


def desplazar_unidad(escenario: Escenario, estado: EstadoJuego, accion: Accion) -> EstadoJuego:
    """Aplica el efecto de un movimiento sobre el estado sin cambiar el turno ni comprobar legalidad.

    Proposito: concentrar la transicion fisica (posicion, recogida y transporte del recurso, victoria) que
    comparten la partida por turnos y la navegacion de una sola unidad.
    Precondiciones: ``accion`` fue generada por ``generar_movimientos`` o ``acciones_validas`` para ``estado``.
    Postcondiciones: la unidad indicada queda en ``accion.destino``; si el recurso estaba libre en esa celda,
    la unidad pasa a ser su portador y ``posicion_recurso`` queda en ``None``; ``estado_partida`` es
    ``"victoria_<bando>"`` si el portador queda en su base y vuelve a ``"en_curso"`` si una victoria previa ya no
    se cumple (solo ocurre en navegacion, donde la unidad puede seguir moviendose). El turno se conserva y
    ``estado`` no se modifica.
    Complejidad: O(U log U) temporal y O(U) espacial por la reconstruccion canonica de la tupla de unidades.
    Uso de IA: Si.
    Intervencion de IA: Claude (Opus 5.5) implemento la implementacion y su documentacion; en E4.1 corrigio que la
    marca de victoria quedara fija al salir el portador de su base, lo que duplicaba estados en navegacion;
    Claude (Sonnet 5.5) movio la regla de recogida a ``recurso.recoger_recurso`` en E3.2, sin cambiar su efecto.
    Validacion del estudiante: el estudiante reviso las reglas frente al enunciado y valido el metodo con
    pytest (tests/juego/test_reglas.py y la exploracion de sucesores en tests/juego/test_espacio_estados.py).
    """
    unidades = tuple(
        replace(unidad, posicion=accion.destino) if unidad.identificador == accion.identificador_unidad else unidad
        for unidad in estado.unidades
    )
    sucesor = recoger_recurso(replace(estado, unidades=unidades), accion.identificador_unidad, accion.destino)
    ganador = obtener_ganador(escenario, sucesor)
    if ganador is not None:
        return replace(sucesor, estado_partida=f"victoria_{ganador}")
    if sucesor.estado_partida.startswith("victoria_"):
        return replace(sucesor, estado_partida=EN_CURSO)
    return sucesor


def costo_accion(escenario: Escenario, accion: Accion) -> int | float:
    """Calcula el costo de una accion como el costo del terreno de la celda destino.

    Proposito: definir el costo de las acciones exclusivamente desde el catalogo ``tipos_terreno`` del JSON,
    de modo que cambiar un costo en el escenario cambie el comportamiento sin tocar codigo.
    Precondiciones: ``accion.destino`` esta dentro del mapa y es transitable.
    Postcondiciones: devuelve el costo positivo declarado para el terreno destino; no modifica nada. En una
    intercepcion (E8.1) el destino es la celda del portador, por lo que cuesta lo mismo que entrar en ella.
    Complejidad: O(1) temporal y espacial.
    Uso de IA: Si.
    Intervencion de IA: Claude (Opus 5.5) propuso la implementacion y su documentacion.
    Validacion del estudiante: el estudiante valido con pytest que al cambiar el costo del terreno en el JSON
    (de 2 a 15) cambia el costo de la accion sin modificar codigo (tests/juego/test_reglas.py).
    """
    return escenario.obtener_costo(accion.destino)


def buscar_unidad(estado: EstadoJuego, identificador: str) -> Unidad:
    """Devuelve la unidad con el identificador dado o lanza ``ValueError`` si no existe en el estado."""
    unidad = _buscar_unidad(estado, identificador)
    if unidad is None:
        raise ValueError(f"No existe la unidad '{identificador}' en el estado.")
    return unidad


def _buscar_unidad(estado: EstadoJuego, identificador: str) -> Unidad | None:
    return next((unidad for unidad in estado.unidades if unidad.identificador == identificador), None)


def _otro_bando(bando: str) -> str:
    return BANDOS[1] if bando == BANDOS[0] else BANDOS[0]
