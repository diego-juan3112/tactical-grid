
"""Aplicacion de consola de TacticalGrid y presentacion textual de resultados."""

import argparse
import sys
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
from tacticalgrid.juego import ProblemaNavegacion, crear_estado_inicial
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
    """Construye un problema de navegación con los datos del escenario.

    Purpose: resolver la unidad y el objetivo indicados por consola o por la configuración de prueba y crear
    el ``ProblemaNavegacion`` que consumen los algoritmos.
    Preconditions: ``escenario`` fue cargado y validado; ``destino``, si se proporciona, contiene dos enteros.
    Postconditions: devuelve el problema, el identificador de unidad y la posición objetivo; lanza
    ``ValueError`` cuando faltan datos o no cumplen el contrato de navegación.
    Complexity: O(U log U + T) temporal y O(U) espacial por construir y normalizar el estado inicial con U
    unidades y recorrer los T tipos de terreno para obtener el costo mínimo de paso.
    AI usage: Yes.
    AI intervention: Codex completo esta documentación académica durante el cierre de auditoría de E5.1 y
    corrigió su complejidad temporal en E6.1 para incluir el recorrido del catálogo de terrenos. Claude (Opus 5.5)
    hizo en E10.1 que la unidad y el objetivo del JSON se tomen de ``configuracion`` (``leer_configuracion_prueba``),
    que ya los valida, en lugar de releer ``prueba``.
    Student validation: pendiente de revisión humana del cambio de E6.1.
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
    """Determina el orden de acciones de Minimax y alfa-beta sin modificar codigo.

    Proposito: permitir cambiar el orden de generacion de acciones desde ``--orden`` o desde el campo propio
    ``juego.orden_acciones`` del JSON, como pide el caso minimo 9 y la sustentacion.
    Precondiciones: ``orden_consola`` es ``None`` o uno de ``ORDENES`` (argparse ya lo restringe); ``escenario`` fue
    validado.
    Postcondiciones: devuelve el orden de consola si se indico (tiene prioridad), si no el del JSON y, si tampoco
    esta, ``generacion``; lanza ``ValueError`` con las opciones validas si el JSON trae un orden desconocido.
    Complejidad: O(1) temporal y espacial.
    Uso de IA: Si.
    Intervencion de IA: Claude (Opus 5.5) implemento esta funcion y la opcion ``--orden`` en E8.6.
    Validacion del estudiante: pendiente de revision del equipo; cubierta por las pruebas de consola de
    tests/algoritmos/test_casos_minimos_adversariales.py.
    """
    if orden_consola is not None:
        return validar_orden(orden_consola)
    return orden_desde_configuracion(escenario.configuracion_juego) or ORDEN_GENERACION


def resolver_profundidad(profundidad_consola, escenario):
    """Determina la profundidad maxima de Minimax sin modificar codigo.

    Purpose: tomar la profundidad de ``--profundidad`` o, si no se indico, de ``juego.profundidad_maxima_minimax``.
    Preconditions: ``profundidad_consola`` es ``None`` o el entero leido por argparse; ``escenario`` fue validado.
    Postconditions: devuelve la profundidad de consola si se indico (tiene prioridad) o la del JSON; lanza
    ``ValueError`` si ninguna esta definida o si el valor no es un entero mayor o igual que 1.
    Complexity: O(1) temporal y espacial.
    AI usage: Yes.
    AI intervention: Claude (Opus 5.5) implemento esta funcion y la opcion ``minimax`` del ejecutor en E8.3.
    Student validation: el estudiante reviso y valido el codigo; ademas, las pruebas de consola de
    tests/algoritmos/test_minimax.py ejecutan ``main.py`` con ``--profundidad``, con el valor del JSON y sin ninguno.
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
    """Describe una accion tactica como ``unidad (origen) -> (destino)``, o ``intercepta en`` si es intercepcion."""
    if accion_tactica is None:
        return "ninguna"
    a = accion_tactica.accion
    verbo = "intercepta en" if a.tipo == "interceptar" else "->"
    return f"{a.identificador_unidad} ({a.origen.fila}, {a.origen.columna}) {verbo} ({a.destino.fila}, {a.destino.columna})"


