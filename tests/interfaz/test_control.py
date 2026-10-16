"""Pruebas del estado transitorio de los controles graficos."""

from pathlib import Path

import pytest

from tacticalgrid.escenario import Posicion
from tacticalgrid.interfaz import control as modulo_control
from tacticalgrid.interfaz.control import ControlGrafico
from tacticalgrid.juego import crear_estado_inicial


RAIZ = Path(__file__).resolve().parents[2]
RUTA = RAIZ / "escenarios" / "ruta_corta_vs_economica.json"
OTRA_RUTA = RAIZ / "escenarios" / "campo_20x20.json"


def _control() -> ControlGrafico:
    return ControlGrafico.crear(RUTA, (RUTA, OTRA_RUTA))


def test_crea_controles_desde_datos_reales_sin_ejecutar_busqueda():
    control = _control()

    assert control.ruta_escenario == RUTA.resolve()
    assert control.unidad in control.unidades
    assert control.objetivo == Posicion(2, 8)
    assert control.algoritmo in ("bfs", "dfs", "ucs", "astar", "beam")
    assert control.resultado is None
    assert control.origen is not None
    assert control.estado_busqueda == "sin ejecutar"
    assert control.estado == crear_estado_inicial(control.escenario)


def test_carga_invalida_conserva_sesion_completa(tmp_path):
    control = _control()
    control.ejecutar()
    previo = (
        control.ruta_escenario,
        control.escenario,
        control.estado,
        control.algoritmo,
        control.unidad,
        control.objetivo,
        control.k,
        control.resultado,
    )
    invalido = tmp_path / "invalido.json"
    invalido.write_text("{}", encoding="utf-8")

    assert not control.cargar_ruta(invalido)
    assert previo == (
        control.ruta_escenario,
        control.escenario,
        control.estado,
        control.algoritmo,
        control.unidad,
        control.objetivo,
        control.k,
        control.resultado,
    )
    assert control.error


def test_carga_valida_sustituye_estado_camino_traza_y_selecciones():
    control = _control()
    control.ejecutar()
    assert control.resultado is not None

    assert control.cargar_ruta(OTRA_RUTA)

    assert control.ruta_escenario == OTRA_RUTA.resolve()
    assert control.resultado is None
    assert not control.exploracion_visible
    assert control.unidad in control.unidades
    assert control.estado == crear_estado_inicial(control.escenario)


@pytest.mark.parametrize("algoritmo", ["bfs", "dfs", "ucs", "astar", "beam"])
def test_ejecuta_cinco_algoritmos_sin_mutar_estado(algoritmo):
    control = _control()
    estado_inicial = control.estado
    control.algoritmo = algoritmo
    control.k = 4

    control.ejecutar()

    assert control.resultado is not None
    assert control.resultado.exito
    assert control.resultado.traza_expansiones is not None
    assert control.estado is estado_inicial
    assert control.estado == crear_estado_inicial(control.escenario)


def test_selecciones_invalidan_resultado_y_objetivo_rechaza_obstaculo():
    control = _control()
    control.ejecutar()
    control.exploracion_visible = True

    control.cambiar_algoritmo(1)
    assert control.resultado is None and not control.exploracion_visible
    control.seleccionar_objetivo(Posicion(1, 1))
    assert control.error
    assert control.objetivo == Posicion(2, 8)
    control.seleccionar_objetivo(Posicion(0, 1))
    assert control.objetivo == Posicion(0, 1)
    assert not control.error


def test_tecla_y_boton_pueden_compartir_unico_alternado_sin_recalcular():
    control = _control()
    control.ejecutar()
    resultado = control.resultado

    control.alternar_exploracion()
    assert control.exploracion_visible
    control.alternar_exploracion()
    assert not control.exploracion_visible
    assert control.resultado is resultado


def test_selectores_recorrren_algoritmos_unidades_escenarios_y_validan_k():
    control = _control()
    algoritmos = []
    for _ in range(5):
        algoritmos.append(control.algoritmo)
        control.cambiar_algoritmo(1)
    assert set(algoritmos) == {"bfs", "dfs", "ucs", "astar", "beam"}

    unidad_inicial = control.unidad
    control.cambiar_unidad(1)
    assert control.unidad in control.unidades
    if len(control.unidades) > 1:
        assert control.unidad != unidad_inicial

    control.algoritmo = "beam"
    control.k = 1
    control.cambiar_k(-1)
    assert control.k == 1
    ruta_inicial = control.ruta_escenario
    control.cambiar_escenario(1)
    assert control.ruta_escenario != ruta_inicial


@pytest.mark.parametrize(
    ("algoritmo", "texto", "criterio", "detalle"),
    [
        ("bfs", "menos movimientos", "menor cantidad", None),
        ("dfs", "Profundiza", "profundizar", None),
        ("ucs", "costo acumulado", "menor costo", None),
        ("astar", "estimacion", "heuristica", "Manhattan"),
        ("beam", "k opciones", "limitada", "k indica"),
    ],
)
def test_ayuda_contextual_corresponde_al_algoritmo(algoritmo, texto, criterio, detalle):
    control = _control()
    control.algoritmo = algoritmo

    ayuda = control.ayuda_algoritmo

    assert any(texto in linea for linea in ayuda.descripcion)
    assert criterio in ayuda.criterio
    assert (detalle is None and ayuda.detalle is None) or detalle in ayuda.detalle


def test_configuracion_invalida_no_ejecuta_y_elimina_resultado_anterior(monkeypatch):
    control = _control()
    control.ejecutar()
    assert control.resultado is not None
    control.objetivo = None
    llamadas = 0

    def contar(*argumentos, **opciones):
        nonlocal llamadas
        llamadas += 1

    monkeypatch.setattr(modulo_control, "preparar_busqueda", contar)

    control.ejecutar()

    assert llamadas == 0
    assert control.resultado is None
    assert control.estado_busqueda == "error de configuracion"
    assert "Seleccione primero" in control.mensaje


def test_bloqueo_reentrante_evitar_ejecuciones_simultaneas(monkeypatch):
    control = _control()
    control.ejecutando = True
    llamadas = 0

    def contar(*argumentos, **opciones):
        nonlocal llamadas
        llamadas += 1

    monkeypatch.setattr(modulo_control, "preparar_busqueda", contar)

    control.ejecutar()

    assert llamadas == 0
