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
    resolver_bloqueo_turno,
    resolver_intercepcion,
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


def _escenario_con_unidades(tmp_path, contenido, unidades):
    contenido["unidades"] = unidades
    return _cargar(tmp_path, contenido)


def test_unidad_bloqueada_no_impide_acciones_de_su_bando(tmp_path, contenido_escenario_valido) -> None:
    escenario = _escenario_con_unidades(
        tmp_path,
        contenido_escenario_valido,
        [
            {"id": "A1", "bando": "A", "tipo": "estandar", "fila": 0, "columna": 0},
            {"id": "A2", "bando": "A", "tipo": "estandar", "fila": 1, "columna": 0},
            {"id": "B1", "bando": "B", "tipo": "estandar", "fila": 1, "columna": 2},
        ],
    )
    estado = crear_estado_inicial(escenario)

    acciones = acciones_validas(escenario, estado)

    assert acciones == (Accion("A2", Posicion(1, 0), Posicion(1, 1)),)
    assert estado.turno_actual == "A"
    with pytest.raises(ValueError):
        aplicar_accion(escenario, estado, Accion("A1", Posicion(0, 0), Posicion(0, 1)))
    assert estado.turno_actual == "A"
    assert estado == crear_estado_inicial(escenario)


def _estado_bloqueado(unidades, turno="A"):
    return EstadoJuego(
        unidades=tuple(unidades),
        turno_actual=turno,
        posicion_recurso=Posicion(0, 2),
        portador_recurso=None,
    )


def _unidades_bloqueo_total(incluir_b2=False):
    unidades = [
        Unidad("A1", "A", "estandar", Posicion(0, 0)),
        Unidad("A2", "A", "estandar", Posicion(1, 0)),
        Unidad("A3", "A", "estandar", Posicion(1, 1)),
        Unidad("B1", "B", "estandar", Posicion(1, 2)),
    ]
    if incluir_b2:
        unidades.append(Unidad("B2", "B", "estandar", Posicion(0, 2)))
    return tuple(unidades)


def test_bloqueo_de_bando_pasa_turno_al_adversario_que_puede_actuar(tmp_path, contenido_escenario_valido) -> None:
    escenario = _cargar(tmp_path, contenido_escenario_valido)
    estado = _estado_bloqueado(_unidades_bloqueo_total())

    assert acciones_validas(escenario, estado) == ()
    resultado = resolver_bloqueo_turno(escenario, estado)

    assert resultado == EstadoJuego(estado.unidades, "B", estado.posicion_recurso, None, estado.estado_partida)
    assert estado.turno_actual == "A"
    assert acciones_validas(escenario, resultado)


def test_bloqueo_total_termina_en_empate_sin_pases_repetidos(tmp_path, contenido_escenario_valido) -> None:
    escenario = _cargar(tmp_path, contenido_escenario_valido)
    estado = _estado_bloqueado(_unidades_bloqueo_total(incluir_b2=True))

    assert acciones_validas(escenario, estado) == ()
    resultado = resolver_bloqueo_turno(escenario, estado)

    assert resultado.estado_partida == "empate_bloqueo"
    assert resolver_bloqueo_turno(escenario, resultado) == resultado
    assert es_terminal(escenario, resultado)
    assert acciones_validas(escenario, resultado) == ()
    assert resultado in {resultado}


def test_intercepcion_transfiere_el_recurso_sin_cambiar_turno_ni_eliminar_unidades(ruta_escenario_valido) -> None:
    escenario = cargar_escenario(ruta_escenario_valido)
    estado = EstadoJuego(
        unidades=(
            Unidad("A1", "A", "estandar", Posicion(1, 0)),
            Unidad("B1", "B", "estandar", Posicion(0, 2)),
        ),
        turno_actual="A",
        posicion_recurso=None,
        portador_recurso="A1",
    )

    resultado = resolver_intercepcion(escenario, estado, "B1")

    assert resultado.portador_recurso == "B1"
    assert resultado.posicion_recurso is None
    assert {unidad.identificador for unidad in resultado.unidades} == {"A1", "B1"}
    assert resultado.turno_actual == estado.turno_actual
    assert estado.portador_recurso == "A1"
    assert resultado.estado_partida == "en_curso"
    assert not es_terminal(escenario, resultado)
    assert hash(resultado)
    assert resultado in {resultado}


def test_intercepcion_en_base_registra_victoria_del_nuevo_portador(ruta_escenario_valido) -> None:
    escenario = cargar_escenario(ruta_escenario_valido)
    estado = EstadoJuego(
        unidades=(
            Unidad("A1", "A", "estandar", Posicion(1, 0)),
            Unidad("B1", "B", "estandar", escenario.bases["B"]),
        ),
        turno_actual="A",
        posicion_recurso=None,
        portador_recurso="A1",
    )
    unidades_antes = estado.unidades

    resultado = resolver_intercepcion(escenario, estado, "B1")

    assert resultado.portador_recurso == "B1"
    assert resultado.posicion_recurso is None
    assert resultado.estado_partida == "victoria_B"
    assert obtener_ganador(escenario, resultado) == "B"
    assert es_terminal(escenario, resultado) is True
    assert resultado.turno_actual == estado.turno_actual
    assert resultado.unidades == unidades_antes
    assert estado.portador_recurso == "A1"
    assert estado.estado_partida == "en_curso"


@pytest.mark.parametrize("interceptor", ["Z9", "A1", "A2"])
def test_intercepcion_rechaza_interceptores_invalidos(ruta_escenario_valido, interceptor) -> None:
    escenario = cargar_escenario(ruta_escenario_valido)
    estado = EstadoJuego(
        unidades=(
            Unidad("A1", "A", "estandar", Posicion(1, 0)),
            Unidad("A2", "A", "estandar", Posicion(1, 1)),
            Unidad("B1", "B", "estandar", Posicion(1, 2)),
        ),
        turno_actual="A",
        posicion_recurso=None,
        portador_recurso="A1",
    )

    with pytest.raises(ValueError):
        resolver_intercepcion(escenario, estado, interceptor)
    assert estado.portador_recurso == "A1"


def test_reglas_de_borde_son_deterministas_y_resultados_hashables(tmp_path, contenido_escenario_valido) -> None:
    escenario = _cargar(tmp_path, contenido_escenario_valido)
    estado = _estado_bloqueado(_unidades_bloqueo_total())

    resultado_1 = resolver_bloqueo_turno(escenario, estado)
    resultado_2 = resolver_bloqueo_turno(escenario, EstadoJuego(
        tuple(reversed(estado.unidades)), estado.turno_actual, estado.posicion_recurso, estado.portador_recurso
    ))

    assert resultado_1 == resultado_2
    assert len({resultado_1, resultado_2}) == 1


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