def mostrar_comparacion_adversarial(comparacion):
    """Muestra lado a lado las siete metricas de Minimax y alfa-beta y cuanto reduce la poda cada una.

    Proposito: cumplir E8.5 presentando de forma clara y comparable nodos generados, evaluados y podados,
    profundidad alcanzada, tiempo, accion elegida y valor de ambos algoritmos sobre el mismo estado.
    Precondiciones: ``comparacion`` es una ``ComparacionAdversarial``.
    Postcondiciones: imprime una fila por metrica (en el orden de ``METRICAS_COMPARABLES``) con el valor de cada
    algoritmo y, en las metricas de trabajo, la reduccion porcentual; despues indica si coinciden la accion y el
    valor. No modifica la comparacion ni ejecuta busquedas.
    Complejidad: O(1) temporal y espacial (siete filas).
    Uso de IA: Si.
    Intervencion de IA: Claude (Opus 5.5) implemento esta presentacion en E8.5.
    Validacion del estudiante: pendiente de revision del equipo; cubierta por la prueba de consola de
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
    """Muestra la decision de Minimax o alfa-beta, sus metricas y el valor de cada accion de la raiz.

    Purpose: presentar en consola las metricas adversariales del enunciado y permitir explicar la decision.
    Preconditions: ``resultado`` es un ``ResultadoMinimax``.
    Postconditions: imprime bando MAX, profundidad, accion seleccionada con su tipo tactico, valor, metricas y una
    fila por accion de la raiz marcando la elegida; con alfa-beta, los valores que son solo cotas por la poda se
    muestran como ``<= v``. No modifica el resultado.
    Complexity: O(A) temporal y O(1) espacial adicional, donde A es la cantidad de acciones de la raiz.
    AI usage: Yes.
    AI intervention: Claude (Opus 5.5) implemento esta presentacion en E8.3 y en E8.4 agrego la marca de cotas.
    Student validation: el estudiante reviso y valido el codigo; ademas, la prueba de consola de
    tests/algoritmos/test_minimax.py comprueba la salida.
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
    """Imprime una fila por accion de la raiz; con alfa-beta, los valores que son cotas se muestran como ``<= v``."""
    print("\nValor de cada acción de la raíz:")
    cotas = resultado.cotas_raiz or (False,) * len(resultado.valores_raiz)
    for (accion_tactica, valor), es_cota in zip(resultado.valores_raiz, cotas):
        texto_valor = f"<= {valor}" if es_cota else f"{valor}"
        marca = "  <== elegida" if accion_tactica == resultado.accion_seleccionada else ""
        print(f"  {describir(accion_tactica):<32} {accion_tactica.tipo_tactico:<24} {texto_valor:>12}{marca}")
    if any(cotas):
        print("  (<= v: rama podada; su valor real es menor o igual que v y no puede superar a la elegida)")


def resolver_anchos_haz(anchos_consola, escenario):
    """Determina los anchos k con los que se ejecutara Beam Search.

    Purpose: permitir cambiar k sin modificar codigo, desde la consola (``--k``) o desde el JSON (``prueba.k``).
    Preconditions: ``anchos_consola`` es ``None`` o una lista de valores leidos por argparse; ``escenario`` fue
    cargado y validado.
    Postconditions: devuelve los anchos de consola si se indicaron (tienen prioridad) o, si no, una tupla con
    ``prueba.k``; lanza ``ValueError`` si ningun origen define k o si algun valor no es un entero mayor o igual
    que 1. No modifica el escenario.
    Complexity: O(K) temporal y espacial, donde K es la cantidad de anchos indicados.
    AI usage: Yes.
    AI intervention: Claude (Opus 5.5) implemento esta funcion y la opcion ``beam`` del ejecutor en E7.1.
    Student validation: el estudiante reviso y valido el codigo; ademas, las pruebas de consola de
    tests/algoritmos/test_busqueda_haz.py ejecutan ``main.py`` con ``--k``, con ``prueba.k`` y sin ninguno.
    """
    if anchos_consola:
        return tuple(validar_ancho_haz(k) for k in anchos_consola)
    desde_json = ancho_haz_desde_prueba(escenario.configuracion_prueba)
    if desde_json is None:
        raise ValueError("Beam Search necesita un ancho: indique --k (por ejemplo --k 1 2 4 8) o defina 'prueba.k' en el JSON.")
    return (desde_json,)


