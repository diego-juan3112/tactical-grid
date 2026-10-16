"""Datos reutilizables para probar las capas sin interfaz grafica."""

import json

import pytest

from tacticalgrid.escenario.cargador import cargar_escenario


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


@pytest.fixture
def pasillo(tmp_path):
    """Pasillo 1x8 de camino con recurso en (0, 1), A1 en (0, 3) y B1 en (0, 6); arbol de alfa-beta calculado a mano.

    Solo pesa ``carrera_recurso`` (peso 1): cada hoja vale distancia(B1, recurso) - distancia(A1, recurso).
    Arbol a profundidad 2 (MAX = A; orden de acciones: izquierda antes que derecha):

    - a1: A1 -> (0, 2), distancia de A1 = 1.
        B1 -> (0, 5): 4 - 1 = 3.   B1 -> (0, 7): 6 - 1 = 5.   MIN = 3.   alfa = 3.
    - a2: A1 -> (0, 4), distancia de A1 = 3.
        B1 -> (0, 5): 4 - 3 = 1 <= alfa (3): MIN ya no puede superar 3, se poda B1 -> (0, 7).
    Minimax evalua 4 hojas y genera 7 nodos; alfa-beta evalua 3, genera 6 y poda 1 rama. Ambos eligen a1 con valor 3.
    """
    contenido = {
        "version": "1.0",
        "mapa": {"filas": 1, "columnas": 8},
        "tipos_terreno": {"camino": {"costo": 1, "transitable": True}},
        "terreno": [["camino"] * 8],
        "bases": {"A": {"fila": 0, "columna": 0}, "B": {"fila": 0, "columna": 7}},
        "recurso": {"fila": 0, "columna": 1},
        "unidades": [
            {"id": "A1", "bando": "A", "tipo": "estandar", "fila": 0, "columna": 3},
            {"id": "B1", "bando": "B", "tipo": "estandar", "fila": 0, "columna": 6},
        ],
        "turno": "A",
        "juego": {
            "portador_recurso": None,
            "profundidad_maxima_minimax": 2,
            "pesos_utilidad": {
                "posesion": 0,
                "entrega": 0,
                "carrera_recurso": 1,
                "amenaza": 0,
                "bloqueo": 0,
                "movilidad": 0,
            },
        },
    }
    ruta = tmp_path / "pasillo.json"
    ruta.write_text(json.dumps(contenido), encoding="utf-8")
    return cargar_escenario(ruta)
