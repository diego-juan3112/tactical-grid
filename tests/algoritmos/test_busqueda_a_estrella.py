"""Pruebas de E6.1 para A* con heuristica Manhattan escalada."""

import json
from pathlib import Path

import pytest

from tacticalgrid.algoritmos import busqueda_a_estrella, busqueda_costo_uniforme, heuristica_manhattan
from tacticalgrid.escenario.cargador import cargar_escenario
from tacticalgrid.escenario.escenario import Posicion
from tacticalgrid.juego.accion import Accion
from tacticalgrid.juego.estado import EstadoJuego
from tacticalgrid.juego.problema import ProblemaNavegacion
from tacticalgrid.juego.unidad import Unidad

CARPETA_ESCENARIOS = Path(__file__).resolve().parents[2] / "escenarios"


def _problema(archivo: str) -> ProblemaNavegacion:
    escenario = cargar_escenario(CARPETA_ESCENARIOS / archivo)
    prueba = escenario.configuracion_prueba
    assert prueba is not None and prueba["modo"] == "busqueda"
    objetivo = Posicion(prueba["objetivo"]["fila"], prueba["objetivo"]["columna"])
    return ProblemaNavegacion(escenario, prueba["unidad_inicio"], objetivo)


def _validar_solucion(problema: ProblemaNavegacion, resultado) -> None:
    assert resultado.exito
    assert resultado.camino[0] == problema.posicion(problema.estado_inicial)
    assert resultado.camino[-1] == problema.objetivo
    assert resultado.longitud == len(resultado.acciones) == len(resultado.camino) - 1
    estado = problema.estado_inicial
    costo = 0
    for origen, destino, accion in zip(resultado.camino, resultado.camino[1:], resultado.acciones):
        assert accion in problema.acciones(estado)
        assert (accion.origen, accion.destino) == (origen, destino)
        assert abs(origen.fila - destino.fila) + abs(origen.columna - destino.columna) == 1
        assert problema.escenario.es_transitable(destino)
        costo += problema.costo(estado, accion)
        estado = problema.resultado(estado, accion)
    assert problema.es_objetivo(estado)
    assert resultado.costo == costo


def _estado(
    posicion: Posicion, portador: str | None = None, posicion_recurso: Posicion | None = Posicion(9, 9)
) -> EstadoJuego:
    return EstadoJuego(
        unidades=(Unidad("A1", "A", "estandar", posicion),),
        turno_actual="A",
        posicion_recurso=None if portador is not None else posicion_recurso,
        portador_recurso=portador,
    )


class ProblemaGrafoOrtogonal:
    """Grafo determinista de prueba cuyas aristas representan pasos ortogonales."""

    def __init__(
        self,
        estado_inicial: EstadoJuego,
        estado_objetivo: EstadoJuego,
        transiciones: dict[EstadoJuego, tuple[tuple[EstadoJuego, int | float], ...]],
        costo_minimo_paso: int | float = 1,
    ) -> None:
        self.estado_inicial = estado_inicial
        self.estado_objetivo = estado_objetivo
        self.objetivo = self.posicion(estado_objetivo)
        self.costo_minimo_paso = costo_minimo_paso
        self.transiciones = transiciones
        self.expandidos: list[EstadoJuego] = []

    def acciones(self, estado: EstadoJuego) -> tuple[Accion, ...]:
        self.expandidos.append(estado)
        origen = self.posicion(estado)
        return tuple(Accion("A1", origen, self.posicion(destino)) for destino, _ in self.transiciones.get(estado, ()))

    def resultado(self, estado: EstadoJuego, accion: Accion) -> EstadoJuego:
        return next(destino for destino, _ in self.transiciones[estado] if self.posicion(destino) == accion.destino)

    def es_objetivo(self, estado: EstadoJuego) -> bool:
        return estado == self.estado_objetivo

    def costo(self, estado: EstadoJuego, accion: Accion) -> int | float:
        return next(costo for destino, costo in self.transiciones[estado] if self.posicion(destino) == accion.destino)

    def posicion(self, estado: EstadoJuego) -> Posicion:
        return estado.unidades[0].posicion


def test_heuristica_manhattan_calcula_distancia_escalada() -> None:
    problema = _problema("ruta_corta_vs_economica.json")

    assert heuristica_manhattan(problema, problema.estado_inicial) == 8


