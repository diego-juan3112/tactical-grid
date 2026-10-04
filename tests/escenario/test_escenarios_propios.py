"""Pruebas del set propio de escenarios (E2.3): todos cargan y cumplen la propiedad para la que se disenaron."""

import heapq
from itertools import count
from pathlib import Path

import pytest

from tacticalgrid.escenario.cargador import cargar_escenario
from tacticalgrid.escenario.escenario import Escenario, Posicion
from tacticalgrid.juego.problema import ProblemaNavegacion

CARPETA_ESCENARIOS = Path(__file__).resolve().parents[2] / "escenarios"
ESCENARIOS = sorted(CARPETA_ESCENARIOS.glob("*.json"))
PROPIOS_E2_3 = ("campo_20x20.json", "ruta_corta_vs_economica.json", "obstaculo_rodeo.json", "recurso_en_transporte.json")


def _problema_de_prueba(escenario: Escenario) -> ProblemaNavegacion:
    prueba = escenario.configuracion_prueba
    assert prueba is not None and prueba["modo"] == "busqueda"
    objetivo = Posicion(prueba["objetivo"]["fila"], prueba["objetivo"]["columna"])
    return ProblemaNavegacion(escenario, prueba["unidad_inicio"], objetivo)


def _mejor_ruta(problema: ProblemaNavegacion, prioridad: str) -> tuple[int, int | float]:
    """Devuelve (movimientos, costo) de la mejor ruta al objetivo segun ``prioridad``.

    Con ``"movimientos"`` minimiza primero los movimientos y desempata por costo; con ``"costo"`` minimiza primero
    el costo y desempata por movimientos. Es un calculo de referencia para validar los escenarios, no la
    implementacion de BFS ni UCS (historias E3 y E4).
    """
    def clave(movimientos: int, costo: int | float) -> tuple:
        return (movimientos, costo) if prioridad == "movimientos" else (costo, movimientos)

    desempate = count()
    mejor = {problema.estado_inicial: clave(0, 0)}
    cola = [(clave(0, 0), next(desempate), problema.estado_inicial, 0, 0)]
    while cola:
        valor, _, estado, movimientos, costo = heapq.heappop(cola)
        if problema.es_objetivo(estado):
            return movimientos, costo
        if valor > mejor[estado]:
            continue
        for accion in problema.acciones(estado):
            sucesor = problema.resultado(estado, accion)
            nuevo_mov, nuevo_costo = movimientos + 1, costo + problema.costo(estado, accion)
            nuevo = clave(nuevo_mov, nuevo_costo)
            if sucesor not in mejor or nuevo < mejor[sucesor]:
                mejor[sucesor] = nuevo
                heapq.heappush(cola, (nuevo, next(desempate), sucesor, nuevo_mov, nuevo_costo))
    raise AssertionError("El objetivo de la prueba no es alcanzable.")


@pytest.mark.parametrize("ruta", ESCENARIOS, ids=lambda ruta: ruta.name)
def test_todos_los_escenarios_del_repositorio_son_validos(ruta) -> None:
    cargar_escenario(ruta)


def test_los_escenarios_propios_estan_versionados_en_la_carpeta_escenarios() -> None:
    assert set(PROPIOS_E2_3) <= {ruta.name for ruta in ESCENARIOS}


def test_existe_al_menos_un_escenario_de_20x20_o_mayor() -> None:
    escenario = cargar_escenario(CARPETA_ESCENARIOS / "campo_20x20.json")

    assert escenario.filas >= 20 and escenario.columnas >= 20


@pytest.mark.parametrize("nombre", PROPIOS_E2_3)
def test_cada_bando_controla_al_menos_tres_unidades(nombre) -> None:
    escenario = cargar_escenario(CARPETA_ESCENARIOS / nombre)

    for bando in ("A", "B"):
        assert sum(unidad.bando == bando for unidad in escenario.unidades_iniciales) >= 3


@pytest.mark.parametrize(
    ("nombre", "corta", "economica"),
    [
        ("ruta_corta_vs_economica.json", (8, 50), (12, 12)),
        ("campo_20x20.json", (16, 42), (34, 34)),
    ],
)
def test_la_ruta_con_menos_movimientos_es_mas_costosa_que_una_mas_larga(nombre, corta, economica) -> None:
    """Requisito del enunciado y base del caso BFS vs. UCS (E5.2).

    Incluso la ruta mas barata entre las de minimo numero de movimientos (la mejor que podria devolver BFS) cuesta
    mas que la ruta de costo minimo (la que devuelve UCS), que a su vez necesita mas movimientos. Por eso BFS y UCS
    producen caminos distintos sin importar como desempaten.
    """
    problema = _problema_de_prueba(cargar_escenario(CARPETA_ESCENARIOS / nombre))

    ruta_corta = _mejor_ruta(problema, "movimientos")
    ruta_economica = _mejor_ruta(problema, "costo")

    assert ruta_corta == corta
    assert ruta_economica == economica
    assert ruta_corta[0] < ruta_economica[0] and ruta_corta[1] > ruta_economica[1]


def test_la_ruta_economica_depende_del_costo_declarado_en_el_json(tmp_path) -> None:
    """Si el pantano cuesta 1, la ruta recta vuelve a ser la mas economica: el resultado sale del JSON."""
    texto = (CARPETA_ESCENARIOS / "ruta_corta_vs_economica.json").read_text(encoding="utf-8")
    ruta = tmp_path / "pantano_barato.json"
    ruta.write_text(texto.replace('"pantano": {"costo": 7', '"pantano": {"costo": 1'), encoding="utf-8")
    problema = _problema_de_prueba(cargar_escenario(ruta))

    assert _mejor_ruta(problema, "costo") == _mejor_ruta(problema, "movimientos") == (8, 8)


def test_obstaculo_obliga_a_rodear_un_objetivo_cercano() -> None:
    problema = _problema_de_prueba(cargar_escenario(CARPETA_ESCENARIOS / "obstaculo_rodeo.json"))
    inicio = next(u.posicion for u in problema.estado_inicial.unidades if u.identificador == problema.identificador_unidad)
    manhattan = abs(inicio.fila - problema.objetivo.fila) + abs(inicio.columna - problema.objetivo.columna)

    movimientos, _ = _mejor_ruta(problema, "movimientos")

    assert manhattan == 3
    assert movimientos == 15


def test_escenario_con_recurso_en_transporte_inicia_con_portador() -> None:
    escenario = cargar_escenario(CARPETA_ESCENARIOS / "recurso_en_transporte.json")

    assert escenario.portador_recurso_inicial == "A2"
    assert escenario.configuracion_prueba == {"modo": "partida"}
