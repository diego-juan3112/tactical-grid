"""Reglas de transición de la partida: acciones válidas, sucesores, condición objetivo y costo.

Reglas deterministas definidas en E1.2 y E1.3:

- En cada turno, el bando en ``turno_actual`` elige una de sus unidades y la mueve una celda en dirección
  ortogonal (arriba, abajo, izquierda, derecha). No hay movimientos diagonales.
- El destino debe estar dentro del mapa, ser transitable y no estar ocupado por otra unidad de ningún bando.
- Si el recurso no tiene portador y una unidad entra en su celda, la unidad lo recoge automáticamente.
- El recurso viaja con su portador. Si el portador entra en la base de su propio bando, ese bando gana.
- Tras cada acción, el turno pasa al otro bando.
- El costo de una acción es el del terreno de la celda destino, leído del escenario cargado.
- Una partida terminada no tiene acciones válidas. Una unidad bloqueada no aporta acciones; si todo el bando está
  bloqueado, el turno pasa al adversario si este puede actuar, o se declara empate si ambos están bloqueados.
- La intercepción transfiere el recurso a una unidad adversaria sin eliminar unidades ni cambiar el turno.
- E8.1: una unidad ortogonalmente adyacente al portador rival puede usar su turno para interceptarlo (acción de
  tipo ``interceptar``): nadie se mueve, el recurso pasa al interceptor y el turno cambia como en cualquier
  acción. Es la única acción táctica con efecto propio; las demás tácticas son movimientos clasificados.
- La ausencia de ruta es un resultado de búsqueda y no modifica el estado del juego.
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
    """Determinar el bando ganador a partir del estado.

    Proposito: definir la condición objetivo de la partida: un bando gana cuando su unidad portadora del recurso se
    encuentra en la base de ese mismo bando.
    Precondiciones: ``estado`` es coherente con ``escenario``; si hay portador, es una unidad del estado.
    Postcondiciones: se devuelve ``"A"`` o ``"B"`` si hay ganador y ``None`` en otro caso; no se modifica nada.
    Complejidad: O(U) temporal y O(1) espacial, con U unidades.
    Uso de IA: Si.
    Intervencion de IA: Claude (Opus 5.5): implementación y documentación a partir del enunciado. Claude (Sonnet 5.5):
    delegación en ``recurso.bando_que_entrego_recurso`` sin cambiar el resultado (E3.2).
    Validacion del estudiante: pruebas de tests/juego/test_reglas.py y exploración completa de sucesores en
    tests/juego/test_espacio_estados.py.
    """
    return bando_que_entrego_recurso(escenario, estado)


def es_terminal(escenario: Escenario, estado: EstadoJuego) -> bool:
    """Indicar si hay victoria o empate por bloqueo total.

    Proposito: centralizar el reconocimiento de los resultados terminales de la partida.
    Precondiciones: ``estado`` es coherente con ``escenario``.
    Postcondiciones: se devuelve verdadero para una victoria vigente o para ``empate_bloqueo``; el estado no cambia.
    Complejidad: O(U) temporal y O(1) espacial, con U unidades.
    Uso de IA: Si.
    Intervencion de IA: Codex: extensión de la condición existente para reconocer el empate de E1.3.
    Validacion del estudiante: pruebas de tests/juego/test_reglas.py y tests/juego/test_partida.py: bloqueo
    individual, pase automático, empate por bloqueo total y victoria terminal.
    """
    return estado.estado_partida == EMPATE_BLOQUEO or obtener_ganador(escenario, estado) is not None


def generar_movimientos(
    escenario: Escenario, unidad: Unidad, ocupadas: frozenset[Posicion] = frozenset()
) -> tuple[Accion, ...]:
    """Generar los movimientos ortogonales de una unidad permitidos por el escenario.

    Proposito: concentrar en un solo punto la regla de movimiento que comparten la partida y la navegación.
    Precondiciones: la posición de ``unidad`` está dentro del mapa de ``escenario``.
    Postcondiciones: se devuelven, en el orden de ``DESPLAZAMIENTOS``, las acciones cuyo destino está dentro del mapa,
    es transitable según el JSON y no pertenece a ``ocupadas``. No se modifica nada.
    Complejidad: O(1) temporal y espacial: a lo sumo cuatro destinos con consultas O(1).
    Uso de IA: Si.
    Intervencion de IA: Claude (Opus 5.5): implementación y documentación.
    Validacion del estudiante: pruebas de tests/juego/test_reglas.py y exploración completa de sucesores en
    tests/juego/test_espacio_estados.py.
    """
    acciones = []
    for delta_fila, delta_columna in DESPLAZAMIENTOS:
        destino = Posicion(unidad.posicion.fila + delta_fila, unidad.posicion.columna + delta_columna)
        if escenario.contiene_posicion(destino) and escenario.es_transitable(destino) and destino not in ocupadas:
            acciones.append(Accion(unidad.identificador, unidad.posicion, destino))
    return tuple(acciones)


def generar_intercepcion(estado: EstadoJuego, unidad: Unidad) -> Accion | None:
    """Devolver la acción de interceptar al portador rival si ``unidad`` puede hacerlo, o ``None``.

    Proposito: definir la condición espacial de la intercepción de E1.3: estar junto al portador.
    Precondiciones: ``unidad`` pertenece a ``estado``; la partida no es terminal (lo comprueba quien llama).
    Postcondiciones: se devuelve ``Accion(unidad.identificador, unidad.posicion, portador.posicion, INTERCEPTAR)``
    solo si hay portador, es de otro bando y está a distancia Manhattan 1 de ``unidad``; en otro caso, ``None``. No
    se modifica nada.
    Complejidad: O(U) temporal para localizar al portador y O(1) espacial.
    Uso de IA: Si.
    Intervencion de IA: Claude (Opus 5.5): regla de adyacencia e implementación (E8.1).
    Validacion del estudiante: pruebas de tests/juego/test_tacticas.py: portador adyacente, no adyacente, aliado, en
    diagonal y ausencia de portador.
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
    """Enumerar las acciones legales del bando en turno.

    Proposito: definir el conjunto de acciones válidas de la partida, común a Minimax, alfa-beta y la interfaz.
    Precondiciones: ``estado`` es coherente con ``escenario``.
    Postcondiciones: se devuelve una tupla vacía si la partida terminó o si todas las unidades del bando en turno
    están bloqueadas; una unidad bloqueada no impide las acciones de sus aliadas. En otro caso se devuelven las
    acciones de cada unidad del bando en orden de identificador: primero sus movimientos en el orden de
    ``DESPLAZAMIENTOS`` y, si está junto al portador rival, la intercepción (E8.1). El estado no cambia.
    Complejidad: O(U^2) temporal en el peor caso, porque cada unidad puede localizar al portador, y O(U) espacial;
    cada unidad aporta a lo sumo cinco acciones (cuatro movimientos y una intercepción).
    Uso de IA: Si.
    Intervencion de IA: Claude (Opus 5.5): implementación y documentación; intercepción al final de las acciones de
    cada unidad (E8.1).
    Validacion del estudiante: pruebas de tests/juego/test_reglas.py y exploración completa de sucesores en
    tests/juego/test_espacio_estados.py.
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
    """Aplicar el pase automático o el empate cuando el bando activo no tiene acciones.

    Proposito: resolver de forma determinista el bloqueo del bando activo sin generar pases recursivos.
    Precondiciones: ``estado`` es coherente con ``escenario`` y sus unidades representan la situación actual.
    Postcondiciones: el estado se conserva si hay acciones activas o la partida ya terminó; el turno pasa una vez si
    solo el adversario puede actuar; si ninguno puede, se devuelve un estado con ``empate_bloqueo``. El original no se
    modifica.
    Complejidad: O(U) temporal y espacial, por consultar las acciones de ambos bandos y copiar el estado.
    Uso de IA: Si.
    Intervencion de IA: Codex: implementación de la transición de E1.3.
    Validacion del estudiante: pruebas de tests/juego/test_reglas.py: bando bloqueado sin acciones, pase al
    adversario, empate por bloqueo total sin pases repetidos y determinismo de las reglas de borde.
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
    """Transferir atómicamente el recurso del portador actual a una unidad adversaria.

    Proposito: aplicar la consecuencia en el dominio de una intercepción ya establecida, sin definir su acción
    espacial.
    Precondiciones: la partida está en curso, hay un portador existente y el interceptor existe, pertenece al otro
    bando y no es el portador actual.
    Postcondiciones: se devuelve un estado nuevo con el interceptor como portador y ``posicion_recurso=None``; se
    conservan las unidades y el turno, y se registra la victoria si el nuevo portador está en su propia base. El estado
    original no cambia. Las condiciones inválidas lanzan ``ValueError``.
    Complejidad: O(U) temporal y espacial para localizar las unidades y crear el estado inmutable.
    Uso de IA: Si.
    Intervencion de IA: Codex: transferencia atómica de E1.3.
    Validacion del estudiante: pruebas de tests/juego/test_reglas.py: transferencia sin cambio de turno ni pérdida de
    unidades, victoria al interceptar en la propia base y rechazo de interceptores inválidos.
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
    """Comprobar si una acción es legal en el estado dado según las reglas de la partida.

    Proposito: permitir que la verificación de soluciones y de decisiones Minimax compruebe la legalidad.
    Precondiciones: ``estado`` es coherente con ``escenario``.
    Postcondiciones: se devuelve ``True`` solo si ``accion`` pertenece a ``acciones_validas(escenario, estado)``.
    Complejidad: O(U) temporal y espacial.
    Uso de IA: Si.
    Intervencion de IA: Claude (Opus 5.5): implementación y documentación.
    Validacion del estudiante: pruebas de tests/juego/test_reglas.py y de los verificadores de Minimax y alfa-beta en
    tests/algoritmos/.
    """
    return accion in acciones_validas(escenario, estado)


def aplicar_accion(escenario: Escenario, estado: EstadoJuego, accion: Accion) -> EstadoJuego:
    """Construir el estado sucesor de la partida al ejecutar una acción válida.

    Proposito: definir la función sucesor de la partida por turnos.
    Precondiciones: ``accion`` es válida en ``estado``; en otro caso se lanza ``ValueError``.
    Postcondiciones: se devuelve un ``EstadoJuego`` nuevo con el turno del otro bando. En un movimiento, la unidad
    queda desplazada y el recurso recogido o transportado según las reglas; en una intercepción (E8.1) nadie se mueve
    y el recurso pasa al interceptor mediante ``resolver_intercepcion``. ``estado_partida`` queda en
    ``"victoria_<bando>"`` si se cumple la condición objetivo. ``estado`` no cambia.
    Complejidad: O(U) temporal y espacial por la validación y la copia de la tupla de unidades.
    Uso de IA: Si.
    Intervencion de IA: Claude (Opus 5.5): implementación y documentación; aplicación de la intercepción con
    ``resolver_intercepcion`` de E1.3 (E8.1).
    Validacion del estudiante: pruebas de tests/juego/test_reglas.py y tests/juego/test_tacticas.py, y exploración
    completa de sucesores en tests/juego/test_espacio_estados.py.
    """
    if not es_accion_valida(escenario, estado, accion):
        raise ValueError(f"La accion {accion} no es valida en el estado actual.")
    if accion.tipo == INTERCEPTAR:
        sucesor = resolver_intercepcion(escenario, estado, accion.identificador_unidad)
    else:
        sucesor = desplazar_unidad(escenario, estado, accion)
    return replace(sucesor, turno_actual=_otro_bando(estado.turno_actual))


def generar_sucesores(escenario: Escenario, estado: EstadoJuego) -> tuple[tuple[Accion, EstadoJuego], ...]:
    """Devolver cada acción válida de la partida junto con el estado que produce, en el orden de generación."""
    return tuple((accion, aplicar_accion(escenario, estado, accion)) for accion in acciones_validas(escenario, estado))


def desplazar_unidad(escenario: Escenario, estado: EstadoJuego, accion: Accion) -> EstadoJuego:
    """Aplicar el efecto de un movimiento sobre el estado sin cambiar el turno ni comprobar la legalidad.

    Proposito: concentrar la transición física (posición, recogida y transporte del recurso, victoria) que comparten
    la partida por turnos y la navegación de una sola unidad.
    Precondiciones: ``accion`` proviene de ``generar_movimientos`` o ``acciones_validas`` para ``estado``.
    Postcondiciones: la unidad indicada queda en ``accion.destino``; si el recurso estaba libre en esa celda, la unidad
    pasa a ser su portadora y ``posicion_recurso`` queda en ``None``; ``estado_partida`` es ``"victoria_<bando>"`` si el
    portador queda en su base y vuelve a ``"en_curso"`` si una victoria previa deja de cumplirse, lo que solo ocurre en
    navegación. El turno se conserva y ``estado`` no cambia.
    Complejidad: O(U log U) temporal y O(U) espacial por la reconstrucción canónica de la tupla de unidades.
    Uso de IA: Si.
    Intervencion de IA: Claude (Opus 5.5): implementación y documentación; corrección de la marca de victoria que
    quedaba fija al salir el portador de su base y duplicaba estados en navegación (E4.1). Claude (Sonnet 5.5):
    traslado de la regla de recogida a ``recurso.recoger_recurso`` sin cambiar su efecto (E3.2).
    Validacion del estudiante: pruebas de tests/juego/test_reglas.py y exploración completa de sucesores en
    tests/juego/test_espacio_estados.py.
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
    """Calcular el costo de una acción como el del terreno de la celda destino.

    Proposito: definir el costo de las acciones exclusivamente con el catálogo ``tipos_terreno`` del JSON, para que
    cambiar un costo en el escenario cambie el comportamiento sin tocar código.
    Precondiciones: ``accion.destino`` está dentro del mapa y es transitable.
    Postcondiciones: se devuelve el costo positivo declarado para el terreno destino; no se modifica nada. En una
    intercepción (E8.1) el destino es la celda del portador, por lo que cuesta lo mismo que entrar en ella.
    Complejidad: O(1) temporal y espacial.
    Uso de IA: Si.
    Intervencion de IA: Claude (Opus 5.5): implementación y documentación.
    Validacion del estudiante: prueba ``test_costo_de_la_accion_es_el_del_terreno_destino_en_el_json`` de
    tests/juego/test_reglas.py: al cambiar a 15 el costo de un terreno en el JSON, el costo de la acción cambia sin
    modificar código.
    """
    return escenario.obtener_costo(accion.destino)


def buscar_unidad(estado: EstadoJuego, identificador: str) -> Unidad:
    """Devolver la unidad con el identificador dado o lanzar ``ValueError`` si no existe en el estado."""
    unidad = _buscar_unidad(estado, identificador)
    if unidad is None:
        raise ValueError(f"No existe la unidad '{identificador}' en el estado.")
    return unidad


def _buscar_unidad(estado: EstadoJuego, identificador: str) -> Unidad | None:
    return next((unidad for unidad in estado.unidades if unidad.identificador == identificador), None)


def _otro_bando(bando: str) -> str:
    return BANDOS[1] if bando == BANDOS[0] else BANDOS[0]
