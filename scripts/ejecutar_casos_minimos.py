"""Ejecuta y archiva los diez experimentos académicos contra la implementación actual."""

import hashlib
import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from tacticalgrid.algoritmos import (
    alfa_beta,
    busqueda_a_estrella,
    busqueda_anchura,
    busqueda_costo_uniforme,
    busqueda_haz,
    busqueda_profundidad,
    comparar_minimax_alfa_beta,
    minimax,
)
from tacticalgrid.algoritmos.heuristica_obstaculos import HeuristicaObstaculos
from tacticalgrid.algoritmos.utilidad import EvaluadorUtilidad
from tacticalgrid.algoritmos.verificador import verificar_busqueda, verificar_decision
from tacticalgrid.escenario import Posicion, cargar_escenario
from tacticalgrid.juego import ProblemaNavegacion, crear_estado_inicial
from tacticalgrid.juego.partida_manual import huella_estado

CARPETA_ESCENARIOS = RAIZ / "escenarios"
DESTINO = RAIZ / "docs" / "experimentos" / "resultados-casos-minimos.json"


def _escenario(nombre: str):
    ruta = CARPETA_ESCENARIOS / nombre
    return ruta, cargar_escenario(ruta)


def _problema(escenario, unidad: str | None = None, objetivo: Posicion | None = None):
    prueba = escenario.configuracion_prueba or {}
    unidad = unidad or prueba.get("unidad_inicio")
    if objetivo is None:
        destino = prueba.get("objetivo")
        objetivo = Posicion(destino["fila"], destino["columna"])
    return ProblemaNavegacion(escenario, unidad, objetivo)


def _verificacion(reporte) -> dict[str, object]:
    return {
        "valido": reporte.es_valido,
        "sujeto": reporte.sujeto,
        "comprobaciones": [
            {"nombre": item.nombre, "correcta": item.correcta, "detalle": item.detalle}
            for item in reporte.comprobaciones
        ],
    }


def _busqueda(nombre: str, archivo: str, algoritmo: str, problema=None, **parametros):
    ruta, escenario = _escenario(archivo)
    problema = problema or _problema(escenario)
    if algoritmo == "bfs":
        resultado = busqueda_anchura(problema)
    elif algoritmo == "dfs":
        resultado = busqueda_profundidad(problema)
    elif algoritmo == "ucs":
        resultado = busqueda_costo_uniforme(problema)
    elif algoritmo == "astar_manhattan":
        resultado = busqueda_a_estrella(problema)
    elif algoritmo == "astar_hto":
        resultado = busqueda_a_estrella(problema, heuristica_preparada=HeuristicaObstaculos(problema))
    elif algoritmo == "beam":
        resultado = busqueda_haz(problema, parametros["k"])
    else:
        raise ValueError(algoritmo)
    reporte = verificar_busqueda(problema, resultado)
    return {
        "archivo": ruta.relative_to(RAIZ).as_posix(),
        "sha256": hashlib.sha256(ruta.read_bytes()).hexdigest(),
        "algoritmo": algoritmo,
        "parametros": parametros,
        "resultado": resultado.a_diccionario(),
        "verificacion": _verificacion(reporte),
    }


def _decision(nombre: str, archivo: str, algoritmo: str, profundidad: int, orden: str = "generacion"):
    ruta, escenario = _escenario(archivo)
    estado = crear_estado_inicial(escenario)
    if algoritmo == "minimax":
        resultado = minimax(escenario, estado, profundidad, orden=orden)
    else:
        resultado = alfa_beta(escenario, estado, profundidad, orden=orden)
    reporte = verificar_decision(escenario, estado, resultado)
    return {
        "archivo": ruta.relative_to(RAIZ).as_posix(),
        "sha256": hashlib.sha256(ruta.read_bytes()).hexdigest(),
        "dimensiones": [escenario.filas, escenario.columnas],
        "algoritmo": algoritmo,
        "parametros": {"profundidad": profundidad, "orden_acciones": orden},
        "resultado": resultado.a_diccionario(),
        "verificacion": _verificacion(reporte),
    }


