"""Pruebas aisladas y de propiedades para la heuristica topologica con obstaculos."""

import heapq
from collections import deque
from dataclasses import FrozenInstanceError, replace
from itertools import count

import pytest

from tacticalgrid.algoritmos.heuristica_obstaculos import HeuristicaObstaculos
from tacticalgrid.escenario.escenario import Escenario, Posicion, UnidadInicial
from tacticalgrid.escenario.terreno import TipoTerreno
from tacticalgrid.juego.estado import EstadoJuego
from tacticalgrid.juego.problema import ProblemaNavegacion

VECINOS_ORACULO = ((0, 1), (1, 0), (0, -1), (-1, 0))


def _crear_escenario(
    terreno: tuple[tuple[str, ...], ...],
    costos: dict[str, int | float | None],
    inicio: Posicion = Posicion(0, 0),
) -> Escenario:
    """Construye un escenario minimo directamente desde datos controlados de prueba."""
    tipos = {
        nombre: TipoTerreno(costo=costo, transitable=costo is not None)
        for nombre, costo in costos.items()
    }
    return Escenario(
        version="prueba",
        filas=len(terreno),
        columnas=len(terreno[0]),
        tipos_terreno=tipos,
        terreno=terreno,
        bases={"A": inicio, "B": inicio},
        recurso=inicio,
        unidades_iniciales=(UnidadInicial("A1", "A", "estandar", inicio),),
        turno_inicial="A",
        portador_recurso_inicial=None,
        configuracion_juego={},
        configuracion_prueba=None,
    )


def _estado_en(
    problema: ProblemaNavegacion,
    posicion: Posicion,
    *,
    turno: str = "A",
    portador: str | None = None,
    posicion_recurso: Posicion | None = Posicion(0, 0),
) -> EstadoJuego:
    """Copia el estado inicial y ubica la unidad navegante en la posicion indicada."""
    unidades = tuple(
        replace(unidad, posicion=posicion)
        if unidad.identificador == problema.identificador_unidad
        else unidad
        for unidad in problema.estado_inicial.unidades
    )
    return EstadoJuego(
        unidades=unidades,
        turno_actual=turno,
        posicion_recurso=None if portador is not None else posicion_recurso,
        portador_recurso=portador,
    )


def _distancias_oraculo(
    terreno: tuple[tuple[str, ...], ...],
    costos: dict[str, int | float | None],
    objetivo: Posicion,
) -> dict[Posicion, int]:
    """Calcula distancias topologicas sin usar HTO ni funciones de movimiento del dominio.

    Purpose: servir como referencia independiente para comprobar la tabla producida por HTO.
    Preconditions: terreno es rectangular y objetivo identifica una celda de la matriz.
    Postconditions: devuelve las distancias minimas desde cada celda conectada y transitable hasta el objetivo.
    Complexity: O(V + E) temporal y O(V) espacial.
    AI usage: Yes.
    AI intervention: Codex implemento un BFS de prueba independiente con su propio orden y generacion de vecinos.
    Student validation: pendiente de revision humana del equipo.
    """
    filas, columnas = len(terreno), len(terreno[0])

    def transitable(posicion: Posicion) -> bool:
        return (
            0 <= posicion.fila < filas
            and 0 <= posicion.columna < columnas
            and costos[terreno[posicion.fila][posicion.columna]] is not None
        )

    if not transitable(objetivo):
        return {}
    distancias = {objetivo: 0}
    frontera = deque([objetivo])
    while frontera:
        actual = frontera.popleft()
        for delta_fila, delta_columna in VECINOS_ORACULO:
            vecina = Posicion(actual.fila + delta_fila, actual.columna + delta_columna)
            if transitable(vecina) and vecina not in distancias:
                distancias[vecina] = distancias[actual] + 1
                frontera.append(vecina)
    return distancias


