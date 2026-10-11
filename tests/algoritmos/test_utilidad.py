"""Pruebas de E8.2: funcion de utilidad propia desde la perspectiva de MAX."""

import json
import math
from pathlib import Path

import pytest

from tacticalgrid.algoritmos import (
    EvaluadorUtilidad,
    PesosUtilidad,
    busqueda_costo_uniforme,
    costos_hacia,
    pesos_desde_configuracion,
    valorar_acciones,
)
from tacticalgrid.escenario.cargador import cargar_escenario
from tacticalgrid.escenario.escenario import Escenario, Posicion
from tacticalgrid.juego.accion import INTERCEPTAR
from tacticalgrid.juego.estado import EstadoJuego, crear_estado_inicial
from tacticalgrid.juego.problema import ProblemaNavegacion
from tacticalgrid.juego.reglas import aplicar_accion, generar_sucesores
from tacticalgrid.juego.tacticas import INTERCEPTAR_PORTADOR, acciones_tacticas
from tacticalgrid.juego.unidad import Unidad

CARPETA_ESCENARIOS = Path(__file__).resolve().parents[2] / "escenarios"
CRITERIOS = ("posesion", "entrega", "carrera_recurso", "amenaza", "bloqueo", "movilidad")


def _escenario_abierto(tmp_path, pesos: dict | None = None) -> Escenario:
    """Mapa 5x5 todo camino (costo 1), base A en (0, 0), base B en (4, 4) y recurso en (2, 2)."""
    contenido = {
        "version": "1.0",
        "mapa": {"filas": 5, "columnas": 5},
        "tipos_terreno": {"camino": {"costo": 1, "transitable": True}},
        "terreno": [["camino"] * 5 for _ in range(5)],
        "bases": {"A": {"fila": 0, "columna": 0}, "B": {"fila": 4, "columna": 4}},
        "recurso": {"fila": 2, "columna": 2},
        "unidades": [
            {"id": "A1", "bando": "A", "tipo": "estandar", "fila": 1, "columna": 0},
            {"id": "B1", "bando": "B", "tipo": "estandar", "fila": 4, "columna": 3},
        ],
        "turno": "A",
        "juego": {"portador_recurso": None} | ({"pesos_utilidad": pesos} if pesos is not None else {}),
    }
    ruta = tmp_path / "abierto.json"
    ruta.write_text(json.dumps(contenido), encoding="utf-8")
    return cargar_escenario(ruta)


@pytest.fixture
def abierto(tmp_path) -> Escenario:
    return _escenario_abierto(tmp_path)


def _u(identificador: str, fila: int, columna: int) -> Unidad:
    return Unidad(identificador, identificador[0], "estandar", Posicion(fila, columna))


def _estado(*unidades, turno="A", portador=None, recurso=None, partida="en_curso") -> EstadoJuego:
    return EstadoJuego(
        unidades=unidades, turno_actual=turno, posicion_recurso=recurso, portador_recurso=portador, estado_partida=partida
    )


def _explorar(escenario: Escenario, profundidad: int) -> set[EstadoJuego]:
    nivel = {crear_estado_inicial(escenario)}
    vistos = set(nivel)
    for _ in range(profundidad):
        nivel = {s for e in nivel for _, s in generar_sucesores(escenario, e)} - vistos
        vistos |= nivel
    return vistos


# --- Distancias con costos del JSON -------------------------------------------------------------------------------

@pytest.mark.parametrize("archivo", ["campo_20x20.json", "ruta_corta_vs_economica.json", "obstaculo_rodeo.json"])
def test_costos_hacia_coinciden_con_el_optimo_de_ucs(archivo) -> None:
    escenario = cargar_escenario(CARPETA_ESCENARIOS / archivo)
    for destino in (escenario.bases["A"], escenario.bases["B"], escenario.recurso):
        mapa = costos_hacia(escenario, destino)
        for unidad in escenario.unidades_iniciales:
            ucs = busqueda_costo_uniforme(ProblemaNavegacion(escenario, unidad.identificador, destino))
            assert mapa.get(unidad.posicion) == (ucs.costo if ucs.exito else None)