def test_heuristica_manhattan_es_cero_en_el_objetivo() -> None:
    problema = _problema("ruta_corta_vs_economica.json")
    estado = problema.estado_inicial
    for columna in range(1, 9):
        estado = problema.resultado(estado, Accion("A1", problema.posicion(estado), Posicion(2, columna)))

    assert problema.es_objetivo(estado)
    assert heuristica_manhattan(problema, estado) == 0


def test_heuristica_manhattan_escala_con_costo_minimo_decimal(tmp_path) -> None:
    contenido = json.loads((CARPETA_ESCENARIOS / "ruta_corta_vs_economica.json").read_text(encoding="utf-8"))
    contenido["tipos_terreno"]["pantano"]["costo"] = 0.5
    ruta = tmp_path / "costo_minimo_decimal.json"
    ruta.write_text(json.dumps(contenido), encoding="utf-8")
    problema = ProblemaNavegacion(cargar_escenario(ruta), "A1", Posicion(2, 8))

    assert problema.costo_minimo_paso == 0.5
    assert heuristica_manhattan(problema, problema.estado_inicial) == 4
    assert busqueda_a_estrella(problema).costo == busqueda_costo_uniforme(problema).costo == 4.5


def test_prioridad_aplica_f_igual_a_g_mas_h() -> None:
    inicio = _estado(Posicion(1, 0))
    barato_lejano = _estado(Posicion(0, 0))
    cercano = _estado(Posicion(1, 1))
    casi_objetivo = _estado(Posicion(1, 2))
    objetivo = _estado(Posicion(1, 3))
    problema = ProblemaGrafoOrtogonal(
        inicio,
        objetivo,
        {
            inicio: ((barato_lejano, 4), (cercano, 5)),
            cercano: ((casi_objetivo, 1),),
            casi_objetivo: ((objetivo, 1),),
        },
    )

    resultado = busqueda_a_estrella(problema)

    assert problema.expandidos == [inicio, cercano, casi_objetivo]
    assert (resultado.costo, resultado.estados_generados, resultado.estados_expandidos) == (7, 5, 3)


@pytest.mark.parametrize("algoritmo", [busqueda_a_estrella, busqueda_costo_uniforme], ids=["a_estrella", "ucs"])
def test_costo_finito_grande_representable_conserva_la_solucion(algoritmo) -> None:
    inicio = _estado(Posicion(0, 0))
    objetivo = _estado(Posicion(0, 1))
    problema = ProblemaGrafoOrtogonal(
        inicio,
        objetivo,
        {inicio: ((objetivo, 1e307),)},
        costo_minimo_paso=1e307,
    )

    resultado = algoritmo(problema)

    assert resultado.exito
    assert (resultado.costo, resultado.longitud) == (1e307, 1)


@pytest.mark.parametrize("algoritmo", [busqueda_a_estrella, busqueda_costo_uniforme], ids=["a_estrella", "ucs"])
def test_acumulacion_de_costos_finitos_que_desborda_falla_de_forma_controlada(algoritmo) -> None:
    inicio = _estado(Posicion(0, 0))
    intermedio = _estado(Posicion(0, 1))
    objetivo = _estado(Posicion(0, 2))
    problema = ProblemaGrafoOrtogonal(
        inicio,
        objetivo,
        {
            inicio: ((intermedio, 1e308),),
            intermedio: ((objetivo, 1e308),),
        },
    )

    with pytest.raises(ValueError, match="costo acumulado.*rango numerico finito"):
        algoritmo(problema)


def test_producto_manhattan_por_costo_minimo_que_desborda_falla_de_forma_controlada() -> None:
    inicio = _estado(Posicion(0, 0))
    objetivo = _estado(Posicion(0, 2))
    problema = ProblemaGrafoOrtogonal(inicio, objetivo, {}, costo_minimo_paso=1e308)

    with pytest.raises(ValueError, match="heuristica Manhattan.*rango numerico finito"):
        heuristica_manhattan(problema, inicio)


def test_suma_de_g_y_h_finitos_que_desborda_no_se_inserta_en_la_frontera() -> None:
    inicio = _estado(Posicion(0, 0))
    intermedio = _estado(Posicion(0, 1))
    objetivo = _estado(Posicion(0, 2))
    problema = ProblemaGrafoOrtogonal(
        inicio,
        objetivo,
        {inicio: ((intermedio, 1e308),)},
        costo_minimo_paso=8e307,
    )

    with pytest.raises(ValueError, match=r"prioridad f\(n\).*rango numerico finito"):
        busqueda_a_estrella(problema)