def _costo_optimo_oraculo(
    terreno: tuple[tuple[str, ...], ...],
    costos: dict[str, int | float | None],
    origen: Posicion,
    objetivo: Posicion,
) -> int | float | None:
    """Calcula el costo secuencial minimo sin reutilizar transiciones ni costos del dominio.

    Purpose: comprobar admisibilidad de HTO frente a una referencia de Dijkstra independiente.
    Preconditions: terreno es rectangular; origen y objetivo son posiciones representables de la matriz.
    Postconditions: devuelve el menor costo float acumulado en orden de recorrido o None si no existe camino.
    Complexity: O((V + E) log V) temporal y O(V) espacial.
    AI usage: Yes.
    AI intervention: Codex implemento el oraculo con lectura directa de matriz, vecinos propios y costo del destino.
    Student validation: pendiente de revision humana del equipo.
    """
    filas, columnas = len(terreno), len(terreno[0])

    def costo_destino(posicion: Posicion) -> int | float | None:
        if not (0 <= posicion.fila < filas and 0 <= posicion.columna < columnas):
            return None
        return costos[terreno[posicion.fila][posicion.columna]]

    desempate = count()
    mejores: dict[Posicion, int | float] = {origen: 0}
    frontera: list[tuple[int | float, int, Posicion]] = [(0, next(desempate), origen)]
    while frontera:
        costo, _, actual = heapq.heappop(frontera)
        if costo != mejores[actual]:
            continue
        if actual == objetivo:
            return costo
        for delta_fila, delta_columna in VECINOS_ORACULO:
            vecina = Posicion(actual.fila + delta_fila, actual.columna + delta_columna)
            paso = costo_destino(vecina)
            if paso is None:
                continue
            nuevo_costo = costo + paso
            if vecina not in mejores or nuevo_costo < mejores[vecina]:
                mejores[vecina] = nuevo_costo
                heapq.heappush(frontera, (nuevo_costo, next(desempate), vecina))
    return None


def test_cuadricula_abierta_calcula_distancias_conocidas() -> None:
    terreno = (("libre",) * 3,) * 3
    problema = ProblemaNavegacion(_crear_escenario(terreno, {"libre": 1}), "A1", Posicion(2, 2))

    heuristica = HeuristicaObstaculos(problema)

    assert heuristica.distancias[Posicion(0, 0)] == 4
    assert heuristica.distancias[Posicion(1, 2)] == 1
    assert heuristica.evaluar(problema.estado_inicial) == 4


def test_corredor_y_objetivo_adyacente_conservan_distancias_unitarias() -> None:
    terreno = (("libre", "libre", "libre", "libre", "libre"),)
    problema = ProblemaNavegacion(_crear_escenario(terreno, {"libre": 2}), "A1", Posicion(0, 4))
    heuristica = HeuristicaObstaculos(problema)

    assert heuristica.distancias[Posicion(0, 0)] == 4
    assert heuristica.distancias[Posicion(0, 3)] == 1
    assert heuristica.evaluar(_estado_en(problema, Posicion(0, 3))) == 2


def test_barrera_obliga_a_rodear() -> None:
    terreno = (
        ("libre", "libre", "libre"),
        ("libre", "muro", "libre"),
        ("libre", "libre", "libre"),
    )
    problema = ProblemaNavegacion(
        _crear_escenario(terreno, {"libre": 1, "muro": None}, Posicion(1, 0)),
        "A1",
        Posicion(1, 2),
    )

    assert HeuristicaObstaculos(problema).distancias[Posicion(1, 0)] == 4


def test_objetivo_igual_a_posicion_inicial_devuelve_cero() -> None:
    escenario = _crear_escenario((("libre",),), {"libre": 1})
    problema = ProblemaNavegacion(escenario, "A1", Posicion(0, 0))

    assert HeuristicaObstaculos(problema).evaluar(problema.estado_inicial) == 0


def test_componente_desconectada_devuelve_cero() -> None:
    terreno = (("libre", "muro", "libre"),)
    problema = ProblemaNavegacion(
        _crear_escenario(terreno, {"libre": 1, "muro": None}),
        "A1",
        Posicion(0, 2),
    )
    heuristica = HeuristicaObstaculos(problema)

    assert Posicion(0, 0) not in heuristica.distancias
    assert heuristica.evaluar(problema.estado_inicial) == 0


