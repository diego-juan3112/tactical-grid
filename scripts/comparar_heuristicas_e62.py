"""Comparar A* con Manhattan, A* con HTO y UCS en tres escenarios de TacticalGrid.

Desde la raíz del repositorio, ejecutar la campaña predeterminada con:
    .venv/bin/python scripts/comparar_heuristicas_e62.py

Para guardar los registros crudos fuera del repositorio:
    .venv/bin/python scripts/comparar_heuristicas_e62.py --salida-cruda /tmp/e62.jsonl
"""

import argparse
import json
import math
import platform
import random
import statistics
import sys
import time
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from tacticalgrid.algoritmos import busqueda_a_estrella, busqueda_costo_uniforme
from tacticalgrid.algoritmos.heuristica_obstaculos import HeuristicaObstaculos
from tacticalgrid.algoritmos.resultado_busqueda import ResultadoBusqueda
from tacticalgrid.escenario.cargador import cargar_escenario
from tacticalgrid.escenario.escenario import Escenario, Posicion
from tacticalgrid.juego.problema import ProblemaNavegacion


RAIZ_REPOSITORIO = Path(__file__).resolve().parents[1]
RUTAS_ESCENARIOS = (
    RAIZ_REPOSITORIO / "escenarios" / "obstaculo_rodeo.json",
    RAIZ_REPOSITORIO / "escenarios" / "ruta_corta_vs_economica.json",
    RAIZ_REPOSITORIO / "escenarios" / "campo_20x20.json",
)
SEMILLA_FIJA = 6022026


@dataclass(frozen=True)
class Estrategia:
    """Etiqueta experimental y algoritmo ejecutado en cada muestra."""

    algoritmo: str
    heuristica: str


@dataclass(frozen=True)
class RegistroEjecucion:
    """Muestra cruda, identificable y serializable de una estrategia."""

    escenario: str
    algoritmo: str
    heuristica: str
    repeticion: int
    orden_ejecucion: int
    muestra: str
    exito: bool
    costo: int | float | None
    longitud: int
    estados_generados: int
    estados_expandidos: int
    maximo_frontera: int
    preparacion_ns: int
    busqueda_segundos: float
    total_segundos: float


ESTRATEGIAS = (
    Estrategia("A_ESTRELLA", "MANHATTAN"),
    Estrategia("A_ESTRELLA", "HTO"),
    Estrategia("UCS", "SIN_HEURISTICA"),
)


def _resolver_configuracion(escenario: Escenario) -> tuple[str, Posicion]:
    """Obtener la unidad y el destino del bloque ``prueba`` del JSON.

    Proposito: usar sin modificaciones la configuración de navegación declarada por cada escenario.
    Precondiciones: el escenario está cargado y validado por la capa de escenario.
    Postcondiciones: se devuelven el identificador y el destino, o se lanza ``RuntimeError`` si el escenario no declara
    una prueba de navegación válida.
    Complejidad: O(1) temporal y espacial.
    Uso de IA: Si.
    Intervencion de IA: Copilot SDK: lectura de los tres escenarios requeridos desde las API reales de TacticalGrid, sin
    codificar posiciones de inicio ni de destino.
    Validacion del estudiante: ejecución del script documentada en
    docs/casos-minimos/casos-3-4-obstaculo-y-heuristicas.md; el script no tiene pruebas automatizadas propias.
    """
    prueba = escenario.configuracion_prueba
    if prueba is None or prueba.get("modo") != "busqueda":
        raise RuntimeError("El escenario no declara prueba.modo = 'busqueda'.")
    unidad = prueba.get("unidad_inicio")
    objetivo = prueba.get("objetivo")
    if not isinstance(unidad, str) or not isinstance(objetivo, Mapping):
        raise RuntimeError("La prueba debe declarar unidad_inicio y objetivo.")
    fila = objetivo.get("fila")
    columna = objetivo.get("columna")
    if (
        isinstance(fila, bool)
        or not isinstance(fila, int)
        or isinstance(columna, bool)
        or not isinstance(columna, int)
    ):
        raise RuntimeError("El objetivo debe declarar coordenadas enteras fila y columna.")
    return unidad, Posicion(fila, columna)


