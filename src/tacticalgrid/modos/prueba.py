"""Lectura del campo ``prueba`` del escenario y resolucion del modo a ejecutar (E10.1).

El enunciado define el campo ``prueba`` para que el profesor cargue un estado y solicite una operacion concreta, con
al menos tres modos:

- ``busqueda``: resolver una navegacion concreta con BFS, DFS, UCS, A* o Beam Search.
- ``partida``: cargar el escenario completo para continuar el juego por turnos.
- ``adversarial``: evaluar un estado mediante Minimax o alfa-beta y seleccionar una accion.

Campos que se leen (todos opcionales salvo ``modo``):

- ``modo`` (enunciado): uno de los tres anteriores.
- ``unidad_inicio`` y ``objetivo`` (enunciado, modo ``busqueda``): unidad que navega y celda de destino.
- ``algoritmo`` (campo propio): algoritmo a usar, de la familia del modo.
- ``max_turnos`` (campo propio, modo ``partida``): limite de jugadas de la partida.
- ``k`` (campo propio de E7.1): ancho del haz, que se sigue leyendo con ``ancho_haz_desde_prueba``.

La consola puede sobrescribir cualquiera de ellos, de modo que un escenario externo sin campos propios tambien se
puede ejecutar. Este modulo solo interpreta datos ya cargados y validados por la capa de escenario: no abre archivos
ni ejecuta algoritmos.
"""

from collections.abc import Mapping
from dataclasses import dataclass

from tacticalgrid.escenario.escenario import Escenario, Posicion

MODO_BUSQUEDA = "busqueda"
MODO_PARTIDA = "partida"
MODO_ADVERSARIAL = "adversarial"
MODOS = (MODO_BUSQUEDA, MODO_PARTIDA, MODO_ADVERSARIAL)

ALGORITMOS_BUSQUEDA = ("bfs", "dfs", "ucs", "a_estrella", "beam")
ALGORITMOS_ADVERSARIALES = ("minimax", "alfa_beta")
# Comparaciones que solo ofrece la consola: ejecutan varios algoritmos de una misma familia.
COMPARACIONES_BUSQUEDA = ("ambos", "bfs_dfs")
COMPARACIONES_ADVERSARIALES = ("minimax_alfa_beta",)

MAX_TURNOS_POR_DEFECTO = 50

# Algoritmos admitidos en cada modo, desde el JSON (sin comparaciones) y desde la consola (con comparaciones).
_ALGORITMOS_JSON = {
    MODO_BUSQUEDA: ALGORITMOS_BUSQUEDA,
    MODO_ADVERSARIAL: ALGORITMOS_ADVERSARIALES,
    MODO_PARTIDA: ALGORITMOS_ADVERSARIALES,
}
_ALGORITMOS_CONSOLA = {
    MODO_BUSQUEDA: ALGORITMOS_BUSQUEDA + COMPARACIONES_BUSQUEDA,
    MODO_ADVERSARIAL: ALGORITMOS_ADVERSARIALES + COMPARACIONES_ADVERSARIALES,
    MODO_PARTIDA: ALGORITMOS_ADVERSARIALES,
}


@dataclass(frozen=True)
class ConfiguracionPrueba:
    """Datos del campo ``prueba`` ya validados; los que el JSON no declara quedan en ``None``."""

    modo: str
    unidad: str | None = None
    objetivo: Posicion | None = None
    algoritmo: str | None = None
    max_turnos: int | None = None


def leer_configuracion_prueba(escenario: Escenario) -> ConfiguracionPrueba | None:
    """Interpreta el campo ``prueba`` del escenario cargado.

    Proposito: concentrar en un solo lugar la lectura de ``prueba`` para que la consola (y la interfaz) ejecuten el
    modo que pide un escenario externo sin modificar codigo.
    Precondiciones: ``escenario`` fue cargado y validado por ``cargar_escenario``.
    Postcondiciones: devuelve ``None`` si el escenario no tiene ``prueba``; si la tiene, devuelve una
    ``ConfiguracionPrueba`` con el modo y los campos presentes. Lanza ``ValueError`` con un mensaje que nombra el
    campo si el modo no es uno de ``MODOS``, si ``unidad_inicio`` no es un texto, si ``objetivo`` no tiene ``fila``
    y ``columna`` enteras, si ``algoritmo`` no pertenece a la familia del modo o si ``max_turnos`` no es un entero
    mayor o igual que 1. No modifica el escenario.
    Complejidad: O(1) temporal y espacial.
    Uso de IA: Si.
    Intervencion de IA: Claude (Opus 5.5) propuso los campos propios ``algoritmo`` y ``max_turnos`` y la
    implementacion en E10.1, unificando la lectura de ``unidad_inicio`` y ``objetivo`` que hacia ``main.py``.
    Validacion del estudiante: se valida la implementacion de la configuracion de prueba, cubierta por
    tests/modos/test_configuracion_prueba.py.
    """
    prueba = escenario.configuracion_prueba
    if prueba is None:
        return None
    modo = prueba.get("modo")
    if modo not in MODOS:
        raise ValueError(f"El campo 'prueba.modo' debe ser uno de {list(MODOS)} y se recibio {modo!r}.")
    return ConfiguracionPrueba(
        modo=modo,
        unidad=_leer_unidad(prueba),
        objetivo=_leer_objetivo(prueba),
        algoritmo=_leer_algoritmo(prueba, modo),
        max_turnos=_leer_max_turnos(prueba),
    )


