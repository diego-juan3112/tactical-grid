"""Preparación común de las búsquedas solicitadas por la interfaz gráfica."""

from collections.abc import Mapping

from tacticalgrid.algoritmos import (
    ObservadorExpansiones,
    ResultadoBusqueda,
    ancho_haz_desde_prueba,
    busqueda_a_estrella,
    busqueda_anchura,
    busqueda_costo_uniforme,
    busqueda_haz,
    busqueda_profundidad,
    validar_ancho_haz,
)
from tacticalgrid.algoritmos.heuristica_obstaculos import HeuristicaObstaculos
from tacticalgrid.escenario import Posicion
from tacticalgrid.escenario.escenario import Escenario
from tacticalgrid.juego import EstadoJuego, ProblemaNavegacion


ALGORITMOS = ("bfs", "dfs", "ucs", "astar", "beam")
LIMITE_TRAZA_EXPLORACION = 10_000


def preparar_busqueda(
    escenario: Escenario,
    estado: EstadoJuego,
    algoritmo: str | None,
    unidad: str | None = None,
    objetivo: tuple[int, int] | None = None,
    k: int | None = None,
    heuristica: str = "manhattan",
) -> ResultadoBusqueda | None:
    """Resolver los parámetros y ejecutar una única búsqueda para la interfaz.

    Proposito: conectar los controles o argumentos gráficos con las API estructuradas de navegación y búsqueda.
    Precondiciones: ``escenario`` está validado, ``estado`` le pertenece y ``algoritmo`` es admitido o ``None``.
    Postcondiciones: sin algoritmo se devuelve ``None``; con algoritmo, su resultado con una traza acotada. A* acepta
    ``manhattan`` o la heurística HTO preparada; los demás algoritmos conservan su estrategia original. Los valores
    explícitos tienen prioridad sobre ``prueba`` y el estado recibido no cambia.
    Complejidad: el costo del algoritmo más O(min(X, L_t)) espacial para X expansiones y límite L_t.
    Uso de IA: Si.
    Intervencion de IA: Codex: extracción del ejecutor de E9.2 y E9.3 y selección explícita de la heurística de A*,
    reutilizando la HTO existente.
    Validacion del estudiante: pruebas de tests/interfaz/test_aplicacion.py: cada algoritmo ejecutado una vez sobre el
    estado inicial, prioridad de la consola sobre el JSON, ``k`` leído del JSON y rechazo de combinaciones inválidas.
    """
    if algoritmo is None:
        if unidad is not None or objetivo is not None or k is not None:
            raise ValueError("--unidad, --objetivo y --k requieren indicar --algoritmo.")
        return None
    if algoritmo not in ALGORITMOS:
        raise ValueError(f"Algoritmo no admitido: {algoritmo!r}.")
    if algoritmo != "beam" and k is not None:
        raise ValueError("--k solo puede usarse con --algoritmo beam.")
    if heuristica not in ("manhattan", "hto"):
        raise ValueError("La heuristica A* debe ser 'manhattan' o 'hto'.")
    if algoritmo != "astar" and heuristica != "manhattan":
        raise ValueError("La seleccion de heuristica solo aplica a A*.")

    configuracion = escenario.configuracion_prueba
    if not isinstance(configuracion, Mapping) or configuracion.get("modo") != "busqueda":
        configuracion = {}

    identificador = unidad if unidad is not None else configuracion.get("unidad_inicio")
    if not isinstance(identificador, str) or not identificador:
        raise ValueError("Debe indicar --unidad o definir 'prueba.unidad_inicio' en el JSON.")

    posicion_objetivo = resolver_objetivo(objetivo, configuracion)
    problema = ProblemaNavegacion(escenario, identificador, posicion_objetivo, estado)
    observador = ObservadorExpansiones(LIMITE_TRAZA_EXPLORACION)

    if algoritmo == "beam":
        ancho = validar_ancho_haz(k) if k is not None else ancho_haz_desde_prueba(configuracion)
        if ancho is None:
            raise ValueError("Beam Search necesita --k o el campo 'prueba.k' en el JSON.")
        return busqueda_haz(problema, ancho, observador_expansiones=observador)

    funciones = {
        "bfs": busqueda_anchura,
        "dfs": busqueda_profundidad,
        "ucs": busqueda_costo_uniforme,
        "astar": busqueda_a_estrella,
    }
    if algoritmo == "astar" and heuristica == "hto":
        return busqueda_a_estrella(
            problema,
            heuristica_preparada=HeuristicaObstaculos(problema),
            observador_expansiones=observador,
        )
    return funciones[algoritmo](problema, observador_expansiones=observador)


def resolver_objetivo(
    objetivo: tuple[int, int] | None,
    configuracion: Mapping[str, object],
) -> Posicion:
    """Convertir el objetivo explícito o el del JSON al tipo de posición del dominio."""
    if objetivo is not None:
        return Posicion(*objetivo)
    datos = configuracion.get("objetivo")
    if not isinstance(datos, Mapping):
        raise ValueError("Debe indicar --objetivo FILA COLUMNA o definir 'prueba.objetivo' en el JSON.")
    fila = datos.get("fila")
    columna = datos.get("columna")
    if type(fila) is not int or type(columna) is not int:
        raise ValueError("El objetivo debe contener fila y columna enteras.")
    return Posicion(fila, columna)
