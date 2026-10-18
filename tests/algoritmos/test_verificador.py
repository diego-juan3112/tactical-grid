"""Pruebas de E10.2: el verificador acepta las respuestas reales y detecta respuestas alteradas a proposito."""

import os
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import pytest

from tacticalgrid.algoritmos import (
    ORDENES,
    alfa_beta,
    busqueda_a_estrella,
    busqueda_anchura,
    busqueda_costo_uniforme,
    busqueda_haz,
    busqueda_profundidad,
    minimax,
)
from tacticalgrid.algoritmos.verificador import (
    errores_de_estado,
    verificar_busqueda,
    verificar_decision,
    verificar_partida,
)
from tacticalgrid.escenario.cargador import cargar_escenario
from tacticalgrid.escenario.escenario import Posicion
from tacticalgrid.juego.accion import INTERCEPTAR, Accion
from tacticalgrid.juego.estado import EstadoJuego, crear_estado_inicial
from tacticalgrid.juego.problema import ProblemaNavegacion
from tacticalgrid.juego.tacticas import AccionTactica
from tacticalgrid.juego.unidad import Unidad
from tacticalgrid.modos.partida_automatica import jugar_partida

RAIZ = Path(__file__).resolve().parents[2]
CARPETA_ESCENARIOS = RAIZ / "escenarios"
ESCENARIOS_BUSQUEDA = ("ejemplo_enunciado.json", "ruta_corta_vs_economica.json", "obstaculo_rodeo.json", "campo_20x20.json")


def _problema(archivo: str) -> ProblemaNavegacion:
    escenario = cargar_escenario(CARPETA_ESCENARIOS / archivo)
    prueba = escenario.configuracion_prueba
    return ProblemaNavegacion(
        escenario, prueba["unidad_inicio"], Posicion(prueba["objetivo"]["fila"], prueba["objetivo"]["columna"])
    )


def _fallidas(reporte) -> set[str]:
    return {c.nombre for c in reporte.fallidas}


# --- Busquedas: respuestas reales ----------------------------------------------------------------------------------

ALGORITMOS = {
    "BFS": busqueda_anchura,
    "DFS": busqueda_profundidad,
    "UCS": busqueda_costo_uniforme,
    "A*": busqueda_a_estrella,
    **{f"BEAM k={k}": (lambda problema, k=k: busqueda_haz(problema, k)) for k in (1, 2, 4, 8)},
}


@pytest.mark.parametrize("nombre", ALGORITMOS)
@pytest.mark.parametrize("archivo", ESCENARIOS_BUSQUEDA)
def test_respuestas_reales_de_busqueda_son_validas(archivo, nombre) -> None:
    problema = _problema(archivo)

    reporte = verificar_busqueda(problema, ALGORITMOS[nombre](problema))

    assert reporte.es_valido, reporte.fallidas


def test_reporte_de_busqueda_exitosa_tiene_todas_las_comprobaciones() -> None:
    problema = _problema("ruta_corta_vs_economica.json")

    reporte = verificar_busqueda(problema, busqueda_costo_uniforme(problema))

    assert [c.nombre for c in reporte.comprobaciones] == [
        "movimientos_validos",
        "sin_obstaculos",
        "camino_coherente",
        "costo_coincide",
        "estado_final_objetivo",
        "estados_validos",
        "metricas_coherentes",
    ]
    assert "costo 12" in reporte.comprobaciones[3].detalle


def test_fracaso_real_de_beam_search_es_coherente() -> None:
    """Con k = 1, Beam Search no llega al recurso en el mapa 20x20 (E7.2): es un fracaso legitimo, no un error."""
    problema = _problema("campo_20x20.json")

    reporte = verificar_busqueda(problema, busqueda_haz(problema, 1))

    assert reporte.es_valido
    assert [c.nombre for c in reporte.comprobaciones] == ["fracaso_coherente", "metricas_coherentes"]


# --- Busquedas: respuestas alteradas ------------------------------------------------------------------------------

@pytest.fixture
def ucs_ruta_corta():
    problema = _problema("ruta_corta_vs_economica.json")
    return problema, busqueda_costo_uniforme(problema)


def test_detecta_costo_falso(ucs_ruta_corta) -> None:
    problema, resultado = ucs_ruta_corta

    reporte = verificar_busqueda(problema, replace(resultado, costo=11))

    assert _fallidas(reporte) == {"costo_coincide"}
    assert "11" in reporte.fallidas[0].detalle and "12" in reporte.fallidas[0].detalle


