
"""Aplicación de consola de TacticalGrid y presentación textual de resultados."""

import argparse
import base64
import contextlib
import hashlib
import io
import json
import sys
import tempfile
from dataclasses import asdict
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]

from tacticalgrid.algoritmos import (
    ancho_haz_desde_prueba,
    busqueda_a_estrella,
    busqueda_anchura,
    busqueda_costo_uniforme,
    busqueda_haz,
    busqueda_profundidad,
    validar_ancho_haz,
)
from tacticalgrid.algoritmos.heuristica_obstaculos import HeuristicaObstaculos
from tacticalgrid.escenario import (
    ErrorValidacionEscenario,
    Posicion,
    cargar_escenario,
)
from tacticalgrid.algoritmos.alfa_beta import alfa_beta
from tacticalgrid.algoritmos.comparacion_adversarial import (
    METRICAS_COMPARABLES,
    METRICAS_DE_TRABAJO,
    comparar_minimax_alfa_beta,
)
from tacticalgrid.algoritmos.minimax import minimax, profundidad_desde_configuracion, validar_profundidad
from tacticalgrid.algoritmos.orden_acciones import (
    ORDEN_GENERACION,
    ORDENES,
    orden_desde_configuracion,
    validar_orden,
)
from tacticalgrid.algoritmos.utilidad import pesos_desde_configuracion
from tacticalgrid.algoritmos.verificador import verificar_busqueda, verificar_decision, verificar_partida
from tacticalgrid.juego import ProblemaNavegacion, crear_estado_inicial
from tacticalgrid.modos.registro import RegistroExperimento, serializar
from tacticalgrid.modos.reproduccion import reproducir_registro_partida
from tacticalgrid.modos import (
    MAX_TURNOS_POR_DEFECTO,
    MODOS,
    jugar_partida,
    leer_configuracion_prueba,
    resolver_modo,
    validar_max_turnos,
)


ALGORITMOS = {
    "bfs": busqueda_anchura,
    "dfs": busqueda_profundidad,
    "ucs": busqueda_costo_uniforme,
    "a_estrella": busqueda_a_estrella,
}

DECISORES = {
    "minimax": minimax,
    "alfa_beta": alfa_beta,
}

ADVERSARIALES = (*DECISORES, "minimax_alfa_beta")

ESCENARIO_INICIAL = RAIZ / "escenarios" / "campo_20x20.json"


def construir_problema(escenario, unidad=None, destino=None, configuracion=None):
    """Construir un problema de navegación con los datos del escenario.

    Proposito: resolver la unidad y el objetivo indicados por consola o por la configuración de prueba y crear el
    ``ProblemaNavegacion`` que consumen los algoritmos.
    Precondiciones: ``escenario`` está cargado y validado; ``destino``, si se proporciona, contiene dos enteros.
    Postcondiciones: se devuelven el problema, el identificador de la unidad y la posición objetivo; se lanza
    ``ValueError`` si faltan datos o no cumplen el contrato de navegación.
    Complejidad: O(U log U + T) temporal y O(U) espacial por construir y normalizar el estado inicial con U unidades y
    recorrer los T tipos de terreno para obtener el costo mínimo de paso.
    Uso de IA: Si.
    Intervencion de IA: Codex: documentación académica durante el cierre de auditoría de E5.1 y corrección de la
    complejidad temporal en E6.1 para incluir el recorrido del catálogo de terrenos. Claude (Opus 5.5): lectura de la
    unidad y el objetivo del JSON desde ``configuracion`` (``leer_configuracion_prueba``), que ya los valida, en lugar
    de releer ``prueba`` (E10.1).
    Validacion del estudiante: pruebas de tests/modos/test_consola_modos.py: consola con la unidad y el objetivo del
    JSON, y búsqueda sin unidad ni objetivo que explica qué falta.
    """

    if unidad is None and configuracion is not None:
        unidad = configuracion.unidad

    if not unidad:
        raise ValueError(
            "Debe indicar una unidad con --unidad o definir "
            "'prueba.unidad_inicio' en el JSON."
        )

    if destino is not None:
        objetivo = Posicion(*destino)
    elif configuracion is not None and configuracion.objetivo is not None:
        objetivo = configuracion.objetivo
    else:
        raise ValueError(
            "Debe indicar --objetivo FILA COLUMNA o definir "
            "'prueba.objetivo' en el JSON."
        )

    problema = ProblemaNavegacion(escenario, unidad, objetivo)

    return problema, unidad, objetivo


def resolver_orden(orden_consola, escenario):
    """Determinar el orden de acciones de Minimax y alfa-beta sin modificar código.

    Proposito: permitir cambiar el orden de generación de acciones desde ``--orden`` o desde el campo propio
    ``juego.orden_acciones`` del JSON, como pide el caso mínimo 9.
    Precondiciones: ``orden_consola`` es ``None`` o uno de ``ORDENES`` (argparse ya lo restringe); ``escenario`` está
    validado.
    Postcondiciones: se devuelve el orden de consola si se indicó (tiene prioridad); si no, el del JSON y, si tampoco
    está, ``generacion``. Se lanza ``ValueError`` con las opciones válidas si el JSON trae un orden desconocido.
    Complejidad: O(1) temporal y espacial.
    Uso de IA: Si.
    Intervencion de IA: Claude (Opus 5.5): función y opción ``--orden`` (E8.6).
    Validacion del estudiante: pruebas de consola de tests/algoritmos/test_casos_minimos_adversariales.py: cambio del
    orden sin tocar código, lectura del orden del JSON y rechazo de un orden inválido.
    """
    if orden_consola is not None:
        return validar_orden(orden_consola)
    return orden_desde_configuracion(escenario.configuracion_juego) or ORDEN_GENERACION