def test_costos_hacia_usan_el_costo_del_json(tmp_path) -> None:
    texto = (CARPETA_ESCENARIOS / "ruta_corta_vs_economica.json").read_text(encoding="utf-8")
    original = cargar_escenario(CARPETA_ESCENARIOS / "ruta_corta_vs_economica.json")
    ruta = tmp_path / "pantano_barato.json"
    ruta.write_text(texto.replace('"pantano": {"costo": 7', '"pantano": {"costo": 1'), encoding="utf-8")
    barato = cargar_escenario(ruta)

    # De (2, 0) a (2, 8): rodeo por camino (12) con pantano a 7; recta (8) con pantano a 1.
    assert costos_hacia(original, Posicion(2, 8))[Posicion(2, 0)] == 12
    assert costos_hacia(barato, Posicion(2, 8))[Posicion(2, 0)] == 8


# --- Valores terminales, suma cero y estructura -------------------------------------------------------------------

def test_valores_terminales(abierto) -> None:
    victoria_a = _estado(_u("A1", 0, 0), _u("B1", 4, 3), portador="A1", partida="victoria_A")
    empate = _estado(_u("A1", 1, 0), _u("B1", 4, 3), recurso=Posicion(2, 2), partida="empate_bloqueo")

    assert EvaluadorUtilidad(abierto, "A").desglosar(victoria_a) == {"terminal": 10_000}
    assert EvaluadorUtilidad(abierto, "B").evaluar(victoria_a) == -10_000
    assert EvaluadorUtilidad(abierto, "A").evaluar(empate) == 0


@pytest.mark.parametrize("archivo", ["ejemplo_enunciado.json", "recurso_en_transporte.json"])
def test_suma_cero_intercambiar_roles_cambia_el_signo(archivo) -> None:
    escenario = cargar_escenario(CARPETA_ESCENARIOS / archivo)
    max_a, max_b = EvaluadorUtilidad(escenario, "A"), EvaluadorUtilidad(escenario, "B")

    for estado in _explorar(escenario, 3):
        desglose_a, desglose_b = max_a.desglosar(estado), max_b.desglosar(estado)
        assert desglose_a.keys() == desglose_b.keys()
        assert all(desglose_a[c] == -desglose_b[c] for c in desglose_a)
        assert math.isfinite(max_a.evaluar(estado))
        assert max_a.evaluar(estado) == sum(desglose_a.values())


def test_estado_no_terminal_desglosa_todos_los_criterios(abierto) -> None:
    assert set(EvaluadorUtilidad(abierto, "A").desglosar(crear_estado_inicial(abierto))) == set(CRITERIOS)


def test_bando_max_invalido(abierto) -> None:
    with pytest.raises(ValueError, match="bando MAX"):
        EvaluadorUtilidad(abierto, "C")


# --- Cada criterio por separado (perspectiva de MAX = A) ----------------------------------------------------------

def test_posesion_y_entrega(abierto) -> None:
    evaluador = EvaluadorUtilidad(abierto, "A")
    lejos = evaluador.desglosar(_estado(_u("A1", 3, 3), _u("B1", 4, 0), portador="A1"))
    cerca = evaluador.desglosar(_estado(_u("A1", 1, 1), _u("B1", 4, 0), portador="A1"))
    rival = evaluador.desglosar(_estado(_u("A1", 0, 3), _u("B1", 3, 3), portador="B1"))

    assert lejos["posesion"] == cerca["posesion"] == 100
    assert (lejos["entrega"], cerca["entrega"]) == (-12, -4)  # costo 6 y 2 hasta (0, 0), por 2
    assert rival["posesion"] == -100 and rival["entrega"] == 4  # al portador de B le faltan 2