def ejecutar_experimentos() -> dict[str, object]:
    """Ejecuta algoritmos reales y verifica los resultados de cada caso mínimo del PDF.

    Proposito: producir evidencia reproducible de rutas, costos, métricas y decisiones de los diez casos.
    Precondiciones: los escenarios indicados en ``docs/casos-minimos`` cargan y las dependencias están instaladas.
    Postcondiciones: devuelve diez registros con hashes, parámetros, resultados y reportes independientes.
    Complejidad: domina Minimax en las profundidades configuradas; memoria acotada por los árboles explorados.
    Uso de IA: Si.
    Intervencion de IA: Codex escribió este ejecutor de experimentos a petición del usuario.
    Validacion del estudiante: no puedo confirmar ejecución o revisión por el equipo; los verificadores del proyecto
    validan cada ruta y decisión y este script comprueba además las propiedades esperadas de los casos.
    """
    casos: dict[str, object] = {}
    casos["01_bfs_vs_dfs"] = {
        "ejecuciones": [
            _busqueda("01", "campo_20x20.json", "bfs"),
            _busqueda("01", "campo_20x20.json", "dfs"),
        ]
    }
    casos["02_ruta_corta_vs_economica"] = {
        "ejecuciones": [
            _busqueda("02", "ruta_corta_vs_economica.json", "bfs"),
            _busqueda("02", "ruta_corta_vs_economica.json", "ucs"),
        ]
    }
    casos["03_obstaculo"] = {
        "ejecuciones": [_busqueda("03", "obstaculo_rodeo.json", "astar_manhattan"),
                        _busqueda("03", "obstaculo_rodeo.json", "ucs")]
    }
    casos["04_heuristicas"] = {
        "ejecuciones": [_busqueda("04", "obstaculo_rodeo.json", "astar_manhattan"),
                        _busqueda("04", "obstaculo_rodeo.json", "astar_hto"),
                        _busqueda("04", "obstaculo_rodeo.json", "ucs")]
    }
    casos["05_beam"] = {
        "ejecuciones": [_busqueda("05", "campo_20x20.json", "beam", k=k) for k in (1, 2, 4, 8)]
    }
    pares = []
    for archivo in ("estado_compuesto_libre.json", "estado_compuesto_portador.json"):
        ruta, escenario = _escenario(archivo)
        estado = crear_estado_inicial(escenario)
        evaluador = EvaluadorUtilidad(escenario, estado.turno_actual)
        decision = alfa_beta(escenario, estado, 4)
        pares.append({
            "archivo": ruta.relative_to(RAIZ).as_posix(),
            "sha256": hashlib.sha256(ruta.read_bytes()).hexdigest(),
            "estado": {
                "unidades": [[u.identificador, u.posicion.fila, u.posicion.columna] for u in estado.unidades],
                "recurso": None if estado.posicion_recurso is None else [estado.posicion_recurso.fila, estado.posicion_recurso.columna],
                "portador": estado.portador_recurso,
                "huella_estado": huella_estado(estado),
            },
            "utilidad": evaluador.evaluar(estado),
            "decision": decision.a_diccionario(),
            "verificacion": _verificacion(verificar_decision(escenario, estado, decision)),
        })
    casos["06_estado_compuesto"] = {"ejecuciones": pares, "posiciones_iguales": pares[0]["estado"]["unidades"] == pares[1]["estado"]["unidades"]}
    casos["07_decision_adversarial"] = {
        "ejecuciones": [_decision("07", "decision_adversarial.json", "minimax", profundidad) for profundidad in (1, 2, 3, 4)]
    }
    ruta8, escenario8 = _escenario("recurso_en_transporte.json")
    estado8 = crear_estado_inicial(escenario8)
    comp8 = comparar_minimax_alfa_beta(escenario8, estado8, 4)
    casos["08_minimax_vs_alfa_beta"] = {
        "archivo": ruta8.relative_to(RAIZ).as_posix(),
        "sha256": hashlib.sha256(ruta8.read_bytes()).hexdigest(),
        "parametros": {"profundidad": 4, "orden_acciones": "generacion"},
        "resultado": comp8.a_diccionario(),
        "verificaciones": [_verificacion(verificar_decision(escenario8, estado8, item)) for item in (comp8.minimax, comp8.alfa_beta)],
    }
    casos["09_orden_acciones"] = {
        archivo: [_decision("09", archivo, "alfa_beta", 4, orden) for orden in ("generacion", "inverso", "tactico")]
        for archivo in ("recurso_en_transporte.json", "campo_20x20.json")
    }
    casos["10_profundidad"] = {
        "ejecuciones": [
            {
                "minimax": _decision("10", "recurso_en_transporte.json", "minimax", profundidad),
                "alfa_beta": _decision("10", "recurso_en_transporte.json", "alfa_beta", profundidad),
            }
            for profundidad in (1, 2, 3, 4)
        ]
    }
    variantes_20x20 = _ejecutar_variantes_20x20()
    _validar_propiedades(casos, variantes_20x20)
    return {
        "formato": "tacticalgrid.experimentos-casos-minimos/1",
        "fecha_utc": datetime.now(timezone.utc).isoformat(),
        "python": platform.python_version(),
        "plataforma": platform.platform(),
        "casos": casos,
        "variantes_20x20": variantes_20x20,
    }