def resolver_profundidad(profundidad_consola, escenario):
    """Determinar la profundidad máxima de Minimax sin modificar código.

    Proposito: tomar la profundidad de ``--profundidad`` o, si no se indicó, de ``juego.profundidad_maxima_minimax``.
    Precondiciones: ``profundidad_consola`` es ``None`` o el entero leído por argparse; ``escenario`` está validado.
    Postcondiciones: se devuelve la profundidad de consola si se indicó (tiene prioridad) o la del JSON; se lanza
    ``ValueError`` si ninguna está definida o si el valor no es un entero mayor o igual que 1.
    Complejidad: O(1) temporal y espacial.
    Uso de IA: Si.
    Intervencion de IA: Claude (Opus 5.5): función y opción ``minimax`` del ejecutor (E8.3).
    Validacion del estudiante: pruebas de consola de tests/algoritmos/test_minimax.py, que ejecutan ``main.py`` con
    ``--profundidad``, con el valor del JSON y sin ninguno.
    """
    if profundidad_consola is not None:
        return validar_profundidad(profundidad_consola)
    desde_json = profundidad_desde_configuracion(escenario.configuracion_juego)
    if desde_json is None:
        raise ValueError(
            "Minimax necesita una profundidad: indique --profundidad o defina 'juego.profundidad_maxima_minimax'."
        )
    return desde_json


def describir_accion_tactica(accion_tactica):
    """Describir una acción táctica como ``unidad (origen) -> (destino)``, o con ``intercepta en``."""
    if accion_tactica is None:
        return "ninguna"
    a = accion_tactica.accion
    verbo = "intercepta en" if a.tipo == "interceptar" else "->"
    return f"{a.identificador_unidad} ({a.origen.fila}, {a.origen.columna}) {verbo} ({a.destino.fila}, {a.destino.columna})"


def mostrar_comparacion_adversarial(comparacion):
    """Mostrar lado a lado las siete métricas de Minimax y alfa-beta y la reducción que logra la poda en cada una.

    Proposito: presentar de forma clara y comparable (E8.5) los nodos generados, evaluados y podados, la profundidad
    alcanzada, el tiempo, la acción elegida y el valor de ambos algoritmos sobre el mismo estado.
    Precondiciones: ``comparacion`` es una ``ComparacionAdversarial``.
    Postcondiciones: se imprime una fila por métrica, en el orden de ``METRICAS_COMPARABLES``, con el valor de cada
    algoritmo y, en las métricas de trabajo, la reducción porcentual; después se indica si coinciden la acción y el
    valor. La comparación no cambia y no se ejecutan búsquedas.
    Complejidad: O(1) temporal y espacial (siete filas).
    Uso de IA: Si.
    Intervencion de IA: Claude (Opus 5.5): presentación (E8.5).
    Validacion del estudiante: prueba ``test_consola_muestra_la_tabla_comparativa_con_las_siete_metricas`` de
    tests/algoritmos/test_comparacion_adversarial.py.
    """

    def formatear(campo, valor):
        if campo == "accion_seleccionada":
            return describir_accion_tactica(valor)
        if campo == "tiempo_segundos":
            return f"{valor:.6f}"
        return f"{valor}"

    print(f"\n{'=' * 92}")
    print("COMPARACIÓN MINIMAX vs. ALFA-BETA")
    print("=" * 92)
    print(f"Bando MAX: {comparacion.minimax.bando_max} | Profundidad máxima: {comparacion.minimax.profundidad_maxima}")
    print(f"Orden de acciones: {comparacion.minimax.orden_acciones}")
    print(f"{'Métrica':<22} {'Minimax':>24} {'Alfa-beta':>24} {'Reducción':>12}")
    for etiqueta, campo in METRICAS_COMPARABLES:
        reduccion = comparacion.reduccion_porcentual(campo) if campo in METRICAS_DE_TRABAJO else None
        texto_reduccion = "" if reduccion is None else f"{reduccion:.1f} %"
        print(
            f"{etiqueta:<22} {formatear(campo, getattr(comparacion.minimax, campo)):>24} "
            f"{formatear(campo, getattr(comparacion.alfa_beta, campo)):>24} {texto_reduccion:>12}"
        )
    print(f"Misma acción: {'Sí' if comparacion.misma_accion else 'No'}")
    print(f"Mismo valor: {'Sí' if comparacion.mismo_valor else 'No'}")


def mostrar_resultado_minimax(resultado):
    """Mostrar la decisión de Minimax o alfa-beta, sus métricas y el valor de cada acción de la raíz.

    Proposito: presentar en consola las métricas adversariales del enunciado y permitir explicar la decisión.
    Precondiciones: ``resultado`` es un ``ResultadoMinimax``.
    Postcondiciones: se imprimen el bando MAX, la profundidad, la acción seleccionada con su tipo táctico, el valor, las
    métricas y una fila por acción de la raíz con la elegida marcada; con alfa-beta, los valores que son solo cotas por
    la poda se muestran como ``<= v``. El resultado no cambia.
    Complejidad: O(A) temporal y O(1) espacial adicional, con A la cantidad de acciones de la raíz.
    Uso de IA: Si.
    Intervencion de IA: Claude (Opus 5.5): presentación (E8.3) y marca de cotas (E8.4).
    Validacion del estudiante: pruebas de consola de tests/algoritmos/test_minimax.py y
    ``test_consola_alfa_beta_elige_lo_mismo_que_minimax_y_reporta_la_poda`` de tests/algoritmos/test_alfa_beta.py.
    """
    describir = describir_accion_tactica

    print(f"\n{'=' * 60}")
    print(f"ALGORITMO: {resultado.algoritmo}")
    print("=" * 60)
    print(f"Bando MAX: {resultado.bando_max}")
    print(f"Profundidad máxima: {resultado.profundidad_maxima}")
    print(f"Orden de acciones: {resultado.orden_acciones}")
    if resultado.accion_seleccionada is None:
        print("Acción seleccionada: ninguna (estado terminal o bando sin acciones)")
    else:
        print(
            f"Acción seleccionada: {describir(resultado.accion_seleccionada)} "
            f"[{resultado.accion_seleccionada.tipo_tactico}]"
        )
    print(f"Valor obtenido: {resultado.valor}")
    print(f"Nodos generados: {resultado.nodos_generados}")
    print(f"Nodos evaluados: {resultado.nodos_evaluados}")
    print(f"Nodos podados: {resultado.nodos_podados}")
    print(f"Profundidad alcanzada: {resultado.profundidad_alcanzada}")
    print(f"Tiempo: {resultado.tiempo_segundos:.6f} segundos")
    if resultado.valores_raiz:
        _mostrar_valores_raiz(resultado, describir)