def test_detecta_movimiento_en_diagonal(ucs_ruta_corta) -> None:
    problema, resultado = ucs_ruta_corta
    primera = resultado.acciones[0]
    diagonal = Accion(primera.identificador_unidad, primera.origen, Posicion(primera.origen.fila - 1, primera.origen.columna + 1))

    reporte = verificar_busqueda(problema, replace(resultado, acciones=(diagonal, *resultado.acciones[1:])))

    assert {"movimientos_validos", "costo_coincide", "estado_final_objetivo"} <= _fallidas(reporte)


def test_detecta_paso_por_un_muro(ucs_ruta_corta) -> None:
    """(1, 1) es muro en ruta_corta_vs_economica.json: un camino que lo atraviesa debe rechazarse."""
    problema, resultado = ucs_ruta_corta
    origen = Posicion(2, 1)
    reporte = verificar_busqueda(
        problema,
        replace(
            resultado,
            camino=(Posicion(2, 0), origen, Posicion(1, 1)),
            acciones=(Accion("A1", Posicion(2, 0), origen), Accion("A1", origen, Posicion(1, 1))),
        ),
    )

    assert {"sin_obstaculos", "movimientos_validos"} <= _fallidas(reporte)
    assert "(1, 1)" in next(c for c in reporte.fallidas if c.nombre == "sin_obstaculos").detalle


def test_detecta_camino_que_no_llega_al_objetivo(ucs_ruta_corta) -> None:
    problema, resultado = ucs_ruta_corta
    recortado = replace(
        resultado,
        camino=resultado.camino[:-1],
        acciones=resultado.acciones[:-1],
        costo=resultado.costo - 1,
    )

    assert _fallidas(verificar_busqueda(problema, recortado)) == {"estado_final_objetivo"}


def test_detecta_camino_que_no_coincide_con_las_acciones(ucs_ruta_corta) -> None:
    problema, resultado = ucs_ruta_corta
    camino = list(resultado.camino)
    camino[3] = Posicion(4, 4)

    assert "camino_coherente" in _fallidas(verificar_busqueda(problema, replace(resultado, camino=tuple(camino))))


def test_detecta_metricas_imposibles(ucs_ruta_corta) -> None:
    problema, resultado = ucs_ruta_corta

    reporte = verificar_busqueda(problema, replace(resultado, estados_expandidos=resultado.estados_generados + 1))

    assert _fallidas(reporte) == {"metricas_coherentes"}


def test_detecta_fracaso_incoherente(ucs_ruta_corta) -> None:
    problema, resultado = ucs_ruta_corta

    reporte = verificar_busqueda(problema, replace(resultado, exito=False))

    assert _fallidas(reporte) == {"fracaso_coherente"}


# --- Estados invalidos -------------------------------------------------------------------------------------------

@pytest.mark.parametrize(
    ("unidades", "portador", "recurso", "partida", "mensaje"),
    [
        ((("A1", "A", 1, 1),), None, Posicion(2, 2), "en_curso", "obstaculo"),
        ((("A1", "A", 9, 9),), None, Posicion(2, 2), "en_curso", "fuera del mapa"),
        ((("A1", "A", 0, 0), ("B1", "B", 0, 0)), None, Posicion(2, 2), "en_curso", "comparten la celda"),
        ((("A1", "A", 0, 0),), "Z9", None, "en_curso", "no es una unidad"),
        ((("A1", "A", 0, 0),), "A1", Posicion(2, 2), "en_curso", "a la vez una posicion"),
        ((("A1", "A", 0, 0),), None, None, "en_curso", "ni posicion"),
        ((("A1", "C", 0, 0),), None, Posicion(2, 2), "en_curso", "bando invalido"),
        ((("A1", "A", 0, 1),), "A1", None, "victoria_A", "no esta en la base"),
        ((("A1", "A", 0, 0),), None, Posicion(2, 2), "ganando", "desconocido"),
    ],
)
def test_detecta_cada_tipo_de_estado_invalido(unidades, portador, recurso, partida, mensaje) -> None:
    escenario = cargar_escenario(CARPETA_ESCENARIOS / "ejemplo_enunciado.json")  # (1, 1) es muro; base A en (0, 0)
    estado = EstadoJuego(
        unidades=tuple(Unidad(i, b, "estandar", Posicion(f, c)) for i, b, f, c in unidades),
        turno_actual="A",
        posicion_recurso=recurso,
        portador_recurso=portador,
        estado_partida=partida,
    )

    errores = errores_de_estado(escenario, estado)

    assert any(mensaje in error for error in errores), errores