def resolver_modo(
    modo_consola: str | None, algoritmo_consola: str | None, configuracion: ConfiguracionPrueba | None
) -> str:
    """Decide que modo ejecutar a partir de la consola y del campo ``prueba``.

    Proposito: que un escenario externo se ejecute en el modo que declara, sin romper los usos anteriores de la
    consola con ``--algoritmo``.
    Precondiciones: ``modo_consola`` es ``None`` o el valor de ``--modo``; ``algoritmo_consola`` es ``None`` o el de
    ``--algoritmo``; ``configuracion`` es el resultado de ``leer_configuracion_prueba``.
    Postcondiciones: devuelve, por orden de prioridad, ``modo_consola``; si no, el modo de la familia de
    ``algoritmo_consola`` (un ``--algoritmo`` explicito conserva su comportamiento anterior); si no,
    ``configuracion.modo``; y si no hay nada, ``busqueda``. Lanza ``ValueError`` si ``modo_consola`` es desconocido
    o si ``algoritmo_consola`` no se puede usar en el modo indicado. No modifica nada.
    Complejidad: O(1) temporal y espacial.
    Uso de IA: Si.
    Intervencion de IA: Claude (Opus 5.5) propuso la regla de precedencia y la implementacion en E10.1.
    Validacion del estudiante: se valida la implementacion de la configuracion de prueba, cubierta por
    tests/modos/test_configuracion_prueba.py.
    """
    if modo_consola is not None:
        if modo_consola not in MODOS:
            raise ValueError(f"El modo debe ser uno de {list(MODOS)} y se recibio {modo_consola!r}.")
        if algoritmo_consola is not None and algoritmo_consola not in _ALGORITMOS_CONSOLA[modo_consola]:
            raise ValueError(
                f"El algoritmo {algoritmo_consola!r} no se puede usar en el modo {modo_consola!r}; "
                f"use uno de {list(_ALGORITMOS_CONSOLA[modo_consola])}."
            )
        return modo_consola
    if algoritmo_consola is not None:
        if algoritmo_consola in _ALGORITMOS_CONSOLA[MODO_ADVERSARIAL]:
            return MODO_ADVERSARIAL
        return MODO_BUSQUEDA
    if configuracion is not None:
        return configuracion.modo
    return MODO_BUSQUEDA


def _leer_unidad(prueba: Mapping[str, object]) -> str | None:
    unidad = prueba.get("unidad_inicio")
    if unidad is not None and (not isinstance(unidad, str) or not unidad):
        raise ValueError(f"El campo 'prueba.unidad_inicio' debe ser el id de una unidad y se recibio {unidad!r}.")
    return unidad


def _leer_objetivo(prueba: Mapping[str, object]) -> Posicion | None:
    objetivo = prueba.get("objetivo")
    if objetivo is None:
        return None
    if not isinstance(objetivo, Mapping) or not all(
        isinstance(objetivo.get(campo), int) and not isinstance(objetivo.get(campo), bool) for campo in ("fila", "columna")
    ):
        raise ValueError(
            f"El campo 'prueba.objetivo' debe ser un objeto con 'fila' y 'columna' enteras y se recibio {objetivo!r}."
        )
    return Posicion(objetivo["fila"], objetivo["columna"])


def _leer_algoritmo(prueba: Mapping[str, object], modo: str) -> str | None:
    algoritmo = prueba.get("algoritmo")
    if algoritmo is not None and algoritmo not in _ALGORITMOS_JSON[modo]:
        raise ValueError(
            f"El campo 'prueba.algoritmo' del modo {modo!r} debe ser uno de {list(_ALGORITMOS_JSON[modo])} "
            f"y se recibio {algoritmo!r}."
        )
    return algoritmo


def _leer_max_turnos(prueba: Mapping[str, object]) -> int | None:
    max_turnos = prueba.get("max_turnos")
    if max_turnos is None:
        return None
    return validar_max_turnos(max_turnos)


def validar_max_turnos(max_turnos: object) -> int:
    """Devuelve ``max_turnos`` si es un entero (no booleano) mayor o igual que 1; si no, lanza ``ValueError``."""
    if isinstance(max_turnos, bool) or not isinstance(max_turnos, int) or max_turnos < 1:
        raise ValueError(f"El limite 'max_turnos' debe ser un entero mayor o igual que 1 y se recibio {max_turnos!r}.")
    return max_turnos