def _mostrar_valores_raiz(resultado, describir):
    """Imprimir una fila por acción de la raíz; con alfa-beta, los valores que son cotas se muestran como ``<= v``."""
    print("\nValor de cada acción de la raíz:")
    cotas = resultado.cotas_raiz or (False,) * len(resultado.valores_raiz)
    for (accion_tactica, valor), es_cota in zip(resultado.valores_raiz, cotas):
        texto_valor = f"<= {valor}" if es_cota else f"{valor}"
        marca = "  <== elegida" if accion_tactica == resultado.accion_seleccionada else ""
        print(f"  {describir(accion_tactica):<32} {accion_tactica.tipo_tactico:<24} {texto_valor:>12}{marca}")
    if any(cotas):
        print("  (<= v: rama podada; su valor real es menor o igual que v y no puede superar a la elegida)")


def resolver_anchos_haz(anchos_consola, escenario):
    """Determinar los anchos k con los que se ejecuta Beam Search.

    Proposito: permitir cambiar k sin modificar código, desde la consola (``--k``) o desde el JSON (``prueba.k``).
    Precondiciones: ``anchos_consola`` es ``None`` o una lista de valores leídos por argparse; ``escenario`` está
    cargado y validado.
    Postcondiciones: se devuelven los anchos de consola si se indicaron (tienen prioridad) o, si no, una tupla con
    ``prueba.k``; se lanza ``ValueError`` si ningún origen define k o si algún valor no es un entero mayor o igual que
    1. El escenario no cambia.
    Complejidad: O(K) temporal y espacial, con K la cantidad de anchos indicados.
    Uso de IA: Si.
    Intervencion de IA: Claude (Opus 5.5): función y opción ``beam`` del ejecutor (E7.1).
    Validacion del estudiante: pruebas de consola de tests/algoritmos/test_busqueda_haz.py, que ejecutan ``main.py``
    con ``--k``, con ``prueba.k`` y sin ninguno.
    """
    if anchos_consola:
        return tuple(validar_ancho_haz(k) for k in anchos_consola)
    desde_json = ancho_haz_desde_prueba(escenario.configuracion_prueba)
    if desde_json is None:
        raise ValueError("Beam Search necesita un ancho: indique --k (por ejemplo --k 1 2 4 8) o defina 'prueba.k' en el JSON.")
    return (desde_json,)


def mostrar_resultado(nombre, resultado):
    """Mostrar el camino y las métricas de una búsqueda.

    Proposito: presentar en consola un ``ResultadoBusqueda`` sin recalcular ni alterar sus métricas.
    Precondiciones: ``resultado`` cumple el contrato común de resultados de E4.1.
    Postcondiciones: se imprimen el éxito, el camino, los movimientos, el costo y las métricas; el resultado no cambia.
    Complejidad: O(L) temporal y espacial por construir el texto de un camino de L posiciones.
    Uso de IA: Si.
    Intervencion de IA: Codex: documentación académica durante el cierre de auditoría de E5.1.
    Validacion del estudiante: pruebas de consola de tests/modos/test_consola_modos.py,
    tests/algoritmos/test_caso_minimo_1.py y tests/algoritmos/test_caso_minimo_5.py.
    """

    print(f"\n{'=' * 45}")
    print(f"ALGORITMO: {nombre.upper()}")
    print("=" * 45)

    print(f"Solución encontrada: {'Sí' if resultado.exito else 'No'}")

    if resultado.exito:
        camino = " -> ".join(
            f"({pos.fila}, {pos.columna})"
            for pos in resultado.camino
        )
        print(f"Camino: {camino}")
    else:
        print("Camino: No disponible")

    print(f"Movimientos: {resultado.longitud}")
    print(f"Costo acumulado: {resultado.costo}")
    print(f"Estados generados: {resultado.estados_generados}")
    print(f"Estados expandidos: {resultado.estados_expandidos}")
    print(f"Máximo de frontera: {resultado.maximo_frontera}")
    print(f"Tiempo: {resultado.tiempo_segundos:.6f} segundos")


def mostrar_comparacion(resultados):
    """Comparar en consola los resultados reales de BFS y UCS.

    Proposito: resumir movimientos, costo, éxito, menor costo e igualdad de caminos cuando ambos algoritmos se ejecutan
    sobre el mismo problema.
    Precondiciones: ``resultados`` contiene las claves ``bfs`` y ``ucs`` con resultados de E4.1.
    Postcondiciones: se imprime la comparación sin modificar los resultados ni ejecutar nuevas búsquedas.
    Complejidad: O(L) temporal por comparar caminos de hasta L posiciones y O(1) espacial adicional.
    Uso de IA: Si.
    Intervencion de IA: Codex: comparación solicitada por la auditoría final de E5.1.
    Validacion del estudiante: pruebas de tests/modos/test_registro.py y tests/algoritmos/test_verificador.py que
    ejecutan la comparación ``ambos`` desde la consola.
    """
    bfs = resultados["bfs"]
    ucs = resultados["ucs"]

    if bfs.exito and ucs.exito:
        if bfs.costo < ucs.costo:
            menor_costo = "BFS"
        elif ucs.costo < bfs.costo:
            menor_costo = "UCS"
        else:
            menor_costo = "Empate"
    elif bfs.exito:
        menor_costo = "BFS (único con solución)"
    elif ucs.exito:
        menor_costo = "UCS (único con solución)"
    else:
        menor_costo = "No disponible"

    caminos = "Iguales" if bfs.camino == ucs.camino else "Diferentes"

    print(f"\n{'=' * 45}")
    print("COMPARACIÓN BFS vs. UCS")
    print("=" * 45)
    print(f"BFS: solución={'Sí' if bfs.exito else 'No'}, movimientos={bfs.longitud}, costo={bfs.costo}")
    print(f"UCS: solución={'Sí' if ucs.exito else 'No'}, movimientos={ucs.longitud}, costo={ucs.costo}")
    print(f"Menor costo: {menor_costo}")
    print(f"Caminos: {caminos}")


