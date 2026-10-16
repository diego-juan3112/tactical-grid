"""Orden configurable de las acciones que exploran Minimax y alfa-beta (E8.6, caso minimo 9).

El enunciado pide cambiar el orden de generacion de acciones y analizar como afecta la cantidad de poda. El orden
no cambia el valor Minimax de un estado (el maximo o el minimo de un conjunto no depende del orden en que se
recorre), pero si cambia cuanto poda alfa-beta: si las mejores jugadas se exploran primero, alfa y beta se ajustan
antes y se cortan mas ramas. Ante un empate de valor ambos algoritmos conservan la primera accion, de modo que con
otro orden la accion elegida puede ser otra de igual valor.

Ordenes disponibles:

- ``generacion``: el de ``acciones_tacticas`` (unidades por identificador y movimientos arriba, abajo, izquierda,
  derecha). Es el orden por defecto, el mismo de E8.3 y E8.4.
- ``inverso``: el orden de generacion al reves.
- ``tactico``: primero las acciones de mayor impacto segun su tipo tactico (E8.1): interceptar al portador, avanzar
  con el recurso, aproximarse al recurso, bloquear, perseguir, proteger y, al final, reposicionar. Las acciones del
  mismo tipo conservan el orden de generacion, por lo que el resultado es determinista.

El orden se puede cambiar sin modificar codigo, desde la consola (``--orden``) o desde el campo propio
``juego.orden_acciones`` del escenario.
"""

from collections.abc import Mapping

from tacticalgrid.juego.tacticas import (
    APROXIMARSE_AL_RECURSO,
    AVANZAR,
    BLOQUEAR_POSICION,
    INTERCEPTAR_PORTADOR,
    PERSEGUIR_PORTADOR,
    PROTEGER_ZONA,
    REPOSICIONAR,
    AccionTactica,
)

ORDEN_GENERACION = "generacion"
ORDEN_INVERSO = "inverso"
ORDEN_TACTICO = "tactico"
ORDENES = (ORDEN_GENERACION, ORDEN_INVERSO, ORDEN_TACTICO)
CLAVE_ORDEN = "orden_acciones"

# Menor numero = se explora antes en el orden ``tactico``.
PRIORIDAD_TACTICA: dict[str, int] = {
    INTERCEPTAR_PORTADOR: 0,
    AVANZAR: 1,
    APROXIMARSE_AL_RECURSO: 2,
    BLOQUEAR_POSICION: 3,
    PERSEGUIR_PORTADOR: 4,
    PROTEGER_ZONA: 5,
    REPOSICIONAR: 6,
}


def validar_orden(orden: object) -> str:
    """Devuelve ``orden`` si es uno de ``ORDENES``; si no, lanza ``ValueError`` con las opciones validas."""
    if not isinstance(orden, str) or orden not in ORDENES:
        raise ValueError(f"El orden de acciones debe ser uno de {list(ORDENES)} y se recibio {orden!r}.")
    return orden


def orden_desde_configuracion(configuracion_juego: Mapping[str, object] | None) -> str | None:
    """Lee el campo propio ``juego.orden_acciones`` del escenario cargado.

    Proposito: permitir cambiar el orden de las acciones de Minimax y alfa-beta editando el JSON, sin modificar
    codigo.
    Precondiciones: ``configuracion_juego`` es ``Escenario.configuracion_juego`` o ``None``.
    Postcondiciones: devuelve ``None`` si el campo no esta y el orden si es valido; si no lo es, lanza
    ``ValueError`` con las opciones validas. No modifica nada.
    Complejidad: O(1) temporal y espacial.
    Uso de IA: Si.
    Intervencion de IA: Claude (Opus 5.5) propuso el campo propio y la implementacion en E8.6.
    Validacion del estudiante: validada; cubierta por tests/algoritmos/test_orden_acciones.py.
    """
    if configuracion_juego is None or CLAVE_ORDEN not in configuracion_juego:
        return None
    return validar_orden(configuracion_juego[CLAVE_ORDEN])


def ordenar_acciones(acciones: tuple[AccionTactica, ...], orden: str) -> tuple[AccionTactica, ...]:
    """Devuelve las acciones en el orden en que Minimax o alfa-beta deben explorarlas.

    Proposito: concentrar en un solo punto el orden de exploracion, para que Minimax y alfa-beta usen siempre el
    mismo y la comparacion de E8.4 y E8.5 siga siendo valida con cualquier orden.
    Precondiciones: ``acciones`` es la tupla de ``acciones_tacticas`` de un estado; ``orden`` es uno de ``ORDENES``
    (ya validado).
    Postcondiciones: devuelve una permutacion de ``acciones``: identica con ``generacion``, invertida con
    ``inverso`` y ordenada por ``PRIORIDAD_TACTICA`` con ``tactico`` (orden estable: las acciones del mismo tipo
    conservan el orden de generacion). No agrega ni quita acciones, por lo que todas siguen siendo legales.
    Complejidad: O(A log A) temporal y O(A) espacial, donde A es la cantidad de acciones.
    Uso de IA: Si.
    Intervencion de IA: Claude (Opus 5.5) propuso los tres ordenes, la prioridad tactica y la implementacion en E8.6.
    Validacion del estudiante: validada; cubierta por tests/algoritmos/test_orden_acciones.py.
    """
    if orden == ORDEN_INVERSO:
        return tuple(reversed(acciones))
    if orden == ORDEN_TACTICO:
        return tuple(sorted(acciones, key=lambda accion_tactica: PRIORIDAD_TACTICA[accion_tactica.tipo_tactico]))
    return acciones