def test_objetivo_no_transitable_prepara_heuristica_cero() -> None:
    terreno = (("libre", "muro"),)
    problema = ProblemaNavegacion(
        _crear_escenario(terreno, {"libre": 1, "muro": None}),
        "A1",
        Posicion(0, 1),
    )
    heuristica = HeuristicaObstaculos(problema)

    assert dict(heuristica.distancias) == {}
    assert heuristica.estimaciones == (0,)
    assert heuristica.evaluar(problema.estado_inicial) == 0
    assert heuristica.evaluar(_estado_en(problema, Posicion(0, 1))) == 0


def test_estados_compuestos_distintos_con_igual_posicion_comparten_estimacion() -> None:
    escenario = _crear_escenario((("libre", "libre"),), {"libre": 1})
    problema = ProblemaNavegacion(escenario, "A1", Posicion(0, 1))
    heuristica = HeuristicaObstaculos(problema)
    sin_recurso = _estado_en(problema, Posicion(0, 0), turno="A", posicion_recurso=Posicion(0, 1))
    con_recurso = _estado_en(problema, Posicion(0, 0), turno="B", portador="A1")

    assert sin_recurso != con_recurso
    assert heuristica.evaluar(sin_recurso) == heuristica.evaluar(con_recurso) == 1
    assert sin_recurso.turno_actual == "A"
    assert sin_recurso.portador_recurso is None


def test_posicion_inicial_no_transitable_devuelve_cero_y_puede_ingresar_al_grafo() -> None:
    terreno = (
        ("libre", "libre", "libre"),
        ("libre", "muro", "libre"),
    )
    escenario = _crear_escenario(terreno, {"libre": 1, "muro": None})
    estado_externo = _estado_en(
        ProblemaNavegacion(escenario, "A1", Posicion(0, 2)),
        Posicion(1, 1),
    )
    problema = ProblemaNavegacion(escenario, "A1", Posicion(0, 2), estado_externo)
    heuristica = HeuristicaObstaculos(problema)

    assert heuristica.evaluar(estado_externo) == 0
    acciones = problema.acciones(estado_externo)
    assert {accion.destino for accion in acciones} == {
        Posicion(0, 1),
        Posicion(1, 0),
        Posicion(1, 2),
    }
    for accion in acciones:
        sucesor = problema.resultado(estado_externo, accion)
        assert 0 <= problema.costo(estado_externo, accion) + heuristica.evaluar(sucesor)


def test_posicion_inicial_externa_adyacente_devuelve_cero_y_puede_ingresar() -> None:
    escenario = _crear_escenario((("libre", "libre"),), {"libre": 1})
    problema_base = ProblemaNavegacion(escenario, "A1", Posicion(0, 1))
    estado_externo = _estado_en(problema_base, Posicion(-1, 0))
    problema = ProblemaNavegacion(escenario, "A1", Posicion(0, 1), estado_externo)
    heuristica = HeuristicaObstaculos(problema)

    assert heuristica.evaluar(estado_externo) == 0
    assert tuple(accion.destino for accion in problema.acciones(estado_externo)) == (Posicion(0, 0),)


@pytest.mark.parametrize(("costo", "esperado"), [(2, 8), (0.5, 2.0)])
def test_recurrencia_con_costos_enteros_y_decimal_exacto(costo, esperado) -> None:
    terreno = (("libre", "libre", "libre", "libre", "libre"),)
    problema = ProblemaNavegacion(_crear_escenario(terreno, {"libre": costo}), "A1", Posicion(0, 4))
    heuristica = HeuristicaObstaculos(problema)

    assert heuristica.evaluar(problema.estado_inicial) == esperado


def test_recurrencia_con_una_decima_evitar_multiplicacion_directa() -> None:
    terreno = (("libre",) * 7,)
    problema = ProblemaNavegacion(_crear_escenario(terreno, {"libre": 0.1}), "A1", Posicion(0, 6))
    heuristica = HeuristicaObstaculos(problema)
    acumulado = 0.0
    for _ in range(6):
        acumulado += 0.1

    assert heuristica.evaluar(problema.estado_inicial) == acumulado
    assert heuristica.estimaciones[6] == acumulado == 0.6
    assert heuristica.estimaciones[6] < 6 * 0.1


