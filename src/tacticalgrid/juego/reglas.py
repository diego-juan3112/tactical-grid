"""Reglas de transicion de la partida: acciones validas, sucesores, condicion objetivo y costo.

Reglas deterministas definidas en E1.2:

- En cada turno el bando en ``turno_actual`` elige una de sus unidades y la mueve una celda en direccion
  ortogonal (arriba, abajo, izquierda, derecha). No hay movimientos diagonales.
- El destino debe estar dentro del mapa, ser transitable y no estar ocupado por otra unidad (de cualquier bando).
- Si el recurso no tiene portador y una unidad entra en su celda, lo recoge automaticamente.
- El recurso viaja con su portador. Si el portador entra en la base de su propio bando, ese bando gana.
- Tras cada accion el turno pasa al otro bando.
- El costo de una accion es el costo del terreno de la celda destino, leido del escenario cargado.
- Una partida terminada no tiene acciones validas. Un bando sin movimientos posibles (todas sus unidades
  bloqueadas) tampoco tiene acciones validas en ese estado.
"""

from dataclasses import replace

from tacticalgrid.escenario.escenario import Escenario, Posicion

from .accion import DESPLAZAMIENTOS, Accion
from .estado import EstadoJuego
from .unidad import Unidad

EN_CURSO = "en_curso"
BANDOS = ("A", "B")


def obtener_ganador(escenario: Escenario, estado: EstadoJuego) -> str | None:
    """Determina el bando ganador a partir de la informacion del estado.

    Proposito: definir la condicion objetivo de la partida: un bando gana cuando su unidad portadora del
    recurso se encuentra en la base de ese mismo bando.
    Precondiciones: ``estado`` es coherente con ``escenario`` (si hay portador, es una unidad del estado).
    Postcondiciones: devuelve ``"A"`` o ``"B"`` si hay ganador y ``None`` en otro caso; no modifica nada.
    Complejidad: O(U) temporal y O(1) espacial, donde U es el numero de unidades.
    Uso de IA: Si.
    Intervencion de IA: Claude (Opus 5.5) propuso la implementacion y su documentacion a partir del enunciado.
    Validacion del estudiante: el estudiante reviso las reglas frente al enunciado y valido el metodo con
    pytest (tests/juego/test_reglas.py y la exploracion de sucesores en tests/juego/test_espacio_estados.py).
    """
    portador = _buscar_unidad(estado, estado.portador_recurso) if estado.portador_recurso else None
    if portador is not None and portador.posicion == escenario.bases[portador.bando]:
        return portador.bando
    return None


def es_terminal(escenario: Escenario, estado: EstadoJuego) -> bool:
    """Indica si la partida termino porque algun bando ya cumplio la condicion objetivo."""
    return obtener_ganador(escenario, estado) is not None


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


def acciones_validas(escenario: Escenario, estado: EstadoJuego) -> tuple[Accion, ...]:
    """Enumera las acciones legales del bando en turno.

    Proposito: definir el conjunto de acciones validas de la partida, comun a Minimax, alfa-beta y la interfaz.
    Precondiciones: ``estado`` es coherente con ``escenario``.
    Postcondiciones: devuelve una tupla vacia si la partida termino o si todas las unidades del bando en
    turno estan bloqueadas; en otro caso, los movimientos de cada unidad del bando, recorridas en orden de
    identificador y, para cada una, en el orden de ``DESPLAZAMIENTOS``. No modifica el estado.
    Complejidad: O(U) temporal y espacial: el conjunto de ocupadas se calcula una vez y cada unidad aporta a
    lo sumo cuatro acciones.
    Uso de IA: Si.
    Intervencion de IA: Claude (Opus 5.5) propuso la implementacion y su documentacion.
    Validacion del estudiante: el estudiante reviso las reglas frente al enunciado y valido el metodo con
    pytest (tests/juego/test_reglas.py y la exploracion de sucesores en tests/juego/test_espacio_estados.py).
    """
    if es_terminal(escenario, estado):
        return ()
    ocupadas = frozenset(unidad.posicion for unidad in estado.unidades)
    return tuple(
        accion
        for unidad in estado.unidades
        if unidad.bando == estado.turno_actual
        for accion in generar_movimientos(escenario, unidad, ocupadas)
    )


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
    Postcondiciones: devuelve un nuevo ``EstadoJuego`` con la unidad desplazada, el recurso recogido o
    transportado segun las reglas, ``estado_partida`` actualizado a ``"victoria_<bando>"`` si se cumplio la
    condicion objetivo y el turno cedido al otro bando. ``estado`` no se modifica.
    Complejidad: O(U) temporal y espacial por la validacion y la copia de la tupla de unidades.
    Uso de IA: Si.
    Intervencion de IA: Claude (Opus 5.5) propuso la implementacion y su documentacion.
    Validacion del estudiante: el estudiante reviso las reglas frente al enunciado y valido el metodo con
    pytest (tests/juego/test_reglas.py y la exploracion de sucesores en tests/juego/test_espacio_estados.py).
    """
    if not es_accion_valida(escenario, estado, accion):
        raise ValueError(f"La accion {accion} no es valida en el estado actual.")
    desplazado = desplazar_unidad(escenario, estado, accion)
    return replace(desplazado, turno_actual=_otro_bando(estado.turno_actual))


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
    Intervencion de IA: Claude (Opus 5.5) propuso la implementacion y su documentacion; en E4.1 corrigio que la
    marca de victoria quedara fija al salir el portador de su base, lo que duplicaba estados en navegacion.
    Validacion del estudiante: el estudiante reviso las reglas frente al enunciado y valido el metodo con
    pytest (tests/juego/test_reglas.py y la exploracion de sucesores en tests/juego/test_espacio_estados.py).
    """
    unidades = tuple(
        replace(unidad, posicion=accion.destino) if unidad.identificador == accion.identificador_unidad else unidad
        for unidad in estado.unidades
    )
    portador = estado.portador_recurso
    posicion_recurso = estado.posicion_recurso
    if portador is None and posicion_recurso == accion.destino:
        portador = accion.identificador_unidad
        posicion_recurso = None
    sucesor = replace(estado, unidades=unidades, portador_recurso=portador, posicion_recurso=posicion_recurso)
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
    Postcondiciones: devuelve el costo positivo declarado para el terreno destino; no modifica nada.
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
