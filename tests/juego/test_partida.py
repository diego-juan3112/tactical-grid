"""Pruebas de orquestacion paso a paso del dominio de juego (E3.1)."""

import json
from dataclasses import replace

import pytest

from tacticalgrid.escenario.cargador import cargar_escenario
from tacticalgrid.escenario.escenario import Posicion
from tacticalgrid.juego.accion import Accion
from tacticalgrid.juego.estado import crear_estado_inicial
from tacticalgrid.juego.partida import acciones_para_unidad, preparar_turno, unidades_seleccionables
from tacticalgrid.juego.reglas import aplicar_accion, es_terminal


def _cargar(tmp_path, contenido: dict[str, object]):
    ruta = tmp_path / "escenario.json"
    ruta.write_text(json.dumps(contenido), encoding="utf-8")
    return cargar_escenario(ruta)


def _escenario_bloqueo_individual(tmp_path, contenido_escenario_valido):
    contenido = dict(contenido_escenario_valido)
    contenido["mapa"] = {"filas": 3, "columnas": 3}
    contenido["terreno"] = [
        ["camino", "muro", "camino"],
        ["camino", "camino", "camino"],
        ["camino", "camino", "camino"],
    ]
    contenido["bases"] = {"A": {"fila": 0, "columna": 0}, "B": {"fila": 2, "columna": 2}}
    contenido["recurso"] = {"fila": 1, "columna": 1}
    contenido["unidades"] = [
        {"id": "A1", "bando": "A", "tipo": "estandar", "fila": 0, "columna": 0},
        {"id": "A2", "bando": "A", "tipo": "estandar", "fila": 1, "columna": 0},
        {"id": "B1", "bando": "B", "tipo": "estandar", "fila": 2, "columna": 2},
    ]
    return _cargar(tmp_path, contenido)


@pytest.mark.parametrize(("turno", "esperada"), [("A", "A1"), ("B", "B1")])
def test_solo_unidades_del_bando_activo_son_seleccionables(
    ruta_escenario_valido, turno, esperada
) -> None:
    escenario = cargar_escenario(ruta_escenario_valido)
    estado = crear_estado_inicial(escenario)
    estado = replace(estado, turno_actual=turno)

    assert tuple(unidad.identificador for unidad in unidades_seleccionables(escenario, estado)) == (esperada,)


def test_unidad_bloqueada_no_es_seleccionable_pero_consulta_cero_acciones(
    tmp_path, contenido_escenario_valido
) -> None:
    escenario = _escenario_bloqueo_individual(tmp_path, contenido_escenario_valido)
    estado = crear_estado_inicial(escenario)

    assert tuple(unidad.identificador for unidad in unidades_seleccionables(escenario, estado)) == ("A2",)
    assert acciones_para_unidad(escenario, estado, "A1") == ()
    assert estado.turno_actual == "A"


@pytest.mark.parametrize("identificador", ["B1", "NO_EXISTE"])
def test_acciones_para_unidad_rechaza_unidad_adversaria_o_inexistente(
    ruta_escenario_valido, identificador
) -> None:
    escenario = cargar_escenario(ruta_escenario_valido)
    estado = crear_estado_inicial(escenario)

    with pytest.raises(ValueError):
        acciones_para_unidad(escenario, estado, identificador)


def test_acciones_para_unidad_filtra_y_conserva_orden_de_e1_2(ruta_escenario_valido) -> None:
    escenario = cargar_escenario(ruta_escenario_valido)
    estado = crear_estado_inicial(escenario)

    acciones = acciones_para_unidad(escenario, estado, "A1")

    assert acciones == (Accion("A1", Posicion(0, 0), Posicion(1, 0)),)
    assert all(accion.identificador_unidad == "A1" for accion in acciones)


def test_accion_valida_cambia_turno_una_vez_y_conserva_estado_original(ruta_escenario_valido) -> None:
    escenario = cargar_escenario(ruta_escenario_valido)
    original = crear_estado_inicial(escenario)
    preparado = preparar_turno(escenario, original)
    unidad = unidades_seleccionables(escenario, preparado)[0]
    accion = acciones_para_unidad(escenario, preparado, unidad.identificador)[0]

    sucesor = aplicar_accion(escenario, preparado, accion)

    assert sucesor.turno_actual == "B"
    assert sucesor != original
    assert original == crear_estado_inicial(escenario)
    assert hash(original) == hash(crear_estado_inicial(escenario))


def test_accion_invalida_no_modifica_estado_ni_turno(ruta_escenario_valido) -> None:
    escenario = cargar_escenario(ruta_escenario_valido)
    estado = crear_estado_inicial(escenario)
    accion = Accion("A1", Posicion(0, 0), Posicion(0, 1))

    with pytest.raises(ValueError):
        aplicar_accion(escenario, estado, accion)

    assert estado.turno_actual == "A"
    assert estado == crear_estado_inicial(escenario)


def test_integracion_paso_a_paso_alterna_a_b_a_sin_reconstruir_estado(ruta_escenario_valido) -> None:
    escenario = cargar_escenario(ruta_escenario_valido)
    estado = crear_estado_inicial(escenario)

    estado = preparar_turno(escenario, estado)
    unidad_a = unidades_seleccionables(escenario, estado)[0]
    accion_a = acciones_para_unidad(escenario, estado, unidad_a.identificador)[0]
    estado = aplicar_accion(escenario, estado, accion_a)
    assert estado.turno_actual == "B"

    estado = preparar_turno(escenario, estado)
    unidad_b = unidades_seleccionables(escenario, estado)[0]
    accion_b = acciones_para_unidad(escenario, estado, unidad_b.identificador)[0]
    estado = aplicar_accion(escenario, estado, accion_b)

    assert estado.turno_actual == "A"