def test_costos_heterogeneos_usan_el_minimo_del_problema() -> None:
    terreno = (("caro", "medio", "barato"),)
    costos = {"barato": 0.5, "medio": 3, "caro": 100}
    problema = ProblemaNavegacion(_crear_escenario(terreno, costos), "A1", Posicion(0, 2))

    assert HeuristicaObstaculos(problema).evaluar(problema.estado_inicial) == 1.0


def test_costo_minimo_de_terreno_no_usado_escala_la_estimacion() -> None:
    terreno = (("caro", "caro", "caro"),)
    costos = {"caro": 10, "barato_no_usado": 0.25}
    problema = ProblemaNavegacion(_crear_escenario(terreno, costos), "A1", Posicion(0, 2))

    assert HeuristicaObstaculos(problema).evaluar(problema.estado_inicial) == 0.5


def test_costos_de_magnitudes_diferentes_permanecen_finitos() -> None:
    terreno = (("enorme", "minimo", "enorme"),)
    costos = {"minimo": 1e-200, "enorme": 1e200}
    problema = ProblemaNavegacion(_crear_escenario(terreno, costos), "A1", Posicion(0, 2))

    assert HeuristicaObstaculos(problema).evaluar(problema.estado_inicial) == 2e-200


def test_recurrencia_admite_el_menor_subnormal_positivo() -> None:
    costo = float.fromhex("0x0.0000000000001p-1022")
    terreno = (("minimo",) * 6,)
    problema = ProblemaNavegacion(_crear_escenario(terreno, {"minimo": costo}), "A1", Posicion(0, 5))
    heuristica = HeuristicaObstaculos(problema)
    esperadas = [0.0]
    for _ in range(5):
        esperadas.append(esperadas[-1] + costo)

    assert heuristica.evaluar(problema.estado_inicial) == esperadas[-1]
    assert heuristica.estimaciones == tuple(esperadas)


def test_desbordamiento_requerido_conserva_el_prefijo_finito() -> None:
    terreno = (("enorme", "enorme", "enorme"),)
    problema = ProblemaNavegacion(_crear_escenario(terreno, {"enorme": 1e308}), "A1", Posicion(0, 2))
    heuristica = HeuristicaObstaculos(problema)

    assert heuristica.estimaciones == (0,)
    with pytest.raises(
        ValueError,
        match=r"recurrencia HTO.*solicitar H\(2\).*calcular H\(2\).*1e\+308",
    ):
        heuristica.evaluar(problema.estado_inicial)

    assert heuristica.estimaciones == (0, 1e308)
    assert heuristica.evaluar(_estado_en(problema, Posicion(0, 2))) == 0
    assert heuristica.evaluar(_estado_en(problema, Posicion(0, 1))) == 1e308
    with pytest.raises(ValueError, match=r"solicitar H\(2\).*calcular H\(2\)"):
        heuristica.evaluar(problema.estado_inicial)
    assert heuristica.estimaciones == (0, 1e308)


def test_costo_extremo_no_desborda_si_la_unidad_esta_en_el_objetivo() -> None:
    terreno = (("enorme", "enorme", "enorme"),)
    problema = ProblemaNavegacion(
        _crear_escenario(terreno, {"enorme": 1e308}, Posicion(0, 2)),
        "A1",
        Posicion(0, 2),
    )
    heuristica = HeuristicaObstaculos(problema)

    assert max(heuristica.distancias.values()) == 2
    assert heuristica.evaluar(problema.estado_inicial) == 0
    assert heuristica.estimaciones == (0,)


def test_costo_extremo_adyacente_prepara_solo_hasta_h_uno() -> None:
    terreno = (("enorme", "enorme", "enorme"),)
    problema = ProblemaNavegacion(
        _crear_escenario(terreno, {"enorme": 1e308}, Posicion(0, 1)),
        "A1",
        Posicion(0, 2),
    )
    heuristica = HeuristicaObstaculos(problema)

    assert max(heuristica.distancias.values()) == 2
    assert heuristica.evaluar(problema.estado_inicial) == 1e308
    assert heuristica.estimaciones == (0, 1e308)


