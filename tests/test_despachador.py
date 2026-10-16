"""Pruebas del punto de entrada limpio y la compatibilidad de consola."""

import importlib.util
from pathlib import Path

import pygame
import pytest

from tacticalgrid import despachador


RAIZ = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize(
    ("argumentos", "destino", "restantes"),
    [
        ([], "gui", ()),
        (["--gui"], "gui", ()),
        (["--gui", "escenarios/campo_20x20.json"], "gui", ("escenarios/campo_20x20.json",)),
        (["--consola", "escenarios/campo_20x20.json"], "consola", ("escenarios/campo_20x20.json",)),
        (
            ["escenarios/campo_20x20.json", "--algoritmo", "ucs"],
            "consola",
            ("escenarios/campo_20x20.json", "--algoritmo", "ucs"),
        ),
    ],
)
def test_despacha_gui_predeterminada_y_consola_historica(monkeypatch, argumentos, destino, restantes):
    llamadas = []
    monkeypatch.setattr(despachador, "_ejecutar_gui", lambda args: llamadas.append(("gui", tuple(args))) or 7)
    monkeypatch.setattr(despachador, "_ejecutar_consola", lambda args: llamadas.append(("consola", tuple(args))) or 9)

    codigo = despachador.ejecutar(argumentos)

    assert llamadas == [(destino, restantes)]
    assert codigo == (7 if destino == "gui" else 9)


def test_importar_main_no_inicializa_pygame_ni_ejecuta_aplicacion():
    pygame.quit()
    especificacion = importlib.util.spec_from_file_location("main_tacticalgrid_prueba", RAIZ / "main.py")
    modulo = importlib.util.module_from_spec(especificacion)

    especificacion.loader.exec_module(modulo)

    assert not pygame.get_init()
    assert callable(modulo.ejecutar)
