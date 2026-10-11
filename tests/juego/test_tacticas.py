"""Pruebas de E8.1: accion de intercepcion y clasificacion tactica de las acciones legales."""

import json
from collections import Counter
from pathlib import Path

import pytest

from tacticalgrid.escenario.cargador import cargar_escenario
from tacticalgrid.escenario.escenario import Escenario, Posicion
from tacticalgrid.juego.accion import INTERCEPTAR, Accion
from tacticalgrid.juego.estado import EstadoJuego, crear_estado_inicial
from tacticalgrid.juego.partida import acciones_para_unidad
from tacticalgrid.juego.reglas import acciones_validas, aplicar_accion, costo_accion, es_accion_valida, es_terminal
from tacticalgrid.juego.tacticas import (
    APROXIMARSE_AL_RECURSO,
    AVANZAR,
    BLOQUEAR_POSICION,
    INTERCEPTAR_PORTADOR,
    PERSEGUIR_PORTADOR,
    PROTEGER_ZONA,
    REPOSICIONAR,
    TIPOS_TACTICOS,
    acciones_tacticas,
    clasificar_accion,
)
from tacticalgrid.juego.unidad import Unidad

CARPETA_ESCENARIOS = Path(__file__).resolve().parents[2] / "escenarios"


@pytest.fixture
def mapa_abierto(tmp_path) -> Escenario:
    """Mapa 5x5 todo camino (costo 1) salvo pasto (costo 2) en (2, 2). Base A en (0, 0) y base B en (4, 4)."""
    terreno = [["camino"] * 5 for _ in range(5)]
    terreno[2][2] = "pasto"
    contenido = {
        "version": "1.0",
        "mapa": {"filas": 5, "columnas": 5},
        "tipos_terreno": {"camino": {"costo": 1, "transitable": True}, "pasto": {"costo": 2, "transitable": True}},
        "terreno": terreno,
        "bases": {"A": {"fila": 0, "columna": 0}, "B": {"fila": 4, "columna": 4}},
        "recurso": {"fila": 2, "columna": 2},
        "unidades": [
            {"id": "A1", "bando": "A", "tipo": "estandar", "fila": 1, "columna": 1},
            {"id": "B1", "bando": "B", "tipo": "estandar", "fila": 3, "columna": 3},
        ],
        "turno": "A",
        "juego": {"portador_recurso": None},
    }
    ruta = tmp_path / "abierto.json"
    ruta.write_text(json.dumps(contenido), encoding="utf-8")
    return cargar_escenario(ruta)


def _u(identificador: str, fila: int, columna: int) -> Unidad:
    return Unidad(identificador, identificador[0], "estandar", Posicion(fila, columna))


def _estado(*unidades: Unidad, turno: str, portador: str | None = None, recurso: Posicion | None = None) -> EstadoJuego:
    return EstadoJuego(unidades=unidades, turno_actual=turno, posicion_recurso=recurso, portador_recurso=portador)


def _tipo(escenario, estado, unidad: str, destino: Posicion) -> str:
    accion = next(a for a in acciones_validas(escenario, estado) if a.identificador_unidad == unidad and a.destino == destino)
    return clasificar_accion(escenario, estado, accion)


# --- Accion de intercepcion ---------------------------------------------------------------------------------------

def test_unidad_adyacente_al_portador_rival_puede_interceptar(mapa_abierto) -> None:
    estado = _estado(_u("A1", 2, 2), _u("B1", 2, 3), turno="B", portador="A1")

    acciones_b1 = acciones_para_unidad(mapa_abierto, estado, "B1")

    intercepcion = Accion("B1", Posicion(2, 3), Posicion(2, 2), INTERCEPTAR)
    assert acciones_b1[-1] == intercepcion  # despues de los movimientos de la unidad
    assert es_accion_valida(mapa_abierto, estado, intercepcion)
    # Sigue sin poder moverse a la celda ocupada del portador.
    assert Posicion(2, 2) not in [a.destino for a in acciones_b1 if a.tipo != INTERCEPTAR]