def _ejecutar_variantes_20x20() -> dict[str, object]:
    """Ejecuta y verifica las variantes 20x20 sin sustituir resultados didacticos historicos.

    Proposito: registrar por separado las ejecuciones que cumplen el tamano academico minimo.
    Precondiciones: los cinco JSON 20x20 de casos 6, 7, 8 y 10 existen y cargan correctamente.
    Postcondiciones: devuelve resultados, huellas y verificaciones de estado compuesto, decision, comparacion y
    profundidad; no altera los casos pequeños ni los algoritmos.
    Complejidad: domina alfa-beta a profundidad 4 en los casos 8/10, O(b^d) en peor caso; almacenamiento proporcional
    a los reportes producidos.
    Uso de IA: Si.
    Intervencion de IA: Codex agrego la ejecucion de escenarios academicos 20x20 y su registro separado a pedido del
    usuario.
    Validacion del estudiante: pendiente; la funcion comprueba automaticamente las propiedades y los verificadores
    pero el equipo aun debe revisar los escenarios y defender sus resultados.
    """
    casos: dict[str, object] = {}
    pares = []
    for archivo in (
        "caso_06_estado_compuesto_libre_20x20.json",
        "caso_06_estado_compuesto_portador_20x20.json",
    ):
        ruta, escenario = _escenario(archivo)
        estado = crear_estado_inicial(escenario)
        decision = alfa_beta(escenario, estado, 4)
        pares.append({
            "archivo": ruta.relative_to(RAIZ).as_posix(),
            "sha256": hashlib.sha256(ruta.read_bytes()).hexdigest(),
            "dimensiones": [escenario.filas, escenario.columnas],
            "estado": {
                "unidades": [[u.identificador, u.posicion.fila, u.posicion.columna] for u in estado.unidades],
                "recurso": None if estado.posicion_recurso is None else [estado.posicion_recurso.fila, estado.posicion_recurso.columna],
                "portador": estado.portador_recurso,
                "huella_estado": huella_estado(estado),
            },
            "utilidad": EvaluadorUtilidad(escenario, estado.turno_actual).evaluar(estado),
            "decision": decision.a_diccionario(),
            "verificacion": _verificacion(verificar_decision(escenario, estado, decision)),
        })
    casos["06_estado_compuesto"] = {
        "ejecuciones": pares,
        "posiciones_iguales": pares[0]["estado"]["unidades"] == pares[1]["estado"]["unidades"],
    }

    casos["07_decision_adversarial"] = {
        "ejecuciones": [
            _decision("07-20x20", "caso_07_decision_adversarial_20x20.json", "minimax", d)
            for d in (1, 2, 3, 4)
        ]
    }

    ruta8, escenario8 = _escenario("caso_08_minimax_alfa_beta_20x20.json")
    estado8 = crear_estado_inicial(escenario8)
    comparacion8 = comparar_minimax_alfa_beta(escenario8, estado8, 4)
    casos["08_minimax_vs_alfa_beta"] = {
        "archivo": ruta8.relative_to(RAIZ).as_posix(),
        "sha256": hashlib.sha256(ruta8.read_bytes()).hexdigest(),
        "dimensiones": [escenario8.filas, escenario8.columnas],
        "parametros": {"profundidad": 4, "orden_acciones": "generacion"},
        "resultado": comparacion8.a_diccionario(),
        "verificaciones": [
            _verificacion(verificar_decision(escenario8, estado8, item))
            for item in (comparacion8.minimax, comparacion8.alfa_beta)
        ],
    }

    casos["10_profundidad"] = {
        "ejecuciones": [
            {
                "minimax": _decision("10-20x20", "caso_10_profundidad_20x20.json", "minimax", d),
                "alfa_beta": _decision("10-20x20", "caso_10_profundidad_20x20.json", "alfa_beta", d),
            }
            for d in (1, 2, 3, 4)
        ]
    }
    return casos


