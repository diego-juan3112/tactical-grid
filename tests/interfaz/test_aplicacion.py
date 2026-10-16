"""Pruebas de la seleccion y ejecucion de busquedas desde la interfaz Pygame."""

import os
from dataclasses import replace
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame
import pytest

from tacticalgrid.algoritmos import (
    ObservadorExpansiones,
    busqueda_a_estrella,
    busqueda_anchura,
    busqueda_costo_uniforme,
    busqueda_haz,
    busqueda_profundidad,
)
from tacticalgrid.escenario import Posicion, cargar_escenario
from tacticalgrid.interfaz import aplicacion
from tacticalgrid.interfaz.aplicacion import _leer_argumentos, ejecutar_aplicacion, preparar_busqueda
from tacticalgrid.juego import ProblemaNavegacion, crear_estado_inicial


RAIZ = Path(__file__).resolve().parents[2]
RUTA_COMPARACION = RAIZ / "escenarios" / "ruta_corta_vs_economica.json"


@pytest.mark.parametrize(
    ("algoritmo", "k", "nombre", "longitud", "costo"),
    [
        ("bfs", None, "BFS", 8, 50),
        ("dfs", None, "DFS", 12, 12),
        ("ucs", None, "UCS", 12, 12),
        ("astar", None, "A_ESTRELLA", 12, 12),
        ("beam", 4, "BEAM_SEARCH_K4", 8, 50),
    ],
)
def test_ejecuta_cada_algoritmo_una_vez_sobre_el_estado_inicial(
    algoritmo: str,
    k: int | None,
    nombre: str,
    longitud: int,
    costo: int,
) -> None:
    escenario = cargar_escenario(RUTA_COMPARACION)
    estado = crear_estado_inicial(escenario)

    resultado = preparar_busqueda(escenario, estado, algoritmo, k=k)

    assert resultado is not None
    assert (resultado.algoritmo, resultado.exito, resultado.longitud, resultado.costo) == (
        nombre,
        True,
        longitud,
        costo,
    )
    assert resultado.camino[0] == Posicion(2, 0)
    assert resultado.camino[-1] == Posicion(2, 8)
    assert estado == crear_estado_inicial(escenario)


def test_bfs_y_ucs_conservan_caminos_academicos_diferentes() -> None:
    escenario = cargar_escenario(RUTA_COMPARACION)
    estado = crear_estado_inicial(escenario)

    bfs = preparar_busqueda(escenario, estado, "bfs")
    ucs = preparar_busqueda(escenario, estado, "ucs")

    assert bfs is not None and ucs is not None
    assert bfs.camino != ucs.camino
    assert (bfs.longitud, bfs.costo) == (8, 50)
    assert (ucs.longitud, ucs.costo) == (12, 12)


def test_cli_tiene_prioridad_sobre_unidad_objetivo_y_k_del_json() -> None:
    escenario_original = cargar_escenario(RUTA_COMPARACION)
    escenario = replace(
        escenario_original,
        configuracion_prueba={
            "modo": "busqueda",
            "unidad_inicio": "A2",
            "objetivo": {"fila": 0, "columna": 1},
            "k": 1,
        },
    )
    estado = crear_estado_inicial(escenario)

    resultado = preparar_busqueda(escenario, estado, "beam", "A1", (2, 8), 4)

    assert resultado is not None
    assert resultado.algoritmo == "BEAM_SEARCH_K4"
    assert resultado.camino[0] == Posicion(2, 0)
    assert resultado.camino[-1] == Posicion(2, 8)


def test_beam_usa_k_del_json_cuando_no_hay_valor_cli() -> None:
    escenario_original = cargar_escenario(RUTA_COMPARACION)
    escenario = replace(
        escenario_original,
        configuracion_prueba={**escenario_original.configuracion_prueba, "k": 1},
    )

    resultado = preparar_busqueda(escenario, crear_estado_inicial(escenario), "beam")

    assert resultado is not None
    assert resultado.algoritmo == "BEAM_SEARCH_K1"