def test_carrera_por_el_recurso_libre(abierto) -> None:
    evaluador = EvaluadorUtilidad(abierto, "A")
    a_gana = evaluador.desglosar(_estado(_u("A1", 2, 1), _u("B1", 4, 4), recurso=Posicion(2, 2)))
    b_gana = evaluador.desglosar(_estado(_u("A1", 0, 0), _u("B1", 3, 2), recurso=Posicion(2, 2)))

    assert a_gana["carrera_recurso"] == 2 * (4 - 1)
    assert b_gana["carrera_recurso"] == 2 * (1 - 4)


def test_amenaza_y_bloqueo_sobre_el_portador(abierto) -> None:
    evaluador = EvaluadorUtilidad(abierto, "A")
    # B1 adyacente al portador A1 y dentro de su rectangulo hacia (0, 0); B2 lejos.
    desglose = evaluador.desglosar(_estado(_u("A1", 2, 2), _u("B1", 1, 2), _u("B2", 4, 4), portador="A1"))

    assert desglose["amenaza"] == -60
    assert desglose["bloqueo"] == -10


def test_movilidad_cuenta_unidades_disponibles(tmp_path) -> None:
    # Corredor 1x3: A1 en (0, 0) queda bloqueado por B1 en (0, 1); B1 puede moverse a (0, 2).
    contenido = {
        "version": "1.0",
        "mapa": {"filas": 1, "columnas": 3},
        "tipos_terreno": {"camino": {"costo": 1, "transitable": True}},
        "terreno": [["camino"] * 3],
        "bases": {"A": {"fila": 0, "columna": 0}, "B": {"fila": 0, "columna": 2}},
        "recurso": {"fila": 0, "columna": 2},
        "unidades": [
            {"id": "A1", "bando": "A", "tipo": "estandar", "fila": 0, "columna": 0},
            {"id": "B1", "bando": "B", "tipo": "estandar", "fila": 0, "columna": 1},
        ],
        "turno": "A",
        "juego": {"portador_recurso": None},
    }
    ruta = tmp_path / "corredor.json"
    ruta.write_text(json.dumps(contenido), encoding="utf-8")
    escenario = cargar_escenario(ruta)

    assert EvaluadorUtilidad(escenario, "A").desglosar(crear_estado_inicial(escenario))["movilidad"] == -1


# --- Explicar decisiones y efecto de los pesos ---------------------------------------------------------------------

def _mejor_accion(evaluador: EvaluadorUtilidad, estado: EstadoJuego):
    valoradas = valorar_acciones(evaluador, estado)
    signo = 1 if estado.turno_actual == evaluador.bando_max else -1
    return max(valoradas, key=lambda v: signo * v.utilidad)


def _situacion_de_amenaza() -> EstadoJuego:
    """A1 porta el recurso en (2, 2); B1 en (1, 1) vigila la ruta corta hacia la base A (0, 0)."""
    return _estado(_u("A1", 2, 2), _u("B1", 1, 1), portador="A1")


def test_con_pesos_por_defecto_el_portador_se_aleja_de_la_amenaza(abierto) -> None:
    evaluador = EvaluadorUtilidad(abierto, "A")
    valores = {v.accion_tactica.accion.destino: v for v in valorar_acciones(evaluador, _situacion_de_amenaza())}

    # Acercarse por (1, 2): entrega -6, pero queda junto a B1 (amenaza -60). Retroceder a (3, 2): entrega -10, sin amenaza.
    assert valores[Posicion(1, 2)].desglose["amenaza"] == -60
    assert valores[Posicion(3, 2)].desglose["amenaza"] == 0
    assert valores[Posicion(3, 2)].utilidad > valores[Posicion(1, 2)].utilidad
    assert _mejor_accion(evaluador, _situacion_de_amenaza()).accion_tactica.accion.destino == Posicion(3, 2)


def test_sin_peso_de_amenaza_el_portador_toma_la_ruta_corta(tmp_path) -> None:
    """Cambiar un peso en el JSON cambia la decision sin tocar codigo."""
    escenario = _escenario_abierto(tmp_path, pesos={"amenaza": 0})
    evaluador = EvaluadorUtilidad(escenario, "A", pesos_desde_configuracion(escenario.configuracion_juego))

    mejor = _mejor_accion(evaluador, _situacion_de_amenaza())

    assert mejor.accion_tactica.accion.destino in (Posicion(1, 2), Posicion(2, 1))
    assert mejor.accion_tactica.tipo_tactico == "avanzar"


