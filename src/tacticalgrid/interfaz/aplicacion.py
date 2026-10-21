"""Punto de entrada de la visualización Pygame de TacticalGrid."""

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from tacticalgrid.escenario import ErrorValidacionEscenario, Posicion

from .busquedas import ALGORITMOS, preparar_busqueda
from .control import CONTROL_ALGORITMOS, ControlGrafico
from .dialogo import DialogoNoDisponible, pedir_ruta_escenario, pedir_ruta_registro
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
    """Cargar un escenario, ejecutar una búsqueda opcional y mantener visible el tablero.

    Proposito: integrar la carga validada, la búsqueda estructurada y el renderizado, incluida la capa de exploración
    de E9.3 bajo demanda.
    Precondiciones: Pygame está instalado, existe un entorno gráfico y la ruta identifica un escenario válido.
    Postcondiciones: se carga el modo declarado por el escenario. En búsqueda, Enter y su botón ejecutan el algoritmo;
    en partida, se juega seleccionando una unidad y destinos legales en el tablero o, con control por algoritmos,
    avanzando una jugada con N o su botón. V verifica las búsquedas; M o su botón cambian el modo; la apertura de
    escenarios es atómica; Pygame se libera al cerrar.
    Complejidad: el costo de la búsqueda más O(E*(F*C + U + T + L + P)) temporal durante el ciclo y
    O(F*C + T + L + P) espacial, con P posiciones expandidas almacenadas y E fotogramas.
    Uso de IA: Si.
    Intervencion de IA: Codex: integración de E9.2 y E9.3, controles directos de escenario, algoritmo, unidad, objetivo
    y Beam sin recalcular por fotograma ni modificar el estado de juego, verificación de búsquedas con V y partida
    manual con eventos de Pygame y transiciones del dominio. Claude (Opus 5.5): apertura de escenarios JSON con la
    tecla O, su botón y arrastrar y soltar (E9.4); controles de la partida por turnos entre algoritmos (E9.5).
    Validacion del estudiante: pruebas de tests/interfaz/test_aplicacion.py bajo SDL dummy: inicio y cierre sin repetir
    la búsqueda, error antes de abrir la ventana, turno jugado con clics, cambio a modo partida, verificación con V y
    apertura de JSON; pruebas de tests/interfaz/test_turnos_aplicacion.py: tecla N y botones de la partida por
    algoritmos.
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
        resultado = (
            preparar_busqueda(
                control.escenario,
                control.estado,
                algoritmo,
                unidad,
                objetivo,
                k,
                control.heuristica_astar if algoritmo == "astar" else "manhattan",
            )
            if control.modo == "busqueda"
            else None
        )
        control.resultado = resultado
        if control.modo != "busqueda" and any(valor is not None for valor in (algoritmo, unidad, objetivo, k)):
            control.mensaje = f"El escenario solicita modo {control.modo}; los parametros de busqueda no se aplican."
            control.error = True
        elif algoritmo is not None:
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
                en_ejecucion = _procesar_evento(control, evento, disposicion, rectangulos) and en_ejecucion
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
    """Interpretar solo los argumentos gráficos y delegar en la aplicación.

    Proposito: mantener el parser gráfico separado del parser histórico de consola.
    Precondiciones: ``argumentos`` no incluye ``--gui`` ni el nombre del programa.
    Postcondiciones: se ejecuta la interfaz con las opciones interpretadas y se devuelve su código de salida.
    Complejidad: O(A) temporal y espacial para A argumentos, más el costo de la aplicación delegada.
    Uso de IA: Si.
    Intervencion de IA: Codex: extracción de este adaptador durante la refactorización final de ``main.py``.
    Validacion del estudiante: prueba ``test_despacha_gui_predeterminada_y_consola_historica`` de
    tests/test_despachador.py y pruebas del parser gráfico en tests/interfaz/test_aplicacion.py.
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
    """Catalogar los JSON incluidos y conservar una ruta externa recibida explícitamente."""
    incluidas = tuple((RAIZ_PROYECTO / "escenarios").glob("*.json"))
    return tuple(sorted({ruta.resolve() for ruta in incluidas} | {Path(ruta_actual).resolve()}))