def test_sin_algoritmo_conserva_e91_y_no_produce_resultado() -> None:
    escenario = cargar_escenario(RUTA_COMPARACION)

    assert preparar_busqueda(escenario, crear_estado_inicial(escenario), None) is None


@pytest.mark.parametrize(
    ("algoritmo", "unidad", "objetivo", "k", "mensaje"),
    [
        (None, "A1", None, None, "requieren indicar --algoritmo"),
        ("bfs", None, None, 4, "solo puede usarse"),
        ("beam", None, None, None, "necesita --k"),
        ("beam", None, None, 0, "mayor o igual que 1"),
    ],
)
def test_rechaza_combinaciones_invalidas(
    algoritmo: str | None,
    unidad: str | None,
    objetivo: tuple[int, int] | None,
    k: int | None,
    mensaje: str,
) -> None:
    escenario = cargar_escenario(RUTA_COMPARACION)

    with pytest.raises(ValueError, match=mensaje):
        preparar_busqueda(escenario, crear_estado_inicial(escenario), algoritmo, unidad, objetivo, k)


def test_informa_unidad_y_objetivo_faltantes_fuera_del_modo_busqueda() -> None:
    escenario_original = cargar_escenario(RUTA_COMPARACION)
    escenario = replace(escenario_original, configuracion_prueba={"modo": "partida"})
    estado = crear_estado_inicial(escenario)

    with pytest.raises(ValueError, match="Debe indicar --unidad"):
        preparar_busqueda(escenario, estado, "bfs")
    with pytest.raises(ValueError, match="Debe indicar --objetivo"):
        preparar_busqueda(escenario, estado, "bfs", "A1")


@pytest.mark.parametrize("algoritmo", ["bfs", "dfs", "ucs", "astar", "beam"])
def test_parser_admite_los_cinco_nombres_publicos(algoritmo: str) -> None:
    argumentos = [str(RUTA_COMPARACION), "--algoritmo", algoritmo]
    if algoritmo == "beam":
        argumentos.extend(("--k", "4"))

    resultado = _leer_argumentos(argumentos)

    assert resultado.algoritmo == algoritmo
    assert resultado.k == (4 if algoritmo == "beam" else None)


def test_parser_lee_unidad_y_objetivo_explicitos() -> None:
    resultado = _leer_argumentos(
        [str(RUTA_COMPARACION), "--algoritmo", "astar", "--unidad", "A1", "--objetivo", "2", "8"]
    )

    assert resultado.unidad == "A1"
    assert resultado.objetivo == [2, 8]


@pytest.mark.parametrize(("algoritmo", "k"), [(None, None), ("bfs", None), ("beam", 4)])
def test_aplicacion_inicia_con_sdl_dummy_y_cierra_sin_repetir_busqueda(monkeypatch, algoritmo, k):
    llamadas = 0
    preparar_original = aplicacion.preparar_busqueda

    def contar_preparacion(*argumentos, **opciones):
        nonlocal llamadas
        llamadas += 1
        return preparar_original(*argumentos, **opciones)

    monkeypatch.setattr(aplicacion, "preparar_busqueda", contar_preparacion)
    monkeypatch.setattr(pygame.event, "get", lambda: [pygame.event.Event(pygame.QUIT)])

    codigo = ejecutar_aplicacion(RUTA_COMPARACION, algoritmo=algoritmo, k=k)

    assert codigo == 0
    assert llamadas == 1


def test_aplicacion_informa_error_antes_de_abrir_ventana(capsys):
    codigo = ejecutar_aplicacion(RUTA_COMPARACION, algoritmo="ucs", k=4)

    assert codigo == 1
    assert "--k solo puede usarse con --algoritmo beam" in capsys.readouterr().err


