"""Caso minimo 1 (E4.4): BFS y DFS encuentran solucion, pero recorren el espacio de busqueda de forma distinta.

Cada prueba fija una afirmacion del caso 1 de docs/casos-minimos/casos-1-2-5-busqueda.md, de modo que el experimento
sea reproducible y la documentacion deje de ser valida si cambian los algoritmos, las reglas o los escenarios.
"""

import os
import subprocess
import sys
from collections import deque
from pathlib import Path

import pytest

from tacticalgrid.algoritmos import busqueda_anchura, busqueda_profundidad
from tacticalgrid.escenario.cargador import cargar_escenario
from tacticalgrid.escenario.escenario import Posicion
from tacticalgrid.juego.accion import Accion
from tacticalgrid.juego.estado import EstadoJuego
from tacticalgrid.juego.problema import ProblemaNavegacion

RAIZ = Path(__file__).resolve().parents[2]


class ProblemaRegistrado:
    """Envuelve un ``ProblemaNavegacion`` y anota cada estado expandido, sin modificar BFS ni DFS.

    ``expandir`` (E4.1) llama a ``acciones`` exactamente una vez por expansion, asi que el orden de esas llamadas es
    el orden de expansion del algoritmo.
    """

    def __init__(self, problema: ProblemaNavegacion) -> None:
        self._problema = problema
        self.estado_inicial = problema.estado_inicial
        self.expandidos: list[EstadoJuego] = []

    def acciones(self, estado: EstadoJuego) -> tuple[Accion, ...]:
        self.expandidos.append(estado)
        return self._problema.acciones(estado)

    def __getattr__(self, nombre: str):
        return getattr(self._problema, nombre)

    def posiciones_expandidas(self) -> list[tuple[int, int]]:
        return [(self.posicion(e).fila, self.posicion(e).columna) for e in self.expandidos]


def _problema(archivo: str, objetivo: Posicion) -> ProblemaNavegacion:
    return ProblemaNavegacion(cargar_escenario(RAIZ / "escenarios" / archivo), "A1", objetivo)


def _ejecutar(algoritmo, archivo: str, objetivo: Posicion):
    registrado = ProblemaRegistrado(_problema(archivo, objetivo))
    return algoritmo(registrado), registrado


def _validar_camino(problema: ProblemaNavegacion, resultado) -> None:
    """Reproduce cada accion con las reglas del problema y recalcula el costo desde el JSON."""
    estado, costo = problema.estado_inicial, 0
    for origen, destino, accion in zip(resultado.camino, resultado.camino[1:], resultado.acciones):
        assert accion in problema.acciones(estado)
        assert (accion.origen, accion.destino) == (origen, destino)
        costo += problema.costo(estado, accion)
        estado = problema.resultado(estado, accion)
    assert problema.es_objetivo(estado)
    assert resultado.costo == costo


def _profundidad_minima(problema: ProblemaNavegacion) -> dict[EstadoJuego, int]:
    """Minimo numero de movimientos hasta cada estado alcanzable (calculo de referencia, independiente de BFS)."""
    distancia = {problema.estado_inicial: 0}
    cola = deque([problema.estado_inicial])
    while cola:
        estado = cola.popleft()
        for accion in problema.acciones(estado):
            sucesor = problema.resultado(estado, accion)
            if sucesor not in distancia:
                distancia[sucesor] = distancia[estado] + 1
                cola.append(sucesor)
    return distancia


# --- Escenario principal: campo_20x20.json, A1 (1, 2) -> (9, 10) ---------------------------------------------------

CAMPO = ("campo_20x20.json", Posicion(9, 10))


@pytest.mark.parametrize(
    ("algoritmo", "esperado"),
    [
        # (exito, movimientos, costo, generados, expandidos, maximo de frontera)
        (busqueda_anchura, (True, 16, 45, 205, 186, 20)),
        (busqueda_profundidad, (True, 98, 283, 206, 102, 104)),
    ],
    ids=["BFS", "DFS"],
)
def test_campo_ambos_encuentran_solucion_con_metricas_distintas(algoritmo, esperado) -> None:
    resultado, registrado = _ejecutar(algoritmo, *CAMPO)

    obtenido = (
        resultado.exito,
        resultado.longitud,
        resultado.costo,
        resultado.estados_generados,
        resultado.estados_expandidos,
        resultado.maximo_frontera,
    )
    assert obtenido == esperado
    _validar_camino(registrado._problema, resultado)


def test_campo_bfs_obtiene_el_minimo_de_movimientos_posible() -> None:
    """16 es la distancia Manhattan entre (1, 2) y (9, 10): ningun camino ortogonal puede ser mas corto."""
    resultado, _ = _ejecutar(busqueda_anchura, *CAMPO)

    assert resultado.longitud == abs(9 - 1) + abs(10 - 2) == 16


def test_campo_bfs_expande_por_niveles() -> None:
    """La profundidad minima de los estados expandidos por BFS nunca disminuye: explora por ondas."""
    resultado, registrado = _ejecutar(busqueda_anchura, *CAMPO)
    profundidad = _profundidad_minima(registrado._problema)

    niveles = [profundidad[estado] for estado in registrado.expandidos]
    assert niveles == sorted(niveles)
    # El objetivo se comprueba al extraer de la cola: antes de sacarlo, BFS ya expandio otros estados de su nivel.
    assert niveles[-1] == resultado.longitud == 16


def test_campo_dfs_no_expande_por_niveles() -> None:
    _, registrado = _ejecutar(busqueda_profundidad, *CAMPO)
    profundidad = _profundidad_minima(registrado._problema)

    niveles = [profundidad[estado] for estado in registrado.expandidos]
    assert niveles != sorted(niveles)


