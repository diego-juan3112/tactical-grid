"""Caso minimo 5 (E7.2): efecto de k en Beam Search sobre un mismo escenario.

Cada prueba fija una afirmacion de la discusion escrita en el README (seccion E7.2), de modo que el analisis sea
reproducible y deje de ser valido si cambian el algoritmo, las reglas o el escenario.
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest

from tacticalgrid.algoritmos import NivelHaz, busqueda_anchura, busqueda_costo_uniforme, busqueda_haz
from tacticalgrid.escenario.cargador import cargar_escenario
from tacticalgrid.escenario.escenario import Posicion
from tacticalgrid.juego.estado import EstadoJuego
from tacticalgrid.juego.problema import ProblemaNavegacion

RAIZ = Path(__file__).resolve().parents[2]
ANCHOS = (1, 2, 4, 8)


def _problema(archivo: str, objetivo: Posicion) -> ProblemaNavegacion:
    return ProblemaNavegacion(cargar_escenario(RAIZ / "escenarios" / archivo), "A1", objetivo)


@pytest.fixture(scope="module")
def campo() -> ProblemaNavegacion:
    return _problema("campo_20x20.json", Posicion(9, 10))


@pytest.fixture(scope="module")
def ruta_corta() -> ProblemaNavegacion:
    return _problema("ruta_corta_vs_economica.json", Posicion(2, 8))


def _estados_de_la_ruta_optima(problema: ProblemaNavegacion) -> list[EstadoJuego]:
    """Estados del camino de UCS (costo minimo); el estado i esta a profundidad i."""
    estados = [problema.estado_inicial]
    for accion in busqueda_costo_uniforme(problema).acciones:
        estados.append(problema.resultado(estados[-1], accion))
    return estados


def _niveles(problema: ProblemaNavegacion, k: int) -> list[NivelHaz]:
    niveles: list[NivelHaz] = []
    busqueda_haz(problema, k, observador=niveles.append)
    return niveles


def _perdida_de_la_ruta_optima(problema: ProblemaNavegacion, k: int):
    """Primer nivel en que el estado de la ruta optima no entra en el haz: (nivel, posicion, f, f de corte)."""
    ruta = _estados_de_la_ruta_optima(problema)
    for nivel in _niveles(problema, k)[1:]:
        if nivel.nivel >= len(ruta):
            return None
        referencia = ruta[nivel.nivel]
        if not any(nodo.estado == referencia for _, nodo in nivel.conservados):
            f_descartado = next(f for f, nodo in nivel.descartados if nodo.estado == referencia)
            return nivel.nivel, problema.posicion(referencia), f_descartado, nivel.conservados[-1][0]
    return None


# --- Escenario principal: campo_20x20.json -------------------------------------------------------------------------

def test_referencias_ucs_bfs_del_mismo_problema(campo) -> None:
    ucs, bfs = busqueda_costo_uniforme(campo), busqueda_anchura(campo)

    assert (ucs.costo, ucs.longitud) == (34, 34)
    assert bfs.longitud == 16


@pytest.mark.parametrize(
    ("k", "esperado"),
    [
        # k: (exito, movimientos, costo, generados, expandidos, maximo de frontera, niveles recorridos)
        (1, (False, 0, None, 74, 74, 1, 74)),
        (2, (False, 0, None, 137, 137, 2, 70)),
        (4, (True, 34, 40, 137, 133, 4, 34)),
        (8, (True, 36, 46, 284, 276, 8, 36)),
    ],
)
def test_tabla_de_resultados_para_k_1_2_4_8(campo, k, esperado) -> None:
    niveles: list[NivelHaz] = []
    r = busqueda_haz(campo, k, observador=niveles.append)

    obtenido = (r.exito, r.longitud, r.costo, r.estados_generados, r.estados_expandidos, r.maximo_frontera)
    assert obtenido + (niveles[-1].nivel,) == esperado


@pytest.mark.parametrize(
    ("k", "nivel", "posicion", "f_descartado", "f_corte"),
    [
        (1, 9, Posicion(1, 11), 18, 17),
        (2, 9, Posicion(1, 11), 18, 18),
        (4, 11, Posicion(1, 13), 22, 22),
        (8, 12, Posicion(1, 14), 24, 24),
    ],
)
def test_cada_k_descarta_la_ruta_optima_en_un_nivel_concreto(campo, k, nivel, posicion, f_descartado, f_corte) -> None:
    """Ningun k de 1 a 8 conserva el camino de costo 34: todos lo podan sobre la carretera de la fila 1."""
    assert _perdida_de_la_ruta_optima(campo, k) == (nivel, posicion, f_descartado, f_corte)


def test_con_k_1_la_heuristica_saca_a_la_unidad_de_la_carretera(campo) -> None:
    """En el nivel 9, (2, 10) tiene f = 17 (g 10 + h 7) y (1, 11) tiene f = 18 (g 9 + h 9): gana el desvio al lago."""
    nivel_9 = _niveles(campo, 1)[9]

    assert [(campo.posicion(n.estado), f, n.costo_acumulado) for f, n in nivel_9.conservados] == [
        (Posicion(2, 10), 17, 10)
    ]
    assert (Posicion(1, 11), 18) in [(campo.posicion(n.estado), f) for f, n in nivel_9.descartados]


def test_con_k_1_y_2_el_haz_queda_atrapado_entre_celdas_ya_visitadas(campo) -> None:
    for k in (1, 2):
        niveles = _niveles(campo, k)
        assert niveles[-1].conservados == () and niveles[-1].descartados == ()
        assert Posicion(15, 5) in [campo.posicion(n.estado) for _, n in niveles[-2].conservados]


def test_con_k_2_4_y_8_la_poda_se_decide_por_empate(campo) -> None:
    """El descartado tiene la misma f que el ultimo conservado: decide el orden de generacion de las acciones."""
    for k in (2, 4, 8):
        _, _, f_descartado, f_corte = _perdida_de_la_ruta_optima(campo, k)
        assert f_descartado == f_corte


def test_con_k_8_ramas_del_oeste_ocupan_el_haz_al_perder_la_ruta(campo) -> None:
    """En el nivel 12 la mitad del haz son celdas del oeste (columna <= 4) que el lago bloquea."""
    nivel_12 = _niveles(campo, 8)[12]
    columnas = [campo.posicion(n.estado).columna for _, n in nivel_12.conservados]

    assert sum(columna <= 4 for columna in columnas) == 4


def test_k_4_y_k_8_terminan_en_soluciones_mas_caras_que_ucs(campo) -> None:
    optimo = busqueda_costo_uniforme(campo).costo

    assert busqueda_haz(campo, 4).costo - optimo == 6
    assert busqueda_haz(campo, 8).costo - optimo == 12


# --- Escenario complementario: ruta_corta_vs_economica.json ---------------------------------------------------------

@pytest.mark.parametrize(
    ("k", "esperado"),
    [(1, (True, 12, 12)), (2, (True, 12, 12)), (4, (True, 8, 50)), (8, (True, 8, 50))],
)
def test_complementario_aumentar_k_empeora_el_costo(ruta_corta, k, esperado) -> None:
    r = busqueda_haz(ruta_corta, k)

    assert (r.exito, r.longitud, r.costo) == esperado


def test_complementario_un_haz_estrecho_poda_el_pantano_en_el_nivel_1(ruta_corta) -> None:
    """Desde (2, 0): camino (1, 0) f = 10, pasto (3, 0) f = 11, pantano (2, 1) f = 14."""
    for k in (1, 2):
        nivel_1 = _niveles(ruta_corta, k)[1]
        assert Posicion(2, 1) in [ruta_corta.posicion(n.estado) for _, n in nivel_1.descartados]
    nivel_1 = _niveles(ruta_corta, 4)[1]
    assert [(ruta_corta.posicion(n.estado), f) for f, n in nivel_1.conservados] == [
        (Posicion(1, 0), 10),
        (Posicion(3, 0), 11),
        (Posicion(2, 1), 14),
    ]


# --- Reproduccion desde consola -------------------------------------------------------------------------------------

def test_la_consola_reproduce_la_tabla_comparativa() -> None:
    salida = subprocess.run(
        [sys.executable, "-B", str(RAIZ / "main.py"), "escenarios/campo_20x20.json", "--algoritmo", "beam", "--k", "1", "2", "4", "8"],
        cwd=RAIZ,
        env=os.environ | {"PYTHONIOENCODING": "utf-8"},
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )

    assert salida.returncode == 0, salida.stderr
    assert "COMPARACIÓN BEAM SEARCH POR ANCHO k" in salida.stdout
    filas = [linea.split()[:7] for linea in salida.stdout.splitlines() if linea.strip()[:1].isdigit()]
    assert filas[-4:] == [
        ["1", "No", "0", "-", "74", "74", "1"],
        ["2", "No", "0", "-", "137", "137", "2"],
        ["4", "Sí", "34", "40", "137", "133", "4"],
        ["8", "Sí", "36", "46", "284", "276", "8"],
    ]
