"""Pruebas de acciones validas, sucesores, condicion objetivo y costo de la partida."""

import json

import pytest

from tacticalgrid.escenario.cargador import cargar_escenario
from tacticalgrid.escenario.escenario import Escenario, Posicion
from tacticalgrid.juego.accion import Accion
from tacticalgrid.juego.estado import EstadoJuego, crear_estado_inicial
from tacticalgrid.juego.reglas import (
    acciones_validas,
    aplicar_accion,
    costo_accion,
    es_accion_valida,
    es_terminal,
    generar_sucesores,
    obtener_ganador,
)
from tacticalgrid.juego.unidad import Unidad


def _cargar(tmp_path, contenido: dict[str, object]) -> Escenario:
    ruta = tmp_path / "escenario.json"
    ruta.write_text(json.dumps(contenido), encoding="utf-8")
    return cargar_escenario(ruta)


def _estado(unidades: tuple[Unidad, ...], turno: str = "A", recurso: Posicion | None = Posicion(1, 1), portador: str | None = None) -> EstadoJuego:
    return EstadoJuego(unidades=unidades, turno_actual=turno, posicion_recurso=recurso, portador_recurso=portador)


def test_acciones_iniciales_respetan_limites_y_obstaculos(ruta_escenario_valido) -> None:
    escenario = cargar_escenario(ruta_escenario_valido)

    acciones = acciones_validas(escenario, crear_estado_inicial(escenario))

    # A1 esta en (0, 0): arriba e izquierda salen del mapa y derecha es muro.
    assert acciones == (Accion("A1", Posicion(0, 0), Posicion(1, 0)),)


def test_solo_actua_el_bando_en_turno(ruta_escenario_valido) -> None:
    escenario = cargar_escenario(ruta_escenario_valido)
    estado = crear_estado_inicial(escenario)

    sucesor = aplicar_accion(escenario, estado, Accion("A1", Posicion(0, 0), Posicion(1, 0)))

    assert sucesor.turno_actual == "B"
    assert {accion.identificador_unidad for accion in acciones_validas(escenario, sucesor)} == {"B1"}


def test_una_unidad_no_puede_entrar_en_una_celda_ocupada(ruta_escenario_valido) -> None:
    escenario = cargar_escenario(ruta_escenario_valido)
    estado = _estado(
        (
            Unidad("A1", "A", "estandar", Posicion(1, 0)),
            Unidad("B1", "B", "estandar", Posicion(1, 1)),
        ),
        recurso=Posicion(0, 2),
    )

    destinos = {accion.destino for accion in acciones_validas(escenario, estado)}

    assert destinos == {Posicion(0, 0)}
    assert not es_accion_valida(escenario, estado, Accion("A1", Posicion(1, 0), Posicion(1, 1)))


def test_aplicar_accion_invalida_lanza_error(ruta_escenario_valido) -> None:
    escenario = cargar_escenario(ruta_escenario_valido)
    estado = crear_estado_inicial(escenario)

    with pytest.raises(ValueError):
        aplicar_accion(escenario, estado, Accion("A1", Posicion(0, 0), Posicion(0, 1)))
    with pytest.raises(ValueError):
        aplicar_accion(escenario, estado, Accion("B1", Posicion(1, 2), Posicion(0, 2)))


def test_aplicar_accion_no_modifica_el_estado_original(ruta_escenario_valido) -> None:
    escenario = cargar_escenario(ruta_escenario_valido)
    estado = crear_estado_inicial(escenario)
    copia = crear_estado_inicial(escenario)

    aplicar_accion(escenario, estado, Accion("A1", Posicion(0, 0), Posicion(1, 0)))

    assert estado == copia


def test_entrar_en_la_celda_del_recurso_lo_recoge(ruta_escenario_valido) -> None:
    escenario = cargar_escenario(ruta_escenario_valido)
    estado = _estado(
        (
            Unidad("A1", "A", "estandar", Posicion(1, 0)),
            Unidad("B1", "B", "estandar", Posicion(1, 2)),
        )
    )

    sucesor = aplicar_accion(escenario, estado, Accion("A1", Posicion(1, 0), Posicion(1, 1)))

    assert sucesor.portador_recurso == "A1"
    assert sucesor.posicion_recurso is None