def test_interceptar_es_la_mejor_accion_para_el_rival_del_portador(abierto) -> None:
    estado = _estado(_u("A1", 2, 2), _u("B1", 2, 3), turno="B", portador="A1")

    for bando_max in ("A", "B"):
        mejor = _mejor_accion(EvaluadorUtilidad(abierto, bando_max), estado)
        assert mejor.accion_tactica.accion.tipo == INTERCEPTAR
        assert mejor.accion_tactica.tipo_tactico == INTERCEPTAR_PORTADOR


def test_valorar_acciones_respeta_el_orden_y_evalua_el_sucesor() -> None:
    escenario = cargar_escenario(CARPETA_ESCENARIOS / "recurso_en_transporte.json")
    evaluador = EvaluadorUtilidad(escenario, "A")
    estado = crear_estado_inicial(escenario)

    valoradas = valorar_acciones(evaluador, estado)

    assert [v.accion_tactica for v in valoradas] == list(acciones_tacticas(escenario, estado))
    for v in valoradas:
        assert v.utilidad == evaluador.evaluar(aplicar_accion(escenario, estado, v.accion_tactica.accion))


def test_ejemplo_documentado_en_recurso_en_transporte() -> None:
    """A2 porta el recurso: avanzar a (2, 3) es lo mejor (entrega -18 -> -16); ir a (3, 4) lo peor (bloqueo -20)."""
    escenario = cargar_escenario(CARPETA_ESCENARIOS / "recurso_en_transporte.json")
    evaluador = EvaluadorUtilidad(escenario, "A")
    estado = crear_estado_inicial(escenario)
    valores = {
        (v.accion_tactica.accion.identificador_unidad, v.accion_tactica.accion.destino): v
        for v in valorar_acciones(evaluador, estado)
    }

    assert evaluador.evaluar(estado) == 72
    assert valores[("A2", Posicion(2, 3))].utilidad == 74
    assert valores[("A2", Posicion(2, 3))].accion_tactica.tipo_tactico == "avanzar"
    assert valores[("A2", Posicion(3, 4))].utilidad == 60
    assert valores[("A2", Posicion(3, 4))].desglose["bloqueo"] == -20
    assert max(v.utilidad for v in valores.values()) == 74


# --- Pesos configurables desde el JSON -----------------------------------------------------------------------------

def test_pesos_por_defecto_sin_configuracion(abierto) -> None:
    assert pesos_desde_configuracion(abierto.configuracion_juego) == PesosUtilidad()
    assert pesos_desde_configuracion(None) == PesosUtilidad()


def test_pesos_parciales_desde_el_json(tmp_path) -> None:
    escenario = _escenario_abierto(tmp_path, pesos={"amenaza": 0, "posesion": 250})

    pesos = pesos_desde_configuracion(escenario.configuracion_juego)

    assert (pesos.amenaza, pesos.posesion, pesos.entrega) == (0, 250, PesosUtilidad().entrega)


@pytest.mark.parametrize(
    ("pesos", "mensaje"),
    [
        ({"velocidad": 3}, "desconocidos"),
        ({"amenaza": "alta"}, "numero finito"),
        ({"amenaza": True}, "numero finito"),
        ({"victoria": 0}, "positivo"),
        ([1, 2], "debe ser un objeto"),
    ],
)
def test_pesos_invalidos_en_el_json_se_rechazan(tmp_path, pesos, mensaje) -> None:
    escenario = _escenario_abierto(tmp_path, pesos=pesos)

    with pytest.raises(ValueError, match=mensaje):
        pesos_desde_configuracion(escenario.configuracion_juego)


def test_peso_infinito_se_rechaza() -> None:
    with pytest.raises(ValueError, match="numero finito"):
        PesosUtilidad(entrega=float("inf"))
