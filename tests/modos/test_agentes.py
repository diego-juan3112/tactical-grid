"""Pruebas de la partida por turnos entre algoritmos: una jugada por bando decidida por su algoritmo."""

import json
from pathlib import Path

import pytest

from tacticalgrid.algoritmos.alfa_beta import alfa_beta
from tacticalgrid.algoritmos.minimax import minimax
from tacticalgrid.escenario.cargador import cargar_escenario
from tacticalgrid.escenario.escenario import Posicion
from tacticalgrid.juego.accion import INTERCEPTAR, Accion
from tacticalgrid.juego.estado import EstadoJuego, crear_estado_inicial
from tacticalgrid.juego.partida import preparar_turno
from tacticalgrid.juego.problema import ProblemaNavegacionPartida
from tacticalgrid.juego.reglas import aplicar_accion, es_accion_valida, es_terminal
from tacticalgrid.juego.unidad import Unidad
from tacticalgrid.modos.agentes import ALGORITMOS_AGENTE, ConfiguracionAgente, decidir_jugada

CARPETA_ESCENARIOS = Path(__file__).resolve().parents[2] / "escenarios"
ALGORITMOS_BUSQUEDA = ("bfs", "dfs", "ucs", "astar", "beam")


def _escenario(tmp_path, terreno, unidades, recurso, bases=None, nombre="mapa.json"):
    contenido = {
        "version": "1.0",
        "mapa": {"filas": len(terreno), "columnas": len(terreno[0])},
        "tipos_terreno": {"camino": {"costo": 1, "transitable": True}, "muro": {"transitable": False}},
        "terreno": terreno,
        "bases": bases or {"A": {"fila": 0, "columna": 0}, "B": {"fila": 0, "columna": len(terreno[0]) - 1}},
        "recurso": {"fila": recurso[0], "columna": recurso[1]},
        "unidades": [
            {"id": ident, "bando": ident[0], "tipo": "estandar", "fila": fila, "columna": columna}
            for ident, fila, columna in unidades
        ],
        "turno": "A",
        "juego": {"portador_recurso": None},
    }
    ruta = tmp_path / nombre
    ruta.write_text(json.dumps(contenido), encoding="utf-8")
    return cargar_escenario(ruta)


def _con_portador(estado: EstadoJuego, portador: str, turno: str = "A") -> EstadoJuego:
    from dataclasses import replace

    return replace(estado, portador_recurso=portador, posicion_recurso=None, turno_actual=turno)


# --- Problema de navegación dentro de la partida ----------------------------------------------------------------------


def test_problema_de_partida_trata_como_obstaculo_las_celdas_ocupadas(tmp_path) -> None:
    escenario = _escenario(tmp_path, [["camino"] * 4] * 2, [("A1", 0, 1), ("B1", 0, 2)], (1, 3))
    estado = crear_estado_inicial(escenario)

    problema = ProblemaNavegacionPartida(escenario, "A1", Posicion(1, 3), estado)

    assert Posicion(0, 2) not in [accion.destino for accion in problema.acciones(estado)]
    assert {accion.destino for accion in problema.acciones(estado)} == {Posicion(0, 0), Posicion(1, 1)}


def test_problema_de_partida_admite_entrar_en_el_objetivo_aunque_este_ocupado(tmp_path) -> None:
    escenario = _escenario(tmp_path, [["camino"] * 4], [("A1", 0, 1), ("B1", 0, 2)], (0, 3))
    estado = crear_estado_inicial(escenario)

    problema = ProblemaNavegacionPartida(escenario, "A1", Posicion(0, 2), estado)

    assert Posicion(0, 2) in [accion.destino for accion in problema.acciones(estado)]


# --- Decisión de los algoritmos de búsqueda ---------------------------------------------------------------------------


@pytest.mark.parametrize("algoritmo", ALGORITMOS_BUSQUEDA)
def test_busqueda_avanza_un_paso_hacia_el_recurso_libre(tmp_path, algoritmo) -> None:
    escenario = _escenario(tmp_path, [["camino"] * 6], [("A1", 0, 1), ("B1", 0, 5)], (0, 3))
    estado = crear_estado_inicial(escenario)

    decision = decidir_jugada(escenario, estado, ConfiguracionAgente(algoritmo))

    assert decision.accion == Accion("A1", Posicion(0, 1), Posicion(0, 2))
    assert (decision.bando, decision.meta, decision.objetivo) == ("A", "recurso", Posicion(0, 3))
    assert decision.busqueda is not None and decision.busqueda.exito
    assert decision.busqueda.camino[0] == Posicion(0, 1) and decision.busqueda.camino[-1] == Posicion(0, 3)
    assert decision.adversarial is None


def test_con_recurso_libre_actua_la_unidad_de_menor_costo(tmp_path) -> None:
    escenario = _escenario(
        tmp_path, [["camino"] * 7, ["camino"] * 7], [("A1", 0, 0), ("A2", 1, 4), ("B1", 0, 6)], (0, 4)
    )

    decision = decidir_jugada(escenario, crear_estado_inicial(escenario), ConfiguracionAgente("ucs"))

    assert decision.accion == Accion("A2", Posicion(1, 4), Posicion(0, 4))


