"""Compara A* Manhattan, A* HTO y UCS en tres escenarios de TacticalGrid.

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
    """Obtiene unidad y destino del bloque de prueba del JSON.

    Purpose: usar sin modificaciones la configuración de navegación declarada por cada escenario.
    Preconditions: el escenario fue cargado y validado por la capa de escenario.
    Postconditions: devuelve identificador y destino o lanza RuntimeError si el escenario no declara una
    prueba de navegación válida.
    Complexity: O(1) temporal y espacial.
    AI usage: Yes.
    AI intervention: Copilot SDK implementó la lectura de los tres escenarios requeridos desde las APIs reales
    de TacticalGrid, sin codificar posiciones de inicio o destino.
    Student validation: pendiente de validación del equipo.
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
    """Crea un problema y estado inicial frescos para una sola ejecución.

    Purpose: aislar cada muestra del estado y de los objetos que usaron otras repeticiones.
    Preconditions: el escenario tiene una configuración válida en modo búsqueda.
    Postconditions: devuelve una nueva instancia de ProblemaNavegacion construida sobre el mismo escenario
    inmutable y con un nuevo estado inicial.
    Complexity: O(U log U + T) temporal y O(U) espacial, según el constructor del problema.
    AI usage: Yes.
    AI intervention: Copilot SDK implementó la creación por ejecución para evitar compartir problemas o estados
    entre calentamiento, estrategias y repeticiones.
    Student validation: pendiente de validación del equipo.
    """
    unidad, objetivo = _resolver_configuracion(escenario)
    return ProblemaNavegacion(escenario, unidad, objetivo)


def _validar_solucion(
    problema: ProblemaNavegacion,
    resultado: ResultadoBusqueda,
    estrategia: Estrategia,
) -> None:
    """Verifica ruta, legalidad, objetivo, longitud y costo sin afectar el tiempo medido.

    Purpose: aceptar únicamente soluciones reproducibles y compatibles con las reglas del problema.
    Preconditions: la búsqueda terminó y produjo un ResultadoBusqueda.
    Postconditions: retorna si la ruta es legal, termina en el objetivo, concuerda con la longitud declarada y
    reproduce exactamente el costo reportado; en caso contrario lanza RuntimeError.
    Complexity: O(L * A) temporal y O(1) espacial adicional, donde L es la longitud y A las acciones legales
    de cada estado.
    AI usage: Yes.
    AI intervention: Copilot SDK implementó la comprobación posterior a la búsqueda siguiendo el patrón de los
    tests existentes y recalculando los costos desde ProblemaNavegacion.
    Student validation: pendiente de validación del equipo.
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
    """Ejecuta una estrategia, midiendo sólo los componentes establecidos por el contrato.

    Purpose: medir el preprocesamiento HTO con perf_counter_ns y tomar el tiempo de búsqueda del resultado
    instrumentado, creando una instancia HTO nueva en cada ejecución.
    Preconditions: escenario validado; estrategia pertenece a ESTRATEGIAS; repetición y orden son positivos.
    Postconditions: retorna una muestra validada con tiempos de preparación, búsqueda y suma total; el costo de
    carga del escenario y la validación de la solución quedan fuera de ambos intervalos.
    Complexity: la búsqueda conserva la complejidad de su algoritmo; la validación O(L * A) ocurre fuera del
    tiempo de búsqueda.
    AI usage: Yes.
    AI intervention: Copilot SDK conectó A*, HTO y UCS con sus interfaces existentes y aplicó la convención
    distinta de cronometraje prescrita para preparación y búsqueda.
    Student validation: pendiente de validación del equipo.
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
    """Contrasta A* con el costo de UCS en la misma repetición.

    Purpose: usar UCS como referencia funcional por repetición, sin exigir caminos idénticos.
    Preconditions: se recibieron exactamente las tres estrategias de una repetición y escenario.
    Postconditions: confirma que ambas variantes A* encuentran el costo reportado por UCS, mediante igualdad
    numérica estricta y sin tolerancia; de otro modo lanza RuntimeError.
    Complexity: O(1) temporal y espacial para las tres estrategias.
    AI usage: Yes.
    AI intervention: Copilot SDK añadió el contraste con UCS después de validar cada ruta y sin cambiar los
    algoritmos ni sus resultados.
    Student validation: pendiente de validación del equipo.
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
    """Construye la firma de métricas que debe permanecer estable entre repeticiones.

    Purpose: excluir los tiempos y comparar éxito, solución y contadores discretos.
    Preconditions: registro contiene una muestra experimental completa.
    Postconditions: retorna una tupla comparable entre ejecuciones de la misma estrategia y escenario.
    Complexity: O(1) temporal y espacial.
    AI usage: Yes.
    AI intervention: Copilot SDK implementó una firma discreta para detectar variaciones antes de resumir
    estadísticas temporales.
    Student validation: pendiente de validación del equipo.
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
    """Rechaza cualquier variación discreta entre muestras equivalentes.

    Purpose: evitar promediar o resumir contadores que cambien inesperadamente entre repeticiones.
    Preconditions: contiene todas las mediciones de la campaña.
    Postconditions: retorna si cada escenario y estrategia tiene una única firma discreta; de lo contrario,
    informa las repeticiones distintas y lanza RuntimeError.
    Complexity: O(N) temporal y O(S) espacial, donde N son muestras y S grupos escenario-estrategia.
    AI usage: Yes.
    AI intervention: Copilot SDK implementó la validación previa a la generación de las tablas descriptivas.
    Student validation: pendiente de validación del equipo.
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
    """Imprime los datos de escenario que definen las condiciones experimentales.

    Purpose: hacer auditable la configuración, topología, costos y estado inicial usados.
    Preconditions: escenario corresponde al JSON ya cargado desde ruta.
    Postconditions: escribe en stdout el nombre, dimensiones, terrenos, obstáculos, unidad, estado y objetivo.
    Complexity: O(F * C + T + U) temporal y O(1) espacial adicional.
    AI usage: Yes.
    AI intervention: Copilot SDK implementó el resumen a partir de la representación validada del escenario.
    Student validation: pendiente de validación del equipo.
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
    """Calcula la mediana de una lista no vacía.

    Purpose: centralizar el cálculo de mediana usado para tiempos y MAD descriptivos.
    Preconditions: valores contiene al menos una muestra numérica.
    Postconditions: devuelve la mediana sin modificar la secuencia o lanza RuntimeError si está vacía.
    Complexity: O(N log N) temporal y O(N) espacial según statistics.median.
    AI usage: Yes.
    AI intervention: Copilot SDK implementó este adaptador para evitar resúmenes sobre grupos vacíos.
    Student validation: pendiente de validación del equipo.
    """
    if not valores:
        raise RuntimeError("No hay muestras para calcular una mediana.")
    return statistics.median(valores)