def mostrar_comparacion_haz(resultados):
    """Resumir en una tabla los resultados de Beam Search con distintos anchos k.

    Proposito: apoyar el caso mínimo 5 (E7.2) comparando en una sola vista cómo cambian la solución y la exploración al
    variar k sobre el mismo problema.
    Precondiciones: ``resultados`` es un diccionario no vacío ``{k: ResultadoBusqueda}`` con resultados de E4.1.
    Postcondiciones: se imprime una fila por k, en orden creciente, con la solución, los movimientos, el costo, los
    estados generados y expandidos, el máximo de frontera y el tiempo; los resultados no cambian y no se ejecutan
    búsquedas.
    Complejidad: O(K log K) temporal por ordenar los K anchos y O(1) espacial adicional por fila.
    Uso de IA: Si.
    Intervencion de IA: Claude (Opus 5.5): tabla e implementación (E7.2).
    Validacion del estudiante: prueba ``test_la_consola_reproduce_la_tabla_comparativa`` de
    tests/algoritmos/test_caso_minimo_5.py.
    """
    print(f"\n{'=' * 78}")
    print("COMPARACIÓN BEAM SEARCH POR ANCHO k")
    print("=" * 78)
    print(f"{'k':>4} {'Solución':>9} {'Movs':>5} {'Costo':>6} {'Generados':>10} {'Expandidos':>11} {'Frontera':>9} {'Tiempo (s)':>11}")
    for k in sorted(resultados):
        r = resultados[k]
        costo = "-" if r.costo is None else r.costo
        print(
            f"{k:>4} {'Sí' if r.exito else 'No':>9} {r.longitud:>5} {costo:>6} {r.estados_generados:>10} "
            f"{r.estados_expandidos:>11} {r.maximo_frontera:>9} {r.tiempo_segundos:>11.6f}"
        )


def mostrar_comparacion_bfs_dfs(resultados):
    """Comparar en consola cómo BFS y DFS recorren el mismo problema.

    Proposito: apoyar el caso mínimo 1 (E4.4) mostrando lado a lado la solución, los movimientos, el costo y las
    métricas de exploración de BFS y DFS sobre el mismo escenario, estado inicial, unidad y objetivo.
    Precondiciones: ``resultados`` contiene las claves ``bfs`` y ``dfs`` con resultados de E4.1.
    Postcondiciones: se imprime una fila por métrica (solución, movimientos, costo, estados generados y expandidos,
    máximo de frontera) y si los caminos son iguales o diferentes; los resultados no cambian y no se ejecutan nuevas
    búsquedas.
    Complejidad: O(L) temporal por comparar caminos de hasta L posiciones y O(1) espacial adicional.
    Uso de IA: Si.
    Intervencion de IA: Claude (Opus 5.5): comparación e implementación (E4.4).
    Validacion del estudiante: prueba ``test_la_consola_reproduce_la_comparacion`` de
    tests/algoritmos/test_caso_minimo_1.py.
    """
    bfs = resultados["bfs"]
    dfs = resultados["dfs"]

    def valor(resultado, campo):
        dato = getattr(resultado, campo)
        if campo == "exito":
            return "Sí" if dato else "No"
        return "-" if dato is None else dato

    print(f"\n{'=' * 45}")
    print("COMPARACIÓN BFS vs. DFS")
    print("=" * 45)
    print(f"{'Métrica':<20} {'BFS':>10} {'DFS':>10}")
    for etiqueta, campo in (
        ("Solución", "exito"),
        ("Movimientos", "longitud"),
        ("Costo", "costo"),
        ("Estados generados", "estados_generados"),
        ("Estados expandidos", "estados_expandidos"),
        ("Máximo de frontera", "maximo_frontera"),
    ):
        print(f"{etiqueta:<20} {valor(bfs, campo):>10} {valor(dfs, campo):>10}")
    print(f"Caminos: {'Iguales' if bfs.camino == dfs.camino else 'Diferentes'}")


def _marcas_de_verificacion():
    """Devolver las marcas de correcto y fallido que la salida estándar actual puede escribir."""
    codificacion = getattr(sys.stdout, "encoding", None) or "utf-8"
    try:
        "✓✗".encode(codificacion)
    except (UnicodeEncodeError, LookupError):
        return "[OK]", "[FALLA]"
    return "✓", "✗"


def mostrar_verificacion(reporte):
    """Imprimir un reporte del verificador (E10.2) y devolver ``True`` si todas las comprobaciones se cumplen.

    Proposito: mostrar en consola, comprobación por comprobación, si la respuesta de un algoritmo es correcta.
    Precondiciones: ``reporte`` es un ``ReporteVerificacion``.
    Postcondiciones: se imprime una línea por comprobación con su marca (correcta o fallida) y su detalle, y el
    veredicto final; se devuelve ``reporte.es_valido``. Si la salida no puede codificar las marcas, como cp1252 al
    redirigir en Windows, se usan ``[OK]`` y ``[FALLA]``. El reporte no cambia.
    Complejidad: O(C) temporal y O(1) espacial adicional, con C la cantidad de comprobaciones.
    Uso de IA: Si.
    Intervencion de IA: Claude (Opus 5.5): presentación (E10.2) y marcas de respaldo para salidas que no admiten los
    símbolos (E11.6).
    Validacion del estudiante: pruebas ``test_consola_verifica_cada_modo`` y
    ``test_consola_verifica_aunque_la_salida_no_admita_las_marcas`` de tests/algoritmos/test_verificador.py.
    """
    print(f"\nVERIFICACIÓN: {reporte.sujeto}")
    print("-" * 60)
    correcta, fallida = _marcas_de_verificacion()
    for comprobacion in reporte.comprobaciones:
        marca = correcta if comprobacion.correcta else fallida
        print(f"  {marca} {comprobacion.nombre}: {comprobacion.detalle}")
    print(f"Resultado de la verificación: {'VÁLIDO' if reporte.es_valido else 'INVÁLIDO'}")
    return reporte.es_valido


def _verificar(reporte, registro):
    """Mostrar un reporte de E10.2, agregarlo al registro de E10.3 si existe y devolver si es válido."""
    if registro is not None:
        registro.agregar_verificacion(reporte)
    return mostrar_verificacion(reporte)


