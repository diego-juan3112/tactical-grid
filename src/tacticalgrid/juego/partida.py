"""Orquestacion sincrona y paso a paso de los turnos de una partida."""

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
    """Devuelve las unidades activas que tienen al menos una accion legal.

    Proposito: exponer las opciones de unidad del turno sin elegir por el consumidor.
    Precondiciones: ``escenario`` y ``estado`` representan una partida coherente.
    Postcondiciones: devuelve una tupla ordenada por identificador con unidades del bando activo que aparecen
    en ``acciones_validas``; devuelve una tupla vacia si el estado es terminal. No modifica el estado.
    Complejidad: O(U + A) temporal y O(U + A) espacial, donde U es el numero de unidades y A el de acciones
    legales del bando activo.
    Uso de IA: Si.
    Intervencion de IA: Codex implemento esta consulta y sus pruebas para E3.1 a partir de la decision aprobada.
    Validacion del estudiante: Se reviso manualmente la implementacion de E3.1 contra sus criterios de aceptacion.
    Se verifico que solo sean seleccionables unidades del bando activo con acciones legales, que las acciones por
    unidad reutilicen las reglas de E1.2, que el cambio de turno ocurra exactamente una vez, que los bloqueos
    reutilicen E1.3, que la seleccion permanezca fuera de EstadoJuego y que el flujo sea secuencial y simetrico
    para A y B. Tambien se ejecutaron las pruebas especificas de E3.1, las pruebas de juego y la suite completa.
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
    """Devuelve las acciones legales de una unidad activa concreta.

    Proposito: presentar al consumidor solo las acciones E1.2 asociadas a su unidad elegida.
    Precondiciones: ``escenario`` y ``estado`` son coherentes; ``identificador`` identifica una unidad existente.
    Postcondiciones: devuelve las acciones legales en el orden de E1.2, o una tupla vacia para una unidad activa
    bloqueada; lanza ``ValueError`` si la partida es terminal, la unidad no existe o pertenece al adversario.
    No modifica el estado.
    Complejidad: O(U + A) temporal y O(A) espacial, donde U es el numero de unidades y A el de acciones legales.
    Uso de IA: Si.
    Intervencion de IA: Codex implemento esta consulta y sus pruebas para E3.1 a partir de la decision aprobada.
    Validacion del estudiante: Se reviso manualmente la implementacion de E3.1 contra sus criterios de aceptacion.
    Se verifico que solo sean seleccionables unidades del bando activo con acciones legales, que las acciones por
    unidad reutilicen las reglas de E1.2, que el cambio de turno ocurra exactamente una vez, que los bloqueos
    reutilicen E1.3, que la seleccion permanezca fuera de EstadoJuego y que el flujo sea secuencial y simetrico
    para A y B. Tambien se ejecutaron las pruebas especificas de E3.1, las pruebas de juego y la suite completa.
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
    """Resuelve el pase por bloqueo antes de que el consumidor solicite elecciones.

    Proposito: entregar el estado desde el que puede comenzar el turno jugable siguiente.
    Precondiciones: ``escenario`` y ``estado`` representan una partida coherente.
    Postcondiciones: devuelve el mismo estado si es terminal o el bando actual puede actuar; en otro caso
    reutiliza E1.3 para pasar una vez al adversario o declarar ``empate_bloqueo``. No modifica el original.
    Complejidad: O(U + A) temporal y O(U + A) espacial, donde U es el numero de unidades y A las acciones
    examinadas por las reglas de bloqueo.
    Uso de IA: Si.
    Intervencion de IA: Codex implemento esta orquestacion para E3.1 reutilizando la regla aprobada de E1.3.
    Validacion del estudiante: Se reviso manualmente la implementacion de E3.1 contra sus criterios de aceptacion.
    Se verifico que solo sean seleccionables unidades del bando activo con acciones legales, que las acciones por
    unidad reutilicen las reglas de E1.2, que el cambio de turno ocurra exactamente una vez, que los bloqueos
    reutilicen E1.3, que la seleccion permanezca fuera de EstadoJuego y que el flujo sea secuencial y simetrico
    para A y B. Tambien se ejecutaron las pruebas especificas de E3.1, las pruebas de juego y la suite completa.
    """
    if es_terminal(escenario, estado):
        return estado
    return resolver_bloqueo_turno(escenario, estado)