def _nuevo_problema(escenario: Escenario) -> ProblemaNavegacion:
    """Crear un problema y un estado inicial nuevos para una sola ejecución.

    Proposito: aislar cada muestra del estado y de los objetos que usaron otras repeticiones.
    Precondiciones: el escenario tiene una configuración válida en modo búsqueda.
    Postcondiciones: se devuelve una nueva instancia de ``ProblemaNavegacion`` construida sobre el mismo escenario
    inmutable y con un nuevo estado inicial.
    Complejidad: O(U log U + T) temporal y O(U) espacial, según el constructor del problema.
    Uso de IA: Si.
    Intervencion de IA: Copilot SDK: creación por ejecución para no compartir problemas ni estados entre el
    calentamiento, las estrategias y las repeticiones.
    Validacion del estudiante: ejecución del script documentada en
    docs/casos-minimos/casos-3-4-obstaculo-y-heuristicas.md; el script no tiene pruebas automatizadas propias.
    """
    unidad, objetivo = _resolver_configuracion(escenario)
    return ProblemaNavegacion(escenario, unidad, objetivo)


def _validar_solucion(
    problema: ProblemaNavegacion,
    resultado: ResultadoBusqueda,
    estrategia: Estrategia,
) -> None:
    """Verificar la ruta, la legalidad, el objetivo, la longitud y el costo sin afectar el tiempo medido.

    Proposito: aceptar solo soluciones reproducibles y compatibles con las reglas del problema.
    Precondiciones: la búsqueda terminó y produjo un ``ResultadoBusqueda``.
    Postcondiciones: la función retorna si la ruta es legal, termina en el objetivo, concuerda con la longitud declarada
    y reproduce exactamente el costo reportado; en otro caso se lanza ``RuntimeError``.
    Complejidad: O(L * A) temporal y O(1) espacial adicional, con L la longitud y A las acciones legales de cada estado.
    Uso de IA: Si.
    Intervencion de IA: Copilot SDK: comprobación posterior a la búsqueda con el patrón de las pruebas existentes y
    recálculo de los costos desde ``ProblemaNavegacion``.
    Validacion del estudiante: ejecución del script documentada en
    docs/casos-minimos/casos-3-4-obstaculo-y-heuristicas.md; el script no tiene pruebas automatizadas propias.
    """
    if resultado.algoritmo != estrategia.algoritmo:
        raise RuntimeError(
            f"{estrategia.algoritmo}/{estrategia.heuristica} devolvió algoritmo "
            f"{resultado.algoritmo!r}."
        )
    if not resultado.exito:
        raise RuntimeError(
            f"{estrategia.algoritmo}/{estrategia.heuristica} no encontró ruta "
            f"en el escenario asociado a {problema.objetivo}."
        )
    inicio = problema.posicion(problema.estado_inicial)
    if not resultado.camino or resultado.camino[0] != inicio:
        raise RuntimeError("El camino no comienza en la posición de la unidad navegante.")
    if resultado.longitud != len(resultado.acciones) or resultado.longitud != len(resultado.camino) - 1:
        raise RuntimeError("La longitud no coincide con las acciones y posiciones del camino.")

    estado = problema.estado_inicial
    costo_recalculado: int | float = 0
    for origen, destino, accion in zip(
        resultado.camino[:-1],
        resultado.camino[1:],
        resultado.acciones,
        strict=True,
    ):
        if accion not in problema.acciones(estado):
            raise RuntimeError(f"La acción {accion!r} no es legal en el estado actual.")
        if (accion.origen, accion.destino) != (origen, destino):
            raise RuntimeError("Las acciones no corresponden a las posiciones del camino.")
        if abs(origen.fila - destino.fila) + abs(origen.columna - destino.columna) != 1:
            raise RuntimeError(f"El movimiento {origen} -> {destino} no es ortogonal unitario.")
        if not problema.escenario.es_transitable(destino):
            raise RuntimeError(f"El camino atraviesa una celda no transitable: {destino}.")
        costo_recalculado += problema.costo(estado, accion)
        estado = problema.resultado(estado, accion)

    if not problema.es_objetivo(estado) or resultado.camino[-1] != problema.objetivo:
        raise RuntimeError("El estado final de la ruta no satisface el objetivo de navegación.")
    if resultado.costo != costo_recalculado:
        raise RuntimeError(
            f"El costo reportado {resultado.costo!r} difiere del costo recalculado "
            f"{costo_recalculado!r}."
        )
    if resultado.costo is None or not math.isfinite(resultado.tiempo_segundos):
        raise RuntimeError("La solución o su tiempo de búsqueda no son finitos.")
    if resultado.tiempo_segundos < 0:
        raise RuntimeError("El tiempo de búsqueda no puede ser negativo.")
    if min(
        resultado.estados_generados,
        resultado.estados_expandidos,
        resultado.maximo_frontera,
    ) < 0:
        raise RuntimeError("Los contadores de búsqueda no pueden ser negativos.")