def ejecutar_adversarial(
    algoritmo, profundidad_consola, escenario, ruta, orden_consola=None, verificar=False, registro=None
):
    """Ejecutar Minimax, alfa-beta o su comparación sobre el estado inicial del escenario y mostrar el resultado.

    Proposito: concentrar el flujo adversarial del ejecutor de consola (E8.3, E8.4, E8.5 y E8.6).
    Precondiciones: ``algoritmo`` pertenece a ``ADVERSARIALES``; ``escenario`` está cargado y validado.
    Postcondiciones: se imprimen el encabezado del escenario y el resultado del algoritmo o, para
    ``minimax_alfa_beta``, la tabla comparativa de E8.5, con el orden de acciones de la consola, del JSON o el de
    generación. Si ``verificar`` es verdadero, también se imprime el reporte de ``verificar_decision`` (E10.2) de cada
    decisión. Con ``registro`` (E10.3), se registran el modo, los parámetros resueltos, los resultados y las
    verificaciones. Se devuelve 0, o 1 si alguna verificación falla. Se lanza ``ValueError`` si no hay una
    profundidad válida en la consola ni en el JSON, o si el JSON trae un orden desconocido.
    Complejidad: la de la búsqueda o búsquedas ejecutadas.
    Uso de IA: Si.
    Intervencion de IA: Claude (Opus 5.5): extracción de este flujo desde ``main`` y opción ``minimax_alfa_beta``
    (E8.5), orden de acciones configurable (E8.6), verificación opcional (E10.2) y registro (E10.3).
    Validacion del estudiante: pruebas de consola de tests/algoritmos/test_verificador.py,
    tests/algoritmos/test_minimax.py, tests/algoritmos/test_alfa_beta.py,
    tests/algoritmos/test_comparacion_adversarial.py y tests/algoritmos/test_casos_minimos_adversariales.py.
    """
    profundidad = resolver_profundidad(profundidad_consola, escenario)
    orden = resolver_orden(orden_consola, escenario)
    estado = crear_estado_inicial(escenario)
    _imprimir_encabezado("adversarial", ruta, escenario, 60)
    print(f"Turno: {estado.turno_actual} | Portador del recurso: {estado.portador_recurso or 'ninguno'}")
    if registro is not None:
        registro.definir(
            "adversarial",
            algoritmo=algoritmo,
            profundidad=profundidad,
            orden_acciones=orden,
            bando_max=estado.turno_actual,
            pesos_utilidad=asdict(pesos_desde_configuracion(escenario.configuracion_juego)),
        )
    if algoritmo == "minimax_alfa_beta":
        comparacion = comparar_minimax_alfa_beta(escenario, estado, profundidad, orden=orden)
        mostrar_comparacion_adversarial(comparacion)
        decisiones = (comparacion.minimax, comparacion.alfa_beta)
        if registro is not None:
            registro.agregar_resultado(comparacion)
    else:
        decisiones = (DECISORES[algoritmo](escenario, estado, profundidad, orden=orden),)
        mostrar_resultado_minimax(decisiones[0])
        if registro is not None:
            registro.agregar_resultado(decisiones[0])
    if verificar:
        validas = [_verificar(verificar_decision(escenario, estado, decision), registro) for decision in decisiones]
        return 0 if all(validas) else 1
    return 0


def _imprimir_encabezado(modo, ruta, escenario, ancho):
    """Imprimir el encabezado común de los tres modos: título, modo, escenario y dimensiones."""
    print("\nTACTICALGRID")
    print("=" * ancho)
    print(f"MODO: {modo}")
    print(f"Escenario: {ruta.name}")
    print(f"Dimensiones: {escenario.filas} x {escenario.columnas}")


def ejecutar_busqueda(algoritmo, args, escenario, ruta, configuracion, registro=None):
    """Resolver la navegación del modo ``busqueda`` con el algoritmo o la comparación indicados y mostrar el resultado.

    Proposito: ejecutar el modo ``busqueda`` del enunciado (BFS, DFS, UCS, A* o Beam Search) y las comparaciones de
    consola (``ambos`` y ``bfs_dfs``), con la unidad y el objetivo de la consola o del campo ``prueba``.
    Precondiciones: ``algoritmo`` es de la familia de búsqueda; ``escenario`` está validado; ``configuracion`` es el
    resultado de ``leer_configuracion_prueba``.
    Postcondiciones: se imprimen el encabezado y el resultado de cada algoritmo y, en las comparaciones, la tabla
    comparativa. Con ``--verificar`` se imprime el reporte de ``verificar_busqueda`` (E10.2) de cada resultado. Con
    ``registro`` (E10.3), se registran los parámetros resueltos, los resultados y las verificaciones. Se devuelve 0, o
    1 si alguna verificación falla. Se lanza ``ValueError`` si falta la unidad, el objetivo o, con ``beam``, el ancho
    ``k``.
    Complejidad: la de las búsquedas ejecutadas más O(L) por presentar caminos de L posiciones.
    Uso de IA: Si.
    Intervencion de IA: Claude (Opus 5.5): extracción de este flujo desde ``main`` sin cambiar su comportamiento
    (E10.1), verificación opcional (E10.2) y registro (E10.3).
    Validacion del estudiante: pruebas de tests/modos/test_consola_modos.py: algoritmo por defecto y del JSON, ``k`` de
    Beam desde el JSON y búsqueda sin unidad ni objetivo.
    """
    problema, unidad, objetivo = construir_problema(escenario, args.unidad, args.objetivo, configuracion)
    origen = problema.posicion(problema.estado_inicial)

    _imprimir_encabezado("busqueda", ruta, escenario, 45)
    print(f"Unidad: {unidad}")
    print(f"Origen: ({origen.fila}, {origen.columna})")
    print(f"Destino: ({objetivo.fila}, {objetivo.columna})")

    verificar = getattr(args, "verificar", False)
    anchos = resolver_anchos_haz(args.k, escenario) if algoritmo == "beam" else None
    heuristica = getattr(args, "heuristica", None) or "manhattan"
    if heuristica not in ("manhattan", "hto"):
        raise ValueError("La heuristica debe ser 'manhattan' o 'hto'.")
    if heuristica != "manhattan" and algoritmo != "a_estrella":
        raise ValueError("--heuristica solo puede usarse con --algoritmo a_estrella.")
    if registro is not None:
        registro.definir(
            "busqueda",
            algoritmo=algoritmo,
            unidad=unidad,
            objetivo=[objetivo.fila, objetivo.columna],
            k=None if anchos is None else list(anchos),
            heuristica=heuristica if algoritmo == "a_estrella" else None,
        )
    if algoritmo == "beam":
        resultados_haz = {}
        for k in anchos:
            resultados_haz[k] = busqueda_haz(problema, k)
            mostrar_resultado(f"beam search (k={k})", resultados_haz[k])
            if registro is not None:
                registro.agregar_resultado(resultados_haz[k])
        if len(resultados_haz) > 1:
            mostrar_comparacion_haz(resultados_haz)
        if verificar:
            validas = [_verificar(verificar_busqueda(problema, r), registro) for r in resultados_haz.values()]
            return 0 if all(validas) else 1
        return 0

    nombres = {"ambos": ("bfs", "ucs"), "bfs_dfs": ("bfs", "dfs")}.get(algoritmo, (algoritmo,))
    resultados = {}
    for nombre in nombres:
        resultados[nombre] = (
            ALGORITMOS[nombre](problema, heuristica_preparada=HeuristicaObstaculos(problema))
            if nombre == "a_estrella" and heuristica == "hto"
            else ALGORITMOS[nombre](problema)
        )
        mostrar_resultado(nombre, resultados[nombre])
        if registro is not None:
            registro.agregar_resultado(resultados[nombre])

    if algoritmo == "ambos":
        mostrar_comparacion(resultados)
    elif algoritmo == "bfs_dfs":
        mostrar_comparacion_bfs_dfs(resultados)
    if verificar:
        validas = [_verificar(verificar_busqueda(problema, r), registro) for r in resultados.values()]
        return 0 if all(validas) else 1
    return 0