def test_tecla_e_alterna_exploracion_sin_repetir_busqueda(monkeypatch):
    llamadas_busqueda = 0
    visibilidades = []
    preparar_original = aplicacion.preparar_busqueda
    renderizar_original = aplicacion.RenderizadorTablero.renderizar
    tandas = iter(
        [
            [pygame.event.Event(pygame.KEYDOWN, key=pygame.K_e)],
            [pygame.event.Event(pygame.KEYDOWN, key=pygame.K_e)],
            [pygame.event.Event(pygame.QUIT)],
        ]
    )

    def contar_preparacion(*argumentos, **opciones):
        nonlocal llamadas_busqueda
        llamadas_busqueda += 1
        return preparar_original(*argumentos, **opciones)

    def registrar_visibilidad(self, *argumentos, **opciones):
        visibilidades.append(opciones["exploracion_visible"])
        return renderizar_original(self, *argumentos, **opciones)

    monkeypatch.setattr(aplicacion, "preparar_busqueda", contar_preparacion)
    monkeypatch.setattr(aplicacion.RenderizadorTablero, "renderizar", registrar_visibilidad)
    monkeypatch.setattr(pygame.event, "get", lambda: next(tandas))

    assert ejecutar_aplicacion(RUTA_COMPARACION, algoritmo="bfs") == 0
    assert llamadas_busqueda == 1
    assert visibilidades == [True, False, False]


def test_tecla_e_sin_busqueda_no_activa_capa_ni_falla(monkeypatch):
    visibilidades = []
    renderizar_original = aplicacion.RenderizadorTablero.renderizar
    tandas = iter(
        [
            [pygame.event.Event(pygame.KEYDOWN, key=pygame.K_e)],
            [pygame.event.Event(pygame.QUIT)],
        ]
    )

    def registrar_visibilidad(self, *argumentos, **opciones):
        visibilidades.append(opciones["exploracion_visible"])
        return renderizar_original(self, *argumentos, **opciones)

    monkeypatch.setattr(aplicacion.RenderizadorTablero, "renderizar", registrar_visibilidad)
    monkeypatch.setattr(pygame.event, "get", lambda: next(tandas))

    assert ejecutar_aplicacion(RUTA_COMPARACION) == 0
    assert visibilidades == [False, False]


@pytest.mark.parametrize("algoritmo", ["bfs", "dfs", "ucs", "astar", "beam"])
def test_observador_no_altera_resultado_metricas_ni_estado(algoritmo):
    escenario = cargar_escenario(RUTA_COMPARACION)
    estado = crear_estado_inicial(escenario)
    objetivo = Posicion(2, 8)
    problema = ProblemaNavegacion(escenario, "A1", objetivo, estado)
    observador = ObservadorExpansiones()
    funciones = {
        "bfs": busqueda_anchura,
        "dfs": busqueda_profundidad,
        "ucs": busqueda_costo_uniforme,
        "astar": busqueda_a_estrella,
    }
    if algoritmo == "beam":
        sin_observador = busqueda_haz(problema, 4)
        con_observador = busqueda_haz(problema, 4, observador_expansiones=observador)
    else:
        funcion = funciones[algoritmo]
        sin_observador = funcion(problema)
        con_observador = funcion(problema, observador_expansiones=observador)

    campos = (
        "algoritmo",
        "exito",
        "camino",
        "costo",
        "estados_generados",
        "estados_expandidos",
        "maximo_frontera",
        "acciones",
    )
    assert tuple(getattr(sin_observador, campo) for campo in campos) == tuple(
        getattr(con_observador, campo) for campo in campos
    )
    assert sin_observador.traza_expansiones is None
    assert con_observador.traza_expansiones.total_expansiones == con_observador.estados_expandidos
    assert estado == crear_estado_inicial(escenario)


