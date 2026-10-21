"""Orquestación síncrona y paso a paso de los turnos de una partida."""

from tacticalgrid.escenario.escenario import Escenario

from .accion import Accion
from .estado import EstadoJuego
from .reglas import (
    acciones_validas,
    buscar_unidad,
    es_terminal,
    resolver_bloqueo_turno,
)
from .unidad import Unidad


def unidades_seleccionables(escenario: Escenario, estado: EstadoJuego) -> tuple[Unidad, ...]:
    """Devolver las unidades activas que tienen al menos una acción legal.

    Proposito: exponer las opciones de unidad del turno sin elegir por el consumidor.
    Precondiciones: ``escenario`` y ``estado`` representan una partida coherente.
    Postcondiciones: se devuelve una tupla ordenada por identificador con las unidades del bando activo presentes en
    ``acciones_validas``, o una tupla vacía si el estado es terminal. El estado no cambia.
    Complejidad: O(U + A) temporal y espacial, con U unidades y A acciones legales del bando activo.
    Uso de IA: Si.
    Intervencion de IA: Codex: implementación de la consulta y sus pruebas (E3.1).
    Validacion del estudiante: pruebas de tests/juego/test_partida.py: solo el bando activo es seleccionable, una
    unidad bloqueada no se ofrece y una victoria terminal no ofrece unidades.
    """
    identificadores_con_acciones = {accion.identificador_unidad for accion in acciones_validas(escenario, estado)}
    return tuple(
        unidad
        for unidad in estado.unidades
        if unidad.bando == estado.turno_actual and unidad.identificador in identificadores_con_acciones
    )


def acciones_para_unidad(
    escenario: Escenario, estado: EstadoJuego, identificador: str
) -> tuple[Accion, ...]:
    """Devolver las acciones legales de una unidad activa concreta.

    Proposito: presentar al consumidor solo las acciones de E1.2 asociadas a la unidad elegida.
    Precondiciones: ``escenario`` y ``estado`` son coherentes; ``identificador`` corresponde a una unidad existente.
    Postcondiciones: se devuelven las acciones legales en el orden de E1.2, o una tupla vacía para una unidad activa
    bloqueada; se lanza ``ValueError`` si la partida es terminal, la unidad no existe o pertenece al adversario. El
    estado no cambia.
    Complejidad: O(U + A) temporal y O(A) espacial, con U unidades y A acciones legales.
    Uso de IA: Si.
    Intervencion de IA: Codex: implementación de la consulta y sus pruebas (E3.1).
    Validacion del estudiante: pruebas de tests/juego/test_partida.py: filtrado y orden de E1.2, rechazo de unidades
    adversarias o inexistentes y cero acciones para una unidad bloqueada.
    """
    if es_terminal(escenario, estado):
        raise ValueError("No se pueden consultar acciones durante una partida terminada.")
    unidad = buscar_unidad(estado, identificador)
    if unidad.bando != estado.turno_actual:
        raise ValueError(f"La unidad '{identificador}' no pertenece al bando en turno.")
    return tuple(
        accion
        for accion in acciones_validas(escenario, estado)
        if accion.identificador_unidad == identificador
    )


def preparar_turno(escenario: Escenario, estado: EstadoJuego) -> EstadoJuego:
    """Resolver el pase por bloqueo antes de que el consumidor solicite elecciones.

    Proposito: entregar el estado desde el que comienza el siguiente turno jugable.
    Precondiciones: ``escenario`` y ``estado`` representan una partida coherente.
    Postcondiciones: se devuelve el mismo estado si es terminal o si el bando actual puede actuar; en otro caso se
    reutiliza la regla de E1.3 para pasar una vez al adversario o declarar ``empate_bloqueo``. El original no cambia.
    Complejidad: O(U + A) temporal y espacial, con U unidades y A acciones examinadas por las reglas de bloqueo.
    Uso de IA: Si.
    Intervencion de IA: Codex: orquestación de E3.1 sobre la regla de bloqueo de E1.3.
    Validacion del estudiante: pruebas de tests/juego/test_partida.py: bloqueo individual sin pase, pase único del
    bando bloqueado, empate por bloqueo total, simetría entre bandos y ausencia de mutación.
    """
    if es_terminal(escenario, estado):
        return estado
    return resolver_bloqueo_turno(escenario, estado)
