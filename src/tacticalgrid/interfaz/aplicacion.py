"""Punto de entrada de la visualizacion Pygame de TacticalGrid."""

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from tacticalgrid.escenario import ErrorValidacionEscenario, Posicion

from .busquedas import ALGORITMOS, preparar_busqueda
from .control import ControlGrafico
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
    """Carga un escenario, ejecuta una busqueda opcional y mantiene visible el tablero.

    Proposito: integrar carga validada, busqueda estructurada y renderizado, incluida la capa E9.3 bajo demanda.
    Precondiciones: Pygame esta instalado, existe un entorno grafico y la ruta identifica un escenario valido.
    Postcondiciones: carga el modo declarado por el escenario; busqueda usa Enter y su boton, y partida se juega
    seleccionando unidad y destinos legales en el tablero. V verifica busquedas; M o su boton cambian el modo; abrir
    escenarios es atomico; Pygame se libera al cerrar.
    Complejidad: costo de la busqueda mas O(E*(F*C + U + T + L + P)) temporal durante el ciclo y
    O(F*C + T + L + P) espacial, donde P son posiciones expandidas almacenadas y E los fotogramas.
    Uso de IA: Si.
    Intervencion de IA: Codex integro E9.2/E9.3 y agrego controles directos para escenario, algoritmo, unidad,
    objetivo y Beam sin recalcular por fotograma ni modificar el estado de juego. Claude (Opus 5.5) agrego en E9.4
    la apertura de escenarios JSON con la tecla O, su boton y arrastrar y soltar. Codex conecto la verificacion de
    busquedas con V y el modo partida manual con eventos de Pygame y transiciones del dominio.
    Validacion del estudiante: No puedo confirmar una revision manual del equipo para la verificacion y partida
    integradas. Las pruebas automatizadas de aplicacion y renderizador cubren eventos y presentacion bajo SDL dummy.
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
    """Interpreta exclusivamente argumentos graficos y delega la aplicacion.

    Proposito: mantener separado el parser grafico del parser historico de consola.
    Precondiciones: ``argumentos`` no incluye ``--gui`` ni el nombre del programa.
    Postcondiciones: ejecuta la GUI con las opciones interpretadas y devuelve su codigo de salida.
    Complejidad: O(A) temporal y espacial para A argumentos, mas el costo de la aplicacion delegada.
    Uso de IA: Si.
    Intervencion de IA: Codex extrajo este adaptador durante la refactorizacion final de ``main.py``.
    Validacion del estudiante: revisado y aprobado por el equipo; cubierta por pruebas del despachador y parser grafico.
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


def _procesar_evento(control: ControlGrafico, evento, disposicion, rectangulos: RectangulosControles) -> bool:
    """Atiende eventos Pygame, incluidos atajos de modo y exportacion reproducible."""
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
    """Traduce un clic a una unica operacion de control o a seleccion de objetivo.

    Proposito: centralizar hitboxes y garantizar que teclado y boton de exploracion compartan estado.
    Precondiciones: disposicion y rectangulos corresponden al ultimo fotograma renderizado.
    Postcondiciones: ejecuta a lo sumo una accion; en busqueda selecciona objetivo, en partida aplica solo acciones
    legales y en adversarial evalua/verifica o solicita confirmacion de aplicacion. Evaluar no cambia el estado.
    Complejidad: O(1) salvo carga de escenario o busqueda solicitadas explicitamente.
    Uso de IA: Si.
    Intervencion de IA: Codex implemento la interaccion directa de Pygame para E9.3, apertura JSON, partida y
    evaluacion adversarial con aplicacion confirmada en esta continuacion.
    Validacion del estudiante: No puedo confirmar revision manual; pruebas SDL dummy cubren eventos de busqueda,
    partida y evaluacion/verificacion/aplicacion adversarial.
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
                (rectangulos.unidad_anterior, lambda: control.cambiar_unidad(-1)),
                (rectangulos.unidad_siguiente, lambda: control.cambiar_unidad(1)),
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