def test_en_navegacion_dos_unidades_pueden_compartir_celda() -> None:
    """E1.2: en navegacion las demas unidades no bloquean, asi que compartir celda no es un error."""
    escenario = cargar_escenario(CARPETA_ESCENARIOS / "ejemplo_enunciado.json")
    estado = EstadoJuego(
        unidades=(Unidad("A1", "A", "estandar", Posicion(3, 2)), Unidad("B1", "B", "estandar", Posicion(3, 2))),
        turno_actual="A",
        posicion_recurso=Posicion(2, 2),
        portador_recurso=None,
    )

    assert errores_de_estado(escenario, estado, exigir_celdas_libres=False) == ()
    assert errores_de_estado(escenario, estado) != ()


# --- Decisiones adversariales -------------------------------------------------------------------------------------

@pytest.mark.parametrize("orden", ORDENES)
@pytest.mark.parametrize("decisor", [minimax, alfa_beta], ids=["minimax", "alfa_beta"])
@pytest.mark.parametrize("archivo", ["ejemplo_enunciado.json", "recurso_en_transporte.json"])
def test_decisiones_reales_son_validas(archivo, decisor, orden) -> None:
    escenario = cargar_escenario(CARPETA_ESCENARIOS / archivo)
    estado = crear_estado_inicial(escenario)

    for profundidad in (1, 2, 3):
        reporte = verificar_decision(escenario, estado, decisor(escenario, estado, profundidad, orden=orden))
        assert reporte.es_valido, (profundidad, reporte.fallidas)


def test_minimax_reporta_exactamente_el_arbol_regenerado() -> None:
    escenario = cargar_escenario(CARPETA_ESCENARIOS / "recurso_en_transporte.json")
    estado = crear_estado_inicial(escenario)

    resultado = minimax(escenario, estado, 2)
    reporte = verificar_decision(escenario, estado, resultado)

    assert reporte.es_valido
    # El arbol regenerado tiene tantos estados (raiz incluida) como nodos generados reporta Minimax: 80.
    assert resultado.nodos_generados == 80
    assert "80 estados del arbol" in next(c for c in reporte.comprobaciones if c.nombre == "estados_validos").detalle


@pytest.fixture
def decision_real():
    escenario = cargar_escenario(CARPETA_ESCENARIOS / "recurso_en_transporte.json")
    estado = crear_estado_inicial(escenario)
    return escenario, estado, minimax(escenario, estado, 2)


def test_detecta_accion_seleccionada_ilegal(decision_real) -> None:
    escenario, estado, resultado = decision_real
    ilegal = AccionTactica(Accion("A2", Posicion(3, 3), Posicion(2, 2)), "avanzar")  # (2, 2) es muro

    reporte = verificar_decision(escenario, estado, replace(resultado, accion_seleccionada=ilegal))

    assert {"accion_seleccionada_legal", "decision_optima"} <= _fallidas(reporte)


def test_detecta_intercepcion_inventada_en_la_raiz(decision_real) -> None:
    escenario, estado, resultado = decision_real
    falsa = AccionTactica(Accion("A1", Posicion(0, 2), Posicion(0, 3), INTERCEPTAR), "interceptar_portador")

    reporte = verificar_decision(escenario, estado, replace(resultado, valores_raiz=(*resultado.valores_raiz, (falsa, 0.0))))

    assert _fallidas(reporte) == {"valores_raiz_legales"}


def test_detecta_valor_falso(decision_real) -> None:
    escenario, estado, resultado = decision_real

    assert _fallidas(verificar_decision(escenario, estado, replace(resultado, valor=999.0))) == {"valor_correcto"}


def test_detecta_decision_que_no_es_la_optima(decision_real) -> None:
    escenario, estado, resultado = decision_real
    peor = min(resultado.valores_raiz, key=lambda par: par[1])

    reporte = verificar_decision(escenario, estado, replace(resultado, accion_seleccionada=peor[0], valor=peor[1]))

    assert {"decision_optima", "valor_correcto"} == _fallidas(reporte)


def test_detecta_metricas_de_minimax_que_no_corresponden_al_arbol(decision_real) -> None:
    escenario, estado, resultado = decision_real

    reporte = verificar_decision(escenario, estado, replace(resultado, nodos_generados=resultado.nodos_generados - 5))

    assert _fallidas(reporte) == {"metricas_coherentes"}


