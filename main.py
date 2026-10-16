
"""Punto de entrada principal de TacticalGrid."""

import argparse
import sys
from collections.abc import Mapping
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ / "src"))

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
from tacticalgrid.juego import ProblemaNavegacion, crear_estado_inicial


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

ESCENARIO_INICIAL =RAIZ / "escenarios" / "campo_20x20.json"


def construir_problema(escenario, unidad=None, destino=None):
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
    corrigió su complejidad temporal en E6.1 para incluir el recorrido del catálogo de terrenos.
    Student validation: pendiente de revisión humana del cambio de E6.1.
    """

    prueba = escenario.configuracion_prueba

    if not isinstance(prueba, Mapping) or prueba.get("modo") != "busqueda":
        prueba = {}

    if unidad is None:
        unidad = prueba.get("unidad_inicio")

    if not unidad:
        raise ValueError(
            "Debe indicar una unidad con --unidad o definir "
            "'prueba.unidad_inicio' en el JSON."
        )

    if destino is None:
        datos = prueba.get("objetivo")

        if not isinstance(datos, Mapping):
            raise ValueError(
                "Debe indicar --objetivo FILA COLUMNA o definir "
                "'prueba.objetivo' en el JSON."
            )

        fila = datos.get("fila")
        columna = datos.get("columna")

        if type(fila) is not int or type(columna) is not int:
            raise ValueError("El objetivo debe contener fila y columna enteras.")

        destino = (fila, columna)

    objetivo = Posicion(*destino)
    problema = ProblemaNavegacion(escenario, unidad, objetivo)

    return problema, unidad, objetivo


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


def ejecutar_adversarial(algoritmo, profundidad_consola, escenario, ruta):
    """Ejecuta Minimax, alfa-beta o su comparacion sobre el estado inicial del escenario y muestra el resultado.

    Proposito: concentrar el flujo adversarial del ejecutor de consola (E8.3, E8.4 y E8.5).
    Precondiciones: ``algoritmo`` pertenece a ``ADVERSARIALES``; ``escenario`` fue cargado y validado.
    Postcondiciones: imprime el encabezado del escenario y el resultado del algoritmo o, para
    ``minimax_alfa_beta``, la tabla comparativa de E8.5; devuelve 0. Lanza ``ValueError`` si no hay una profundidad
    valida en la consola ni en el JSON.
    Complejidad: la de la busqueda o busquedas ejecutadas.
    Uso de IA: Si.
    Intervencion de IA: Claude (Opus 5.5) extrajo este flujo de ``main`` y agrego la opcion ``minimax_alfa_beta`` en
    E8.5.
    Validacion del estudiante: pendiente de revision del equipo; cubierta por las pruebas de consola de
    tests/algoritmos/test_minimax.py, test_alfa_beta.py y test_comparacion_adversarial.py.
    """
    profundidad = resolver_profundidad(profundidad_consola, escenario)
    estado = crear_estado_inicial(escenario)
    print("\nTACTICALGRID")
    print("=" * 60)
    print(f"Escenario: {ruta.name}")
    print(f"Dimensiones: {escenario.filas} x {escenario.columnas}")
    print(f"Turno: {estado.turno_actual} | Portador del recurso: {estado.portador_recurso or 'ninguno'}")
    if algoritmo == "minimax_alfa_beta":
        mostrar_comparacion_adversarial(comparar_minimax_alfa_beta(escenario, estado, profundidad))
    else:
        mostrar_resultado_minimax(DECISORES[algoritmo](escenario, estado, profundidad))
    return 0


def main():
    """Carga el escenario y ejecuta los algoritmos seleccionados.

    Purpose: ofrecer un ejecutor de consola para BFS, DFS, UCS, A*, Beam Search (con uno o varios anchos k), las
    comparaciones BFS/UCS y BFS/DFS sobre una navegación elegida, o Minimax sobre el estado inicial del escenario.
    Preconditions: los argumentos de consola respetan el formato declarado y la ruta apunta a un escenario
    legible; los datos del escenario se validan en ``cargar_escenario``.
    Postconditions: devuelve 0 tras mostrar los resultados y, para ``ambos``, su comparación; devuelve 1 y
    muestra un error si el escenario o los parámetros de navegación no son válidos.
    Complexity: corresponde a la carga del escenario y a las búsquedas seleccionadas; la presentación agrega
    O(L) temporal y espacial para un camino de L posiciones.
    AI usage: Yes.
    AI intervention: Codex documentó el flujo y agregó la comparación final de E5.1; en E6.1 incorporó A* sin
    alterar la semántica de la opción ``ambos``. Claude (Opus 5.5) agregó en E7.1 la opción ``beam`` y ``--k``, y en
    E7.2 la tabla comparativa cuando se indican varios anchos; en E4.3 agregó la opción ``dfs`` y en E4.4 la
    opción ``bfs_dfs``; en E8.3 agregó la opción ``minimax`` y ``--profundidad``, en E8.4 la opción ``alfa_beta`` y en
    E8.5 la opción ``minimax_alfa_beta``, moviendo el flujo adversarial a ``ejecutar_adversarial``.
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
        "--algoritmo",
        choices=["bfs", "dfs", "ucs", "a_estrella", "beam", "ambos", "bfs_dfs", *ADVERSARIALES],
        default="ucs",
        help="Algoritmo de búsqueda (predeterminado: ucs)",
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

    args = parser.parse_args()

    ruta = args.escenario
    if not ruta.is_absolute():
        ruta = RAIZ / ruta

    try:
        escenario = cargar_escenario(ruta)

        if args.algoritmo in ADVERSARIALES:
            return ejecutar_adversarial(args.algoritmo, args.profundidad, escenario, ruta)

        problema, unidad, objetivo = construir_problema(
            escenario,
            args.unidad,
            args.objetivo,
        )

        origen = problema.posicion(problema.estado_inicial)

        print("\nTACTICALGRID")
        print("=" * 45)
        print(f"Escenario: {ruta.name}")
        print(f"Dimensiones: {escenario.filas} x {escenario.columnas}")
        print(f"Unidad: {unidad}")
        print(f"Origen: ({origen.fila}, {origen.columna})")
        print(f"Destino: ({objetivo.fila}, {objetivo.columna})")

        if args.algoritmo == "beam":
            resultados_haz = {}
            for k in resolver_anchos_haz(args.k, escenario):
                resultados_haz[k] = busqueda_haz(problema, k)
                mostrar_resultado(f"beam search (k={k})", resultados_haz[k])
            if len(resultados_haz) > 1:
                mostrar_comparacion_haz(resultados_haz)
            return 0

        if args.algoritmo == "ambos":
            nombres = ("bfs", "ucs")
        elif args.algoritmo == "bfs_dfs":
            nombres = ("bfs", "dfs")
        else:
            nombres = (args.algoritmo,)
        seleccionados = {nombre: ALGORITMOS[nombre] for nombre in nombres}

        resultados = {}
        for nombre, algoritmo in seleccionados.items():
            resultado = algoritmo(problema)
            resultados[nombre] = resultado
            mostrar_resultado(nombre, resultado)

        if args.algoritmo == "ambos":
            mostrar_comparacion(resultados)
        elif args.algoritmo == "bfs_dfs":
            mostrar_comparacion_bfs_dfs(resultados)

        return 0

    except (ErrorValidacionEscenario, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