def _ejecutar(
    escenario: Escenario,
    nombre_escenario: str,
    estrategia: Estrategia,
    repeticion: int,
    orden_ejecucion: int,
) -> RegistroEjecucion:
    """Ejecutar una estrategia midiendo solo los componentes que fija el contrato experimental.

    Proposito: medir la preparación de HTO con ``perf_counter_ns`` y tomar el tiempo de búsqueda del resultado
    instrumentado, con una instancia de HTO nueva en cada ejecución.
    Precondiciones: el escenario está validado; la estrategia pertenece a ``ESTRATEGIAS``; la repetición y el orden son
    positivos.
    Postcondiciones: se devuelve una muestra validada con los tiempos de preparación, búsqueda y total; la carga del
    escenario y la validación de la solución quedan fuera de ambos intervalos.
    Complejidad: la búsqueda conserva la complejidad de su algoritmo; la validación O(L * A) ocurre fuera del tiempo de
    búsqueda.
    Uso de IA: Si.
    Intervencion de IA: Copilot SDK: conexión de A*, HTO y UCS con sus interfaces existentes y cronometraje separado de
    la preparación y la búsqueda.
    Validacion del estudiante: ejecución del script documentada en
    docs/casos-minimos/casos-3-4-obstaculo-y-heuristicas.md; el script no tiene pruebas automatizadas propias.
    """
    problema = _nuevo_problema(escenario)
    heuristica: HeuristicaObstaculos | None = None
    preparacion_ns = 0

    if estrategia.algoritmo == "A_ESTRELLA" and estrategia.heuristica == "HTO":
        inicio_preparacion = time.perf_counter_ns()
        heuristica = HeuristicaObstaculos(problema)
        preparacion_ns = time.perf_counter_ns() - inicio_preparacion
        resultado = busqueda_a_estrella(problema, heuristica_preparada=heuristica)
    elif estrategia.algoritmo == "A_ESTRELLA" and estrategia.heuristica == "MANHATTAN":
        resultado = busqueda_a_estrella(problema)
    elif estrategia.algoritmo == "UCS" and estrategia.heuristica == "SIN_HEURISTICA":
        resultado = busqueda_costo_uniforme(problema)
    else:
        raise RuntimeError(f"Estrategia experimental desconocida: {estrategia!r}.")

    _validar_solucion(problema, resultado, estrategia)
    if heuristica is not None:
        if heuristica.problema is not problema:
            raise RuntimeError("HTO no está ligada a la instancia de problema de esta búsqueda.")
        if len(heuristica.estimaciones) <= 1 and not problema.es_objetivo(problema.estado_inicial):
            raise RuntimeError("A* no extendió la recurrencia de la instancia HTO registrada.")

    preparacion_segundos = preparacion_ns / 1_000_000_000
    tiempo_total = preparacion_segundos + resultado.tiempo_segundos
    if not all(math.isfinite(valor) and valor >= 0 for valor in (
        preparacion_segundos,
        resultado.tiempo_segundos,
        tiempo_total,
    )):
        raise RuntimeError("Se obtuvo una medición temporal negativa o no finita.")

    return RegistroEjecucion(
        escenario=nombre_escenario,
        algoritmo=estrategia.algoritmo,
        heuristica=estrategia.heuristica,
        repeticion=repeticion,
        orden_ejecucion=orden_ejecucion,
        muestra="medicion",
        exito=resultado.exito,
        costo=resultado.costo,
        longitud=resultado.longitud,
        estados_generados=resultado.estados_generados,
        estados_expandidos=resultado.estados_expandidos,
        maximo_frontera=resultado.maximo_frontera,
        preparacion_ns=preparacion_ns,
        busqueda_segundos=resultado.tiempo_segundos,
        total_segundos=tiempo_total,
    )