def test_consulta_rechaza_un_valor_no_finito() -> None:
    escenario = _crear_escenario((("libre", "libre"),), {"libre": 1})
    problema = ProblemaNavegacion(escenario, "A1", Posicion(0, 1))
    heuristica = HeuristicaObstaculos(problema)
    heuristica._estimaciones = (0, float("inf"))

    with pytest.raises(ValueError, match="consulta HTO.*no finito"):
        heuristica.evaluar(problema.estado_inicial)


def test_objetivos_distintos_producen_tablas_distintas() -> None:
    escenario = _crear_escenario((("libre", "libre", "libre"),), {"libre": 1})
    izquierda = HeuristicaObstaculos(ProblemaNavegacion(escenario, "A1", Posicion(0, 0)))
    derecha = HeuristicaObstaculos(ProblemaNavegacion(escenario, "A1", Posicion(0, 2)))

    assert izquierda.distancias[Posicion(0, 0)] == 0
    assert derecha.distancias[Posicion(0, 0)] == 2


def test_topologias_distintas_producen_distancias_distintas() -> None:
    abierta = (("libre", "libre", "libre"), ("libre", "libre", "libre"))
    rodeo = (("libre", "muro", "libre"), ("libre", "libre", "libre"))
    costos = {"libre": 1, "muro": None}
    h_abierta = HeuristicaObstaculos(
        ProblemaNavegacion(_crear_escenario(abierta, costos), "A1", Posicion(0, 2))
    )
    h_rodeo = HeuristicaObstaculos(
        ProblemaNavegacion(_crear_escenario(rodeo, costos), "A1", Posicion(0, 2))
    )

    assert h_abierta.distancias[Posicion(0, 0)] == 2
    assert h_rodeo.distancias[Posicion(0, 0)] == 4


def test_misma_topologia_con_costos_distintos_reutiliza_la_misma_distancia_logica() -> None:
    terreno = (("libre", "libre", "libre"),)
    h_uno = HeuristicaObstaculos(
        ProblemaNavegacion(_crear_escenario(terreno, {"libre": 1}), "A1", Posicion(0, 2))
    )
    h_dos = HeuristicaObstaculos(
        ProblemaNavegacion(_crear_escenario(terreno, {"libre": 2}), "A1", Posicion(0, 2))
    )

    assert dict(h_uno.distancias) == dict(h_dos.distancias)
    h_uno.evaluar(h_uno.problema.estado_inicial)
    h_dos.evaluar(h_dos.problema.estado_inicial)
    assert h_uno.estimaciones != h_dos.estimaciones


def test_orden_de_consultas_conserva_exactamente_la_misma_recurrencia() -> None:
    terreno = (("libre",) * 9,)
    escenario = _crear_escenario(terreno, {"libre": 0.1})
    problema_ascendente = ProblemaNavegacion(escenario, "A1", Posicion(0, 8))
    problema_descendente = ProblemaNavegacion(escenario, "A1", Posicion(0, 8))
    problema_mixto = ProblemaNavegacion(escenario, "A1", Posicion(0, 8))
    ascendente = HeuristicaObstaculos(problema_ascendente)
    descendente = HeuristicaObstaculos(problema_descendente)
    mixta = HeuristicaObstaculos(problema_mixto)

    valores_ascendentes = tuple(
        ascendente.evaluar(_estado_en(problema_ascendente, Posicion(0, 8 - distancia)))
        for distancia in range(9)
    )
    descendente.evaluar(_estado_en(problema_descendente, Posicion(0, 0)))
    valores_descendentes = tuple(
        descendente.evaluar(_estado_en(problema_descendente, Posicion(0, 8 - distancia)))
        for distancia in reversed(range(9))
    )
    for distancia in (3, 1, 7, 2, 8, 4, 0, 6, 5):
        mixta.evaluar(_estado_en(problema_mixto, Posicion(0, 8 - distancia)))

    assert valores_descendentes == tuple(reversed(valores_ascendentes))
    assert ascendente.estimaciones == descendente.estimaciones == mixta.estimaciones
    prefijo = mixta.estimaciones
    assert mixta.evaluar(_estado_en(problema_mixto, Posicion(0, 5))) == prefijo[3]
    assert mixta.estimaciones == prefijo