def ejecutar_partida(algoritmo, args, escenario, ruta, configuracion, registro=None):
    """Continuar la partida del escenario por turnos, con ambos bandos decidiendo con el mismo algoritmo.

    Proposito: ejecutar desde la consola el modo ``partida`` del enunciado ("cargar el escenario completo para
    continuar el juego por turnos").
    Precondiciones: ``algoritmo`` es ``minimax`` o ``alfa_beta``; ``escenario`` está validado.
    Postcondiciones: se juega desde el estado cargado con la profundidad y el orden de la consola o del JSON y con el
    límite de ``--turnos``, ``prueba.max_turnos`` o ``MAX_TURNOS_POR_DEFECTO``; se imprimen cada jugada y el resultado
    y, con ``--verificar``, el reporte de ``verificar_partida`` (E10.2). Con ``registro`` (E10.3), se registran los
    parámetros resueltos, la partida y la verificación. Se devuelve 0, o 1 si la verificación falla. Se lanza
    ``ValueError`` si falta la profundidad o algún parámetro no es válido.
    Complejidad: la de ``jugar_partida`` más O(T) por presentar T jugadas.
    Uso de IA: Si.
    Intervencion de IA: Claude (Opus 5.5): flujo (E10.1), verificación opcional (E10.2) y registro (E10.3).
    Validacion del estudiante: pruebas de tests/modos/test_consola_modos.py: partida del JSON hasta el límite de turnos,
    partida con ganador y turnos indicados desde la consola.
    """
    profundidad = resolver_profundidad(args.profundidad, escenario)
    orden = resolver_orden(args.orden, escenario)
    if args.turnos is not None:
        max_turnos = validar_max_turnos(args.turnos)
    elif configuracion is not None and configuracion.max_turnos is not None:
        max_turnos = configuracion.max_turnos
    else:
        max_turnos = MAX_TURNOS_POR_DEFECTO
    estado = crear_estado_inicial(escenario)

    _imprimir_encabezado("partida", ruta, escenario, 60)
    print(f"Turno inicial: {estado.turno_actual} | Portador del recurso: {estado.portador_recurso or 'ninguno'}")
    print(f"Algoritmo de ambos bandos: {algoritmo} | Profundidad: {profundidad} | Orden de acciones: {orden}")
    print(f"Límite: {max_turnos} jugadas")
    if registro is not None:
        registro.definir(
            "partida",
            algoritmo=algoritmo,
            profundidad=profundidad,
            orden_acciones=orden,
            max_turnos=max_turnos,
            pesos_utilidad=asdict(pesos_desde_configuracion(escenario.configuracion_juego)),
        )
    partida = jugar_partida(escenario, estado, profundidad, algoritmo=algoritmo, orden=orden, max_turnos=max_turnos)
    mostrar_partida(partida)
    if registro is not None:
        registro.agregar_resultado(partida)
    if getattr(args, "verificar", False):
        return 0 if _verificar(verificar_partida(escenario, partida), registro) else 1
    return 0


def mostrar_partida(partida):
    """Imprimir cada jugada de la partida (bando, acción, valor y nodos evaluados), los pases y el resultado final."""
    print()
    for turno in partida.turnos:
        if turno.hubo_pase:
            bloqueado = "B" if turno.bando == "A" else "A"
            print(f"  (el bando {bloqueado} estaba bloqueado y pasó el turno)")
        decision = turno.decision
        accion = decision.accion_seleccionada
        print(
            f"Turno {turno.numero} | {turno.bando} | {describir_accion_tactica(accion)} [{accion.tipo_tactico}] "
            f"| valor {decision.valor} | evaluados {decision.nodos_evaluados}"
        )
    jugadas = len(partida.turnos)
    if partida.ganador is not None:
        texto = f"victoria de {partida.ganador} en {jugadas} jugadas"
    elif partida.resultado == "empate_bloqueo":
        texto = f"empate por bloqueo total tras {jugadas} jugadas"
    else:
        texto = f"límite de {jugadas} jugadas alcanzado sin ganador"
    print(f"\nResultado: {texto}")
    print(f"Portador final del recurso: {partida.estado_final.portador_recurso or 'ninguno'}")