def _procesar_evento(control: ControlGrafico, evento, disposicion, rectangulos: RectangulosControles) -> bool:
    """Atender los eventos de Pygame, incluidos los atajos de modo, apertura y exportación reproducible."""
    import pygame

    if evento.type == pygame.QUIT:
        return False
    if evento.type == pygame.KEYDOWN and evento.key == pygame.K_e:
        control.evaluar_decision(comparar=True) if control.modo == "adversarial" else control.alternar_exploracion()
    elif evento.type == pygame.KEYDOWN and evento.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
        control.evaluar_decision() if control.modo == "adversarial" else control.ejecutar()
    elif evento.type == pygame.KEYDOWN and evento.key == pygame.K_o:
        control.abrir_con_dialogo(pedir_ruta_escenario)
    elif evento.type == pygame.KEYDOWN and evento.key == pygame.K_v:
        control.verificar_decision_actual() if control.modo == "adversarial" else control.verificar()
    elif evento.type == pygame.KEYDOWN and evento.key == pygame.K_m:
        control.cambiar_modo()
    elif evento.type == pygame.KEYDOWN and evento.key == pygame.K_r and control.modo == "partida":
        control.reiniciar_partida()
    elif evento.type == pygame.KEYDOWN and evento.key == pygame.K_n and control.modo == "partida":
        control.siguiente_turno()
    elif evento.type == pygame.KEYDOWN and evento.key == pygame.K_a:
        control.aplicar_decision_recomendada(confirmar=control.aplicar_confirmacion_pendiente)
    elif evento.type == pygame.KEYDOWN and evento.key == pygame.K_q:
        control.evaluar_decision()
    elif evento.type == pygame.KEYDOWN and evento.key == pygame.K_c:
        control.evaluar_decision(comparar=True)
    elif evento.type == pygame.KEYDOWN and evento.key == pygame.K_j:
        try:
            destino = pedir_ruta_registro(control.ruta_escenario.parent)
        except DialogoNoDisponible as error:
            control.mensaje = f"No se pudo abrir el selector de guardado: {error}"
            control.error = True
        else:
            if destino is None:
                control.mensaje = "Exportacion cancelada."
                control.estado_busqueda = "exportacion cancelada"
            else:
                control.exportar_experimento(destino)
    elif evento.type == pygame.DROPFILE:
        control.abrir_escenario(evento.file)
    elif evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
        _procesar_clic(control, evento.pos, disposicion, rectangulos)
    return True