def test_inicio_igual_al_objetivo_reporta_raiz_sin_expandir() -> None:
    problema_base = _problema("ruta_corta_vs_economica.json")
    problema = ProblemaNavegacion(problema_base.escenario, "A1", Posicion(2, 0))

    resultado = busqueda_a_estrella(problema)

    assert resultado.algoritmo == "A_ESTRELLA"
    assert resultado.camino == (Posicion(2, 0),)
    assert resultado.acciones == ()
    assert (resultado.longitud, resultado.costo) == (0, 0)
    assert (resultado.estados_generados, resultado.estados_expandidos, resultado.maximo_frontera) == (1, 0, 1)


def test_mejora_estricta_reinserta_y_la_entrada_obsoleta_no_se_expande() -> None:
    inicio = _estado(Posicion(0, 0))
    rama_cara = _estado(Posicion(0, 1))
    rama_barata = _estado(Posicion(1, 0))
    convergencia = _estado(Posicion(1, 1))
    objetivo = _estado(Posicion(2, 1))
    problema = ProblemaGrafoOrtogonal(
        inicio,
        objetivo,
        {
            inicio: ((rama_cara, 1), (rama_barata, 5)),
            rama_cara: ((convergencia, 10),),
            rama_barata: ((convergencia, 1),),
            convergencia: ((objetivo, 100),),
        },
    )

    resultado = busqueda_a_estrella(problema)

    assert resultado.camino == (Posicion(0, 0), Posicion(1, 0), Posicion(1, 1), Posicion(2, 1))
    assert (resultado.costo, resultado.longitud) == (106, 3)
    assert (resultado.estados_generados, resultado.estados_expandidos, resultado.maximo_frontera) == (6, 4, 2)
    assert problema.expandidos.count(convergencia) == 1


def test_mejores_costos_conservan_la_identidad_del_estado_compuesto() -> None:
    inicio = _estado(Posicion(0, 0), posicion_recurso=Posicion(0, 1))
    con_recurso = _estado(Posicion(0, 1), portador="A1")
    regreso_misma_posicion = _estado(Posicion(0, 0), portador="A1")
    objetivo = _estado(Posicion(1, 0), portador="A1")
    problema = ProblemaGrafoOrtogonal(
        inicio,
        objetivo,
        {
            inicio: ((con_recurso, 1),),
            con_recurso: ((regreso_misma_posicion, 1),),
            regreso_misma_posicion: ((objetivo, 1),),
        },
    )

    resultado = busqueda_a_estrella(problema)

    assert inicio != regreso_misma_posicion
    assert problema.posicion(inicio) == problema.posicion(regreso_misma_posicion)
    assert resultado.camino == (Posicion(0, 0), Posicion(0, 1), Posicion(0, 0), Posicion(1, 0))
    assert resultado.costo == 3


def test_meta_transitable_inalcanzable_devuelve_fracaso(tmp_path, contenido_escenario_valido) -> None:
    contenido_escenario_valido["terreno"][1][1] = "muro"
    contenido_escenario_valido["recurso"] = {"fila": 0, "columna": 2}
    ruta = tmp_path / "meta_transitable_aislada.json"
    ruta.write_text(json.dumps(contenido_escenario_valido), encoding="utf-8")
    escenario = cargar_escenario(ruta)
    objetivo = Posicion(0, 2)
    assert escenario.es_transitable(objetivo)
    problema = ProblemaNavegacion(escenario, "A1", objetivo)

    resultado = busqueda_a_estrella(problema)

    assert not resultado.exito
    assert resultado.camino == resultado.acciones == ()
    assert resultado.costo is None
    assert (resultado.estados_generados, resultado.estados_expandidos, resultado.maximo_frontera) == (2, 2, 1)
    with pytest.raises(ValueError):
        ProblemaNavegacion(escenario, "A1", Posicion(0, 3))


@pytest.mark.parametrize(
    ("archivo", "costo_esperado", "longitud_esperada"),
    [
        ("ruta_corta_vs_economica.json", 12, 12),
        ("obstaculo_rodeo.json", 16, 15),
        ("campo_20x20.json", 34, 34),
    ],
)
def test_a_estrella_iguala_el_costo_optimo_de_ucs(archivo, costo_esperado, longitud_esperada) -> None:
    problema = _problema(archivo)

    a_estrella = busqueda_a_estrella(problema)
    ucs = busqueda_costo_uniforme(problema)

    assert a_estrella.costo == ucs.costo == costo_esperado
    assert a_estrella.longitud == longitud_esperada
    _validar_solucion(problema, a_estrella)