def _verificar_costos_optimos(registros: Sequence[RegistroEjecucion]) -> None:
    """Contrastar el costo de A* con el de UCS en la misma repetición.

    Proposito: usar UCS como referencia funcional por repetición, sin exigir caminos idénticos.
    Precondiciones: se recibieron exactamente las tres estrategias de una repetición y un escenario.
    Postcondiciones: se confirma que ambas variantes de A* encuentran el costo reportado por UCS, con igualdad numérica
    estricta y sin tolerancia; en otro caso se lanza ``RuntimeError``.
    Complejidad: O(1) temporal y espacial para las tres estrategias.
    Uso de IA: Si.
    Intervencion de IA: Copilot SDK: contraste con UCS después de validar cada ruta, sin cambiar los algoritmos ni sus
    resultados.
    Validacion del estudiante: ejecución del script documentada en
    docs/casos-minimos/casos-3-4-obstaculo-y-heuristicas.md; el script no tiene pruebas automatizadas propias.
    """
    referencias = [registro for registro in registros if registro.algoritmo == "UCS"]
    if len(referencias) != 1 or len(registros) != len(ESTRATEGIAS):
        raise RuntimeError("La ronda no contiene exactamente una ejecución de cada estrategia.")
    costo_ucs = referencias[0].costo
    for registro in registros:
        if registro.costo != costo_ucs:
            raise RuntimeError(
                f"Divergencia de costo en {registro.escenario}, repetición {registro.repeticion}: "
                f"{registro.algoritmo}/{registro.heuristica}={registro.costo!r}, UCS={costo_ucs!r}."
            )


def _firma_discreta(registro: RegistroEjecucion) -> tuple[object, ...]:
    """Construir la firma de métricas que debe permanecer estable entre repeticiones.

    Proposito: excluir los tiempos y comparar el éxito, la solución y los contadores discretos.
    Precondiciones: ``registro`` contiene una muestra experimental completa.
    Postcondiciones: se devuelve una tupla comparable entre ejecuciones de la misma estrategia y escenario.
    Complejidad: O(1) temporal y espacial.
    Uso de IA: Si.
    Intervencion de IA: Copilot SDK: firma discreta para detectar variaciones antes de resumir las estadísticas
    temporales.
    Validacion del estudiante: ejecución del script documentada en
    docs/casos-minimos/casos-3-4-obstaculo-y-heuristicas.md; el script no tiene pruebas automatizadas propias.
    """
    return (
        registro.exito,
        registro.costo,
        registro.longitud,
        registro.estados_generados,
        registro.estados_expandidos,
        registro.maximo_frontera,
    )


def _verificar_reproducibilidad(registros: Sequence[RegistroEjecucion]) -> None:
    """Rechazar cualquier variación discreta entre muestras equivalentes.

    Proposito: evitar promediar o resumir contadores que cambien de forma inesperada entre repeticiones.
    Precondiciones: se reciben todas las mediciones de la campaña.
    Postcondiciones: la función retorna si cada escenario y estrategia tiene una única firma discreta; en otro caso
    informa las repeticiones distintas y lanza ``RuntimeError``.
    Complejidad: O(N) temporal y O(S) espacial, con N muestras y S grupos de escenario y estrategia.
    Uso de IA: Si.
    Intervencion de IA: Copilot SDK: validación previa a la generación de las tablas descriptivas.
    Validacion del estudiante: ejecución del script documentada en
    docs/casos-minimos/casos-3-4-obstaculo-y-heuristicas.md; el script no tiene pruebas automatizadas propias.
    """
    firmas: dict[tuple[str, str, str], tuple[object, ...]] = {}
    for registro in registros:
        clave = (registro.escenario, registro.algoritmo, registro.heuristica)
        firma = _firma_discreta(registro)
        anterior = firmas.setdefault(clave, firma)
        if firma != anterior:
            raise RuntimeError(
                f"Métricas discretas no reproducibles para {clave}: "
                f"repetición {registro.repeticion}, firma={firma!r}, esperada={anterior!r}."
            )