def _procesar_clic(
    control: ControlGrafico,
    punto: tuple[int, int],
    disposicion,
    rectangulos: RectangulosControles,
) -> None:
    """Traducir un clic en una única operación de control o en la selección de un objetivo.

    Proposito: centralizar las áreas sensibles y garantizar que el teclado y el botón de exploración compartan estado.
    Precondiciones: la disposición y los rectángulos corresponden al último fotograma renderizado.
    Postcondiciones: se ejecuta como máximo una acción: en búsqueda se selecciona el objetivo, en partida solo se
    aplican acciones legales y en modo adversarial se evalúa, se verifica o se pide confirmación para aplicar. Evaluar
    no cambia el estado. En partida, las flechas del algoritmo alternan el control manual o por algoritmos; con
    control por algoritmos, las flechas de unidad y de k eligen el algoritmo de los bandos A y B y el botón de
    ejecutar avanza exactamente una jugada.
    Complejidad: O(1), salvo la carga de un escenario, la búsqueda o la decisión de una jugada solicitadas
    explícitamente.
    Uso de IA: Si.
    Intervencion de IA: Codex: interacción directa de Pygame para E9.3, apertura de JSON, partida y evaluación
    adversarial con aplicación confirmada. Claude (Opus 5.5): controles de la partida por turnos entre algoritmos
    (E9.5).
    Validacion del estudiante: pruebas de tests/interfaz/test_aplicacion.py bajo SDL dummy: clic en el tablero que
    selecciona el objetivo sin mover unidades, botón de ejecutar con una sola búsqueda, turno jugado con clics y
    evaluación, verificación y confirmación de la recomendación; pruebas de
    tests/interfaz/test_turnos_aplicacion.py: cambio de control, algoritmo por bando, una jugada por clic o por tecla N
    y reinicio.
    """
    acciones = [
        (rectangulos.modo, control.cambiar_modo),
        (rectangulos.escenario_anterior, lambda: control.cambiar_escenario(-1)),
        (rectangulos.escenario_siguiente, lambda: control.cambiar_escenario(1)),
        (rectangulos.abrir, lambda: control.abrir_con_dialogo(pedir_ruta_escenario)),
    ]
    if control.modo == "busqueda":
        acciones.extend(
            [
                (rectangulos.unidad_anterior, lambda: control.cambiar_unidad(-1)),
                (rectangulos.unidad_siguiente, lambda: control.cambiar_unidad(1)),
                (rectangulos.algoritmo_anterior, lambda: control.cambiar_algoritmo(-1)),
                (rectangulos.algoritmo_siguiente, lambda: control.cambiar_algoritmo(1)),
                (
                    rectangulos.k_menor,
                    lambda: control.cambiar_heuristica_astar(-1)
                    if control.algoritmo == "astar"
                    else control.cambiar_k(-1),
                ),
                (
                    rectangulos.k_mayor,
                    lambda: control.cambiar_heuristica_astar(1)
                    if control.algoritmo == "astar"
                    else control.cambiar_k(1),
                ),
                (rectangulos.ejecutar, control.ejecutar),
                (rectangulos.exploracion, control.alternar_exploracion),
                (rectangulos.verificar, control.verificar),
            ]
        )
    elif control.modo == "partida":
        acciones.extend(
            [
                (rectangulos.algoritmo_anterior, lambda: control.cambiar_control_partida(-1)),
                (rectangulos.algoritmo_siguiente, lambda: control.cambiar_control_partida(1)),
            ]
        )
        if control.control_partida == CONTROL_ALGORITMOS:
            acciones.extend(
                [
                    (rectangulos.unidad_anterior, lambda: control.cambiar_algoritmo_bando("A", -1)),
                    (rectangulos.unidad_siguiente, lambda: control.cambiar_algoritmo_bando("A", 1)),
                    (rectangulos.k_menor, lambda: control.cambiar_algoritmo_bando("B", -1)),
                    (rectangulos.k_mayor, lambda: control.cambiar_algoritmo_bando("B", 1)),
                    (rectangulos.ejecutar, control.siguiente_turno),
                ]
            )
        else:
            acciones.extend(
                [
                    (rectangulos.unidad_anterior, lambda: control.cambiar_unidad(-1)),
                    (rectangulos.unidad_siguiente, lambda: control.cambiar_unidad(1)),
                ]
            )
        acciones.extend(
            [
                (rectangulos.verificar, control.verificar),
                (rectangulos.exploracion, control.reiniciar_partida),
            ]
        )
    elif control.modo == "adversarial":
        acciones.extend(
            [
                (rectangulos.algoritmo_anterior, lambda: control.cambiar_algoritmo_adversarial(-1)),
                (rectangulos.algoritmo_siguiente, lambda: control.cambiar_algoritmo_adversarial(1)),
                (rectangulos.unidad_anterior, lambda: control.cambiar_profundidad_adversarial(-1)),
                (rectangulos.unidad_siguiente, lambda: control.cambiar_profundidad_adversarial(1)),
                (rectangulos.k_menor, lambda: control.cambiar_orden_adversarial(-1)),
                (rectangulos.k_mayor, lambda: control.cambiar_orden_adversarial(1)),
                (rectangulos.ejecutar, control.evaluar_decision),
                (rectangulos.exploracion, lambda: control.evaluar_decision(comparar=True)),
                (rectangulos.verificar, control.verificar_decision_actual),
                (
                    rectangulos.aplicar,
                    lambda: control.aplicar_decision_recomendada(confirmar=control.aplicar_confirmacion_pendiente),
                ),
            ]
        )
    for rectangulo, accion in acciones:
        if rectangulo.collidepoint(punto):
            accion()
            return
    if disposicion.tablero.collidepoint(punto):
        columna = (punto[0] - disposicion.tablero.x) // disposicion.tamano_celda
        fila = (punto[1] - disposicion.tablero.y) // disposicion.tamano_celda
        posicion = Posicion(fila, columna)
        if control.modo == "partida":
            control.clic_partida(posicion)
        elif control.modo == "busqueda":
            control.seleccionar_objetivo(posicion)


def _leer_argumentos(argumentos: Sequence[str] | None = None) -> argparse.Namespace:
    """Leer la selección opcional de escenario y búsqueda de la interfaz gráfica."""
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
