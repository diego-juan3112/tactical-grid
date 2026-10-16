"""Punto de entrada de la visualizacion Pygame de TacticalGrid."""

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from tacticalgrid.escenario import ErrorValidacionEscenario, Posicion

from .busquedas import ALGORITMOS, preparar_busqueda
from .control import ControlGrafico
from .renderizador import EstadoPanelControl, RectangulosControles, RenderizadorTablero


RAIZ_PROYECTO = Path(__file__).resolve().parents[3]
RUTA_ESCENARIO_PREDETERMINADO = RAIZ_PROYECTO / "escenarios" / "campo_20x20.json"


def ejecutar_aplicacion(
    ruta_escenario: str | Path | None = None,
    *,
    algoritmo: str | None = None,
    unidad: str | None = None,
    objetivo: tuple[int, int] | None = None,
    k: int | None = None,
) -> int:
    """Carga un escenario, ejecuta una busqueda opcional y mantiene visible el tablero.

    Purpose: integrar carga validada, busqueda estructurada y renderizado, incluida la capa E9.3 bajo demanda.
    Preconditions: Pygame esta instalado, existe un entorno grafico y la ruta identifica un escenario valido.
    Postconditions: carga una sesion editable; Enter y el boton Ejecutar comparten una sola accion de busqueda;
    cambiar de escenario es atomico; E o su boton solo alternan visibilidad, y Pygame se libera al cerrar.
    Complexity: costo de la busqueda mas O(E*(F*C + U + T + L + P)) temporal durante el ciclo y
    O(F*C + T + L + P) espacial, donde P son posiciones expandidas almacenadas y E los fotogramas.
    AI usage: Yes.
    AI intervention: Codex integro E9.2/E9.3 y agrego controles directos para escenario, algoritmo, unidad,
    objetivo y Beam sin recalcular por fotograma ni modificar el estado de juego.
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
        control = ControlGrafico.crear(ruta_escenario, _rutas_escenarios(ruta_escenario))
        resultado = preparar_busqueda(control.escenario, control.estado, algoritmo, unidad, objetivo, k)
        control.resultado = resultado
        if algoritmo is not None:
            control.algoritmo = algoritmo
            if unidad is not None:
                control.unidad = unidad
            if objetivo is not None:
                control.objetivo = Posicion(*objetivo)
            if k is not None:
                control.k = k
            control.mensaje = "Busqueda inicial finalizada."
            control.estado_busqueda = "completada" if resultado.exito else "sin solucion"
    except (ErrorValidacionEscenario, OSError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1

    pygame.init()
    try:
        pygame.display.set_caption("TacticalGrid")
        ancho = max(800, min(1400, control.escenario.columnas * 32 + RenderizadorTablero.ANCHO_PANEL + 48))
        alto = max(600, min(1000, control.escenario.filas * 32 + 32))
        ventana = pygame.display.set_mode((ancho, alto), pygame.RESIZABLE)
        renderizador = RenderizadorTablero()
        disposicion = renderizador.calcular_disposicion(ventana, control.escenario)
        rectangulos = renderizador.calcular_rectangulos_controles(disposicion.panel)
        en_ejecucion = True
        while en_ejecucion:
            for evento in pygame.event.get():
                if evento.type == pygame.QUIT:
                    en_ejecucion = False
                elif evento.type == pygame.KEYDOWN and evento.key == pygame.K_e:
                    control.alternar_exploracion()
                elif evento.type == pygame.KEYDOWN and evento.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    control.ejecutar()
                elif evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
                    _procesar_clic(control, evento.pos, disposicion, rectangulos)
            panel = EstadoPanelControl.desde_control(control)
            disposicion = renderizador.renderizar(
                ventana,
                control.escenario,
                control.estado,
                control.resultado,
                exploracion_visible=control.exploracion_visible,
                control=panel,
            )
            rectangulos = renderizador.calcular_rectangulos_controles(disposicion.panel)
            pygame.display.flip()
    finally:
        pygame.quit()
    return 0


def ejecutar_desde_argumentos(argumentos: Sequence[str] | None = None) -> int:
    """Interpreta exclusivamente argumentos graficos y delega la aplicacion.

    Purpose: mantener separado el parser grafico del parser historico de consola.
    Preconditions: ``argumentos`` no incluye ``--gui`` ni el nombre del programa.
    Postconditions: ejecuta la GUI con las opciones interpretadas y devuelve su codigo de salida.
    Complexity: O(A) temporal y espacial para A argumentos, mas el costo de la aplicacion delegada.
    AI usage: Yes.
    AI intervention: Codex extrajo este adaptador durante la refactorizacion final de ``main.py``.
    Student validation: pendiente de revision humana; cubierta por pruebas del despachador y parser grafico.
    """
    opciones = _leer_argumentos(argumentos)
    return ejecutar_aplicacion(
        opciones.escenario,
        algoritmo=opciones.algoritmo,
        unidad=opciones.unidad,
        objetivo=tuple(opciones.objetivo) if opciones.objetivo is not None else None,
        k=opciones.k,
    )


def _rutas_escenarios(ruta_actual: str | Path) -> tuple[Path, ...]:
    """Cataloga JSON incluidos y conserva una ruta externa recibida explicitamente."""
    incluidas = tuple((RAIZ_PROYECTO / "escenarios").glob("*.json"))
    return tuple(sorted({ruta.resolve() for ruta in incluidas} | {Path(ruta_actual).resolve()}))


def _procesar_clic(
    control: ControlGrafico,
    punto: tuple[int, int],
    disposicion,
    rectangulos: RectangulosControles,
) -> None:
    """Traduce un clic a una unica operacion de control o a seleccion de objetivo.

    Purpose: centralizar hitboxes y garantizar que teclado y boton de exploracion compartan estado.
    Preconditions: disposicion y rectangulos corresponden al ultimo fotograma renderizado.
    Postconditions: ejecuta a lo sumo una accion; seleccionar tablero no mueve unidades ni modifica el dominio.
    Complexity: O(1) salvo carga de escenario o busqueda solicitadas explicitamente.
    AI usage: Yes.
    AI intervention: Codex implemento la interaccion directa de Pygame para la integracion final de E9.3.
    Student validation: pendiente de revision humana; cubierta por pruebas de eventos y controles SDL dummy.
    """
    acciones = (
        (rectangulos.escenario_anterior, lambda: control.cambiar_escenario(-1)),
        (rectangulos.escenario_siguiente, lambda: control.cambiar_escenario(1)),
        (rectangulos.algoritmo_anterior, lambda: control.cambiar_algoritmo(-1)),
        (rectangulos.algoritmo_siguiente, lambda: control.cambiar_algoritmo(1)),
        (rectangulos.unidad_anterior, lambda: control.cambiar_unidad(-1)),
        (rectangulos.unidad_siguiente, lambda: control.cambiar_unidad(1)),
        (rectangulos.k_menor, lambda: control.cambiar_k(-1)),
        (rectangulos.k_mayor, lambda: control.cambiar_k(1)),
        (rectangulos.ejecutar, control.ejecutar),
        (rectangulos.exploracion, control.alternar_exploracion),
    )
    for rectangulo, accion in acciones:
        if rectangulo.collidepoint(punto):
            accion()
            return
    if disposicion.tablero.collidepoint(punto):
        columna = (punto[0] - disposicion.tablero.x) // disposicion.tamano_celda
        fila = (punto[1] - disposicion.tablero.y) // disposicion.tamano_celda
        control.seleccionar_objetivo(Posicion(fila, columna))


def _leer_argumentos(argumentos: Sequence[str] | None = None) -> argparse.Namespace:
    """Lee la seleccion opcional de escenario y busqueda de la interfaz grafica."""
    analizador = argparse.ArgumentParser(description="Visualiza un escenario JSON de TacticalGrid.")
    analizador.add_argument(
        "escenario",
        nargs="?",
        type=Path,
        default=RUTA_ESCENARIO_PREDETERMINADO,
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
    raise SystemExit(ejecutar_desde_argumentos())