def _describir_escenario(ruta: Path, escenario: Escenario) -> None:
    """Imprimir los datos del escenario que definen las condiciones experimentales.

    Proposito: hacer auditables la configuración, la topología, los costos y el estado inicial usados.
    Precondiciones: ``escenario`` corresponde al JSON ya cargado desde ``ruta``.
    Postcondiciones: se escriben en la salida estándar el nombre, las dimensiones, los terrenos, los obstáculos, la
    unidad, el estado y el objetivo.
    Complejidad: O(F * C + T + U) temporal y O(1) espacial adicional.
    Uso de IA: Si.
    Intervencion de IA: Copilot SDK: resumen a partir de la representación validada del escenario.
    Validacion del estudiante: ejecución del script documentada en
    docs/casos-minimos/casos-3-4-obstaculo-y-heuristicas.md; el script no tiene pruebas automatizadas propias.
    """
    unidad, objetivo = _resolver_configuracion(escenario)
    cantidades_terreno: dict[str, int] = {}
    for fila in escenario.terreno:
        for nombre in fila:
            cantidades_terreno[nombre] = cantidades_terreno.get(nombre, 0) + 1
    detalles_terreno = ", ".join(
        f"{nombre}: costo={tipo.costo!r}, transitable={tipo.transitable}, "
        f"celdas={cantidades_terreno.get(nombre, 0)}"
        for nombre, tipo in escenario.tipos_terreno.items()
    )
    muros = sum(
        cantidad
        for nombre, cantidad in cantidades_terreno.items()
        if not escenario.tipos_terreno[nombre].transitable
    )
    problema = _nuevo_problema(escenario)
    print(f"\nEscenario: {ruta.name}")
    print(f"  Dimensiones: {escenario.filas} x {escenario.columnas}")
    print(f"  Tipos/costos/transitabilidad/celdas: {detalles_terreno}")
    print(f"  Obstáculos no transitables: {muros}")
    print(f"  Unidad navegante: {unidad}; inicio: {problema.posicion(problema.estado_inicial)}")
    print(f"  Estado inicial: {problema.estado_inicial!r}")
    print(f"  Objetivo: {objetivo}; condición: posicion(unidad) == objetivo")
    print(f"  Prueba JSON: {dict(escenario.configuracion_prueba or {})!r}")


def _mediana(valores: Sequence[float]) -> float:
    """Calcular la mediana de una lista no vacía.

    Proposito: centralizar el cálculo de la mediana que usan los tiempos y la MAD descriptiva.
    Precondiciones: ``valores`` contiene al menos una muestra numérica.
    Postcondiciones: se devuelve la mediana sin modificar la secuencia, o se lanza ``RuntimeError`` si está vacía.
    Complejidad: O(N log N) temporal y O(N) espacial, según ``statistics.median``.
    Uso de IA: Si.
    Intervencion de IA: Copilot SDK: adaptador que evita resúmenes sobre grupos vacíos.
    Validacion del estudiante: ejecución del script documentada en
    docs/casos-minimos/casos-3-4-obstaculo-y-heuristicas.md; el script no tiene pruebas automatizadas propias.
    """
    if not valores:
        raise RuntimeError("No hay muestras para calcular una mediana.")
    return statistics.median(valores)


def _mad(valores: Sequence[float]) -> float:
    """Calcular la MAD no escalada: mediana de las distancias absolutas a la mediana.

    Proposito: describir la dispersión temporal con una medida robusta a valores extremos.
    Precondiciones: ``valores`` contiene mediciones finitas y no negativas.
    Postcondiciones: se devuelve la MAD en las mismas unidades, sin multiplicar por un factor de consistencia normal.
    Complejidad: O(N log N) temporal y O(N) espacial por la ordenación interna de las medianas.
    Uso de IA: Si.
    Intervencion de IA: Copilot SDK: MAD no escalada como resumen descriptivo.
    Validacion del estudiante: ejecución del script documentada en
    docs/casos-minimos/casos-3-4-obstaculo-y-heuristicas.md; el script no tiene pruebas automatizadas propias.
    """
    centro = _mediana(valores)
    return _mediana([abs(valor - centro) for valor in valores])


