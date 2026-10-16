"""Punto de entrada de la visualizacion Pygame de TacticalGrid."""

import argparse
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path

from tacticalgrid.algoritmos import (
    ResultadoBusqueda,
    ancho_haz_desde_prueba,
    busqueda_a_estrella,
    busqueda_anchura,
    busqueda_costo_uniforme,
    busqueda_haz,
    busqueda_profundidad,
    validar_ancho_haz,
)
from tacticalgrid.escenario import ErrorValidacionEscenario, Posicion, cargar_escenario
from tacticalgrid.escenario.escenario import Escenario
from tacticalgrid.juego import EstadoJuego, ProblemaNavegacion, crear_estado_inicial

from .renderizador import RenderizadorTablero


ALGORITMOS = ("bfs", "dfs", "ucs", "astar", "beam")


def ejecutar_aplicacion(
    ruta_escenario: str | Path | None = None,
    *,
    algoritmo: str | None = None,
    unidad: str | None = None,
    objetivo: tuple[int, int] | None = None,
    k: int | None = None,
) -> int:
    """Carga un escenario, ejecuta una busqueda opcional y mantiene visible el tablero.

    Purpose: integrar carga validada, busqueda estructurada y renderizado sin incorporar mecanicas interactivas.
    Preconditions: Pygame esta instalado, existe un entorno grafico y la ruta identifica un escenario valido.
    Postconditions: la busqueda solicitada se ejecuta una sola vez; cada fotograma refleja el estado inicial y el
    mismo resultado inmutable, y Pygame se libera al cerrar. Sin algoritmo conserva el comportamiento de E9.1.
    Complexity: costo de la busqueda seleccionada mas O(E*(F*C + U + T + L)) temporal durante el ciclo y
    O(F*C + T + L) espacial de renderizado, donde L es la longitud del camino y E la cantidad de fotogramas.
    AI usage: Yes.
    AI intervention: Codex integro E9.2 mediante argumentos de consola, ejecucion unica y entrega del resultado
    comun al renderizador, sin modificar algoritmos ni estado de juego.
    Student validation: pendiente de revision y validacion visual manual del equipo; cubierta por pruebas
    automatizadas de aplicacion y renderizador.
    """
    import pygame

    if ruta_escenario is None:
        argumentos = _leer_argumentos()
        ruta_escenario = argumentos.escenario
        algoritmo = argumentos.algoritmo
        unidad = argumentos.unidad
        objetivo = tuple(argumentos.objetivo) if argumentos.objetivo is not None else None
        k = argumentos.k

    try:
        escenario = cargar_escenario(ruta_escenario)
        estado = crear_estado_inicial(escenario)
        resultado = preparar_busqueda(escenario, estado, algoritmo, unidad, objetivo, k)
    except (ErrorValidacionEscenario, OSError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1

    pygame.init()
    try:
        pygame.display.set_caption("TacticalGrid")
        ancho = max(800, min(1400, escenario.columnas * 32 + RenderizadorTablero.ANCHO_PANEL + 48))
        alto = max(600, min(1000, escenario.filas * 32 + 32))
        ventana = pygame.display.set_mode((ancho, alto), pygame.RESIZABLE)
        renderizador = RenderizadorTablero()
        en_ejecucion = True
        while en_ejecucion:
            for evento in pygame.event.get():
                if evento.type == pygame.QUIT:
                    en_ejecucion = False
            renderizador.renderizar(ventana, escenario, estado, resultado)
            pygame.display.flip()
    finally:
        pygame.quit()
    return 0


def preparar_busqueda(
    escenario: Escenario,
    estado: EstadoJuego,
    algoritmo: str | None,
    unidad: str | None = None,
    objetivo: tuple[int, int] | None = None,
    k: int | None = None,
) -> ResultadoBusqueda | None:
    """Resuelve parametros y ejecuta una unica busqueda para la interfaz.

    Purpose: conectar la seleccion de consola con las APIs estructuradas de navegacion y busqueda.
    Preconditions: ``escenario`` esta validado, ``estado`` le pertenece y ``algoritmo`` es uno de los nombres
    admitidos o ``None``. Los argumentos CLI ya tienen los tipos declarados por ``argparse``.
    Postconditions: sin algoritmo devuelve ``None`` y no ejecuta busquedas; con algoritmo devuelve exactamente su
    ``ResultadoBusqueda``. CLI tiene prioridad sobre ``prueba`` y el estado recibido no se modifica.
    Complexity: costo de construir ``ProblemaNavegacion`` mas el del algoritmo seleccionado; O(1) adicional para
    resolver parametros, sin contar los datos ya cargados en el escenario.
    AI usage: Yes.
    AI intervention: Codex implemento la resolucion comun de unidad, objetivo y k y el despacho de los cinco
    algoritmos para E9.2.
    Student validation: pendiente de revision del equipo; cubierta por pruebas automatizadas de precedencia,
    validacion y resultados reales de los cinco algoritmos.
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

    posicion_objetivo = _resolver_objetivo(objetivo, configuracion)
    problema = ProblemaNavegacion(escenario, identificador, posicion_objetivo, estado)

    if algoritmo == "beam":
        ancho = validar_ancho_haz(k) if k is not None else ancho_haz_desde_prueba(configuracion)
        if ancho is None:
            raise ValueError("Beam Search necesita --k o el campo 'prueba.k' en el JSON.")
        return busqueda_haz(problema, ancho)

    funciones = {
        "bfs": busqueda_anchura,
        "dfs": busqueda_profundidad,
        "ucs": busqueda_costo_uniforme,
        "astar": busqueda_a_estrella,
    }
    return funciones[algoritmo](problema)


def _resolver_objetivo(
    objetivo: tuple[int, int] | None,
    configuracion: Mapping[str, object],
) -> Posicion:
    """Convierte el objetivo de CLI o JSON al tipo de posicion del dominio."""
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


def _leer_argumentos(argumentos: Sequence[str] | None = None) -> argparse.Namespace:
    """Lee la seleccion opcional de escenario y busqueda de la interfaz grafica."""
    analizador = argparse.ArgumentParser(description="Visualiza un escenario JSON de TacticalGrid.")
    analizador.add_argument(
        "escenario",
        nargs="?",
        type=Path,
        default=Path("escenarios/campo_20x20.json"),
        help="ruta al escenario JSON (predeterminado: escenarios/campo_20x20.json)",
    )
    analizador.add_argument("--algoritmo", choices=ALGORITMOS, help="busqueda cuyo camino se visualizara")
    analizador.add_argument("--unidad", help="identificador de la unidad navegante")
    analizador.add_argument(
        "--objetivo",
        nargs=2,
        type=int,
        metavar=("FILA", "COLUMNA"),
        help="coordenadas de destino",
    )
    analizador.add_argument(
        "--k",
        type=int,
        help="ancho de Beam Search; si se omite se usa 'prueba.k' del JSON",
    )
    return analizador.parse_args(argumentos)


if __name__ == "__main__":
    raise SystemExit(ejecutar_aplicacion())
