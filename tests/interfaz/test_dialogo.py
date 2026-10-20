"""Pruebas del selector de archivos que abre un escenario JSON desde la interfaz."""

import sys
from pathlib import Path

import pytest

from tacticalgrid.interfaz import dialogo
from tacticalgrid.interfaz.dialogo import DialogoNoDisponible, pedir_ruta_escenario


class _RaizFalsa:
    def __init__(self):
        self.destruida = False

    def withdraw(self):
        pass

    def attributes(self, *argumentos):
        pass

    def destroy(self):
        self.destruida = True


def test_sin_tkinter_informa_que_el_dialogo_no_esta_disponible(monkeypatch):
    monkeypatch.setitem(sys.modules, "tkinter", None)

    with pytest.raises(DialogoNoDisponible):
        pedir_ruta_escenario(Path.cwd())


def test_devuelve_la_ruta_elegida_y_cierra_la_raiz(monkeypatch, tmp_path):
    tkinter = pytest.importorskip("tkinter")
    from tkinter import filedialog

    raices = []
    opciones_recibidas = {}

    def crear_raiz():
        raices.append(_RaizFalsa())
        return raices[-1]

    def pedir(**opciones):
        opciones_recibidas.update(opciones)
        return str(tmp_path / "mapa.json")

    monkeypatch.setattr(tkinter, "Tk", crear_raiz)
    monkeypatch.setattr(filedialog, "askopenfilename", pedir)

    assert pedir_ruta_escenario(tmp_path) == tmp_path / "mapa.json"
    assert raices[0].destruida
    assert opciones_recibidas["initialdir"] == str(tmp_path)
    assert ("Escenario JSON", "*.json") in opciones_recibidas["filetypes"]


def test_cancelar_devuelve_none(monkeypatch, tmp_path):
    tkinter = pytest.importorskip("tkinter")
    from tkinter import filedialog

    monkeypatch.setattr(tkinter, "Tk", _RaizFalsa)
    monkeypatch.setattr(filedialog, "askopenfilename", lambda **opciones: "")

    assert pedir_ruta_escenario(tmp_path) is None


def test_sin_pantalla_informa_que_el_dialogo_no_esta_disponible(monkeypatch, tmp_path):
    tkinter = pytest.importorskip("tkinter")

    def sin_pantalla():
        raise tkinter.TclError("no display name")

    monkeypatch.setattr(tkinter, "Tk", sin_pantalla)

    with pytest.raises(DialogoNoDisponible):
        pedir_ruta_escenario(tmp_path)


def test_el_modulo_no_importa_tkinter_al_cargarse():
    assert "tkinter" not in vars(dialogo)