def test_boton_e_y_tecla_e_comparten_estado_sin_repetir_busqueda(monkeypatch):
    escenario = cargar_escenario(RUTA_COMPARACION)
    superficie = pygame.Surface((800, 600))
    renderizador = aplicacion.RenderizadorTablero()
    disposicion = renderizador.calcular_disposicion(superficie, escenario)
    boton_e = renderizador.calcular_rectangulos_controles(disposicion.panel).exploracion.center
    tandas = iter(
        [
            [pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=boton_e)],
            [pygame.event.Event(pygame.KEYDOWN, key=pygame.K_e)],
            [pygame.event.Event(pygame.QUIT)],
        ]
    )
    visibilidades = []
    preparar_original = aplicacion.preparar_busqueda
    renderizar_original = aplicacion.RenderizadorTablero.renderizar
    llamadas = 0

    def contar_busqueda(*argumentos, **opciones):
        nonlocal llamadas
        llamadas += 1
        return preparar_original(*argumentos, **opciones)

    def registrar_render(self, *argumentos, **opciones):
        visibilidades.append(opciones["exploracion_visible"])
        return renderizar_original(self, *argumentos, **opciones)

    monkeypatch.setattr(aplicacion, "preparar_busqueda", contar_busqueda)
    monkeypatch.setattr(aplicacion.RenderizadorTablero, "renderizar", registrar_render)
    monkeypatch.setattr(pygame.event, "get", lambda: next(tandas))

    assert ejecutar_aplicacion(RUTA_COMPARACION, algoritmo="bfs") == 0
    assert llamadas == 1
    assert visibilidades == [True, False, False]


def test_clic_en_tablero_selecciona_objetivo_sin_mover_unidades(monkeypatch):
    escenario = cargar_escenario(RUTA_COMPARACION)
    estado = crear_estado_inicial(escenario)
    superficie = pygame.Surface((800, 600))
    renderizador = aplicacion.RenderizadorTablero()
    disposicion = renderizador.calcular_disposicion(superficie, escenario)
    objetivo = Posicion(0, 1)
    punto = (
        disposicion.tablero.x + objetivo.columna * disposicion.tamano_celda + 2,
        disposicion.tablero.y + objetivo.fila * disposicion.tamano_celda + 2,
    )
    tandas = iter(
        [
            [pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=punto)],
            [pygame.event.Event(pygame.QUIT)],
        ]
    )
    seleccionadas = []
    seleccionar_original = aplicacion.ControlGrafico.seleccionar_objetivo

    def registrar_objetivo(self, posicion):
        seleccionadas.append(posicion)
        return seleccionar_original(self, posicion)

    monkeypatch.setattr(aplicacion.ControlGrafico, "seleccionar_objetivo", registrar_objetivo)
    monkeypatch.setattr(pygame.event, "get", lambda: next(tandas))

    assert ejecutar_aplicacion(RUTA_COMPARACION) == 0
    assert seleccionadas == [objetivo]
    assert estado == crear_estado_inicial(escenario)


def test_boton_ejecutar_invoca_una_sola_busqueda(monkeypatch):
    escenario = cargar_escenario(RUTA_COMPARACION)
    control = aplicacion.ControlGrafico.crear(RUTA_COMPARACION, (RUTA_COMPARACION,))
    superficie = pygame.Surface((800, 600))
    renderizador = aplicacion.RenderizadorTablero()
    disposicion = renderizador.calcular_disposicion(superficie, escenario)
    rectangulos = renderizador.calcular_rectangulos_controles(disposicion.panel)
    llamadas = 0

    def contar_ejecucion():
        nonlocal llamadas
        llamadas += 1

    monkeypatch.setattr(control, "ejecutar", contar_ejecucion)

    aplicacion._procesar_clic(control, rectangulos.ejecutar.center, disposicion, rectangulos)

    assert llamadas == 1


@pytest.mark.parametrize("tecla", [pygame.K_RETURN, pygame.K_KP_ENTER])
def test_enter_y_enter_numerico_invocan_la_misma_accion_una_vez(monkeypatch, tecla):
    llamadas = 0
    tandas = iter(
        [
            [pygame.event.Event(pygame.KEYDOWN, key=tecla)],
            [pygame.event.Event(pygame.QUIT)],
        ]
    )

    def contar_ejecucion(self):
        nonlocal llamadas
        llamadas += 1

    monkeypatch.setattr(aplicacion.ControlGrafico, "ejecutar", contar_ejecucion)
    monkeypatch.setattr(pygame.event, "get", lambda: next(tandas))

    assert ejecutar_aplicacion(RUTA_COMPARACION) == 0
    assert llamadas == 1