def mostrar_resultado(nombre, resultado):
    """Muestra el camino y las métricas de búsqueda.

    Purpose: presentar en consola un ``ResultadoBusqueda`` sin recalcular ni alterar sus métricas.
    Preconditions: ``resultado`` cumple el contrato común de resultados de E4.1.
    Postconditions: imprime éxito, camino, movimientos, costo y métricas; no modifica el resultado.
    Complexity: O(L) temporal y espacial por construir el texto de un camino de L posiciones.
    AI usage: Yes.
    AI intervention: Codex completo esta documentación académica durante el cierre de auditoría de E5.1.
    Student validation: pendiente de revisión del equipo.
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
    """Compara en consola los resultados reales de BFS y UCS.

    Purpose: resumir movimientos, costo, éxito, menor costo e igualdad de caminos cuando se ejecutan ambos
    algoritmos sobre el mismo problema.
    Preconditions: ``resultados`` contiene las claves ``bfs`` y ``ucs`` con resultados de E4.1.
    Postconditions: imprime la comparación sin modificar los resultados ni ejecutar nuevas búsquedas.
    Complexity: O(L) temporal por comparar caminos de hasta L posiciones y O(1) espacial adicional.
    AI usage: Yes.
    AI intervention: Codex implementó la comparación solicitada por la auditoría final de E5.1.
    Student validation: pendiente de revisión del equipo.
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
    """Resume en una tabla los resultados de Beam Search con distintos anchos k.

    Purpose: facilitar el caso minimo 5 (E7.2), comparando en una sola vista como cambian la solucion y la
    exploracion al variar k sobre el mismo problema.
    Preconditions: ``resultados`` es un diccionario no vacio ``{k: ResultadoBusqueda}`` con resultados de E4.1.
    Postconditions: imprime una fila por k, en orden creciente, con solucion, movimientos, costo, estados
    generados y expandidos, maximo de frontera y tiempo; no modifica los resultados ni ejecuta busquedas.
    Complexity: O(K log K) temporal por ordenar los K anchos y O(1) espacial adicional por fila.
    AI usage: Yes.
    AI intervention: Claude (Opus 5.5) propuso e implemento esta tabla en E7.2.
    Student validation: el estudiante reviso y valido el codigo; ademas, la prueba de consola de
    tests/algoritmos/test_caso_minimo_5.py comprueba que la tabla aparece con los valores del experimento.
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
    """Compara en consola como BFS y DFS recorren el mismo problema.

    Purpose: apoyar el caso minimo 1 (E4.4) mostrando lado a lado solucion, movimientos, costo y metricas de
    exploracion de BFS y DFS sobre el mismo escenario, estado inicial, unidad y objetivo.
    Preconditions: ``resultados`` contiene las claves ``bfs`` y ``dfs`` con resultados de E4.1.
    Postconditions: imprime una fila por metrica (solucion, movimientos, costo, estados generados y expandidos,
    maximo de frontera) y si los caminos son iguales o diferentes; no modifica los resultados ni ejecuta nuevas
    busquedas.
    Complexity: O(L) temporal por comparar caminos de hasta L posiciones y O(1) espacial adicional.
    AI usage: Yes.
    AI intervention: Claude (Opus 5.5) propuso e implemento esta comparacion en E4.4.
    Student validation: el estudiante reviso y valido el codigo; ademas, la prueba de consola de
    tests/algoritmos/test_caso_minimo_1.py comprueba la tabla con los valores del experimento.
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


def ejecutar_adversarial(algoritmo, profundidad_consola, escenario, ruta, orden_consola=None):
    """Ejecuta Minimax, alfa-beta o su comparacion sobre el estado inicial del escenario y muestra el resultado.

    Proposito: concentrar el flujo adversarial del ejecutor de consola (E8.3, E8.4, E8.5 y E8.6).
    Precondiciones: ``algoritmo`` pertenece a ``ADVERSARIALES``; ``escenario`` fue cargado y validado.
    Postcondiciones: imprime el encabezado del escenario y el resultado del algoritmo o, para
    ``minimax_alfa_beta``, la tabla comparativa de E8.5, usando el orden de acciones de la consola, del JSON o el de
    generacion; devuelve 0. Lanza ``ValueError`` si no hay una profundidad valida en la consola ni en el JSON, o si
    el JSON trae un orden desconocido.
    Complejidad: la de la busqueda o busquedas ejecutadas.
    Uso de IA: Si.
    Intervencion de IA: Claude (Opus 5.5) extrajo este flujo de ``main`` y agrego la opcion ``minimax_alfa_beta`` en
    E8.5, y en E8.6 el orden de acciones configurable.
    Validacion del estudiante: pendiente de revision del equipo; cubierta por las pruebas de consola de
    tests/algoritmos/test_minimax.py, test_alfa_beta.py, test_comparacion_adversarial.py y
    test_casos_minimos_adversariales.py.
    """
    profundidad = resolver_profundidad(profundidad_consola, escenario)
    orden = resolver_orden(orden_consola, escenario)
    estado = crear_estado_inicial(escenario)
    _imprimir_encabezado("adversarial", ruta, escenario, 60)
    print(f"Turno: {estado.turno_actual} | Portador del recurso: {estado.portador_recurso or 'ninguno'}")
    if algoritmo == "minimax_alfa_beta":
        mostrar_comparacion_adversarial(comparar_minimax_alfa_beta(escenario, estado, profundidad, orden=orden))
    else:
        mostrar_resultado_minimax(DECISORES[algoritmo](escenario, estado, profundidad, orden=orden))
    return 0


