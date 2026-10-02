"""Datos reutilizables para probar las capas sin interfaz grafica."""

import json

import pytest


@pytest.fixture
def contenido_escenario_valido() -> dict[str, object]:
    """Devuelve un escenario pequeno valido para pruebas unitarias de arquitectura."""
    return {
        "version": "1.0",
        "mapa": {"filas": 2, "columnas": 3},
        "tipos_terreno": {
            "camino": {"costo": 2, "transitable": True},
            "muro": {"transitable": False},
        },
        "terreno": [["camino", "muro", "camino"], ["camino", "camino", "camino"]],
        "bases": {"A": {"fila": 0, "columna": 0}, "B": {"fila": 1, "columna": 2}},
        "recurso": {"fila": 1, "columna": 1},
        "unidades": [
            {"id": "A1", "bando": "A", "tipo": "estandar", "fila": 0, "columna": 0},
            {"id": "B1", "bando": "B", "tipo": "estandar", "fila": 1, "columna": 2},
        ],
        "turno": "A",
        "juego": {"portador_recurso": None, "profundidad_maxima_minimax": 4},
    }


@pytest.fixture
def ruta_escenario_valido(tmp_path, contenido_escenario_valido) -> object:
    """Escribe el JSON de prueba en una ruta temporal para ejercitar el cargador."""
    ruta = tmp_path / "escenario_valido.json"
    ruta.write_text(json.dumps(contenido_escenario_valido), encoding="utf-8")
    return ruta