def test_consultas_repetidas_no_vuelven_a_consultar_transitabilidad(monkeypatch) -> None:
    escenario = _crear_escenario((("libre", "libre", "libre"),), {"libre": 1})
    original = Escenario.es_transitable
    consultas = 0

    def contar(escenario_actual: Escenario, posicion: Posicion) -> bool:
        nonlocal consultas
        consultas += 1
        return original(escenario_actual, posicion)

    monkeypatch.setattr(Escenario, "es_transitable", contar)
    problema = ProblemaNavegacion(escenario, "A1", Posicion(0, 2))
    heuristica = HeuristicaObstaculos(problema)
    consultas_preparacion = consultas

    for _ in range(5):
        assert heuristica.evaluar(problema.estado_inicial) == 2
    assert consultas == consultas_preparacion


def test_cambio_de_objetivo_rechaza_la_tabla_que_sobreestimaba() -> None:
    escenario = _crear_escenario((("libre",) * 4,), {"libre": 1}, Posicion(0, 1))
    problema = ProblemaNavegacion(escenario, "A1", Posicion(0, 3))
    heuristica = HeuristicaObstaculos(problema)
    problema.objetivo = Posicion(0, 0)

    with pytest.raises(ValueError, match="contexto.*objetivo"):
        heuristica.evaluar(problema.estado_inicial)
    assert heuristica.estimaciones == (0,)


def test_reemplazo_de_escenario_rechaza_el_contexto_preparado() -> None:
    terreno = (("libre", "libre"),)
    problema = ProblemaNavegacion(_crear_escenario(terreno, {"libre": 1}), "A1", Posicion(0, 1))
    heuristica = HeuristicaObstaculos(problema)
    problema.escenario = _crear_escenario(terreno, {"libre": 2})

    with pytest.raises(ValueError, match="contexto.*escenario"):
        heuristica.evaluar(problema.estado_inicial)
    assert heuristica.estimaciones == (0,)


def test_cambio_de_unidad_navegante_rechaza_el_contexto_preparado() -> None:
    problema = ProblemaNavegacion(
        _crear_escenario((("libre", "libre"),), {"libre": 1}),
        "A1",
        Posicion(0, 1),
    )
    heuristica = HeuristicaObstaculos(problema)
    problema.identificador_unidad = "otra"

    with pytest.raises(ValueError, match="contexto.*identificador_unidad"):
        heuristica.evaluar(problema.estado_inicial)
    assert heuristica.estimaciones == (0,)


def test_cambio_de_costo_minimo_rechaza_el_contexto_preparado() -> None:
    problema = ProblemaNavegacion(
        _crear_escenario((("libre", "libre"),), {"libre": 1}),
        "A1",
        Posicion(0, 1),
    )
    heuristica = HeuristicaObstaculos(problema)
    problema._costo_minimo_paso = 0.5

    with pytest.raises(ValueError, match="contexto.*costo_minimo_paso"):
        heuristica.evaluar(problema.estado_inicial)
    assert heuristica.estimaciones == (0,)


def test_reemplazo_del_problema_rechaza_sin_extender_estimaciones() -> None:
    escenario = _crear_escenario((("libre",) * 3,), {"libre": 1})
    problema = ProblemaNavegacion(escenario, "A1", Posicion(0, 2))
    heuristica = HeuristicaObstaculos(problema)
    heuristica.problema = ProblemaNavegacion(escenario, "A1", Posicion(0, 2))

    with pytest.raises(ValueError, match="contexto.*problema"):
        heuristica.evaluar(problema.estado_inicial)
    assert heuristica.estimaciones == (0,)


def test_estructuras_internas_del_escenario_no_admiten_mutacion() -> None:
    escenario = _crear_escenario((("libre", "libre"),), {"libre": 1})

    with pytest.raises(FrozenInstanceError):
        escenario.filas = 2
    with pytest.raises(TypeError):
        escenario.terreno[0][0] = "otro"
    with pytest.raises(TypeError):
        escenario.tipos_terreno["libre"] = TipoTerreno(costo=2, transitable=True)
    with pytest.raises(FrozenInstanceError):
        escenario.tipos_terreno["libre"].costo = 2