def test_detecta_alfa_beta_con_mas_nodos_que_el_arbol_completo() -> None:
    escenario = cargar_escenario(CARPETA_ESCENARIOS / "recurso_en_transporte.json")
    estado = crear_estado_inicial(escenario)
    resultado = alfa_beta(escenario, estado, 2)

    reporte = verificar_decision(escenario, estado, replace(resultado, nodos_generados=10_000))

    assert _fallidas(reporte) == {"metricas_coherentes"}


# --- Partidas -----------------------------------------------------------------------------------------------------

@pytest.fixture(scope="module")
def partida_real():
    escenario = cargar_escenario(CARPETA_ESCENARIOS / "recurso_en_transporte.json")
    return escenario, jugar_partida(escenario, crear_estado_inicial(escenario), 2, max_turnos=8)


def test_partida_real_es_valida(partida_real) -> None:
    escenario, partida = partida_real

    reporte = verificar_partida(escenario, partida)

    assert reporte.es_valido, reporte.fallidas
    assert [c.nombre for c in reporte.comprobaciones][-1] == "decisiones_verificadas"


def test_detecta_partida_con_jugada_manipulada(partida_real) -> None:
    escenario, partida = partida_real
    segundo = partida.turnos[1]
    manipulado = replace(segundo, estado_resultante=partida.turnos[0].estado_previo)

    reporte = verificar_partida(escenario, replace(partida, turnos=(partida.turnos[0], manipulado, *partida.turnos[2:])), verificar_arboles=False)

    assert "estados_encadenados" in _fallidas(reporte)


def test_detecta_resultado_declarado_falso(partida_real) -> None:
    escenario, partida = partida_real

    reporte = verificar_partida(escenario, replace(partida, resultado="victoria_A"), verificar_arboles=False)

    assert _fallidas(reporte) == {"resultado_coherente"}


# --- Consola -------------------------------------------------------------------------------------------------------

def _ejecutar_main(*argumentos: str):
    return subprocess.run(
        [sys.executable, "-B", str(RAIZ / "main.py"), *argumentos],
        cwd=RAIZ,
        env=os.environ | {"PYTHONIOENCODING": "utf-8"},
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )


@pytest.mark.parametrize(
    "argumentos",
    [
        ("escenarios/ruta_corta_vs_economica.json", "--algoritmo", "ambos"),
        ("escenarios/campo_20x20.json", "--algoritmo", "beam", "--k", "1", "4"),
        ("escenarios/recurso_en_transporte.json", "--modo", "adversarial", "--algoritmo", "minimax", "--profundidad", "2"),
        ("escenarios/recurso_en_transporte.json", "--modo", "adversarial", "--algoritmo", "minimax_alfa_beta", "--profundidad", "2"),
        ("escenarios/recurso_en_transporte.json", "--modo", "partida", "--profundidad", "1", "--turnos", "4"),
    ],
    ids=["busqueda", "beam", "minimax", "comparacion", "partida"],
)
def test_consola_verifica_cada_modo(argumentos) -> None:
    salida = _ejecutar_main(*argumentos, "--verificar")

    assert salida.returncode == 0, salida.stderr
    assert "VERIFICACIÓN" in salida.stdout
    assert "✗" not in salida.stdout
    assert "Resultado de la verificación: VÁLIDO" in salida.stdout


def test_consola_verifica_aunque_la_salida_no_admita_las_marcas() -> None:
    # En Windows, al redirigir la salida a un archivo o a una tuberia, Python escribe en cp1252, que no tiene ✓ ni ✗.
    salida = subprocess.run(
        [sys.executable, "-B", str(RAIZ / "main.py"), "escenarios/ruta_corta_vs_economica.json",
         "--algoritmo", "ucs", "--verificar"],
        cwd=RAIZ,
        env=os.environ | {"PYTHONIOENCODING": "cp1252"},
        capture_output=True,
        text=True,
        encoding="cp1252",
        check=False,
    )

    assert salida.returncode == 0, salida.stderr
    assert "[OK] movimientos_validos" in salida.stdout
    assert "Resultado de la verificación: VÁLIDO" in salida.stdout


def test_consola_sin_verificar_no_muestra_el_reporte() -> None:
    salida = _ejecutar_main("escenarios/ruta_corta_vs_economica.json", "--algoritmo", "ucs")

    assert salida.returncode == 0
    assert "VERIFICACIÓN" not in salida.stdout