def _validar_propiedades(casos: dict[str, object], variantes_20x20: dict[str, object]) -> None:
    """Detiene el archivo experimental si una ejecución no demuestra las propiedades esperadas."""
    ejecuciones1 = casos["01_bfs_vs_dfs"]["ejecuciones"]
    assert all(run["verificacion"]["valido"] for run in ejecuciones1)
    assert ejecuciones1[0]["resultado"]["longitud"] < ejecuciones1[1]["resultado"]["longitud"]
    ejecuciones2 = casos["02_ruta_corta_vs_economica"]["ejecuciones"]
    assert ejecuciones2[0]["resultado"]["longitud"] < ejecuciones2[1]["resultado"]["longitud"]
    assert ejecuciones2[1]["resultado"]["costo"] < ejecuciones2[0]["resultado"]["costo"]
    assert all(run["verificacion"]["valido"] for caso in casos.values() for run in _iterar_ejecuciones(caso))
    ejecuciones3 = casos["03_obstaculo"]["ejecuciones"]
    assert all(run["verificacion"]["valido"] for run in ejecuciones3)
    ejecuciones4 = casos["04_heuristicas"]["ejecuciones"]
    assert len({run["resultado"]["costo"] for run in ejecuciones4}) == 1
    ejecuciones5 = casos["05_beam"]["ejecuciones"]
    assert [run["parametros"]["k"] for run in ejecuciones5] == [1, 2, 4, 8]
    assert all(run["verificacion"]["valido"] for run in ejecuciones5)
    assert [run["resultado"]["exito"] for run in ejecuciones5] == [False, False, True, True]
    estados6 = casos["06_estado_compuesto"]["ejecuciones"]
    assert casos["06_estado_compuesto"]["posiciones_iguales"]
    assert estados6[0]["estado"]["huella_estado"] != estados6[1]["estado"]["huella_estado"]
    assert estados6[0]["decision"]["accion_seleccionada"] != estados6[1]["decision"]["accion_seleccionada"]
    ejecuciones7 = casos["07_decision_adversarial"]["ejecuciones"]
    assert ejecuciones7[0]["resultado"]["accion_seleccionada"]["destino"] == [0, 2]
    assert all(run["resultado"]["accion_seleccionada"]["destino"] != [0, 2] for run in ejecuciones7[1:])
    assert all(run["verificacion"]["valido"] for run in ejecuciones7)
    comparacion = casos["08_minimax_vs_alfa_beta"]["resultado"]
    assert comparacion["misma_accion"] and comparacion["mismo_valor"]
    assert comparacion["alfa_beta"]["nodos_podados"] > 0
    assert all(item["valido"] for item in casos["08_minimax_vs_alfa_beta"]["verificaciones"])
    for corridas in casos["09_orden_acciones"].values():
        assert all(run["verificacion"]["valido"] for run in corridas)
        assert len({run["resultado"]["valor"] for run in corridas}) == 1
        assert len({run["resultado"]["nodos_evaluados"] for run in corridas}) > 1
    for par in casos["10_profundidad"]["ejecuciones"]:
        assert par["minimax"]["resultado"]["accion_seleccionada"] == par["alfa_beta"]["resultado"]["accion_seleccionada"]
        assert par["minimax"]["resultado"]["valor"] == par["alfa_beta"]["resultado"]["valor"]
    assert len({
        json.dumps(par["minimax"]["resultado"]["accion_seleccionada"], sort_keys=True)
        for par in casos["10_profundidad"]["ejecuciones"]
    }) > 1

    caso6 = variantes_20x20["06_estado_compuesto"]
    pares6 = caso6["ejecuciones"]
    assert all(par["dimensiones"] == [20, 20] for par in pares6)
    assert caso6["posiciones_iguales"]
    assert pares6[0]["estado"]["huella_estado"] != pares6[1]["estado"]["huella_estado"]
    assert pares6[0]["decision"]["accion_seleccionada"] != pares6[1]["decision"]["accion_seleccionada"]
    caso7 = variantes_20x20["07_decision_adversarial"]["ejecuciones"]
    assert all(run["resultado"]["accion_seleccionada"]["destino"] == [0, 2] for run in caso7[:1])
    assert all(run["resultado"]["accion_seleccionada"]["destino"] != [0, 2] for run in caso7[1:])
    caso8 = variantes_20x20["08_minimax_vs_alfa_beta"]
    assert caso8["dimensiones"] == [20, 20]
    assert caso8["resultado"]["misma_accion"] and caso8["resultado"]["mismo_valor"]
    assert caso8["resultado"]["alfa_beta"]["nodos_podados"] > 0
    caso10 = variantes_20x20["10_profundidad"]["ejecuciones"]
    assert all(
        par["minimax"]["resultado"]["valor"] == par["alfa_beta"]["resultado"]["valor"]
        and par["minimax"]["resultado"]["accion_seleccionada"] == par["alfa_beta"]["resultado"]["accion_seleccionada"]
        for par in caso10
    )
    assert all(run["verificacion"]["valido"] for run in caso7)
    assert all(par["verificacion"]["valido"] for par in pares6)
    assert all(item["valido"] for item in caso8["verificaciones"])
    assert all(
        par[lado]["verificacion"]["valido"]
        for par in caso10
        for lado in ("minimax", "alfa_beta")
    )
    assert len({
        json.dumps(par["minimax"]["resultado"]["accion_seleccionada"], sort_keys=True)
        for par in caso10
    }) > 1


def _iterar_ejecuciones(caso):
    if isinstance(caso, dict):
        if "verificacion" in caso:
            yield caso
            return
        for valor in caso.values():
            yield from _iterar_ejecuciones(valor)
    elif isinstance(caso, list):
        for valor in caso:
            yield from _iterar_ejecuciones(valor)


def main() -> None:
    """Ejecuta y escribe el manifiesto JSON en su ubicación documental estable."""
    DESTINO.parent.mkdir(parents=True, exist_ok=True)
    resultados = ejecutar_experimentos()
    DESTINO.write_text(json.dumps(resultados, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"Casos pequeños preservados: 10; variantes académicas 20x20: "
        f"{len(resultados['variantes_20x20'])}; registro: {DESTINO.relative_to(RAIZ)}"
    )


if __name__ == "__main__":
    main()
