"""Pruebas de los controles Pygame de la partida por turnos entre algoritmos (E9.5)."""

import os
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame
import pytest

from tacticalgrid.escenario import Posicion
from tacticalgrid.interfaz import aplicacion
from tacticalgrid.interfaz.control import CONTROL_ALGORITMOS, CONTROL_MANUAL
from tacticalgrid.modos.agentes import ALGORITMOS_AGENTE


RAIZ = Path(__file__).resolve().parents[2]
RUTA = RAIZ / "escenarios" / "prueba_gui_partida.json"


@pytest.fixture
def interfaz():
    """Control en modo partida y geometria del panel igual a la que dibuja el renderizador."""
    control = aplicacion.ControlGrafico.crear(RUTA, (RUTA,))
    renderizador = aplicacion.RenderizadorTablero()
    disposicion = renderizador.calcular_disposicion(pygame.Surface((800, 600)), control.escenario)
    rectangulos = renderizador.calcular_rectangulos_controles(disposicion.panel)
    return control, disposicion, rectangulos


def _clic(interfaz, nombre: str) -> None:
    control, disposicion, rectangulos = interfaz
    aplicacion._procesar_clic(control, getattr(rectangulos, nombre).center, disposicion, rectangulos)


def _tecla(control, tecla) -> bool:
    return aplicacion._procesar_evento(control, pygame.event.Event(pygame.KEYDOWN, key=tecla), None, None)


def _centro_celda(disposicion, posicion: Posicion) -> tuple[int, int]:
    return (
        disposicion.tablero.x + posicion.columna * disposicion.tamano_celda + disposicion.tamano_celda // 2,
        disposicion.tablero.y + posicion.fila * disposicion.tamano_celda + disposicion.tamano_celda // 2,
    )


def test_flechas_de_algoritmo_alternan_el_control_de_la_partida(interfaz):
    control = interfaz[0]
    assert (control.modo, control.control_partida) == ("partida", CONTROL_MANUAL)

    _clic(interfaz, "algoritmo_siguiente")
    assert control.control_partida == CONTROL_ALGORITMOS
    _clic(interfaz, "algoritmo_anterior")
    assert control.control_partida == CONTROL_MANUAL
    assert control.historial_partida == ()


def test_flechas_de_unidad_y_k_eligen_el_algoritmo_de_cada_bando(interfaz):
    control = interfaz[0]
    _clic(interfaz, "algoritmo_siguiente")
    inicial = dict(control.algoritmos_bandos)
    estado = control.estado

    _clic(interfaz, "unidad_siguiente")
    assert control.algoritmos_bandos["A"] != inicial["A"]
    assert control.algoritmos_bandos["A"] in ALGORITMOS_AGENTE
    assert control.algoritmos_bandos["B"] == inicial["B"]

    _clic(interfaz, "k_mayor")
    assert control.algoritmos_bandos["B"] != inicial["B"]
    assert control.algoritmos_bandos["B"] in ALGORITMOS_AGENTE

    _clic(interfaz, "unidad_anterior")
    _clic(interfaz, "k_menor")
    assert control.algoritmos_bandos == inicial
    assert control.estado is estado
    assert control.historial_partida == ()


def test_boton_ejecutar_avanza_exactamente_una_jugada(interfaz):
    control = interfaz[0]
    _clic(interfaz, "algoritmo_siguiente")
    control.algoritmos_bandos = {"A": "ucs", "B": "ucs"}

    _clic(interfaz, "ejecutar")
    assert len(control.historial_partida) == 1
    assert control.historial_partida[0].bando == "A"
    assert control.estado.turno_actual == "B"

    _clic(interfaz, "ejecutar")
    assert len(control.historial_partida) == 2
    assert control.historial_partida[1].bando == "B"


def test_tecla_n_avanza_una_jugada_con_control_por_algoritmos(interfaz):
    control = interfaz[0]
    _clic(interfaz, "algoritmo_siguiente")
    control.algoritmos_bandos = {"A": "ucs", "B": "ucs"}
    previo = control.estado

    assert _tecla(control, pygame.K_n)
    assert len(control.historial_partida) == 1
    assert control.estado != previo
    assert not control.error


def test_tecla_n_con_control_manual_no_cambia_la_partida(interfaz):
    control = interfaz[0]
    estado = control.estado

    assert _tecla(control, pygame.K_n)
    assert control.estado is estado
    assert control.historial_partida == ()
    assert control.error


def test_tecla_n_fuera_del_modo_partida_no_llama_al_siguiente_turno(interfaz, monkeypatch):
    control = interfaz[0]
    control.cambiar_modo()
    assert control.modo != "partida"
    llamadas = []
    monkeypatch.setattr(control, "siguiente_turno", lambda: llamadas.append(True))

    assert _tecla(control, pygame.K_n)
    assert llamadas == []


def test_clic_en_el_tablero_con_control_por_algoritmos_no_mueve_unidades(interfaz):
    control, disposicion, rectangulos = interfaz
    _clic(interfaz, "algoritmo_siguiente")
    estado = control.estado

    for posicion in (Posicion(0, 1), Posicion(0, 2)):
        aplicacion._procesar_clic(control, _centro_celda(disposicion, posicion), disposicion, rectangulos)

    assert control.estado is estado
    assert control.historial_partida == ()
    assert control.unidad_partida is None
    assert control.error


def test_boton_exploracion_reinicia_la_partida_por_algoritmos(interfaz):
    control = interfaz[0]
    _clic(interfaz, "algoritmo_siguiente")
    control.algoritmos_bandos = {"A": "ucs", "B": "ucs"}
    inicial = control.estado
    _clic(interfaz, "ejecutar")
    _clic(interfaz, "ejecutar")
    assert len(control.historial_partida) == 2

    _clic(interfaz, "exploracion")
    assert control.historial_partida == ()
    assert control.estado == inicial
    assert control.control_partida == CONTROL_ALGORITMOS


def test_boton_verificar_valida_la_partida_jugada_por_algoritmos(interfaz):
    control = interfaz[0]
    _clic(interfaz, "algoritmo_siguiente")
    control.algoritmos_bandos = {"A": "ucs", "B": "ucs"}
    _clic(interfaz, "ejecutar")

    _clic(interfaz, "verificar")
    assert control.verificacion is not None and control.verificacion.es_valido


def test_control_manual_conserva_las_flechas_de_unidad(interfaz, monkeypatch):
    control = interfaz[0]
    pasos = []
    monkeypatch.setattr(control, "cambiar_unidad", pasos.append)
    algoritmos = dict(control.algoritmos_bandos)

    _clic(interfaz, "unidad_siguiente")
    _clic(interfaz, "unidad_anterior")
    assert pasos == [1, -1]
    assert control.algoritmos_bandos == algoritmos
