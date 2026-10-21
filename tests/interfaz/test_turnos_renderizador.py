"""Pruebas del renderizado de la partida por turnos entre algoritmos (E9.5) sobre superficies sin ventana real."""

import os
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame
import pytest

from tacticalgrid.algoritmos.resultado_busqueda import ResultadoBusqueda
from tacticalgrid.escenario.escenario import Posicion
from tacticalgrid.interfaz.control import ControlGrafico
from tacticalgrid.interfaz.renderizador import EstadoPanelControl, RenderizadorTablero

RUTA = Path(__file__).resolve().parents[2] / "escenarios" / "prueba_gui_partida.json"


@pytest.fixture(autouse=True)
def pygame_inicializado():
    pygame.init()
    yield
    pygame.quit()


def _control_tras_un_turno() -> ControlGrafico:
    control = ControlGrafico.crear(RUTA, (RUTA,))
    control.cambiar_control_partida(1)
    control.algoritmos_bandos = {"A": "astar", "B": "ucs"}
    control.siguiente_turno()
    return control


def _celda(disposicion, posicion: Posicion) -> pygame.Rect:
    lado = disposicion.tamano_celda
    return pygame.Rect(
        disposicion.tablero.x + posicion.columna * lado,
        disposicion.tablero.y + posicion.fila * lado,
        lado,
        lado,
    )


def _colores_en(superficie: pygame.Surface, rectangulo: pygame.Rect) -> set[tuple[int, int, int]]:
    return {
        tuple(superficie.get_at((x, y)))[:3]
        for x in range(rectangulo.left, rectangulo.right)
        for y in range(rectangulo.top, rectangulo.bottom)
    }


def _registrar_textos(monkeypatch, renderizador: RenderizadorTablero) -> tuple[list[str], list[str], list[str]]:
    textos: list[str] = []
    centrados: list[str] = []
    botones: list[str] = []
    dibujar_texto = renderizador._dibujar_texto
    dibujar_centrado = renderizador._dibujar_texto_centrado
    dibujar_boton = renderizador._dibujar_boton

    def registrar_texto(superficie_destino, texto, color, posicion, fuente):
        textos.append(texto)
        return dibujar_texto(superficie_destino, texto, color, posicion, fuente)

    def registrar_centrado(superficie_destino, texto, color, rectangulo, fuente):
        centrados.append(texto)
        return dibujar_centrado(superficie_destino, texto, color, rectangulo, fuente)

    def registrar_boton(superficie_destino, rectangulo, texto, color_texto=None):
        botones.append(texto)
        return dibujar_boton(superficie_destino, rectangulo, texto, color_texto)

    monkeypatch.setattr(renderizador, "_dibujar_texto", registrar_texto)
    monkeypatch.setattr(renderizador, "_dibujar_texto_centrado", registrar_centrado)
    monkeypatch.setattr(renderizador, "_dibujar_boton", registrar_boton)
    return textos, centrados, botones


def test_desde_control_proyecta_el_control_por_algoritmos_y_la_ultima_jugada() -> None:
    control = _control_tras_un_turno()
    decision = control.ultima_decision

    panel = EstadoPanelControl.desde_control(control)

    assert decision is not None
    assert panel.control_partida == "algoritmos"
    assert (panel.algoritmo_bando_a, panel.algoritmo_bando_b) == ("A*", "UCS")
    assert panel.ultima_jugada == (decision.accion.origen, decision.accion.destino)
    assert panel.turno_actual == control.estado.turno_actual == "B"
    assert panel.lineas_turno
    assert "bando A con A*" in panel.lineas_turno[0]
    assert any(decision.accion.identificador_unidad in linea for linea in panel.lineas_turno)
    assert any(f"Meta: {decision.meta}" in linea for linea in panel.lineas_turno)
    assert any("Camino planeado: costo" in linea and "estados expandidos" in linea for linea in panel.lineas_turno)
    assert "profundidad" in panel.lineas_turno[-1] and "heurística A*" in panel.lineas_turno[-1]


def test_panel_por_algoritmos_muestra_bandos_siguiente_turno_y_lineas(monkeypatch) -> None:
    control = _control_tras_un_turno()
    panel = EstadoPanelControl.desde_control(control)
    renderizador = RenderizadorTablero()
    textos, centrados, botones = _registrar_textos(monkeypatch, renderizador)
    estado_previo = control.estado
    resultado_previo = control.resultado

    renderizador.renderizar(
        pygame.Surface((960, 720)), control.escenario, control.estado, control.resultado, control=panel
    )

    assert "Control: Algoritmos" in centrados
    assert "Bando A: A*" in centrados and "Bando B: UCS" in centrados
    assert {"N — Siguiente turno", "R — Reiniciar partida", "V — Verificar partida"} <= set(botones)
    assert "1 jugadas | turno de B" in textos
    assert any("bando A con A*" in texto for texto in textos)
    assert "Clic en una unidad activa para seleccionarla" not in centrados
    assert control.estado is estado_previo and control.resultado is resultado_previo
    assert isinstance(control.resultado, ResultadoBusqueda)


def test_destino_de_la_ultima_jugada_tiene_el_color_propio_sin_modificar_estado() -> None:
    control = _control_tras_un_turno()
    panel = EstadoPanelControl.desde_control(control)
    renderizador = RenderizadorTablero()
    superficie = pygame.Surface((960, 720))
    estado_previo = control.estado
    resultado_previo = control.resultado

    disposicion = renderizador.renderizar(
        superficie, control.escenario, control.estado, control.resultado, control=panel
    )

    color = renderizador.COLOR_ULTIMA_JUGADA
    assert color not in {
        renderizador.COLOR_CAMINO,
        renderizador.COLOR_ORIGEN,
        renderizador.COLOR_DESTINO,
        renderizador.COLOR_EXPLORACION,
    }
    origen, destino = panel.ultima_jugada
    assert color in _colores_en(superficie, _celda(disposicion, destino))
    assert color in _colores_en(superficie, _celda(disposicion, origen))
    assert control.estado is estado_previo and control.resultado is resultado_previo


def test_control_manual_no_marca_ultima_jugada_y_conserva_el_texto_manual(monkeypatch) -> None:
    control = ControlGrafico.crear(RUTA, (RUTA,))
    panel = EstadoPanelControl.desde_control(control)
    renderizador = RenderizadorTablero()
    textos, centrados, botones = _registrar_textos(monkeypatch, renderizador)
    superficie = pygame.Surface((960, 720))

    disposicion = renderizador.renderizar(superficie, control.escenario, control.estado, control=panel)

    assert panel.control_partida == "manual"
    assert panel.ultima_jugada is None and panel.lineas_turno == ()
    assert "Control: Manual" in centrados
    assert any(texto.startswith("Unidad activa:") for texto in centrados)
    assert "Clic en una unidad activa para seleccionarla" in centrados
    assert "N — Siguiente turno" not in botones
    assert any(texto.startswith("Acciones legales:") for texto in textos)
    celdas = [_celda(disposicion, Posicion(fila, columna)) for fila in range(5) for columna in range(5)]
    assert all(renderizador.COLOR_ULTIMA_JUGADA not in _colores_en(superficie, celda) for celda in celdas)


def test_volver_a_control_manual_oculta_la_ultima_jugada_de_los_algoritmos() -> None:
    control = _control_tras_un_turno()

    control.cambiar_control_partida(1)
    panel = EstadoPanelControl.desde_control(control)

    assert panel.control_partida == "manual"
    assert panel.ultima_jugada is None and panel.lineas_turno == ()