def _milisegundos(segundos: float) -> float:
    """Convertir segundos a milisegundos para las tablas."""
    return segundos * 1000


def _imprimir_resultados(
    registros: Sequence[RegistroEjecucion],
    repeticiones: int,
    calentamiento: int,
) -> None:
    """Presentar los resultados funcionales y temporales derivados de las muestras medidas.

    Proposito: calcular y mostrar medianas, extremos y MAD, además de las métricas discretas verificadas.
    Precondiciones: los costos óptimos y la reproducibilidad discreta ya están verificados; ``registros`` no está vacío.
    Postcondiciones: se escriben tablas cuya única fuente son las repeticiones medidas.
    Complejidad: O(N log N) temporal y O(N) espacial para agrupar y ordenar las muestras temporales.
    Uso de IA: Si.
    Intervencion de IA: Copilot SDK: tablas de resultados, con la estadística temporal limitada a las dos variantes de
    A* y UCS como referencia funcional.
    Validacion del estudiante: ejecución del script documentada en
    docs/casos-minimos/casos-3-4-obstaculo-y-heuristicas.md; el script no tiene pruebas automatizadas propias.
    """
    print("\nConfiguración experimental")
    print(f"  Python: {platform.python_version()} ({sys.executable})")
    try:
        version_pytest = version("pytest")
    except PackageNotFoundError:
        version_pytest = "no instalado en este entorno"
    print(f"  pytest: {version_pytest}")
    print(f"  Sistema operativo: {platform.platform()}")
    print(f"  Procesador/arquitectura disponible: {platform.processor() or platform.machine() or 'no disponible'}")
    print(f"  Entorno virtual activo: {'sí' if sys.prefix != sys.base_prefix else 'no'}")
    print(f"  .venv del repositorio presente: {'sí' if (RAIZ_REPOSITORIO / '.venv').is_dir() else 'no'}")
    print(f"  Repeticiones medidas por estrategia y escenario: {repeticiones}")
    print(f"  Calentamientos por estrategia y escenario (excluidos): {calentamiento}")
    print(f"  Semilla fija: {SEMILLA_FIJA}")
    print("  Orden: aleatorización reproducible de las tres estrategias en cada ronda por escenario.")
    print(f"  Resolución declarada de perf_counter: {time.get_clock_info('perf_counter').resolution * 1e9:.0f} ns")
    print("  T_total = preparación + búsqueda; la carga JSON y la validación quedan fuera.")
    print("  T_total puede diferir ligeramente del cronometraje externo de extremo a extremo.")
    print("  Dispersión temporal: MAD no escalada = mediana(|muestra - mediana|).")

    referencia_por_grupo = {
        (registro.escenario, registro.algoritmo, registro.heuristica): registro
        for registro in registros
    }
    print("\nResultados funcionales (UCS es referencia de costo óptimo)")
    print("| Escenario | Estrategia | Costo | Longitud | Generados | Expandidos | Frontera |")
    print("|---|---|---:|---:|---:|---:|---:|")
    for escenario in (ruta.name for ruta in RUTAS_ESCENARIOS):
        for estrategia in ESTRATEGIAS:
            registro = referencia_por_grupo[(escenario, estrategia.algoritmo, estrategia.heuristica)]
            etiqueta = f"{registro.algoritmo} / {registro.heuristica}"
            print(
                f"| {escenario} | {etiqueta} | {registro.costo!r} | {registro.longitud} | "
                f"{registro.estados_generados} | {registro.estados_expandidos} | "
                f"{registro.maximo_frontera} |"
            )

    print("\nResultados temporales (A*; UCS se excluye de esta comparación)")
    print(
        "| Escenario | Heurística | Preparación mediana (ms) | Búsqueda mediana (ms) | "
        "Total mediano (ms) | Dispersión |"
    )
    print("|---|---|---:|---:|---:|---|")
    for escenario in (ruta.name for ruta in RUTAS_ESCENARIOS):
        for heuristica in ("MANHATTAN", "HTO"):
            grupo = [
                registro
                for registro in registros
                if registro.escenario == escenario
                and registro.algoritmo == "A_ESTRELLA"
                and registro.heuristica == heuristica
            ]
            preparacion = [_milisegundos(r.preparacion_ns / 1e9) for r in grupo]
            busqueda = [_milisegundos(r.busqueda_segundos) for r in grupo]
            total = [_milisegundos(r.total_segundos) for r in grupo]
            if len(grupo) != repeticiones:
                raise RuntimeError(
                    f"Se esperaban {repeticiones} muestras para {escenario}/{heuristica}; "
                    f"se encontraron {len(grupo)}."
                )
            dispersion = (
                f"n={len(grupo)}; MAD prep/búsq/total="
                f"{_mad(preparacion):.6f}/{_mad(busqueda):.6f}/{_mad(total):.6f} ms; "
                f"min–max prep/búsq/total="
                f"{min(preparacion):.6f}–{max(preparacion):.6f}/"
                f"{min(busqueda):.6f}–{max(busqueda):.6f}/"
                f"{min(total):.6f}–{max(total):.6f} ms"
            )
            print(
                f"| {escenario} | {heuristica} | {_mediana(preparacion):.6f} | "
                f"{_mediana(busqueda):.6f} | {_mediana(total):.6f} | {dispersion} |"
            )