def _mad(valores: Sequence[float]) -> float:
    """Calcula MAD no escalada: mediana de las distancias absolutas a la mediana.

    Purpose: describir la dispersión temporal con una medida robusta a valores extremos.
    Preconditions: valores contiene mediciones finitas y no negativas.
    Postconditions: devuelve MAD en las mismas unidades, sin multiplicar por un factor de consistencia normal.
    Complexity: O(N log N) temporal y O(N) espacial por la ordenación interna de medianas.
    AI usage: Yes.
    AI intervention: Copilot SDK implementó MAD no escalada como resumen descriptivo solicitado.
    Student validation: pendiente de validación del equipo.
    """
    centro = _mediana(valores)
    return _mediana([abs(valor - centro) for valor in valores])


def _milisegundos(segundos: float) -> float:
    """Convierte segundos a milisegundos para las tablas."""
    return segundos * 1000


def _imprimir_resultados(
    registros: Sequence[RegistroEjecucion],
    repeticiones: int,
    calentamiento: int,
) -> None:
    """Presenta resultados funcionales y temporales derivados de las muestras medidas.

    Purpose: calcular y mostrar medianas, extremos y MAD, además de métricas discretas verificadas.
    Preconditions: costos óptimos y reproducibilidad discreta ya verificados; registros no está vacío.
    Postconditions: escribe tablas cuya fuente son únicamente las repeticiones medidas.
    Complexity: O(N log N) temporal y O(N) espacial para agrupar y ordenar las muestras temporales.
    AI usage: Yes.
    AI intervention: Copilot SDK implementó las tablas pedidas y limita la estadística temporal a las dos
    variantes A*, dejando UCS como referencia funcional.
    Student validation: pendiente de validación del equipo.
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
    """Escribe muestras medidas como JSONL fuera del repositorio y sin sobrescribir archivos.

    Purpose: preservar todos los registros crudos de los que se derivan las tablas.
    Preconditions: la ruta de destino se solicitó explícitamente, es externa al repositorio y no existe.
    Postconditions: crea un objeto JSON por muestra, abre el archivo en modo exclusivo y devuelve la ruta
    absoluta; informa errores de escritura en lugar de ocultarlos.
    Complexity: O(N) temporal y espacial en buffers de salida, donde N es el número de muestras.
    AI usage: Yes.
    AI intervention: Copilot SDK implementó exportación JSONL con la biblioteca estándar y guarda sólo datos
    medidos, nunca los calentamientos.
    Student validation: pendiente de validación del equipo.
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
    """Interpreta las opciones públicas del ejecutor experimental.

    Purpose: permitir configurar calentamiento, repeticiones y destino opcional de datos crudos.
    Preconditions: argumentos siguen la sintaxis declarada por argparse.
    Postconditions: devuelve configuración validada o argparse muestra el error y termina.
    Complexity: O(A) temporal y espacial respecto al número de argumentos.
    AI usage: Yes.
    AI intervention: Copilot SDK definió opciones pequeñas y explícitas conforme al uso del script.
    Student validation: pendiente de validación del equipo.
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
    """Ejecuta calentamiento y campaña, verifica datos y presenta resultados trazables.

    Purpose: coordinar la carga única de cada escenario, la aleatorización fija, las muestras y el resumen.
    Preconditions: dependencias de TacticalGrid disponibles; los tres escenarios requeridos existen y son válidos.
    Postconditions: imprime tablas derivadas de mediciones validadas y, si se pidió, exporta JSONL fuera del
    repositorio; devuelve 0. Un fallo de ejecución, validación o exportación se hace explícito con código 1.
    Complexity: O((W + R) * S * (B + V)) temporal para W calentamientos, R repeticiones, S estrategias y
    búsqueda/validación B + V; espacio O(R * S) para las muestras medidas.
    AI usage: Yes.
    AI intervention: Copilot SDK implementó la coordinación reproducible y la salida del experimento E6.2.
    Student validation: pendiente de validación del equipo.
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