def test_tabla_de_distancias_es_inmutable() -> None:
    escenario = _crear_escenario((("libre",),), {"libre": 1})
    heuristica = HeuristicaObstaculos(ProblemaNavegacion(escenario, "A1", Posicion(0, 0)))

    with pytest.raises(TypeError):
        heuristica.distancias[Posicion(0, 0)] = 4


def test_estimaciones_expuestas_no_permiten_corromper_el_prefijo() -> None:
    escenario = _crear_escenario((("libre", "libre"),), {"libre": 1})
    problema = ProblemaNavegacion(escenario, "A1", Posicion(0, 1))
    heuristica = HeuristicaObstaculos(problema)
    heuristica.evaluar(problema.estado_inicial)
    expuestas = heuristica.estimaciones

    with pytest.raises(TypeError):
        expuestas[1] = 99
    assert heuristica.estimaciones == (0, 1)


def test_propiedades_exhaustivas_en_mapas_de_tres_por_tres() -> None:
    """Compara HTO con oraculos independientes en las 256 topologias alrededor de un objetivo central."""
    objetivo = Posicion(1, 1)
    otras = tuple(
        Posicion(fila, columna)
        for fila in range(3)
        for columna in range(3)
        if Posicion(fila, columna) != objetivo
    )
    costos = {"barato": 0.1, "medio": 0.5, "caro": 3.0, "muro": None}
    nombres = ("barato", "medio", "caro")

    for mascara in range(1 << len(otras)):
        bloqueadas = {
            posicion
            for indice, posicion in enumerate(otras)
            if mascara & (1 << indice)
        }
        terreno = tuple(
            tuple(
                "muro"
                if Posicion(fila, columna) in bloqueadas
                else nombres[(fila * 3 + columna) % len(nombres)]
                for columna in range(3)
            )
            for fila in range(3)
        )
        escenario = _crear_escenario(terreno, costos, objetivo)
        problema = ProblemaNavegacion(escenario, "A1", objetivo)
        heuristica = HeuristicaObstaculos(problema)
        distancias = _distancias_oraculo(terreno, costos, objetivo)

        assert dict(heuristica.distancias) == distancias
        for fila in range(3):
            for columna in range(3):
                posicion = Posicion(fila, columna)
                if costos[terreno[fila][columna]] is None:
                    continue
                estado = _estado_en(problema, posicion)
                valor = heuristica.evaluar(estado)
                distancia = distancias.get(posicion)
                if distancia is None:
                    assert valor == 0
                    for delta_fila, delta_columna in VECINOS_ORACULO:
                        vecina = Posicion(fila + delta_fila, columna + delta_columna)
                        if not (0 <= vecina.fila < 3 and 0 <= vecina.columna < 3):
                            continue
                        costo_paso = costos[terreno[vecina.fila][vecina.columna]]
                        if costo_paso is None:
                            continue
                        valor_vecina = heuristica.evaluar(_estado_en(problema, vecina))
                        assert valor <= costo_paso + valor_vecina
                    continue

                costo_optimo = _costo_optimo_oraculo(terreno, costos, posicion, objetivo)
                assert costo_optimo is not None
                assert valor <= costo_optimo
                manhattan = abs(fila - objetivo.fila) + abs(columna - objetivo.columna)
                assert distancia >= manhattan
                manhattan_secuencial = 0.0
                for _ in range(manhattan):
                    manhattan_secuencial += 0.1
                assert valor >= manhattan_secuencial

                for delta_fila, delta_columna in VECINOS_ORACULO:
                    vecina = Posicion(fila + delta_fila, columna + delta_columna)
                    if not (0 <= vecina.fila < 3 and 0 <= vecina.columna < 3):
                        continue
                    costo_paso = costos[terreno[vecina.fila][vecina.columna]]
                    if costo_paso is None:
                        continue
                    valor_vecina = heuristica.evaluar(_estado_en(problema, vecina))
                    assert valor <= costo_paso + valor_vecina