def test_bloqueo_individual_no_pasa_el_turno(tmp_path, contenido_escenario_valido) -> None:
    escenario = _escenario_bloqueo_individual(tmp_path, contenido_escenario_valido)
    estado = crear_estado_inicial(escenario)

    preparado = preparar_turno(escenario, estado)

    assert preparado == estado
    assert tuple(unidad.identificador for unidad in unidades_seleccionables(escenario, preparado)) == ("A2",)


def test_bloqueo_de_bando_pasa_una_vez_y_b_puede_actuar(tmp_path, contenido_escenario_valido) -> None:
    contenido = dict(contenido_escenario_valido)
    contenido["mapa"] = {"filas": 2, "columnas": 3}
    contenido["terreno"] = [["camino", "muro", "muro"], ["camino", "camino", "camino"]]
    contenido["unidades"] = [
        {"id": "A1", "bando": "A", "tipo": "estandar", "fila": 0, "columna": 0},
        {"id": "A2", "bando": "A", "tipo": "estandar", "fila": 1, "columna": 0},
        {"id": "B1", "bando": "B", "tipo": "estandar", "fila": 1, "columna": 1},
    ]
    escenario = _cargar(tmp_path, contenido)
    estado = crear_estado_inicial(escenario)

    preparado = preparar_turno(escenario, estado)

    assert preparado.turno_actual == "B"
    assert tuple(unidad.identificador for unidad in unidades_seleccionables(escenario, preparado)) == ("B1",)
    accion = acciones_para_unidad(escenario, preparado, "B1")[0]
    assert aplicar_accion(escenario, preparado, accion).turno_actual == "A"


def test_bloqueo_total_termina_en_empate_sin_unidades_ni_acciones(tmp_path, contenido_escenario_valido) -> None:
    contenido = dict(contenido_escenario_valido)
    contenido["mapa"] = {"filas": 2, "columnas": 2}
    contenido["terreno"] = [["camino", "camino"], ["camino", "camino"]]
    contenido["bases"] = {"A": {"fila": 0, "columna": 0}, "B": {"fila": 1, "columna": 1}}
    contenido["recurso"] = {"fila": 1, "columna": 0}
    contenido["unidades"] = [
        {"id": "A1", "bando": "A", "tipo": "estandar", "fila": 0, "columna": 0},
        {"id": "A2", "bando": "A", "tipo": "estandar", "fila": 1, "columna": 0},
        {"id": "B1", "bando": "B", "tipo": "estandar", "fila": 0, "columna": 1},
        {"id": "B2", "bando": "B", "tipo": "estandar", "fila": 1, "columna": 1},
    ]
    escenario = _cargar(tmp_path, contenido)
    estado = crear_estado_inicial(escenario)

    empate = preparar_turno(escenario, estado)

    assert empate.estado_partida == "empate_bloqueo"
    assert es_terminal(escenario, empate)
    assert unidades_seleccionables(escenario, empate) == ()
    assert preparar_turno(escenario, empate) is empate
    with pytest.raises(ValueError):
        acciones_para_unidad(escenario, empate, "A1")


@pytest.mark.parametrize("ganador", ["A", "B"])
def test_victoria_terminal_no_pasa_turno_ni_ofrece_unidades(ruta_escenario_valido, ganador) -> None:
    escenario = cargar_escenario(ruta_escenario_valido)
    estado = crear_estado_inicial(escenario)
    identificador = "A1" if ganador == "A" else "B1"
    terminal = replace(estado, portador_recurso=identificador, posicion_recurso=None)

    assert preparar_turno(escenario, terminal) is terminal
    assert unidades_seleccionables(escenario, terminal) == ()
    with pytest.raises(ValueError):
        acciones_para_unidad(escenario, terminal, identificador)


def test_reglas_son_simetricas_al_intercambiar_bandos(tmp_path, contenido_escenario_valido) -> None:
    contenido = dict(contenido_escenario_valido)
    contenido["mapa"] = {"filas": 3, "columnas": 3}
    contenido["terreno"] = [["camino"] * 3 for _ in range(3)]
    contenido["bases"] = {"A": {"fila": 0, "columna": 0}, "B": {"fila": 2, "columna": 2}}
    contenido["recurso"] = {"fila": 0, "columna": 2}
    contenido["unidades"] = [
        {"id": "A1", "bando": "A", "tipo": "estandar", "fila": 1, "columna": 0},
        {"id": "B1", "bando": "B", "tipo": "estandar", "fila": 1, "columna": 2},
    ]
    escenario = _cargar(tmp_path, contenido)
    estado_a = crear_estado_inicial(escenario)
    estado_b = replace(estado_a, turno_actual="B")

    acciones_a = acciones_para_unidad(escenario, estado_a, "A1")
    acciones_b = acciones_para_unidad(escenario, estado_b, "B1")
    sucesor_a = aplicar_accion(escenario, estado_a, acciones_a[0])
    sucesor_b = aplicar_accion(escenario, estado_b, acciones_b[0])

    assert len(acciones_a) == len(acciones_b) == 3
    assert sucesor_a.turno_actual == "B"
    assert sucesor_b.turno_actual == "A"


def test_consultas_y_preparacion_son_deterministas_y_no_mutan_estado(ruta_escenario_valido) -> None:
    escenario = cargar_escenario(ruta_escenario_valido)
    estado = crear_estado_inicial(escenario)
    hash_original = hash(estado)

    assert unidades_seleccionables(escenario, estado) == unidades_seleccionables(escenario, estado)
    assert acciones_para_unidad(escenario, estado, "A1") == acciones_para_unidad(escenario, estado, "A1")
    assert preparar_turno(escenario, estado) == preparar_turno(escenario, estado)
    assert hash(estado) == hash_original
    assert estado in {estado}