def test_campo_primeras_expansiones() -> None:
    _, bfs = _ejecutar(busqueda_anchura, *CAMPO)
    _, dfs = _ejecutar(busqueda_profundidad, *CAMPO)

    # BFS: el inicio y sus vecinos (nivel 1) antes que cualquier celda a dos pasos.
    assert bfs.posiciones_expandidas()[:5] == [(1, 2), (0, 2), (2, 2), (1, 1), (1, 3)]
    # DFS: siempre sigue la primera accion disponible (arriba, abajo, izquierda, derecha) y baja por la columna 0.
    assert dfs.posiciones_expandidas()[:8] == [(1, 2), (0, 2), (0, 1), (0, 0), (1, 0), (2, 0), (3, 0), (4, 0)]


def test_campo_dfs_recorre_columnas_completas_en_serpiente() -> None:
    """El camino de DFS baja por la columna 0, sube por la 2, y repite el patron en las columnas 6, 8 y 10."""
    resultado, _ = _ejecutar(busqueda_profundidad, *CAMPO)
    camino = [(p.fila, p.columna) for p in resultado.camino]

    for columna, filas in ((0, range(0, 20)), (2, range(3, 20)), (6, range(0, 20)), (8, range(0, 20))):
        assert all((fila, columna) in camino for fila in filas)
    assert camino.index((19, 0)) < camino.index((3, 2))  # la columna 0 se recorre antes que la 2


def test_campo_dfs_expande_casi_solo_su_camino() -> None:
    """De 102 estados expandidos, 98 son las posiciones del camino (sin el objetivo, que no se expande)."""
    resultado, registrado = _ejecutar(busqueda_profundidad, *CAMPO)
    expandidas = registrado.posiciones_expandidas()
    camino = {(p.fila, p.columna) for p in resultado.camino[:-1]}

    assert len(camino) == 98
    assert sum(posicion in camino for posicion in expandidas) == 98
    assert sorted(posicion for posicion in expandidas if posicion not in camino) == [(17, 4), (18, 4), (19, 4), (19, 5)]


def test_campo_dfs_mantiene_mas_frontera_que_bfs() -> None:
    """DFS marca los estados al apilarlos: los hermanos que deja pendientes se acumulan en la pila."""
    bfs, _ = _ejecutar(busqueda_anchura, *CAMPO)
    dfs, _ = _ejecutar(busqueda_profundidad, *CAMPO)

    assert dfs.maximo_frontera > bfs.maximo_frontera
    assert dfs.estados_expandidos < bfs.estados_expandidos


# --- Complemento verificado a mano: ejemplo_enunciado.json, A1 (0, 1) -> (3, 2) -----------------------------------

EJEMPLO = ("ejemplo_enunciado.json", Posicion(3, 2))


def test_ejemplo_bfs_coincide_con_la_traza_manual() -> None:
    resultado, registrado = _ejecutar(busqueda_anchura, *EJEMPLO)

    assert registrado.posiciones_expandidas() == [
        (0, 1), (0, 0), (0, 2), (1, 0), (1, 2), (0, 3), (2, 0), (2, 2), (1, 3), (3, 0), (2, 1), (1, 2),
    ]
    # La ultima (1, 2) es un estado distinto de la primera: A1 ya porta el recurso recogido en (2, 2).
    assert registrado.expandidos[-1].portador_recurso == "A1"
    assert registrado.expandidos[4].portador_recurso is None
    assert [(p.fila, p.columna) for p in resultado.camino] == [(0, 1), (0, 2), (1, 2), (2, 2), (3, 2)]
    assert (resultado.longitud, resultado.costo, resultado.estados_generados, resultado.estados_expandidos,
            resultado.maximo_frontera) == (4, 14, 19, 12, 7)


def test_ejemplo_dfs_coincide_con_la_traza_manual() -> None:
    resultado, registrado = _ejecutar(busqueda_profundidad, *EJEMPLO)

    assert registrado.posiciones_expandidas() == [(0, 1), (0, 0), (1, 0), (2, 0), (3, 0), (3, 1)]
    assert [(p.fila, p.columna) for p in resultado.camino] == [(0, 1), (0, 0), (1, 0), (2, 0), (3, 0), (3, 1), (3, 2)]
    assert (resultado.longitud, resultado.costo, resultado.estados_generados, resultado.estados_expandidos,
            resultado.maximo_frontera) == (6, 8, 9, 6, 3)


# --- Reproduccion desde consola -----------------------------------------------------------------------------------

def test_la_consola_reproduce_la_comparacion() -> None:
    salida = subprocess.run(
        [sys.executable, "-B", str(RAIZ / "main.py"), "escenarios/campo_20x20.json", "--algoritmo", "bfs_dfs"],
        cwd=RAIZ,
        env=os.environ | {"PYTHONIOENCODING": "utf-8"},
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )

    assert salida.returncode == 0, salida.stderr
    assert "COMPARACIÓN BFS vs. DFS" in salida.stdout
    filas = {linea[:20].strip(): linea[20:].split() for linea in salida.stdout.splitlines() if len(linea) > 20}
    assert filas["Movimientos"] == ["16", "98"]
    assert filas["Costo"] == ["45", "283"]
    assert filas["Estados generados"] == ["205", "206"]
    assert filas["Estados expandidos"] == ["186", "102"]
    assert filas["Máximo de frontera"] == ["20", "104"]
    assert "Caminos: Diferentes" in salida.stdout