@pytest.mark.parametrize(
    ("descripcion", "unidades", "portador"),
    [
        ("en diagonal", (_u("A1", 2, 2), _u("B1", 3, 3)), "A1"),
        ("a dos celdas", (_u("A1", 2, 2), _u("B1", 2, 4)), "A1"),
        ("sin portador", (_u("A1", 2, 2), _u("B1", 2, 3)), None),
        ("portador aliado", (_u("B2", 2, 2), _u("B1", 2, 3), _u("A1", 0, 4)), "B2"),
    ],
)
def test_no_hay_intercepcion_si_no_se_cumplen_las_condiciones(mapa_abierto, descripcion, unidades, portador) -> None:
    estado = _estado(*unidades, turno="B", portador=portador, recurso=None if portador else Posicion(0, 3))

    assert all(a.tipo != INTERCEPTAR for a in acciones_validas(mapa_abierto, estado)), descripcion


def test_interceptar_transfiere_el_recurso_sin_mover_a_nadie_y_cambia_el_turno(mapa_abierto) -> None:
    estado = _estado(_u("A1", 2, 2), _u("B1", 2, 3), turno="B", portador="A1")
    intercepcion = Accion("B1", Posicion(2, 3), Posicion(2, 2), INTERCEPTAR)

    sucesor = aplicar_accion(mapa_abierto, estado, intercepcion)

    assert sucesor.portador_recurso == "B1"
    assert sucesor.posicion_recurso is None
    assert {(u.identificador, u.posicion) for u in sucesor.unidades} == {(u.identificador, u.posicion) for u in estado.unidades}
    assert sucesor.turno_actual == "A"
    assert sucesor.estado_partida == "en_curso"
    # El costo se lee del terreno de la celda del portador: (2, 2) es pasto.
    assert costo_accion(mapa_abierto, intercepcion) == 2


def test_interceptar_desde_la_propia_base_da_la_victoria(mapa_abierto) -> None:
    estado = _estado(_u("A1", 3, 4), _u("B1", 4, 4), turno="B", portador="A1")

    sucesor = aplicar_accion(mapa_abierto, estado, Accion("B1", Posicion(4, 4), Posicion(3, 4), INTERCEPTAR))

    assert sucesor.estado_partida == "victoria_B"
    assert es_terminal(mapa_abierto, sucesor)
    assert acciones_validas(mapa_abierto, sucesor) == ()


def test_el_portador_interceptado_puede_recuperar_el_recurso_en_su_turno(mapa_abierto) -> None:
    """Ambos bandos tienen las mismas reglas: si siguen adyacentes, el antiguo portador puede interceptar."""
    estado = _estado(_u("A1", 2, 2), _u("B1", 2, 3), turno="B", portador="A1")
    sucesor = aplicar_accion(mapa_abierto, estado, Accion("B1", Posicion(2, 3), Posicion(2, 2), INTERCEPTAR))

    assert Accion("A1", Posicion(2, 2), Posicion(2, 3), INTERCEPTAR) in acciones_validas(mapa_abierto, sucesor)


def test_accion_existente_sin_tipo_sigue_siendo_un_movimiento() -> None:
    assert Accion("A1", Posicion(0, 0), Posicion(0, 1)).tipo == "mover"


# --- Clasificacion tactica --------------------------------------------------------------------------------------

def test_recurso_libre_aproximarse_o_reposicionar(mapa_abierto) -> None:
    estado = crear_estado_inicial(mapa_abierto)  # A1 en (1, 1), recurso libre en (2, 2)

    assert _tipo(mapa_abierto, estado, "A1", Posicion(2, 1)) == APROXIMARSE_AL_RECURSO
    assert _tipo(mapa_abierto, estado, "A1", Posicion(0, 1)) == REPOSICIONAR


def test_portador_propio_avanza_hacia_su_base(mapa_abierto) -> None:
    estado = _estado(_u("A1", 2, 2), _u("A2", 4, 2), _u("B1", 4, 0), turno="A", portador="A1")

    assert _tipo(mapa_abierto, estado, "A1", Posicion(1, 2)) == AVANZAR
    assert _tipo(mapa_abierto, estado, "A1", Posicion(3, 2)) == REPOSICIONAR


def test_aliado_del_portador_protege_su_zona(mapa_abierto) -> None:
    estado = _estado(_u("A1", 2, 2), _u("A2", 4, 2), _u("B1", 4, 0), turno="A", portador="A1")

    assert _tipo(mapa_abierto, estado, "A2", Posicion(3, 2)) == PROTEGER_ZONA
    assert _tipo(mapa_abierto, estado, "A2", Posicion(4, 3)) == REPOSICIONAR


