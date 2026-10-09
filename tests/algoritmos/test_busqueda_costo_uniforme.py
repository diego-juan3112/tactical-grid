"""Pruebas de E5.1 sobre escenarios reales y el contrato comun de busqueda."""

import json
from pathlib import Path

import pytest

from tacticalgrid.algoritmos import busqueda_anchura, busqueda_costo_uniforme
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
    assert resultado.costo == sum(problema.costo(problema.estado_inicial, accion) for accion in resultado.acciones)
    for origen, destino, accion in zip(resultado.camino, resultado.camino[1:], resultado.acciones):
        assert (accion.origen, accion.destino) == (origen, destino)
        assert abs(origen.fila - destino.fila) + abs(origen.columna - destino.columna) == 1
        assert problema.escenario.es_transitable(destino)


def test_inicio_igual_al_objetivo() -> None:
    problema = _problema("ruta_corta_vs_economica.json")
    problema = ProblemaNavegacion(problema.escenario, "A1", Posicion(2, 0))

    resultado = busqueda_costo_uniforme(problema)

    assert resultado.exito
    assert resultado.camino == (Posicion(2, 0),)
    assert resultado.acciones == ()
    assert (resultado.longitud, resultado.costo) == (0, 0)
    assert (resultado.estados_generados, resultado.estados_expandidos, resultado.maximo_frontera) == (1, 0, 1)


def test_ucs_prefiere_ruta_economica_y_bfs_la_ruta_corta() -> None:
    problema = _problema("ruta_corta_vs_economica.json")

    bfs = busqueda_anchura(problema)
    ucs = busqueda_costo_uniforme(problema)

    assert (bfs.longitud, bfs.costo) == (8, 50)
    assert (ucs.longitud, ucs.costo) == (12, 12)
    assert bfs.camino != ucs.camino
    _validar_solucion(problema, bfs)
    _validar_solucion(problema, ucs)


def test_cambiar_un_costo_del_json_cambia_la_ruta_de_ucs(tmp_path) -> None:
    contenido = json.loads((CARPETA_ESCENARIOS / "ruta_corta_vs_economica.json").read_text(encoding="utf-8"))
    contenido["tipos_terreno"]["pantano"]["costo"] = 1
    ruta = tmp_path / "pantano_barato.json"
    ruta.write_text(json.dumps(contenido), encoding="utf-8")
    escenario = cargar_escenario(ruta)
    problema = ProblemaNavegacion(escenario, "A1", Posicion(2, 8))

    resultado = busqueda_costo_uniforme(problema)

    assert (resultado.longitud, resultado.costo) == (8, 8)
    _validar_solucion(problema, resultado)


def test_ucs_rodea_obstaculos_con_costo_minimo() -> None:
    problema = _problema("obstaculo_rodeo.json")

    resultado = busqueda_costo_uniforme(problema)

    assert (resultado.longitud, resultado.costo) == (15, 16)
    _validar_solucion(problema, resultado)


def test_objetivo_inalcanzable_devuelve_fracaso_sin_modificar_estado() -> None:
    escenario = cargar_escenario(CARPETA_ESCENARIOS / "ejemplo_enunciado.json")
    problema = ProblemaNavegacion(escenario, "A1", Posicion(1, 1))
    estado_inicial = problema.estado_inicial

    resultado = busqueda_costo_uniforme(problema)

    assert not resultado.exito
    assert resultado.camino == resultado.acciones == ()
    assert resultado.costo is None
    assert resultado.estados_generados == resultado.estados_expandidos > 0
    assert resultado.maximo_frontera > 0
    assert problema.estado_inicial is estado_inicial


class ProblemaConMejora:
    """Grafo pequeno que fuerza una mejora antes de extraer una entrada obsoleta."""

    def __init__(self) -> None:
        posiciones = {
            "inicio": Posicion(0, 0),
            "caro": Posicion(0, 1),
            "barato": Posicion(1, 0),
            "convergencia": Posicion(1, 1),
            "objetivo": Posicion(2, 1),
        }
        self.estados = {
            nombre: EstadoJuego((Unidad("A1", "A", "estandar", posicion),), "A", None, None)
            for nombre, posicion in posiciones.items()
        }
        self.estado_inicial = self.estados["inicio"]
        self._por_posicion = {posicion: self.estados[nombre] for nombre, posicion in posiciones.items()}
        self._costos = {
            (posiciones["inicio"], posiciones["caro"]): 1,
            (posiciones["inicio"], posiciones["barato"]): 5,
            (posiciones["caro"], posiciones["convergencia"]): 10,
            (posiciones["barato"], posiciones["convergencia"]): 1,
            (posiciones["convergencia"], posiciones["objetivo"]): 100,
        }

    def acciones(self, estado: EstadoJuego) -> tuple[Accion, ...]:
        origen = self.posicion(estado)
        return tuple(Accion("A1", origen, destino) for (actual, destino) in self._costos if actual == origen)

    def resultado(self, estado: EstadoJuego, accion: Accion) -> EstadoJuego:
        return self._por_posicion[accion.destino]

    def es_objetivo(self, estado: EstadoJuego) -> bool:
        return estado == self.estados["objetivo"]

    def costo(self, estado: EstadoJuego, accion: Accion) -> int | float:
        return self._costos[(self.posicion(estado), accion.destino)]

    def posicion(self, estado: EstadoJuego) -> Posicion:
        return estado.unidades[0].posicion


def test_estado_repetido_admite_mejora_y_descarta_entrada_obsoleta() -> None:
    problema = ProblemaConMejora()

    resultado = busqueda_costo_uniforme(problema)

    assert resultado.camino == (Posicion(0, 0), Posicion(1, 0), Posicion(1, 1), Posicion(2, 1))
    assert (resultado.costo, resultado.longitud) == (106, 3)
    assert (resultado.estados_generados, resultado.estados_expandidos, resultado.maximo_frontera) == (6, 4, 2)


@pytest.mark.parametrize("archivo", ["ruta_corta_vs_economica.json", "campo_20x20.json"])
def test_ucs_es_determinista_en_dimensiones_distintas_y_serializable(archivo) -> None:
    problema = _problema(archivo)

    primero = busqueda_costo_uniforme(problema)
    segundo = busqueda_costo_uniforme(problema)
    campos_deterministas = lambda resultado: (
        resultado.exito,
        resultado.camino,
        resultado.acciones,
        resultado.costo,
        resultado.longitud,
        resultado.estados_generados,
        resultado.estados_expandidos,
        resultado.maximo_frontera,
    )

    assert campos_deterministas(primero) == campos_deterministas(segundo)
    assert json.loads(json.dumps(primero.a_diccionario()))["algoritmo"] == "UCS"
    _validar_solucion(problema, primero)


def test_ucs_admite_costos_decimales_positivos(tmp_path) -> None:
    contenido = json.loads((CARPETA_ESCENARIOS / "ruta_corta_vs_economica.json").read_text(encoding="utf-8"))
    contenido["tipos_terreno"]["pantano"]["costo"] = 0.5
    ruta = tmp_path / "costos_decimales.json"
    ruta.write_text(json.dumps(contenido), encoding="utf-8")
    problema = ProblemaNavegacion(cargar_escenario(ruta), "A1", Posicion(2, 8))

    resultado = busqueda_costo_uniforme(problema)

    assert resultado.longitud == 8
    assert resultado.costo == pytest.approx(4.5)
    _validar_solucion(problema, resultado)
