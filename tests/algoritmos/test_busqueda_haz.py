"""Pruebas de E7.1 para Beam Search con ancho k configurable."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from tacticalgrid.algoritmos import (
    ancho_haz_desde_prueba,
    busqueda_anchura,
    busqueda_costo_uniforme,
    busqueda_haz,
    validar_ancho_haz,
)
from tacticalgrid.escenario.cargador import cargar_escenario
from tacticalgrid.escenario.escenario import Escenario, Posicion
from tacticalgrid.juego.problema import ProblemaNavegacion

CARPETA_ESCENARIOS = Path(__file__).resolve().parents[2] / "escenarios"
ESCENARIOS_BUSQUEDA = (
    "ejemplo_enunciado.json",
    "ruta_corta_vs_economica.json",
    "obstaculo_rodeo.json",
    "campo_20x20.json",
)
ANCHOS_DEL_ENUNCIADO = (1, 2, 4, 8)


def _problema_desde_escenario(escenario: Escenario) -> ProblemaNavegacion:
    prueba = escenario.configuracion_prueba
    assert prueba is not None and prueba["modo"] == "busqueda"
    objetivo = Posicion(prueba["objetivo"]["fila"], prueba["objetivo"]["columna"])
    return ProblemaNavegacion(escenario, prueba["unidad_inicio"], objetivo)


def _problema(archivo: str) -> ProblemaNavegacion:
    return _problema_desde_escenario(cargar_escenario(CARPETA_ESCENARIOS / archivo))


def _validar_solucion(problema: ProblemaNavegacion, resultado) -> None:
    """Reproduce cada accion con las reglas del problema y recalcula el costo desde el JSON."""
    assert resultado.camino[0] == problema.posicion(problema.estado_inicial)
    assert resultado.camino[-1] == problema.objetivo
    assert resultado.longitud == len(resultado.acciones) == len(resultado.camino) - 1
    estado = problema.estado_inicial
    costo = 0
    for origen, destino, accion in zip(resultado.camino, resultado.camino[1:], resultado.acciones):
        assert accion in problema.acciones(estado)
        assert (accion.origen, accion.destino) == (origen, destino)
        costo += problema.costo(estado, accion)
        estado = problema.resultado(estado, accion)
    assert problema.es_objetivo(estado)
    assert resultado.costo == costo


@pytest.mark.parametrize("k", ANCHOS_DEL_ENUNCIADO)
@pytest.mark.parametrize("archivo", ESCENARIOS_BUSQUEDA)
def test_beam_search_con_k_del_enunciado_reporta_metricas_coherentes(archivo, k) -> None:
    problema = _problema(archivo)

    resultado = busqueda_haz(problema, k)

    assert resultado.algoritmo == f"BEAM_SEARCH_K{k}"
    assert 1 <= resultado.maximo_frontera <= k
    assert resultado.estados_generados >= 1
    assert resultado.estados_expandidos >= 0
    assert resultado.tiempo_segundos >= 0
    if resultado.exito:
        _validar_solucion(problema, resultado)
    else:
        assert resultado.camino == () and resultado.acciones == () and resultado.costo is None


# Resultados deterministas (exito, costo, longitud) para k = 1, 2, 4, 8. Muestran el efecto de restringir el haz:
# un k pequeno puede descartar el camino conveniente y aumentar k no siempre mejora el costo.
RESULTADOS_ESPERADOS = {
    "ejemplo_enunciado.json": {1: (True, 12, 6), 2: (True, 7, 6), 4: (True, 14, 4), 8: (True, 14, 4)},
    "ruta_corta_vs_economica.json": {1: (True, 12, 12), 2: (True, 12, 12), 4: (True, 50, 8), 8: (True, 50, 8)},
    "obstaculo_rodeo.json": {1: (True, 20, 19), 2: (False, None, 0), 4: (True, 16, 15), 8: (True, 16, 15)},
    "campo_20x20.json": {1: (False, None, 0), 2: (False, None, 0), 4: (True, 40, 34), 8: (True, 46, 36)},
}


@pytest.mark.parametrize("archivo", ESCENARIOS_BUSQUEDA)
def test_resultados_reproducibles_para_k_1_2_4_8(archivo) -> None:
    problema = _problema(archivo)

    obtenidos = {k: busqueda_haz(problema, k) for k in ANCHOS_DEL_ENUNCIADO}

    assert {k: (r.exito, r.costo, r.longitud) for k, r in obtenidos.items()} == RESULTADOS_ESPERADOS[archivo]


def test_un_haz_estrecho_descarta_la_solucion_y_uno_mas_ancho_la_encuentra() -> None:
    """En el mapa 20x20, k = 1 y k = 2 se quedan sin candidatos; k = 4 llega al recurso."""
    problema = _problema("campo_20x20.json")

    assert not busqueda_haz(problema, 1).exito
    assert not busqueda_haz(problema, 2).exito
    assert busqueda_haz(problema, 4).exito


def test_aumentar_k_no_siempre_reduce_el_costo() -> None:
    """Con k = 2 se encuentra la ruta economica (costo 12, igual a UCS); con k = 8 sobrevive la recta por pantano."""
    problema = _problema("ruta_corta_vs_economica.json")

    assert busqueda_haz(problema, 2).costo == busqueda_costo_uniforme(problema).costo == 12
    assert busqueda_haz(problema, 8).costo == 50


@pytest.mark.parametrize("archivo", ESCENARIOS_BUSQUEDA)
def test_sin_poda_beam_search_encuentra_la_longitud_de_bfs(archivo) -> None:
    problema = _problema(archivo)

    sin_poda = busqueda_haz(problema, 10_000)

    assert sin_poda.exito
    assert sin_poda.longitud == busqueda_anchura(problema).longitud
    _validar_solucion(problema, sin_poda)


def test_mismo_problema_y_mismo_k_dan_el_mismo_resultado() -> None:
    problema = _problema("campo_20x20.json")

    primera, segunda = busqueda_haz(problema, 4), busqueda_haz(problema, 4)

    assert (primera.camino, primera.costo, primera.estados_generados, primera.estados_expandidos) == (
        segunda.camino,
        segunda.costo,
        segunda.estados_generados,
        segunda.estados_expandidos,
    )


def test_objetivo_inalcanzable_termina_sin_solucion() -> None:
    # (1, 1) es muro en el ejemplo del enunciado.
    problema = ProblemaNavegacion(cargar_escenario(CARPETA_ESCENARIOS / "ejemplo_enunciado.json"), "A1", Posicion(1, 1))

    resultado = busqueda_haz(problema, 4)

    assert not resultado.exito
    assert resultado.costo is None and resultado.camino == ()
    assert resultado.maximo_frontera <= 4


def test_inicio_que_ya_es_objetivo_no_expande_nada() -> None:
    problema = ProblemaNavegacion(cargar_escenario(CARPETA_ESCENARIOS / "ejemplo_enunciado.json"), "A1", Posicion(0, 1))

    resultado = busqueda_haz(problema, 2)

    assert resultado.exito and resultado.camino == (Posicion(0, 1),)
    assert (resultado.costo, resultado.estados_expandidos, resultado.estados_generados) == (0, 0, 1)


def test_acepta_otra_heuristica_sin_modificar_el_algoritmo() -> None:
    """Con h = 0 el haz ordena solo por costo acumulado g; la solucion sigue siendo legal."""
    problema = _problema("ruta_corta_vs_economica.json")

    resultado = busqueda_haz(problema, 2, heuristica=lambda _problema, _estado: 0)

    assert resultado.exito
    _validar_solucion(problema, resultado)


def test_heuristica_no_finita_se_rechaza() -> None:
    problema = _problema("ejemplo_enunciado.json")

    with pytest.raises(ValueError, match="no finito"):
        busqueda_haz(problema, 2, heuristica=lambda _problema, _estado: float("inf"))


@pytest.mark.parametrize("k", [0, -1, True, 1.5, "2", None])
def test_k_invalido_se_rechaza_con_mensaje_claro(k) -> None:
    with pytest.raises(ValueError, match="ancho del haz k"):
        validar_ancho_haz(k)
    with pytest.raises(ValueError, match="ancho del haz k"):
        busqueda_haz(_problema("ejemplo_enunciado.json"), k)


def _escenario_con_prueba(tmp_path, archivo: str, cambios: dict[str, object]) -> Escenario:
    contenido = json.loads((CARPETA_ESCENARIOS / archivo).read_text(encoding="utf-8"))
    contenido["prueba"] = dict(contenido["prueba"], **cambios)
    ruta = tmp_path / archivo
    ruta.write_text(json.dumps(contenido), encoding="utf-8")
    return cargar_escenario(ruta)


def test_k_se_lee_del_campo_prueba_del_json(tmp_path) -> None:
    escenario = _escenario_con_prueba(tmp_path, "campo_20x20.json", {"k": 4})

    assert ancho_haz_desde_prueba(escenario.configuracion_prueba) == 4


def test_cambiar_k_en_el_json_cambia_el_resultado_sin_tocar_codigo(tmp_path) -> None:
    resultados = {}
    for k in (1, 4):
        escenario = _escenario_con_prueba(tmp_path, "campo_20x20.json", {"k": k})
        problema = _problema_desde_escenario(escenario)
        resultados[k] = busqueda_haz(problema, ancho_haz_desde_prueba(escenario.configuracion_prueba))

    assert not resultados[1].exito
    assert resultados[4].exito


def test_prueba_sin_k_devuelve_none() -> None:
    escenario = cargar_escenario(CARPETA_ESCENARIOS / "ejemplo_enunciado.json")

    assert ancho_haz_desde_prueba(escenario.configuracion_prueba) is None
    assert ancho_haz_desde_prueba(None) is None


def test_k_invalido_en_el_json_se_rechaza(tmp_path) -> None:
    escenario = _escenario_con_prueba(tmp_path, "campo_20x20.json", {"k": 0})

    with pytest.raises(ValueError, match="se recibio 0"):
        ancho_haz_desde_prueba(escenario.configuracion_prueba)


def _ejecutar_main(*argumentos: str) -> subprocess.CompletedProcess:
    raiz = Path(__file__).resolve().parents[2]
    return subprocess.run(
        [sys.executable, "-B", str(raiz / "main.py"), *argumentos],
        cwd=raiz,
        env=os.environ | {"PYTHONIOENCODING": "utf-8"},
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )


def test_consola_ejecuta_beam_con_varios_k() -> None:
    salida = _ejecutar_main("escenarios/campo_20x20.json", "--algoritmo", "beam", "--k", "1", "2", "4", "8")

    assert salida.returncode == 0, salida.stderr
    for k in ANCHOS_DEL_ENUNCIADO:
        assert f"BEAM SEARCH (K={k})" in salida.stdout
    assert "Costo acumulado: 40" in salida.stdout  # k = 4


def test_consola_usa_k_del_json_si_no_se_indica(tmp_path) -> None:
    contenido = json.loads((CARPETA_ESCENARIOS / "campo_20x20.json").read_text(encoding="utf-8"))
    contenido["prueba"]["k"] = 4
    ruta = tmp_path / "campo_con_k.json"
    ruta.write_text(json.dumps(contenido), encoding="utf-8")

    salida = _ejecutar_main(str(ruta), "--algoritmo", "beam")

    assert salida.returncode == 0, salida.stderr
    assert "BEAM SEARCH (K=4)" in salida.stdout


def test_consola_sin_k_explica_como_configurarlo() -> None:
    salida = _ejecutar_main("escenarios/campo_20x20.json", "--algoritmo", "beam")

    assert salida.returncode == 1
    assert "--k" in salida.stderr and "prueba.k" in salida.stderr


@pytest.mark.parametrize("k", ANCHOS_DEL_ENUNCIADO)
def test_observador_recibe_cada_nivel_sin_alterar_el_resultado(k) -> None:
    problema = _problema("campo_20x20.json")
    niveles = []

    observado = busqueda_haz(problema, k, observador=niveles.append)
    sin_observar = busqueda_haz(problema, k)

    assert (observado.exito, observado.camino, observado.costo, observado.estados_generados, observado.estados_expandidos) == (
        sin_observar.exito,
        sin_observar.camino,
        sin_observar.costo,
        sin_observar.estados_generados,
        sin_observar.estados_expandidos,
    )
    assert [nivel.nivel for nivel in niveles] == list(range(len(niveles)))
    assert niveles[0].conservados[0][1].estado == problema.estado_inicial
    assert all(len(nivel.conservados) <= k for nivel in niveles)
    # Los conservados entran al haz como generados; los descartados no cuentan.
    assert sum(len(nivel.conservados) for nivel in niveles) == observado.estados_generados
