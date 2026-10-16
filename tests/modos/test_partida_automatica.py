"""Pruebas de E10.1: modo ``partida``, en el que ambos bandos juegan por turnos con alfa-beta desde el estado cargado."""

import json
from pathlib import Path

import pytest

from tacticalgrid.escenario.cargador import cargar_escenario
from tacticalgrid.escenario.escenario import Escenario, Posicion
from tacticalgrid.juego.estado import EstadoJuego, crear_estado_inicial
from tacticalgrid.juego.reglas import es_accion_valida
from tacticalgrid.juego.unidad import Unidad
from tacticalgrid.modos.partida_automatica import jugar_partida

CARPETA_ESCENARIOS = Path(__file__).resolve().parents[2] / "escenarios"


def _cargar(archivo: str):
    escenario = cargar_escenario(CARPETA_ESCENARIOS / archivo)
    return escenario, crear_estado_inicial(escenario)


@pytest.fixture
def pasillo_bloqueado(tmp_path) -> Escenario:
    """Pasillo 1x5: base A en (0, 0), A1 en (0, 1), recurso en (0, 2), muro en (0, 3) y B1 sobre su base en (0, 4).

    B1 no tiene movimientos (el muro la encierra) ni puede interceptar (nunca queda junto al portador), asi que B
    pasa el turno cada vez (regla de E1.3). Partida calculada a mano: A1 recoge el recurso, B pasa, A1 vuelve a
    (0, 1), B pasa y A1 entra en su base: gana A en 3 jugadas, con 2 pases.
    """
    contenido = {
        "version": "1.0",
        "mapa": {"filas": 1, "columnas": 5},
        "tipos_terreno": {"camino": {"costo": 1, "transitable": True}, "muro": {"transitable": False}},
        "terreno": [["camino", "camino", "camino", "muro", "camino"]],
        "bases": {"A": {"fila": 0, "columna": 0}, "B": {"fila": 0, "columna": 4}},
        "recurso": {"fila": 0, "columna": 2},
        "unidades": [
            {"id": "A1", "bando": "A", "tipo": "estandar", "fila": 0, "columna": 1},
            {"id": "B1", "bando": "B", "tipo": "estandar", "fila": 0, "columna": 4},
        ],
        "turno": "A",
        "juego": {"portador_recurso": None},
    }
    ruta = tmp_path / "pasillo_bloqueado.json"
    ruta.write_text(json.dumps(contenido), encoding="utf-8")
    return cargar_escenario(ruta)


def test_partida_calculada_a_mano_con_pases_por_bloqueo(pasillo_bloqueado) -> None:
    partida = jugar_partida(pasillo_bloqueado, crear_estado_inicial(pasillo_bloqueado), profundidad=2)

    destinos = [(turno.bando, turno.decision.accion_seleccionada.accion.destino) for turno in partida.turnos]
    assert destinos == [("A", Posicion(0, 2)), ("A", Posicion(0, 1)), ("A", Posicion(0, 0))]
    assert [turno.hubo_pase for turno in partida.turnos] == [False, True, True]
    assert partida.resultado == "victoria_A"
    assert partida.ganador == "A"
    assert partida.estado_final.portador_recurso == "A1"


@pytest.mark.parametrize(
    ("archivo", "resultado", "jugadas"),
    [("ejemplo_enunciado.json", "victoria_B", 6), ("estado_compuesto_portador.json", "victoria_A", 9)],
)
def test_partidas_que_terminan_con_un_ganador(archivo, resultado, jugadas) -> None:
    escenario, estado = _cargar(archivo)

    partida = jugar_partida(escenario, estado, profundidad=4)

    assert partida.resultado == resultado
    assert len(partida.turnos) == jugadas
    assert partida.ganador == resultado[-1]


def test_la_partida_continua_desde_el_estado_cargado(tmp_path) -> None:
    """El JSON puede empezar con B en turno: la primera jugada es de B (se continua la partida, no se reinicia)."""
    contenido = json.loads((CARPETA_ESCENARIOS / "ejemplo_enunciado.json").read_text(encoding="utf-8"))
    contenido["turno"] = "B"
    ruta = tmp_path / "turno_b.json"
    ruta.write_text(json.dumps(contenido), encoding="utf-8")
    escenario = cargar_escenario(ruta)

    partida = jugar_partida(escenario, crear_estado_inicial(escenario), profundidad=2, max_turnos=4)

    assert [turno.bando for turno in partida.turnos] == ["B", "A", "B", "A"]