def _exportar_jsonl(registros: Sequence[RegistroEjecucion], ruta: Path) -> Path:
    """Escribir las muestras medidas como JSONL fuera del repositorio y sin sobrescribir archivos.

    Proposito: conservar todos los registros crudos de los que se derivan las tablas.
    Precondiciones: la ruta de destino se solicitó explícitamente, es externa al repositorio y no existe.
    Postcondiciones: se crea un objeto JSON por muestra, el archivo se abre en modo exclusivo y se devuelve la ruta
    absoluta; los errores de escritura se informan.
    Complejidad: O(N) temporal y espacial en los búferes de salida, con N el número de muestras.
    Uso de IA: Si.
    Intervencion de IA: Copilot SDK: exportación JSONL con la biblioteca estándar, solo con datos medidos y sin los
    calentamientos.
    Validacion del estudiante: ejecución del script documentada en
    docs/casos-minimos/casos-3-4-obstaculo-y-heuristicas.md; el script no tiene pruebas automatizadas propias.
    """
    destino = ruta.expanduser().resolve()
    try:
        destino.relative_to(RAIZ_REPOSITORIO)
    except ValueError:
        pass
    else:
        raise ValueError("La ruta de datos crudos debe quedar fuera del repositorio.")
    destino.parent.mkdir(parents=True, exist_ok=True)
    with destino.open("x", encoding="utf-8") as archivo:
        for registro in registros:
            json.dump(asdict(registro), archivo, ensure_ascii=False, allow_nan=False)
            archivo.write("\n")
    return destino