def test_contra_portador_rival_bloquear_perseguir_o_reposicionar(mapa_abierto) -> None:
    # A1 porta el recurso en (2, 2) y su base esta en (0, 0): su rectangulo de rutas cortas es filas 0-2, columnas 0-2.
    estado = _estado(_u("A1", 2, 2), _u("B1", 1, 3), _u("B2", 4, 3), turno="B", portador="A1")

    assert _tipo(mapa_abierto, estado, "B1", Posicion(1, 2)) == BLOQUEAR_POSICION
    assert _tipo(mapa_abierto, estado, "B2", Posicion(3, 3)) == PERSEGUIR_PORTADOR
    assert _tipo(mapa_abierto, estado, "B2", Posicion(4, 4)) == REPOSICIONAR


def test_intercepcion_se_clasifica_como_interceptar_portador(mapa_abierto) -> None:
    estado = _estado(_u("A1", 2, 2), _u("B1", 2, 3), turno="B", portador="A1")

    tipos = {at.accion.tipo: at.tipo_tactico for at in acciones_tacticas(mapa_abierto, estado)}

    assert tipos[INTERCEPTAR] == INTERCEPTAR_PORTADOR


def test_clasificacion_es_simetrica_entre_bandos(mapa_abierto) -> None:
    """Reflejar el tablero (r, c) -> (4 - r, 4 - c) intercambia las bases; con los bandos intercambiados, los tipos
    tacticos se conservan: las tacticas no dependen de ser A o B."""
    def reflejar(p: Posicion) -> Posicion:
        return Posicion(4 - p.fila, 4 - p.columna)

    original = _estado(_u("A1", 2, 2), _u("A2", 4, 2), _u("B1", 1, 3), _u("B2", 2, 3), turno="B", portador="A1")
    espejo = _estado(
        Unidad("B1", "B", "estandar", reflejar(Posicion(2, 2))),
        Unidad("B2", "B", "estandar", reflejar(Posicion(4, 2))),
        Unidad("A1", "A", "estandar", reflejar(Posicion(1, 3))),
        Unidad("A2", "A", "estandar", reflejar(Posicion(2, 3))),
        turno="A",
        portador="B1",
    )

    def tipos(estado):
        return Counter(at.tipo_tactico for at in acciones_tacticas(mapa_abierto, estado))

    assert tipos(original) == tipos(espejo)
    assert tipos(original)[INTERCEPTAR_PORTADOR] == 1


# --- Legalidad y acotacion sobre partidas reales -------------------------------------------------------------------

@pytest.mark.parametrize("archivo", ["ejemplo_enunciado.json", "recurso_en_transporte.json", "campo_20x20.json"])
def test_toda_accion_tactica_es_legal_y_aplicable_en_partidas_reales(archivo) -> None:
    escenario = cargar_escenario(CARPETA_ESCENARIOS / archivo)
    nivel = {crear_estado_inicial(escenario)}
    vistos = set(nivel)
    for _ in range(4):
        siguiente = set()
        for estado in nivel:
            tacticas = acciones_tacticas(escenario, estado)
            assert [at.accion for at in tacticas] == list(acciones_validas(escenario, estado))
            por_unidad = Counter(at.accion.identificador_unidad for at in tacticas)
            assert all(cantidad <= 5 for cantidad in por_unidad.values())
            for at in tacticas:
                assert at.tipo_tactico in TIPOS_TACTICOS
                assert es_accion_valida(escenario, estado, at.accion)
                sucesor = aplicar_accion(escenario, estado, at.accion)
                assert sucesor.turno_actual != estado.turno_actual
                if sucesor not in vistos:
                    vistos.add(sucesor)
                    siguiente.add(sucesor)
        nivel = siguiente
    assert vistos


def test_partida_con_intercepcion_completa(mapa_abierto) -> None:
    """Secuencia legal: B1 intercepta a A1 y luego lleva el recurso a su base."""
    estado = _estado(_u("A1", 3, 2), _u("B1", 3, 3), turno="B", portador="A1")
    for accion in (
        Accion("B1", Posicion(3, 3), Posicion(3, 2), INTERCEPTAR),
        Accion("A1", Posicion(3, 2), Posicion(2, 2)),
        Accion("B1", Posicion(3, 3), Posicion(4, 3)),
        Accion("A1", Posicion(2, 2), Posicion(2, 3)),
        Accion("B1", Posicion(4, 3), Posicion(4, 4)),
    ):
        assert es_accion_valida(mapa_abierto, estado, accion)
        estado = aplicar_accion(mapa_abierto, estado, accion)

    assert estado.estado_partida == "victoria_B"
