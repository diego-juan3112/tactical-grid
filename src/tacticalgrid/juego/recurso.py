"""Reglas del recurso estratégico (E3.2): recogerlo, transportarlo y entregarlo en la base propia.

Reglas deterministas y simétricas para los bandos A y B:

- El recurso empieza libre en una celda (``posicion_recurso``) o en poder de una unidad (``portador_recurso``).
- Una unidad lo recoge automáticamente al entrar en la celda donde está libre; ``posicion_recurso`` pasa a
  ``None`` y la unidad queda registrada como portadora.
- Mientras tiene portador, el recurso viaja con él: su posición es la de la unidad portadora.
- Un bando gana cuando su unidad portadora se encuentra en la base de ese mismo bando.

Este módulo solo consulta y transforma ``EstadoJuego``: no lee JSON ni depende de Pygame ni de los algoritmos.
"""

from dataclasses import replace

from tacticalgrid.escenario.escenario import Escenario, Posicion

from .estado import EstadoJuego
from .unidad import Unidad


def obtener_portador(estado: EstadoJuego) -> Unidad | None:
    """Devolver la unidad que transporta el recurso, o ``None`` si el recurso está libre.

    Proposito: localizar al portador a partir del identificador guardado en el estado.
    Precondiciones: si ``estado.portador_recurso`` no es ``None``, corresponde a una unidad del estado.
    Postcondiciones: se devuelve ``None`` si nadie transporta el recurso o si el identificador no corresponde a ninguna
    unidad; el estado no cambia.
    Complejidad: O(U) temporal y O(1) espacial, con U unidades.
    Uso de IA: Si.
    Intervencion de IA: Claude (Sonnet 5.5): extracción desde reglas.py y documentación (E3.2).
    Validacion del estudiante: pruebas de tests/juego/test_recurso.py.
    """
    if estado.portador_recurso is None:
        return None
    return next((unidad for unidad in estado.unidades if unidad.identificador == estado.portador_recurso), None)


def posicion_del_recurso(estado: EstadoJuego) -> Posicion | None:
    """Devolver la celda del recurso, tanto si está libre como si lo transporta una unidad.

    Proposito: dar a las demás capas (heurísticas, utilidad e interfaz) una única respuesta sobre la ubicación del
    recurso, sin distinguir entre recurso libre y transportado.
    Precondiciones: ``estado`` es coherente: tiene portador o ``posicion_recurso``, no ambos.
    Postcondiciones: se devuelve ``posicion_recurso`` si está libre y la posición del portador si lo transporta;
    ``None`` solo si el estado es incoherente (portador inexistente). El estado no cambia.
    Complejidad: O(U) temporal y O(1) espacial.
    Uso de IA: Si.
    Intervencion de IA: Claude (Sonnet 5.5): implementación y documentación (E3.2).
    Validacion del estudiante: pruebas de tests/juego/test_recurso.py.
    """
    portador = obtener_portador(estado)
    return portador.posicion if portador is not None else estado.posicion_recurso


def recoger_recurso(estado: EstadoJuego, identificador_unidad: str, destino: Posicion) -> EstadoJuego:
    """Aplicar la recogida del recurso cuando una unidad entra en la celda donde está libre.

    Proposito: concentrar la regla de recogida que comparten la partida por turnos y la navegación.
    Precondiciones: ``identificador_unidad`` corresponde a una unidad del estado y ``destino`` es la celda a la que
    esa unidad acaba de entrar; el movimiento ya está resuelto.
    Postcondiciones: si el recurso no tiene portador y está libre en ``destino``, se devuelve un estado nuevo con la
    unidad como portadora y ``posicion_recurso=None``; en cualquier otro caso se devuelve el mismo ``estado``. El
    estado recibido nunca se modifica.
    Complejidad: O(1) temporal y espacial.
    Uso de IA: Si.
    Intervencion de IA: Claude (Sonnet 5.5): extracción desde ``desplazar_unidad`` sin cambiar su comportamiento, y
    documentación (E3.2).
    Validacion del estudiante: pruebas de tests/juego/test_recurso.py y pruebas de reglas y navegación que ejercitan
    esta transición.
    """
    if estado.portador_recurso is None and estado.posicion_recurso == destino:
        return replace(estado, portador_recurso=identificador_unidad, posicion_recurso=None)
    return estado


def bando_que_entrego_recurso(escenario: Escenario, estado: EstadoJuego) -> str | None:
    """Devolver el bando cuyo portador está en su propia base: la condición de victoria.

    Proposito: definir en un solo lugar cuándo se gana la partida.
    Precondiciones: ``estado`` es coherente con ``escenario``; las bases A y B existen.
    Postcondiciones: se devuelve ``"A"`` o ``"B"`` si el portador está en la base de su bando, y ``None`` en otro caso
    (sin portador, o con el portador en una base ajena o en otra celda). No se modifica nada.
    Complejidad: O(U) temporal y O(1) espacial, con U unidades.
    Uso de IA: Si.
    Intervencion de IA: Claude (Sonnet 5.5): extracción de esta condición desde ``obtener_ganador`` (E3.2).
    Validacion del estudiante: pruebas de tests/juego/test_recurso.py y pruebas de condición objetivo de
    tests/juego/test_reglas.py.
    """
    portador = obtener_portador(estado)
    if portador is not None and portador.posicion == escenario.bases[portador.bando]:
        return portador.bando
    return None