def ejecutar_modo(args, escenario, ruta, registro=None):
    """Ejecutar el modo de prueba que piden la consola o el campo ``prueba`` del escenario (E10.1).

    Proposito: ejecutar el modo solicitado por un escenario externo sin cambios de código.
    Precondiciones: ``args`` proviene de ``argparse`` y ``escenario`` está cargado y validado.
    Postcondiciones: se lee ``prueba``, se resuelve el modo con ``resolver_modo`` y el algoritmo con la prioridad
    consola, luego ``prueba.algoritmo`` (si es del mismo modo) y luego el valor por defecto del modo (``ucs`` en
    búsqueda y ``alfa_beta`` en partida y adversarial); se delega en ``ejecutar_busqueda``, ``ejecutar_partida`` o
    ``ejecutar_adversarial``, con ``registro`` (E10.3), y se devuelve su código. Se lanza ``ValueError`` si ``prueba``
    o la combinación de modo y algoritmo no son válidas.
    Complejidad: la del modo ejecutado.
    Uso de IA: Si.
    Intervencion de IA: Claude (Opus 5.5): despacho por modo (E10.1) y paso del registro (E10.3).
    Validacion del estudiante: pruebas de tests/modos/test_consola_modos.py: modos del JSON, modo y turnos desde la
    consola, algoritmo explícito con el comportamiento anterior, combinación incompatible y ``prueba`` inválida.
    """
    configuracion = leer_configuracion_prueba(escenario)
    modo = resolver_modo(args.modo, args.algoritmo, configuracion)
    algoritmo = args.algoritmo
    if algoritmo is None and configuracion is not None and configuracion.modo == modo:
        algoritmo = configuracion.algoritmo
    if algoritmo is None:
        algoritmo = "ucs" if modo == "busqueda" else "alfa_beta"

    if modo == "adversarial":
        return ejecutar_adversarial(
            algoritmo, args.profundidad, escenario, ruta, args.orden, getattr(args, "verificar", False), registro
        )
    if modo == "partida":
        return ejecutar_partida(algoritmo, args, escenario, ruta, configuracion, registro)
    return ejecutar_busqueda(algoritmo, args, escenario, ruta, configuracion, registro)


def crear_registro(ruta, escenario, verificar=False):
    """Crear el registro reproducible (E10.3) de una ejecución sobre el escenario leído de ``ruta``.

    Proposito: identificar sin ambigüedad el escenario usado, con una huella de su contenido, para repetir el
    experimento y detectar si el mapa cambió entre dos ejecuciones.
    Precondiciones: ``ruta`` es el archivo del que se cargó ``escenario``.
    Postcondiciones: se devuelve un ``RegistroExperimento`` con el archivo (relativo a la raíz del repositorio si está
    dentro de él, para que el comando de reproducción sea portable) y la huella SHA-256 de sus bytes. El archivo no
    cambia.
    Complejidad: O(N) temporal por calcular la huella de un archivo de N bytes y O(1) espacial adicional.
    Uso de IA: Si.
    Intervencion de IA: Claude (Opus 5.5): implementación (E10.3).
    Validacion del estudiante: prueba ``test_la_huella_identifica_el_contenido_del_escenario`` de
    tests/modos/test_registro.py.
    """
    try:
        archivo = ruta.resolve().relative_to(RAIZ.resolve()).as_posix()
    except ValueError:
        archivo = str(ruta)
    huella = hashlib.sha256(ruta.read_bytes()).hexdigest()
    return RegistroExperimento(archivo=archivo, huella_sha256=huella, escenario=escenario, verificar=verificar)


