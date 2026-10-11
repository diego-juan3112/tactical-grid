"""Reglas del recurso estrategico (E3.2): recogerlo, transportarlo y entregarlo en la base propia.

Reglas deterministas, simetricas para los bandos A y B:

- El recurso empieza libre en una celda (``posicion_recurso``) o ya en poder de una unidad (``portador_recurso``).
- Una unidad lo recoge automaticamente al entrar en la celda donde esta libre; entonces ``posicion_recurso``
  pasa a ``None`` y la unidad queda registrada como portadora.
- Mientras tiene portador, el recurso viaja con el: su posicion es la de la unidad portadora.
- Un bando gana cuando su unidad portadora se encuentra en la base de ese mismo bando.

Este modulo solo consulta y transforma ``EstadoJuego``: no lee JSON, no conoce Pygame ni los algoritmos.
"""

from dataclasses import replace

from tacticalgrid.escenario.escenario import Escenario, Posicion

from .estado import EstadoJuego
from .unidad import Unidad


def obtener_portador(estado: EstadoJuego) -> Unidad | None:
    """Devuelve la unidad que transporta el recurso, o ``None`` si el recurso esta libre.

    Proposito: localizar al portador a partir del identificador guardado en el estado.
    Precondiciones: si ``estado.portador_recurso`` no es ``None``, identifica una unidad del estado.
    Postcondiciones: no modifica el estado; devuelve ``None`` si nadie transporta el recurso o si el
    identificador no corresponde a ninguna unidad.
    Complejidad: O(U) temporal y O(1) espacial, donde U es el numero de unidades.
    Uso de IA: Si.
    Intervencion de IA: Claude (Sonnet 5.5) implemento la logica extrayendola de reglas.py y documentandola para E3.2.
    Validacion del estudiante: Aprobamos los tests realizados en tests/juego/test_recurso.py y
    tambien se valida que la implementacion sea correcta de acuerdo a la logica de la issue E3.2.
    """
    if estado.portador_recurso is None:
        return None
    return next((unidad for unidad in estado.unidades if unidad.identificador == estado.portador_recurso), None)


def posicion_del_recurso(estado: EstadoJuego) -> Posicion | None:
    """Devuelve la celda donde esta el recurso, tanto si esta libre como si lo transporta una unidad.

    Proposito: dar a las demas capas una unica respuesta a "donde esta el recurso", sin que cada una tenga que
    distinguir el recurso libre del transportado (heuristicas, funcion de utilidad e interfaz).
    Precondiciones: ``estado`` es coherente: tiene portador o ``posicion_recurso``, no ambos.
    Postcondiciones: devuelve ``posicion_recurso`` si esta libre y la posicion del portador si lo transporta;
    ``None`` solo si el estado es incoherente (portador inexistente). No modifica el estado.
    Complejidad: O(U) temporal y O(1) espacial.
    Uso de IA: Si.
    Intervencion de IA: Claude (Sonnet 5.5) Implemento la logica y documentandola para E3.2.
    Validacion del estudiante: pendiente de revision del equipo; cubierta por tests/juego/test_recurso.py.
    """
    portador = obtener_portador(estado)
    return portador.posicion if portador is not None else estado.posicion_recurso


def recoger_recurso(estado: EstadoJuego, identificador_unidad: str, destino: Posicion) -> EstadoJuego:
    """Aplica la recogida del recurso cuando una unidad entra en la celda donde esta libre.

    Proposito: concentrar la regla de recogida que comparten la partida por turnos y la navegacion.
    Precondiciones: ``identificador_unidad`` identifica una unidad del estado y ``destino`` es la celda a la
    que esa unidad acaba de entrar (el movimiento ya esta resuelto).
    Postcondiciones: si el recurso no tiene portador y esta libre en ``destino``, devuelve un estado nuevo con
    la unidad como portadora y ``posicion_recurso=None``; en cualquier otro caso devuelve el mismo ``estado``.
    Nunca modifica el estado recibido.
    Complejidad: O(1) temporal y espacial.
    Uso de IA: Si.
    Intervencion de IA: Claude (Sonnet 5.5) implemento la logica y documentandola en E3.2, extrayendola
    de ``desplazar_unidad`` sin cambiar su comportamiento.
    Validacion del estudiante: Revision aprobada por pruebas en tests/juego/test_recurso.py y
    por las pruebas de reglas y de navegacion que ya ejercitaban esta transicion.
    """
    if estado.portador_recurso is None and estado.posicion_recurso == destino:
        return replace(estado, portador_recurso=identificador_unidad, posicion_recurso=None)
    return estado


def bando_que_entrego_recurso(escenario: Escenario, estado: EstadoJuego) -> str | None:
    """Devuelve el bando cuyo portador esta en su propia base, que es la condicion de victoria.

    Proposito: definir en un solo lugar cuando se gana la partida.
    Precondiciones: ``estado`` es coherente con ``escenario`` (las bases A y B existen).
    Postcondiciones: devuelve ``"A"`` o ``"B"`` si el portador esta en la base de su bando y ``None`` en otro
    caso (sin portador, o portador en una base ajena o en otra celda). No modifica nada.
    Complejidad: O(U) temporal y O(1) espacial, donde U es el numero de unidades.
    Uso de IA: Si.
    Intervencion de IA: Claude (Sonnet 5.5) extrajo esta condicion de ``obtener_ganador`` para E3.2.
    Validacion del estudiante: aprobada por pruebas en tests/juego/test_recurso.py y
    por las pruebas de condicion objetivo de tests/juego/test_reglas.py.
    """
    portador = obtener_portador(estado)
    if portador is not None and portador.posicion == escenario.bases[portador.bando]:
        return portador.bando
    return None
