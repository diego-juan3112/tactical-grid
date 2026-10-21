"""Orden configurable de las acciones que exploran Minimax y alfa-beta (E8.6, caso mínimo 9).

El enunciado pide cambiar el orden de generación de acciones y analizar su efecto en la cantidad de poda. El orden
no cambia el valor Minimax de un estado, porque el máximo o el mínimo de un conjunto no dependen del orden de
recorrido, pero sí cambia cuánto poda alfa-beta: si las mejores jugadas se exploran primero, alfa y beta se ajustan
antes y se cortan más ramas. Ante un empate de valor ambos algoritmos conservan la primera acción, de modo que con
otro orden la acción elegida puede ser otra de igual valor.

Órdenes disponibles:

- ``generacion``: el de ``acciones_tacticas`` (unidades por identificador y movimientos arriba, abajo, izquierda,
  derecha). Es el orden por defecto, el mismo de E8.3 y E8.4.
- ``inverso``: el orden de generación al revés.
- ``tactico``: primero las acciones de mayor impacto según su tipo táctico (E8.1): interceptar al portador, avanzar
  con el recurso, aproximarse al recurso, bloquear, perseguir, proteger y, al final, reposicionar. Las acciones del
  mismo tipo conservan el orden de generación, por lo que el resultado es determinista.

El orden se cambia sin modificar código, desde la consola (``--orden``) o desde el campo propio
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

# Menor número: se explora antes en el orden ``tactico``.
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
    """Devolver ``orden`` si es uno de ``ORDENES``; en otro caso, lanzar ``ValueError`` con las opciones válidas."""
    if not isinstance(orden, str) or orden not in ORDENES:
        raise ValueError(f"El orden de acciones debe ser uno de {list(ORDENES)} y se recibio {orden!r}.")
    return orden


def orden_desde_configuracion(configuracion_juego: Mapping[str, object] | None) -> str | None:
    """Leer el campo propio ``juego.orden_acciones`` del escenario cargado.

    Proposito: permitir cambiar el orden de las acciones de Minimax y alfa-beta editando el JSON, sin modificar código.
    Precondiciones: ``configuracion_juego`` es ``Escenario.configuracion_juego`` o ``None``.
    Postcondiciones: se devuelve ``None`` si el campo no está y el orden si es válido; si no lo es, se lanza
    ``ValueError`` con las opciones válidas. Nada cambia.
    Complejidad: O(1) temporal y espacial.
    Uso de IA: Si.
    Intervencion de IA: Claude (Opus 5.5): campo propio e implementación (E8.6).
    Validacion del estudiante: pruebas de tests/algoritmos/test_orden_acciones.py: lectura del orden desde el JSON,
    orden de generación por defecto y rechazo de un orden inválido.
    """
    if configuracion_juego is None or CLAVE_ORDEN not in configuracion_juego:
        return None
    return validar_orden(configuracion_juego[CLAVE_ORDEN])


def ordenar_acciones(acciones: tuple[AccionTactica, ...], orden: str) -> tuple[AccionTactica, ...]:
    """Devolver las acciones en el orden en que Minimax o alfa-beta deben explorarlas.

    Proposito: concentrar en un solo punto el orden de exploración, para que Minimax y alfa-beta usen siempre el mismo
    y la comparación de E8.4 y E8.5 siga siendo válida con cualquier orden.
    Precondiciones: ``acciones`` es la tupla de ``acciones_tacticas`` de un estado; ``orden`` es uno de ``ORDENES``,
    ya validado.
    Postcondiciones: se devuelve una permutación de ``acciones``: idéntica con ``generacion``, invertida con
    ``inverso`` y ordenada por ``PRIORIDAD_TACTICA`` con ``tactico`` (orden estable: las acciones del mismo tipo
    conservan el orden de generación). No se agregan ni se quitan acciones, por lo que todas siguen siendo legales.
    Complejidad: O(A log A) temporal y O(A) espacial, con A la cantidad de acciones.
    Uso de IA: Si.
    Intervencion de IA: Claude (Opus 5.5): tres órdenes, prioridad táctica e implementación (E8.6).
    Validacion del estudiante: pruebas de tests/algoritmos/test_orden_acciones.py: orden de generación, orden inverso,
    prioridad táctica con empates estables, misma decisión de Minimax y alfa-beta con igual orden, valor Minimax
    invariante y cambio en la cantidad de poda.
    """
    if orden == ORDEN_INVERSO:
        return tuple(reversed(acciones))
    if orden == ORDEN_TACTICO:
        return tuple(sorted(acciones, key=lambda accion_tactica: PRIORIDAD_TACTICA[accion_tactica.tipo_tactico]))
    return acciones