def ejecutar_consola(argumentos=None):
    """Cargar el escenario y ejecutar los algoritmos seleccionados en modo textual.

    Proposito: conservar el ejecutor histórico para BFS, DFS, UCS, A*, Beam Search (con uno o varios anchos k), las
    comparaciones BFS/UCS y BFS/DFS sobre una navegación elegida, o Minimax sobre el estado inicial del escenario.
    Precondiciones: los argumentos de consola respetan el formato declarado y la ruta apunta a un escenario legible;
    los datos del escenario se validan en ``cargar_escenario``.
    Postcondiciones: se devuelve 0 tras mostrar los resultados y, para ``ambos``, su comparación; se devuelve 1 con un
    mensaje de error si el escenario o los parámetros de navegación no son válidos, o si ``--verificar`` detecta que
    alguna respuesta no es correcta. Con ``--json`` solo se imprime el registro reproducible (E10.3) y con
    ``--exportar`` se guarda además en un archivo.
    Complejidad: la carga del escenario y las búsquedas seleccionadas; la presentación agrega O(L) temporal y espacial
    para un camino de L posiciones.
    Uso de IA: Si.
    Intervencion de IA: Codex: documentación del flujo, comparación de E5.1, extracción sin cambios desde ``main.py`` e
    incorporación de A* sin alterar la semántica de ``ambos`` (E6.1). Claude (Opus 5.5): opción ``dfs`` (E4.3),
    opción ``bfs_dfs`` (E4.4), opción ``beam`` y ``--k`` (E7.1), tabla comparativa con varios anchos (E7.2), opción
    ``minimax`` y ``--profundidad`` (E8.3), opción ``alfa_beta`` (E8.4), opción ``minimax_alfa_beta`` con el flujo
    adversarial movido a ``ejecutar_adversarial`` (E8.5), ``--orden`` (E8.6), ``--modo`` y ``--turnos`` con el modo y
    el algoritmo resueltos en ``ejecutar_modo`` y la búsqueda movida a ``ejecutar_busqueda`` (E10.1), ``--verificar``
    (E10.2), y ``--json`` y ``--exportar`` (E10.3).
    Validacion del estudiante: prueba ``test_despacha_gui_predeterminada_y_consola_historica`` de
    tests/test_despachador.py y pruebas de consola de tests/modos/test_consola_modos.py.
    """

    parser = argparse.ArgumentParser(
        description="TacticalGrid - Algoritmos de búsqueda"
    )

    parser.add_argument(
        "escenario",
        nargs="?",
        type=Path,
        default=ESCENARIO_INICIAL,
        help="Archivo JSON del escenario",
    )

    parser.add_argument(
        "--modo",
        choices=MODOS,
        help="Modo de prueba a ejecutar. Si se omite, se deduce de --algoritmo o se usa 'prueba.modo' del JSON "
        "(y, si no hay, 'busqueda').",
    )

    parser.add_argument(
        "--algoritmo",
        choices=["bfs", "dfs", "ucs", "a_estrella", "beam", "ambos", "bfs_dfs", *ADVERSARIALES],
        help="Algoritmo a ejecutar. Si se omite, se usa 'prueba.algoritmo' del JSON o el del modo: ucs en "
        "busqueda y alfa_beta en partida y adversarial.",
    )

    parser.add_argument(
        "--turnos",
        type=int,
        help="Limite de jugadas del modo partida. Si se omite, se usa 'prueba.max_turnos' del JSON o "
        f"{MAX_TURNOS_POR_DEFECTO}.",
    )

    parser.add_argument(
        "--k",
        nargs="+",
        type=int,
        metavar="K",
        help="Ancho del haz para --algoritmo beam; admite varios valores (por ejemplo --k 1 2 4 8). "
        "Si se omite, se usa 'prueba.k' del JSON.",
    )

    parser.add_argument(
        "--heuristica",
        choices=("manhattan", "hto"),
        help="Heuristica para A*; si se omite usa Manhattan.",
    )

    parser.add_argument(
        "--profundidad",
        type=int,
        help="Profundidad maxima para --algoritmo minimax, alfa_beta o minimax_alfa_beta. Si se omite, se usa "
        "'juego.profundidad_maxima_minimax' del JSON.",
    )

    parser.add_argument(
        "--orden",
        choices=ORDENES,
        help="Orden en que Minimax y alfa-beta exploran las acciones. Si se omite, se usa 'juego.orden_acciones' "
        "del JSON o, si no esta, 'generacion'.",
    )

    parser.add_argument(
        "--verificar",
        action="store_true",
        help="Verifica la respuesta (E10.2): movimientos, obstaculos, costo, objetivo, estados validos y legalidad "
        "de las acciones de Minimax. Devuelve 1 si alguna comprobacion falla.",
    )

    parser.add_argument(
        "--json",
        action="store_true",
        help="Imprime solo el registro reproducible del experimento en JSON (E10.3), sin el texto habitual.",
    )

    parser.add_argument(
        "--exportar",
        type=Path,
        metavar="ARCHIVO",
        help="Guarda el registro reproducible del experimento en ARCHIVO como JSON (E10.3); el texto se sigue mostrando.",
    )

    parser.add_argument(
        "--reproducir-registro",
        type=Path,
        metavar="ARCHIVO",
        help="Valida y reproduce un registro de partida manual exportado desde la GUI.",
    )

    parser.add_argument(
        "--unidad",
        type=str,
        help="Identificador de la unidad que se desplazará",
    )

    parser.add_argument(
        "--objetivo",
        nargs=2,
        type=int,
        metavar=("FILA", "COLUMNA"),
        help="Coordenadas de destino",
    )

    args = parser.parse_args(argumentos)

    if args.reproducir_registro is not None:
        return reproducir_archivo_partida(args.reproducir_registro)

    ruta = args.escenario
    if not ruta.is_absolute():
        ruta = RAIZ / ruta

    try:
        escenario = cargar_escenario(ruta)
        if not args.json and args.exportar is None:
            return ejecutar_modo(args, escenario, ruta)
        registro = crear_registro(ruta, escenario, args.verificar)
        if args.json:
            with contextlib.redirect_stdout(io.StringIO()):
                codigo = ejecutar_modo(args, escenario, ruta, registro)
        else:
            codigo = ejecutar_modo(args, escenario, ruta, registro)
        texto = serializar(registro.a_diccionario())
        if args.exportar is not None:
            try:
                args.exportar.write_text(texto + "\n", encoding="utf-8")
            except OSError as error:
                raise ValueError(f"No se pudo exportar el registro a {args.exportar}: {error}") from error
            if not args.json:
                print(f"\nRegistro del experimento exportado a {args.exportar}")
        if args.json:
            print(texto)
        return codigo

    except (ErrorValidacionEscenario, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1


def reproducir_archivo_partida(ruta: str | Path) -> int:
    """Cargar, validar y reproducir un registro autocontenido de la interfaz sin modificar el escenario original.

    Proposito: repetir desde la consola una partida exportada y su evaluación adversarial, sin editar código.
    Precondiciones: ``ruta`` apunta a un registro JSON ``tacticalgrid.partida/1`` íntegro.
    Postcondiciones: se imprimen los reportes de la partida y de la decisión y se devuelve 0 si son válidos, o 1 ante
    discrepancias.
    Complejidad: O(N + T*U + B^d) temporal, con N bytes de JSON, T acciones, U unidades y una evaluación opcional B^d.
    Uso de IA: Si.
    Intervencion de IA: Codex: reproducción desde la consola de los registros exportados por la interfaz.
    Validacion del estudiante: prueba ``test_exporta_y_reproduce_partida_manual_desde_escenario_embebido`` de
    tests/interfaz/test_control.py, que reproduce un registro exportado y obtiene el código 0.
    """
    try:
        registro = json.loads(Path(ruta).read_text(encoding="utf-8"))
        datos_escenario = registro["escenario"]
        escenario_bytes = base64.b64decode(datos_escenario["contenido_base64"], validate=True)
        if hashlib.sha256(escenario_bytes).hexdigest() != datos_escenario["huella_sha256"]:
            raise ValueError("La huella SHA-256 del escenario embebido no coincide.")
        with tempfile.TemporaryDirectory(prefix="tacticalgrid-replay-") as carpeta:
            ruta_escenario = Path(carpeta) / "escenario.json"
            ruta_escenario.write_bytes(escenario_bytes)
            escenario = cargar_escenario(ruta_escenario)
            reproducido = reproducir_registro_partida(escenario, registro)
        print(f"Partida reproducida y verificada: {len(registro['acciones'])} acciones; {registro['resultado']}.")
        if reproducido.resultado_evaluacion is not None:
            print("Evaluación adversarial reproducida; campos deterministas coinciden.")
        for reporte in (reproducido.reporte_partida, reproducido.reporte_decision):
            if reporte is None:
                continue
            for comprobacion in reporte.comprobaciones:
                print(f"{'OK' if comprobacion.correcta else 'FALLO'} {comprobacion.nombre}: {comprobacion.detalle}")
        return 0
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError, ErrorValidacionEscenario) as error:
        print(f"Error al reproducir registro: {error}", file=sys.stderr)
        return 1
