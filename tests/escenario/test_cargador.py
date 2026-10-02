"""Pruebas de carga y consultas de la capa de escenario."""

import json
from pathlib import Path

import pytest

from tacticalgrid.escenario.cargador import cargar_escenario
from tacticalgrid.escenario.escenario import Posicion
from tacticalgrid.escenario.validador import ErrorValidacionEscenario

CARPETA_ESCENARIOS = Path(__file__).resolve().parents[2] / "escenarios"


def test_carga_escenario_valido_y_consulta_propiedades(ruta_escenario_valido) -> None:
    escenario = cargar_escenario(ruta_escenario_valido)

    assert escenario.filas == 2
    assert escenario.contiene_posicion(Posicion(1, 2))
    assert not escenario.contiene_posicion(Posicion(2, 0))
    assert not escenario.es_transitable(Posicion(0, 1))
    assert escenario.obtener_costo(Posicion(1, 0)) == 2


def test_carga_escenario_expone_version_del_formato(ruta_escenario_valido) -> None:
    escenario = cargar_escenario(ruta_escenario_valido)

    assert escenario.version == "1.0"


def test_carga_escenario_con_dimensiones_distintas_de_20x20(tmp_path) -> None:
    """Evidencia del criterio de aceptacion: el cargador no asume 20x20 fijo."""
    contenido = {
        "version": "1.0",
        "mapa": {"filas": 7, "columnas": 4},
        "tipos_terreno": {"camino": {"costo": 1, "transitable": True}},
        "terreno": [["camino"] * 4 for _ in range(7)],
        "bases": {"A": {"fila": 0, "columna": 0}, "B": {"fila": 6, "columna": 3}},
        "recurso": {"fila": 3, "columna": 2},
        "unidades": [
            {"id": "A1", "bando": "A", "tipo": "estandar", "fila": 0, "columna": 0},
            {"id": "B1", "bando": "B", "tipo": "estandar", "fila": 6, "columna": 3},
        ],
        "turno": "A",
        "juego": {"portador_recurso": None},
    }
    ruta = tmp_path / "escenario_7x4.json"
    ruta.write_text(json.dumps(contenido), encoding="utf-8")

    escenario = cargar_escenario(ruta)

    assert (escenario.filas, escenario.columnas) == (7, 4)
    assert escenario.contiene_posicion(Posicion(6, 3))
    assert not escenario.contiene_posicion(Posicion(7, 0))


def test_carga_escenario_tolera_campos_adicionales_propios(tmp_path, contenido_escenario_valido) -> None:
    """Evidencia del criterio de aceptacion: campos propios no alteran el significado de los obligatorios."""
    contenido = dict(contenido_escenario_valido)
    contenido["autor"] = "equipo-tacticalgrid"
    contenido["tipos_terreno"] = {
        nombre: dict(datos, color="verde") for nombre, datos in contenido["tipos_terreno"].items()
    }
    contenido["unidades"] = [dict(unidad, vida=10) for unidad in contenido["unidades"]]
    contenido["juego"] = dict(contenido["juego"], profundidad_maxima_minimax=6)

    ruta = tmp_path / "escenario_con_extras.json"
    ruta.write_text(json.dumps(contenido), encoding="utf-8")

    escenario = cargar_escenario(ruta)

    assert escenario.version == "1.0"
    assert escenario.filas == 2
    assert escenario.configuracion_juego["profundidad_maxima_minimax"] == 6


def test_carga_ejemplo_del_enunciado_con_todos_los_campos_obligatorios() -> None:
    escenario = cargar_escenario(CARPETA_ESCENARIOS / "ejemplo_enunciado.json")

    assert escenario.version == "1.0"
    assert (escenario.filas, escenario.columnas) == (4, 4)
    assert escenario.obtener_costo(Posicion(2, 2)) == 7
    assert not escenario.es_transitable(Posicion(1, 1))
    assert escenario.bases == {"A": Posicion(0, 0), "B": Posicion(3, 3)}
    assert escenario.recurso == Posicion(2, 2)
    assert [unidad.identificador for unidad in escenario.unidades_iniciales] == ["A1", "A2", "B1", "B2"]
    assert escenario.turno_inicial == "A"
    assert escenario.portador_recurso_inicial is None
    assert escenario.configuracion_prueba == {
        "modo": "busqueda",
        "unidad_inicio": "A1",
        "objetivo": {"fila": 3, "columna": 2},
    }


def test_carga_escenario_de_desarrollo_20x20_del_repositorio() -> None:
    escenario = cargar_escenario(CARPETA_ESCENARIOS / "arquitectura_basica.json")

    assert (escenario.filas, escenario.columnas) == (20, 20)


@pytest.mark.parametrize("prueba", [None, "ausente"])
def test_escenario_sin_prueba_expone_configuracion_prueba_nula(tmp_path, contenido_escenario_valido, prueba) -> None:
    contenido = dict(contenido_escenario_valido)
    if prueba != "ausente":
        contenido["prueba"] = prueba
    ruta = tmp_path / "sin_prueba.json"
    ruta.write_text(json.dumps(contenido), encoding="utf-8")

    assert cargar_escenario(ruta).configuracion_prueba is None


def test_carga_escenario_guardado_en_utf8_con_bom(tmp_path, contenido_escenario_valido) -> None:
    ruta = tmp_path / "con_bom.json"
    ruta.write_text(json.dumps(contenido_escenario_valido), encoding="utf-8-sig")

    assert cargar_escenario(ruta).version == "1.0"


def test_rechaza_con_error_claro_un_archivo_que_no_esta_en_utf8(tmp_path, contenido_escenario_valido) -> None:
    contenido = dict(contenido_escenario_valido, autor="Equipo Montaña")
    ruta = tmp_path / "latin1.json"
    ruta.write_bytes(json.dumps(contenido, ensure_ascii=False).encode("latin-1"))

    with pytest.raises(ErrorValidacionEscenario, match="UTF-8"):
        cargar_escenario(ruta)


@pytest.mark.parametrize("constante", ["NaN", "Infinity", "-Infinity"])
def test_rechaza_constantes_numericas_que_no_son_json_estandar(
    tmp_path, contenido_escenario_valido, constante
) -> None:
    texto = json.dumps(contenido_escenario_valido).replace('"costo": 2', f'"costo": {constante}')
    ruta = tmp_path / "constante_no_estandar.json"
    ruta.write_text(texto, encoding="utf-8")

    with pytest.raises(ErrorValidacionEscenario, match=constante):
        cargar_escenario(ruta)


def test_rechaza_prueba_que_no_es_un_objeto(tmp_path, contenido_escenario_valido) -> None:
    contenido = dict(contenido_escenario_valido, prueba="busqueda")
    ruta = tmp_path / "prueba_invalida.json"
    ruta.write_text(json.dumps(contenido), encoding="utf-8")

    with pytest.raises(ErrorValidacionEscenario, match="prueba"):
        cargar_escenario(ruta)
