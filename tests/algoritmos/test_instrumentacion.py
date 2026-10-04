"""Pruebas de la instrumentacion comun de busqueda (E4.1) sobre escenarios reales del repositorio."""

from collections import deque
from collections.abc import Callable
from pathlib import Path

import pytest

from tacticalgrid.algoritmos.instrumentacion import MedidorBusqueda, Nodo, expandir
from tacticalgrid.algoritmos.resultado_busqueda import ResultadoBusqueda
from tacticalgrid.escenario.cargador import cargar_escenario
from tacticalgrid.escenario.escenario import Posicion
from tacticalgrid.juego.problema import ProblemaNavegacion

CARPETA_ESCENARIOS = Path(__file__).resolve().parents[2] / "escenarios"


def _problema(archivo: str, objetivo: Posicion) -> ProblemaNavegacion:
    return ProblemaNavegacion(cargar_escenario(CARPETA_ESCENARIOS / archivo), "A1", objetivo)


def _busqueda_de_prueba(
    problema: ProblemaNavegacion, nombre: str, extraer: Callable[[deque], Nodo]
) -> ResultadoBusqueda:
    """Busqueda minima que solo existe para ejercitar la instrumentacion; no es el BFS ni el DFS del proyecto.

    Muestra que dos estrategias distintas (``extraer`` por el frente o por el final) reutilizan la misma
    instrumentacion sin duplicar conteo de metricas ni reconstruccion del camino.
    """
    medidor = MedidorBusqueda(nombre)
    raiz = Nodo(problema.estado_inicial)
    frontera = deque([raiz])
    visitados = {raiz.estado}
    medidor.registrar_generado()
    medidor.observar_frontera(len(frontera))
    while frontera:
        nodo = extraer(frontera)
        if problema.es_objetivo(nodo.estado):
            return medidor.finalizar(problema, nodo)
        for hijo in expandir(problema, nodo, medidor):
            if hijo.estado not in visitados:
                visitados.add(hijo.estado)
                frontera.append(hijo)
                medidor.registrar_generado()
        medidor.observar_frontera(len(frontera))
    return medidor.finalizar(problema, None)


def test_expandir_genera_hijos_en_orden_con_costo_del_json_y_cuenta_una_expansion() -> None:
    problema = _problema("ejemplo_enunciado.json", Posicion(3, 2))
    medidor = MedidorBusqueda("PRUEBA")
    raiz = Nodo(problema.estado_inicial)

    hijos = expandir(problema, raiz, medidor)

    # A1 en (0, 1): izquierda es camino (costo 1) y derecha es pasto (costo 2) segun el JSON.
    assert [hijo.accion for hijo in hijos] == list(problema.acciones(raiz.estado))
    assert [(problema.posicion(h.estado), h.costo_acumulado) for h in hijos] == [(Posicion(0, 0), 1), (Posicion(0, 2), 2)]
    assert all(hijo.padre is raiz and hijo.profundidad == 1 for hijo in hijos)
    assert (medidor.estados_expandidos, medidor.estados_generados) == (1, 0)


def test_nodo_ruta_va_de_la_raiz_al_nodo() -> None:
    problema = _problema("ejemplo_enunciado.json", Posicion(3, 2))
    medidor = MedidorBusqueda("PRUEBA")
    raiz = Nodo(problema.estado_inicial)
    hijo = expandir(problema, raiz, medidor)[0]
    nieto = expandir(problema, hijo, medidor)[0]

    assert nieto.ruta() == (raiz, hijo, nieto)
    assert raiz.ruta() == (raiz,)


def test_medidor_registra_maximo_de_frontera_y_tiempo() -> None:
    marcas = iter([10.0, 10.75])
    medidor = MedidorBusqueda("PRUEBA", reloj=lambda: next(marcas))
    for tamano in (1, 4, 2):
        medidor.observar_frontera(tamano)
    medidor.registrar_generado(3)

    resultado = medidor.finalizar(_problema("ejemplo_enunciado.json", Posicion(3, 2)), None)

    assert resultado.maximo_frontera == 4
    assert resultado.estados_generados == 3
    assert resultado.tiempo_segundos == pytest.approx(0.75)


@pytest.mark.parametrize("extraer", [deque.popleft, deque.pop], ids=["frente", "final"])
@pytest.mark.parametrize(
    ("archivo", "objetivo"),
    [("ruta_corta_vs_economica.json", Posicion(2, 8)), ("campo_20x20.json", Posicion(9, 10))],
)
def test_resultado_exitoso_es_coherente_con_el_problema(archivo, objetivo, extraer) -> None:
    problema = _problema(archivo, objetivo)

    resultado = _busqueda_de_prueba(problema, "PRUEBA", extraer)

    assert resultado.exito
    assert resultado.camino[0] == problema.posicion(problema.estado_inicial)
    assert resultado.camino[-1] == objetivo
    assert resultado.longitud == len(resultado.camino) - 1 == len(resultado.acciones)
    for origen, destino, accion in zip(resultado.camino, resultado.camino[1:], resultado.acciones):
        assert (accion.origen, accion.destino) == (origen, destino)
        assert abs(origen.fila - destino.fila) + abs(origen.columna - destino.columna) == 1
    # El costo reportado coincide con la suma de los costos del terreno de cada transicion.
    assert resultado.costo == sum(problema.escenario.obtener_costo(accion.destino) for accion in resultado.acciones)
    assert resultado.estados_generados >= resultado.estados_expandidos >= 1
    assert resultado.maximo_frontera >= 1
    assert resultado.tiempo_segundos >= 0


def test_dos_estrategias_distintas_reportan_la_misma_estructura() -> None:
    problema = _problema("campo_20x20.json", Posicion(9, 10))

    por_frente = _busqueda_de_prueba(problema, "FRENTE", deque.popleft).a_diccionario()
    por_final = _busqueda_de_prueba(problema, "FINAL", deque.pop).a_diccionario()

    assert set(por_frente) == set(por_final)
    # Exploran distinto: la instrumentacion refleja esa diferencia en las metricas.
    assert (por_frente["estados_expandidos"], por_frente["longitud"]) != (por_final["estados_expandidos"], por_final["longitud"])


def test_resultado_sin_solucion_cuando_el_objetivo_es_un_muro() -> None:
    # (1, 1) es muro en el ejemplo del enunciado: ningun camino llega.
    resultado = _busqueda_de_prueba(_problema("ejemplo_enunciado.json", Posicion(1, 1)), "PRUEBA", deque.popleft)

    assert not resultado.exito
    assert resultado.camino == () and resultado.acciones == ()
    assert resultado.costo is None
    # Estado compuesto: 15 celdas transitables con A1 portando el recurso, mas 14 sin portarlo (entrar en (2, 2)
    # lo recoge, asi que "A1 en (2, 2) sin recurso" no es alcanzable).
    assert resultado.estados_expandidos == 29


def test_inicio_que_ya_es_objetivo_tiene_camino_de_una_posicion_y_costo_cero() -> None:
    resultado = _busqueda_de_prueba(_problema("ejemplo_enunciado.json", Posicion(0, 1)), "PRUEBA", deque.popleft)

    assert resultado.exito
    assert resultado.camino == (Posicion(0, 1),)
    assert (resultado.longitud, resultado.costo, resultado.estados_expandidos) == (0, 0, 0)
