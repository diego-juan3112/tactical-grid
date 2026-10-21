"""Lectura del campo ``prueba`` del escenario y resolución del modo a ejecutar (E10.1).

El enunciado define el campo ``prueba`` para cargar un estado y solicitar una operación concreta, con al menos tres
modos:

- ``busqueda``: resolver una navegación concreta con BFS, DFS, UCS, A* o Beam Search.
- ``partida``: cargar el escenario completo para continuar el juego por turnos.
- ``adversarial``: evaluar un estado mediante Minimax o alfa-beta y seleccionar una acción.

Campos que se leen, todos opcionales salvo ``modo``:

- ``modo`` (enunciado): uno de los tres anteriores.
- ``unidad_inicio`` y ``objetivo`` (enunciado, modo ``busqueda``): unidad que navega y celda de destino.
- ``algoritmo`` (campo propio): algoritmo a usar, de la familia del modo.
- ``max_turnos`` (campo propio, modo ``partida``): límite de jugadas de la partida.
- ``k`` (campo propio de E7.1): ancho del haz, que se lee con ``ancho_haz_desde_prueba``.

La consola puede sobrescribir cualquiera de ellos, de modo que también se ejecuta un escenario externo sin campos
propios. Este módulo solo interpreta datos ya cargados y validados por la capa de escenario: no abre archivos ni
ejecuta algoritmos.
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
    """Interpretar el campo ``prueba`` del escenario cargado.

    Proposito: concentrar en un solo lugar la lectura de ``prueba`` para que la consola y la interfaz ejecuten el modo
    que pide un escenario externo sin modificar código.
    Precondiciones: ``escenario`` se cargó y validó con ``cargar_escenario``.
    Postcondiciones: se devuelve ``None`` si el escenario no tiene ``prueba``; si la tiene, una ``ConfiguracionPrueba``
    con el modo y los campos presentes. Se lanza ``ValueError`` con un mensaje que nombra el campo si el modo no es uno
    de ``MODOS``, si ``unidad_inicio`` no es un texto, si ``objetivo`` no tiene ``fila`` y ``columna`` enteras, si
    ``algoritmo`` no pertenece a la familia del modo o si ``max_turnos`` no es un entero mayor o igual que 1. El
    escenario no cambia.
    Complejidad: O(1) temporal y espacial.
    Uso de IA: Si.
    Intervencion de IA: Claude (Opus 5.5): campos propios ``algoritmo`` y ``max_turnos`` e implementación, con la
    lectura de ``unidad_inicio`` y ``objetivo`` que antes hacía ``main.py`` unificada aquí (E10.1).
    Validacion del estudiante: pruebas de tests/modos/test_configuracion_prueba.py: ausencia de ``prueba``, navegación
    del ejemplo del enunciado, modos de los escenarios del repositorio, campos propios y rechazo de configuraciones
    inválidas con un mensaje claro.
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
    """Decidir qué modo ejecutar a partir de la consola y del campo ``prueba``.

    Proposito: ejecutar un escenario externo en el modo que declara sin romper los usos anteriores de la consola con
    ``--algoritmo``.
    Precondiciones: ``modo_consola`` es ``None`` o el valor de ``--modo``; ``algoritmo_consola`` es ``None`` o el de
    ``--algoritmo``; ``configuracion`` es el resultado de ``leer_configuracion_prueba``.
    Postcondiciones: se devuelve, por orden de prioridad, ``modo_consola``; si no, el modo de la familia de
    ``algoritmo_consola`` (un ``--algoritmo`` explícito conserva su comportamiento anterior); si no,
    ``configuracion.modo``; y si no hay nada, ``busqueda``. Se lanza ``ValueError`` si ``modo_consola`` es desconocido
    o si ``algoritmo_consola`` no se puede usar en el modo indicado. Nada cambia.
    Complejidad: O(1) temporal y espacial.
    Uso de IA: Si.
    Intervencion de IA: Claude (Opus 5.5): regla de precedencia e implementación (E10.1).
    Validacion del estudiante: pruebas ``test_resolver_modo_respeta_la_precedencia`` y
    ``test_combinacion_incompatible_de_modo_y_algoritmo`` de tests/modos/test_configuracion_prueba.py.
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
    """Leer la posición objetivo opcional de la configuración de prueba.

    Proposito: convertir el objeto JSON ``objetivo`` en ``Posicion`` y rechazar una estructura sin coordenadas enteras
    estrictas.
    Precondiciones: ``prueba`` es el mapeo del campo ``prueba`` ya cargado; aquí no se comprueba que la posición esté
    dentro de las dimensiones del escenario.
    Postcondiciones: se devuelve ``None`` si falta o es ``null``, y ``Posicion(fila, columna)`` si ambas coordenadas son
    ``int`` y no ``bool``; en otro formato se lanza ``ValueError`` con el valor recibido. El mapeo no cambia.
    Complejidad: O(1) temporal y espacial: se consultan dos claves y se crea como máximo una ``Posicion``.
    Uso de IA: Si.
    Intervencion de IA: Claude (Opus 5.5): lector del objetivo (E10.1). Codex: documentación.
    Validacion del estudiante: pruebas de tests/modos/test_configuracion_prueba.py: navegación del ejemplo del
    enunciado y rechazo de objetivos inválidos.
    """
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
    """Leer el algoritmo opcional permitido para el modo indicado.

    Proposito: validar que el nombre configurado pertenezca a la familia admitida desde el JSON para ``modo``.
    Precondiciones: ``prueba`` es el mapeo de configuración y ``modo`` es una clave de ``_ALGORITMOS_JSON``; la validez
    del modo se comprueba antes en ``leer_configuracion_prueba``.
    Postcondiciones: se devuelve ``None`` si falta o es ``null``, y el nombre si aparece en la tupla del modo; en otro
    caso se lanza ``ValueError`` con las opciones válidas. El mapeo no cambia.
    Complejidad: O(1) temporal y espacial, porque las tuplas admitidas tienen tamaño fijo por modo.
    Uso de IA: Si.
    Intervencion de IA: Claude (Opus 5.5): validación del algoritmo por modo (E10.1). Codex: documentación.
    Validacion del estudiante: pruebas de tests/modos/test_configuracion_prueba.py: familias de algoritmos por modo,
    lectura del campo ``algoritmo`` y rechazo de algoritmos de otra familia.
    """
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
    """Devolver ``max_turnos`` si es un entero no booleano mayor o igual que 1; si no, lanzar ``ValueError``."""
    if isinstance(max_turnos, bool) or not isinstance(max_turnos, int) or max_turnos < 1:
        raise ValueError(f"El limite 'max_turnos' debe ser un entero mayor o igual que 1 y se recibio {max_turnos!r}.")
    return max_turnos