def _argumentos(argumentos: Sequence[str] | None = None) -> argparse.Namespace:
    """Interpretar las opciones públicas del ejecutor experimental.

    Proposito: configurar el calentamiento, las repeticiones y el destino opcional de los datos crudos.
    Precondiciones: los argumentos siguen la sintaxis declarada en argparse.
    Postcondiciones: se devuelve la configuración validada, o argparse muestra el error y termina.
    Complejidad: O(A) temporal y espacial respecto al número de argumentos.
    Uso de IA: Si.
    Intervencion de IA: Copilot SDK: opciones pequeñas y explícitas acordes con el uso del script.
    Validacion del estudiante: ejecución del script documentada en
    docs/casos-minimos/casos-3-4-obstaculo-y-heuristicas.md; el script no tiene pruebas automatizadas propias.
    """
    parser = argparse.ArgumentParser(
        description="Compara A* Manhattan, A* HTO y UCS en escenarios TacticalGrid."
    )
    parser.add_argument(
        "--repeticiones",
        type=int,
        default=50,
        help="rondas medidas por escenario y estrategia (predeterminado: 50)",
    )
    parser.add_argument(
        "--calentamiento",
        type=int,
        default=10,
        help="rondas iniciales no incluidas en estadísticas (predeterminado: 10)",
    )
    parser.add_argument(
        "--salida-cruda",
        type=Path,
        help="ruta JSONL opcional para datos medidos; debe estar fuera del repositorio",
    )
    opciones = parser.parse_args(argumentos)
    if opciones.repeticiones <= 0:
        parser.error("--repeticiones debe ser un entero positivo.")
    if opciones.calentamiento < 0:
        parser.error("--calentamiento no puede ser negativo.")
    if opciones.salida_cruda is not None:
        destino = opciones.salida_cruda.expanduser().resolve()
        if destino.exists():
            parser.error(f"la ruta de datos crudos ya existe: {destino}")
        try:
            destino.relative_to(RAIZ_REPOSITORIO)
        except ValueError:
            pass
        else:
            parser.error("--salida-cruda debe quedar fuera del repositorio.")
    return opciones


def main(argumentos: Sequence[str] | None = None) -> int:
    """Ejecutar el calentamiento y la campaña, verificar los datos y presentar resultados trazables.

    Proposito: coordinar la carga única de cada escenario, la aleatorización fija, las muestras y el resumen.
    Precondiciones: las dependencias de TacticalGrid están disponibles; los tres escenarios requeridos existen y son
    válidos.
    Postcondiciones: se imprimen tablas derivadas de mediciones validadas y, si se pidió, se exporta el JSONL fuera del
    repositorio; se devuelve 0. Un fallo de ejecución, validación o exportación devuelve el código 1 con su causa.
    Complejidad: O((W + R) * S * (B + V)) temporal para W calentamientos, R repeticiones, S estrategias y búsqueda y
    validación B + V; espacio O(R * S) para las muestras medidas.
    Uso de IA: Si.
    Intervencion de IA: Copilot SDK: coordinación reproducible y salida del experimento de E6.2.
    Validacion del estudiante: ejecución del script documentada en
    docs/casos-minimos/casos-3-4-obstaculo-y-heuristicas.md; el script no tiene pruebas automatizadas propias.
    """
    opciones = _argumentos(argumentos)
    generador = random.Random(SEMILLA_FIJA)
    mediciones: list[RegistroEjecucion] = []

    try:
        for ruta in RUTAS_ESCENARIOS:
            escenario = cargar_escenario(ruta)
            _describir_escenario(ruta, escenario)
            for _ in range(opciones.calentamiento):
                orden = list(ESTRATEGIAS)
                generador.shuffle(orden)
                registros_ronda = [
                    _ejecutar(
                        escenario,
                        ruta.name,
                        estrategia,
                        repeticion=0,
                        orden_ejecucion=indice,
                    )
                    for indice, estrategia in enumerate(orden, start=1)
                ]
                _verificar_costos_optimos(registros_ronda)

            for repeticion in range(1, opciones.repeticiones + 1):
                orden = list(ESTRATEGIAS)
                generador.shuffle(orden)
                registros_ronda = [
                    _ejecutar(
                        escenario,
                        ruta.name,
                        estrategia,
                        repeticion=repeticion,
                        orden_ejecucion=indice,
                    )
                    for indice, estrategia in enumerate(orden, start=1)
                ]
                _verificar_costos_optimos(registros_ronda)
                mediciones.extend(registros_ronda)

        _verificar_reproducibilidad(mediciones)
        _imprimir_resultados(mediciones, opciones.repeticiones, opciones.calentamiento)
        if opciones.salida_cruda is not None:
            salida = _exportar_jsonl(mediciones, opciones.salida_cruda)
            print(f"\nDatos crudos medidos: {salida} ({len(mediciones)} registros JSONL)")
        else:
            print(f"\nRegistros medidos en memoria: {len(mediciones)}; no se creó ningún archivo.")
    except (OSError, RuntimeError, ValueError) as error:
        print(f"Error experimental: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