def _imprimir_encabezado(modo, ruta, escenario, ancho):
    """Imprime el encabezado comun de los tres modos: titulo, modo, escenario y dimensiones."""
    print("\nTACTICALGRID")
    print("=" * ancho)
    print(f"MODO: {modo}")
    print(f"Escenario: {ruta.name}")
    print(f"Dimensiones: {escenario.filas} x {escenario.columnas}")


def ejecutar_busqueda(algoritmo, args, escenario, ruta, configuracion):
    """Resuelve la navegacion del modo ``busqueda`` con el algoritmo o la comparacion indicados y muestra el resultado.

    Proposito: ejecutar el modo ``busqueda`` del enunciado (BFS, DFS, UCS, A* o Beam Search) y las comparaciones de
    consola (``ambos`` y ``bfs_dfs``), con la unidad y el objetivo de la consola o del campo ``prueba``.
    Precondiciones: ``algoritmo`` es de la familia de busqueda; ``escenario`` fue validado; ``configuracion`` es el
    resultado de ``leer_configuracion_prueba``.
    Postcondiciones: imprime el encabezado y el resultado de cada algoritmo y, en las comparaciones, la tabla
    comparativa; devuelve 0. Lanza ``ValueError`` si falta la unidad, el objetivo o (con ``beam``) el ancho ``k``.
    Complejidad: la de las busquedas ejecutadas mas O(L) por presentar caminos de L posiciones.
    Uso de IA: Si.
    Intervencion de IA: Claude (Opus 5.5) extrajo este flujo de ``main`` en E10.1 sin cambiar su comportamiento.
    Validacion del estudiante: pendiente de revision del equipo; cubierta por las pruebas de consola de busqueda y por
    tests/modos/test_consola_modos.py.
    """
    problema, unidad, objetivo = construir_problema(escenario, args.unidad, args.objetivo, configuracion)
    origen = problema.posicion(problema.estado_inicial)

    _imprimir_encabezado("busqueda", ruta, escenario, 45)
    print(f"Unidad: {unidad}")
    print(f"Origen: ({origen.fila}, {origen.columna})")
    print(f"Destino: ({objetivo.fila}, {objetivo.columna})")

    if algoritmo == "beam":
        resultados_haz = {}
        for k in resolver_anchos_haz(args.k, escenario):
            resultados_haz[k] = busqueda_haz(problema, k)
            mostrar_resultado(f"beam search (k={k})", resultados_haz[k])
        if len(resultados_haz) > 1:
            mostrar_comparacion_haz(resultados_haz)
        return 0

    nombres = {"ambos": ("bfs", "ucs"), "bfs_dfs": ("bfs", "dfs")}.get(algoritmo, (algoritmo,))
    resultados = {}
    for nombre in nombres:
        resultados[nombre] = ALGORITMOS[nombre](problema)
        mostrar_resultado(nombre, resultados[nombre])

    if algoritmo == "ambos":
        mostrar_comparacion(resultados)
    elif algoritmo == "bfs_dfs":
        mostrar_comparacion_bfs_dfs(resultados)
    return 0