def test_misma_posicion_con_y_sin_recurso_son_estados_distintos(ruta_escenario_valido) -> None:
    """Caso 6 del enunciado: la posesion del recurso distingue estados con las mismas posiciones."""
    escenario = cargar_escenario(ruta_escenario_valido)
    estado = _estado(
        (
            Unidad("A1", "A", "estandar", Posicion(1, 0)),
            Unidad("B1", "B", "estandar", Posicion(1, 2)),
        )
    )
    ida = aplicar_accion(escenario, estado, Accion("A1", Posicion(1, 0), Posicion(1, 1)))
    sin_recurso = _estado(ida.unidades, turno="B", recurso=Posicion(0, 2))

    assert {unidad.posicion for unidad in ida.unidades} == {unidad.posicion for unidad in sin_recurso.unidades}
    assert ida != sin_recurso


def test_el_recurso_viaja_con_su_portador_y_gana_al_llegar_a_su_base(ruta_escenario_valido) -> None:
    escenario = cargar_escenario(ruta_escenario_valido)
    estado = _estado(
        (
            Unidad("A1", "A", "estandar", Posicion(1, 0)),
            Unidad("B1", "B", "estandar", Posicion(1, 2)),
        ),
        recurso=None,
        portador="A1",
    )

    sucesor = aplicar_accion(escenario, estado, Accion("A1", Posicion(1, 0), Posicion(0, 0)))

    assert sucesor.portador_recurso == "A1"
    assert sucesor.posicion_recurso is None
    assert obtener_ganador(escenario, sucesor) == "A"
    assert sucesor.estado_partida == "victoria_A"
    assert es_terminal(escenario, sucesor)
    assert acciones_validas(escenario, sucesor) == ()


def test_portador_en_base_rival_no_gana(ruta_escenario_valido) -> None:
    escenario = cargar_escenario(ruta_escenario_valido)
    estado = _estado(
        (
            Unidad("A1", "A", "estandar", Posicion(1, 2)),
            Unidad("B1", "B", "estandar", Posicion(0, 0)),
        ),
        recurso=None,
        portador="A1",
    )

    assert obtener_ganador(escenario, estado) is None
    assert not es_terminal(escenario, estado)


def test_bando_bloqueado_no_tiene_acciones(tmp_path, contenido_escenario_valido) -> None:
    contenido_escenario_valido["mapa"] = {"filas": 1, "columnas": 2}
    contenido_escenario_valido["terreno"] = [["camino", "camino"]]
    contenido_escenario_valido["bases"] = {"A": {"fila": 0, "columna": 0}, "B": {"fila": 0, "columna": 1}}
    contenido_escenario_valido["recurso"] = {"fila": 0, "columna": 1}
    contenido_escenario_valido["unidades"] = [
        {"id": "A1", "bando": "A", "tipo": "estandar", "fila": 0, "columna": 0},
        {"id": "B1", "bando": "B", "tipo": "estandar", "fila": 0, "columna": 1},
    ]
    escenario = _cargar(tmp_path, contenido_escenario_valido)

    assert acciones_validas(escenario, crear_estado_inicial(escenario)) == ()


def test_generar_sucesores_conserva_el_orden_de_las_acciones(ruta_escenario_valido) -> None:
    escenario = cargar_escenario(ruta_escenario_valido)
    estado = _estado(
        (
            Unidad("A1", "A", "estandar", Posicion(1, 1)),
            Unidad("B1", "B", "estandar", Posicion(0, 2)),
        ),
        recurso=Posicion(1, 2),
    )

    sucesores = generar_sucesores(escenario, estado)

    # Orden: arriba (muro, descartada), abajo (fuera), izquierda, derecha.
    assert [accion.destino for accion, _ in sucesores] == [Posicion(1, 0), Posicion(1, 2)]
    assert all(sucesor == aplicar_accion(escenario, estado, accion) for accion, sucesor in sucesores)


def test_costo_de_la_accion_es_el_del_terreno_destino_en_el_json(tmp_path, contenido_escenario_valido) -> None:
    accion = Accion("A1", Posicion(0, 0), Posicion(1, 0))
    escenario_original = _cargar(tmp_path, contenido_escenario_valido)
    contenido_escenario_valido["tipos_terreno"]["camino"]["costo"] = 15
    escenario_modificado = _cargar(tmp_path, contenido_escenario_valido)

    assert costo_accion(escenario_original, accion) == 2
    assert costo_accion(escenario_modificado, accion) == 15
