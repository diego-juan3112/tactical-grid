
"""Punto de entrada principal de TacticalGrid."""

import argparse
import sys
from collections.abc import Mapping
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ / "src"))

from tacticalgrid.algoritmos import busqueda_a_estrella, busqueda_anchura, busqueda_costo_uniforme
from tacticalgrid.escenario import (
    ErrorValidacionEscenario,
    Posicion,
    cargar_escenario,
)
from tacticalgrid.juego import ProblemaNavegacion


ALGORITMOS = {
    "bfs": busqueda_anchura,
    "ucs": busqueda_costo_uniforme,
    "a_estrella": busqueda_a_estrella,
}

ESCENARIO_INICIAL = RAIZ / "escenarios" / "campo_20x20.json"


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


def main():
    """Carga el escenario y ejecuta los algoritmos seleccionados.

    Purpose: ofrecer un ejecutor de consola para BFS, UCS, A* o la comparación existente BFS/UCS sobre un
    escenario y una navegación elegidos.
    Preconditions: los argumentos de consola respetan el formato declarado y la ruta apunta a un escenario
    legible; los datos del escenario se validan en ``cargar_escenario``.
    Postconditions: devuelve 0 tras mostrar los resultados y, para ``ambos``, su comparación; devuelve 1 y
    muestra un error si el escenario o los parámetros de navegación no son válidos.
    Complexity: corresponde a la carga del escenario y a las búsquedas seleccionadas; la presentación agrega
    O(L) temporal y espacial para un camino de L posiciones.
    AI usage: Yes.
    AI intervention: Codex documentó el flujo y agregó la comparación final de E5.1; en E6.1 incorporó A* sin
    alterar la semántica de la opción ``ambos``.
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
        choices=["bfs", "ucs", "a_estrella", "ambos"],
        default="ucs",
        help="Algoritmo de búsqueda (predeterminado: ucs)",
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

        seleccionados = (
            {nombre: ALGORITMOS[nombre] for nombre in ("bfs", "ucs")}
            if args.algoritmo == "ambos"
            else {args.algoritmo: ALGORITMOS[args.algoritmo]}
        )

        resultados = {}
        for nombre, algoritmo in seleccionados.items():
            resultado = algoritmo(problema)
            resultados[nombre] = resultado
            mostrar_resultado(nombre, resultado)

        if args.algoritmo == "ambos":
            mostrar_comparacion(resultados)

        return 0

    except (ErrorValidacionEscenario, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
