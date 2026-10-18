"""Preparacion comun de busquedas solicitadas por la interfaz grafica."""

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
) -> ResultadoBusqueda | None:
    """Resuelve parametros y ejecuta una unica busqueda para la interfaz.

    Proposito: conectar controles o argumentos graficos con las APIs estructuradas de navegacion y busqueda.
    Precondiciones: ``escenario`` esta validado, ``estado`` le pertenece y ``algoritmo`` es admitido o ``None``.
    Postcondiciones: sin algoritmo devuelve ``None``; con algoritmo devuelve su resultado con una traza acotada.
    Los valores explicitos tienen prioridad sobre ``prueba`` y el estado recibido no se modifica.
    Complejidad: costo del algoritmo mas O(min(X, L_t)) espacial para X expansiones y limite L_t.
    Uso de IA: Si.
    Intervencion de IA: Codex extrajo sin cambios el ejecutor E9.2/E9.3 para compartirlo con los controles graficos.
    Validacion del estudiante: revisado y aprobado por el equipo; cubierta por pruebas de los cinco algoritmos y
    regresion.
    """
    if algoritmo is None:
        if unidad is not None or objetivo is not None or k is not None:
            raise ValueError("--unidad, --objetivo y --k requieren indicar --algoritmo.")
        return None
    if algoritmo not in ALGORITMOS:
        raise ValueError(f"Algoritmo no admitido: {algoritmo!r}.")
    if algoritmo != "beam" and k is not None:
        raise ValueError("--k solo puede usarse con --algoritmo beam.")

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
    return funciones[algoritmo](problema, observador_expansiones=observador)


def resolver_objetivo(
    objetivo: tuple[int, int] | None,
    configuracion: Mapping[str, object],
) -> Posicion:
    """Convierte el objetivo explicito o del JSON al tipo de posicion del dominio."""
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