def test_el_portador_planea_hacia_su_propia_base(tmp_path) -> None:
    escenario = _escenario(tmp_path, [["camino"] * 6], [("A1", 0, 3), ("B1", 0, 5)], (0, 3))
    estado = _con_portador(crear_estado_inicial(escenario), "A1")

    decision = decidir_jugada(escenario, estado, ConfiguracionAgente("astar"))

    assert (decision.meta, decision.objetivo) == ("base", Posicion(0, 0))
    assert decision.accion == Accion("A1", Posicion(0, 3), Posicion(0, 2))


def test_junto_al_portador_rival_la_busqueda_intercepta(tmp_path) -> None:
    escenario = _escenario(tmp_path, [["camino"] * 6], [("A1", 0, 2), ("B1", 0, 3)], (0, 3))
    estado = _con_portador(crear_estado_inicial(escenario), "B1")

    decision = decidir_jugada(escenario, estado, ConfiguracionAgente("bfs"))

    assert decision.meta == "interceptar"
    assert decision.accion == Accion("A1", Posicion(0, 2), Posicion(0, 3), INTERCEPTAR)
    assert decision.busqueda is None


def test_lejos_del_portador_rival_la_busqueda_lo_persigue(tmp_path) -> None:
    escenario = _escenario(tmp_path, [["camino"] * 7], [("A1", 0, 1), ("B1", 0, 5)], (0, 5))
    estado = _con_portador(crear_estado_inicial(escenario), "B1")

    decision = decidir_jugada(escenario, estado, ConfiguracionAgente("dfs"))

    assert (decision.meta, decision.objetivo) == ("portador", Posicion(0, 5))
    assert decision.accion == Accion("A1", Posicion(0, 1), Posicion(0, 2))


def test_sin_camino_disponible_se_usa_la_primera_accion_legal(tmp_path) -> None:
    escenario = _escenario(tmp_path, [["camino"] * 5], [("A1", 0, 1), ("B1", 0, 2)], (0, 4))

    decision = decidir_jugada(escenario, crear_estado_inicial(escenario), ConfiguracionAgente("ucs"))

    assert decision.meta == "respaldo"
    assert decision.accion == Accion("A1", Posicion(0, 1), Posicion(0, 0))


# --- Decisión adversarial ---------------------------------------------------------------------------------------------


@pytest.mark.parametrize(("algoritmo", "funcion"), [("minimax", minimax), ("alfa_beta", alfa_beta)])
def test_minimax_y_alfa_beta_eligen_la_accion_de_su_algoritmo(algoritmo, funcion) -> None:
    escenario = cargar_escenario(CARPETA_ESCENARIOS / "ejemplo_enunciado.json")
    estado = preparar_turno(escenario, crear_estado_inicial(escenario))

    decision = decidir_jugada(escenario, estado, ConfiguracionAgente(algoritmo, profundidad=2, orden="tactico"))

    esperado = funcion(escenario, estado, 2, orden="tactico")
    assert decision.accion == esperado.accion_seleccionada.accion
    assert decision.adversarial is not None and decision.adversarial.valor == esperado.valor
    assert (decision.meta, decision.busqueda) == ("minimax", None)


# --- Contratos comunes ------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("algoritmo", ALGORITMOS_AGENTE)
@pytest.mark.parametrize("archivo", ["ejemplo_enunciado.json", "campo_20x20.json"])
def test_cada_algoritmo_juega_jugadas_legales_sin_modificar_el_estado(algoritmo, archivo) -> None:
    escenario = cargar_escenario(CARPETA_ESCENARIOS / archivo)
    estado = preparar_turno(escenario, crear_estado_inicial(escenario))
    configuracion = ConfiguracionAgente(algoritmo, profundidad=1)

    for _ in range(6):
        if es_terminal(escenario, estado):
            break
        copia = estado
        decision = decidir_jugada(escenario, estado, configuracion)
        assert estado == copia
        assert decision.bando == estado.turno_actual
        assert es_accion_valida(escenario, estado, decision.accion)
        estado = preparar_turno(escenario, aplicar_accion(escenario, estado, decision.accion))


def test_la_decision_es_determinista() -> None:
    escenario = cargar_escenario(CARPETA_ESCENARIOS / "campo_20x20.json")
    estado = crear_estado_inicial(escenario)

    primera = decidir_jugada(escenario, estado, ConfiguracionAgente("beam", k=2))
    segunda = decidir_jugada(escenario, estado, ConfiguracionAgente("beam", k=2))

    assert primera.accion == segunda.accion and primera.busqueda.camino == segunda.busqueda.camino


def test_estado_terminal_no_admite_decisiones(tmp_path) -> None:
    escenario = _escenario(tmp_path, [["camino"] * 4], [("A1", 0, 0), ("B1", 0, 3)], (0, 2))
    estado = _con_portador(crear_estado_inicial(escenario), "A1")

    with pytest.raises(ValueError, match="terminal"):
        decidir_jugada(escenario, estado, ConfiguracionAgente("bfs"))


@pytest.mark.parametrize(
    "argumentos",
    [{"algoritmo": "dijkstra"}, {"algoritmo": "minimax", "profundidad": 0}, {"algoritmo": "beam", "k": 0},
     {"algoritmo": "astar", "heuristica": "euclidiana"}, {"algoritmo": "alfa_beta", "orden": "azar"}],
)
def test_configuracion_invalida_se_rechaza(argumentos) -> None:
    with pytest.raises(ValueError):
        ConfiguracionAgente(**argumentos)