def ejecutar_partida(algoritmo, args, escenario, ruta, configuracion):
    """Continua la partida del escenario por turnos, con ambos bandos decidiendo con el mismo algoritmo.

    Proposito: ejecutar el modo ``partida`` del enunciado ("cargar el escenario completo para continuar el juego por
    turnos") desde la consola.
    Precondiciones: ``algoritmo`` es ``minimax`` o ``alfa_beta``; ``escenario`` fue validado.
    Postcondiciones: juega desde el estado cargado con la profundidad y el orden de la consola o del JSON y con el
    limite de ``--turnos``, ``prueba.max_turnos`` o ``MAX_TURNOS_POR_DEFECTO``; imprime cada jugada y el resultado;
    devuelve 0. Lanza ``ValueError`` si falta la profundidad o algun parametro no es valido.
    Complejidad: la de ``jugar_partida`` mas O(T) por presentar T jugadas.
    Uso de IA: Si.
    Intervencion de IA: Claude (Opus 5.5) implemento este flujo en E10.1.
    Validacion del estudiante: pendiente de revision del equipo; cubierta por tests/modos/test_consola_modos.py.
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
    mostrar_partida(jugar_partida(escenario, estado, profundidad, algoritmo=algoritmo, orden=orden, max_turnos=max_turnos))
    return 0


def mostrar_partida(partida):
    """Imprime cada jugada de la partida (bando, accion, valor y nodos evaluados), los pases y el resultado final."""
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


def ejecutar_modo(args, escenario, ruta):
    """Ejecuta el modo de prueba que piden la consola o el campo ``prueba`` del escenario (E10.1).

    Proposito: que la aplicacion ejecute el modo solicitado por un escenario externo sin cambios de codigo.
    Precondiciones: ``args`` viene de ``argparse`` y ``escenario`` fue cargado y validado.
    Postcondiciones: lee ``prueba``, resuelve el modo con ``resolver_modo`` y el algoritmo con la prioridad consola,
    luego ``prueba.algoritmo`` (si es del mismo modo) y luego el valor por defecto del modo (``ucs`` en busqueda y
    ``alfa_beta`` en partida y adversarial); delega en ``ejecutar_busqueda``, ``ejecutar_partida`` o
    ``ejecutar_adversarial`` y devuelve su codigo. Lanza ``ValueError`` si ``prueba`` o la combinacion de modo y
    algoritmo no son validas.
    Complejidad: la del modo ejecutado.
    Uso de IA: Si.
    Intervencion de IA: Claude (Opus 5.5) implemento el despacho por modo en E10.1.
    Validacion del estudiante: pendiente de revision del equipo; cubierta por tests/modos/test_consola_modos.py.
    """
    configuracion = leer_configuracion_prueba(escenario)
    modo = resolver_modo(args.modo, args.algoritmo, configuracion)
    algoritmo = args.algoritmo
    if algoritmo is None and configuracion is not None and configuracion.modo == modo:
        algoritmo = configuracion.algoritmo
    if algoritmo is None:
        algoritmo = "ucs" if modo == "busqueda" else "alfa_beta"

    if modo == "adversarial":
        return ejecutar_adversarial(algoritmo, args.profundidad, escenario, ruta, args.orden)
    if modo == "partida":
        return ejecutar_partida(algoritmo, args, escenario, ruta, configuracion)
    return ejecutar_busqueda(algoritmo, args, escenario, ruta, configuracion)


def ejecutar_consola(argumentos=None):
    """Carga el escenario y ejecuta los algoritmos seleccionados en modo textual.

    Purpose: conservar el ejecutor historico para BFS, DFS, UCS, A*, Beam Search (con uno o varios anchos k), las
    comparaciones BFS/UCS y BFS/DFS sobre una navegación elegida, o Minimax sobre el estado inicial del escenario.
    Preconditions: los argumentos de consola respetan el formato declarado y la ruta apunta a un escenario
    legible; los datos del escenario se validan en ``cargar_escenario``.
    Postconditions: devuelve 0 tras mostrar los resultados y, para ``ambos``, su comparación; devuelve 1 y
    muestra un error si el escenario o los parámetros de navegación no son válidos.
    Complexity: corresponde a la carga del escenario y a las búsquedas seleccionadas; la presentación agrega
    O(L) temporal y espacial para un camino de L posiciones.
    AI usage: Yes.
    AI intervention: Codex documentó el flujo, agregó la comparación E5.1 y lo extrajo intacto de ``main.py``;
    en E6.1 incorporó A* sin
    alterar la semántica de la opción ``ambos``. Claude (Opus 5.5) agregó en E7.1 la opción ``beam`` y ``--k``, y en
    E7.2 la tabla comparativa cuando se indican varios anchos; en E4.3 agregó la opción ``dfs`` y en E4.4 la
    opción ``bfs_dfs``; en E8.3 agregó la opción ``minimax`` y ``--profundidad``, en E8.4 la opción ``alfa_beta`` y en
    E8.5 la opción ``minimax_alfa_beta``, moviendo el flujo adversarial a ``ejecutar_adversarial``; en E8.6 agregó
    ``--orden``; en E10.1 agregó ``--modo`` y ``--turnos``, quitó el valor fijo de ``--algoritmo`` (el modo y el
    algoritmo se resuelven en ``ejecutar_modo``) y movió la busqueda a ``ejecutar_busqueda``.
    Student validation: pendiente de revisión del equipo.
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

    ruta = args.escenario
    if not ruta.is_absolute():
        ruta = RAIZ / ruta

    try:
        return ejecutar_modo(args, cargar_escenario(ruta), ruta)

    except (ErrorValidacionEscenario, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