def test_cada_jugada_es_legal_y_los_bandos_alternan(transporte_partida) -> None:
    escenario, partida = transporte_partida

    for turno in partida.turnos:
        assert es_accion_valida(escenario, turno.estado_previo, turno.decision.accion_seleccionada.accion)
        assert turno.estado_previo.turno_actual == turno.bando == turno.decision.bando_max
    assert [turno.bando for turno in partida.turnos] == ["A", "B", "A", "B", "A"]
    assert [turno.numero for turno in partida.turnos] == [1, 2, 3, 4, 5]


@pytest.fixture(scope="module")
def transporte_partida():
    escenario, estado = _cargar("recurso_en_transporte.json")
    return escenario, jugar_partida(escenario, estado, profundidad=3, max_turnos=5)


def test_se_detiene_al_alcanzar_el_limite_de_turnos(transporte_partida) -> None:
    _, partida = transporte_partida

    assert partida.resultado == "limite_turnos"
    assert partida.ganador is None
    assert len(partida.turnos) == partida.max_turnos == 5


def test_estado_inicial_terminal_no_juega_ningun_turno(pasillo_bloqueado) -> None:
    ganado = EstadoJuego(
        unidades=(Unidad("A1", "A", "estandar", Posicion(0, 0)), Unidad("B1", "B", "estandar", Posicion(0, 4))),
        turno_actual="B",
        posicion_recurso=None,
        portador_recurso="A1",
    )

    partida = jugar_partida(pasillo_bloqueado, ganado, profundidad=2)

    assert partida.turnos == ()
    assert partida.resultado == "victoria_A"


def test_empate_por_bloqueo_total(tmp_path) -> None:
    contenido = {
        "version": "1.0",
        "mapa": {"filas": 1, "columnas": 5},
        "tipos_terreno": {"camino": {"costo": 1, "transitable": True}, "muro": {"transitable": False}},
        "terreno": [["camino", "muro", "camino", "muro", "camino"]],
        "bases": {"A": {"fila": 0, "columna": 0}, "B": {"fila": 0, "columna": 4}},
        "recurso": {"fila": 0, "columna": 2},
        "unidades": [
            {"id": "A1", "bando": "A", "tipo": "estandar", "fila": 0, "columna": 0},
            {"id": "B1", "bando": "B", "tipo": "estandar", "fila": 0, "columna": 4},
        ],
        "turno": "A",
        "juego": {"portador_recurso": None},
    }
    ruta = tmp_path / "bloqueo_total.json"
    ruta.write_text(json.dumps(contenido), encoding="utf-8")
    escenario = cargar_escenario(ruta)

    partida = jugar_partida(escenario, crear_estado_inicial(escenario), profundidad=2)

    assert partida.turnos == ()
    assert partida.resultado == "empate_bloqueo"
    assert partida.ganador is None


def test_minimax_y_alfa_beta_juegan_la_misma_partida() -> None:
    escenario, estado = _cargar("ejemplo_enunciado.json")

    con_minimax = jugar_partida(escenario, estado, profundidad=3, algoritmo="minimax")
    con_alfa_beta = jugar_partida(escenario, estado, profundidad=3, algoritmo="alfa_beta")

    assert [t.decision.accion_seleccionada for t in con_minimax.turnos] == [
        t.decision.accion_seleccionada for t in con_alfa_beta.turnos
    ]
    assert con_minimax.resultado == con_alfa_beta.resultado


def test_la_partida_es_determinista() -> None:
    escenario, estado = _cargar("estado_compuesto_portador.json")

    primera = jugar_partida(escenario, estado, profundidad=3)
    segunda = jugar_partida(escenario, estado, profundidad=3)

    assert [t.decision.accion_seleccionada for t in primera.turnos] == [
        t.decision.accion_seleccionada for t in segunda.turnos
    ]
    assert primera.estado_final == segunda.estado_final


def test_a_diccionario_es_serializable(transporte_partida) -> None:
    _, partida = transporte_partida

    datos = partida.a_diccionario()

    assert datos["resultado"] == "limite_turnos"
    assert datos["algoritmo"] == "alfa_beta"
    assert datos["profundidad"] == 3
    assert len(datos["turnos"]) == 5
    assert {"numero", "bando", "hubo_pase", "decision"} <= set(datos["turnos"][0])
    json.dumps(datos)


@pytest.mark.parametrize(
    ("argumentos", "mensaje"),
    [
        ({"profundidad": 0}, "profundidad"),
        ({"profundidad": 2, "max_turnos": 0}, "max_turnos"),
        ({"profundidad": 2, "algoritmo": "bfs"}, "algoritmo"),
        ({"profundidad": 2, "orden": "aleatorio"}, "orden de acciones"),
    ],
)
def test_parametros_invalidos_se_rechazan(pasillo_bloqueado, argumentos, mensaje) -> None:
    with pytest.raises(ValueError, match=mensaje):
        jugar_partida(pasillo_bloqueado, crear_estado_inicial(pasillo_bloqueado), **argumentos)
