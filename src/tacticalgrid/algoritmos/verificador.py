"""Verificador de soluciones (E10.2): comprueba propiedades basicas de cada respuesta en lugar de confiar en ella.

No reutiliza los resultados internos de los algoritmos: reproduce cada respuesta con las reglas del juego (E1.2, E1.3,
E8.1) y compara. Cada verificacion devuelve un :class:`ReporteVerificacion` con una comprobacion por propiedad, sin
detenerse en la primera falla, para que el reporte diga exactamente que esta mal.

- :func:`verificar_busqueda` (BFS, DFS, UCS, A*, Beam Search): movimientos validos, ningun obstaculo atravesado,
  camino coherente con las acciones, costo igual a las transiciones, estado final objetivo, estados validos y metricas
  coherentes.
- :func:`verificar_decision` (Minimax y alfa-beta): regenera el arbol con las mismas reglas, orden y profundidad, y
  comprueba que toda accion considerada en cualquier nodo es legal, que todo estado generado es valido, que el valor
  y la accion elegida son los de Minimax exacto y que las metricas son coherentes con el arbol.
- :func:`verificar_partida` (modo ``partida``): cada jugada es legal y produce el estado siguiente, y el resultado
  final corresponde al ultimo estado.
"""

import math
from dataclasses import dataclass

from tacticalgrid.escenario.escenario import Escenario, Posicion
from tacticalgrid.juego.accion import MOVER
from tacticalgrid.juego.estado import EstadoJuego
from tacticalgrid.juego.partida import preparar_turno
from tacticalgrid.juego.problema import ProblemaNavegacion
from tacticalgrid.juego.reglas import (
    EMPATE_BLOQUEO,
    EN_CURSO,
    aplicar_accion,
    es_accion_valida,
    es_terminal,
    obtener_ganador,
)
from tacticalgrid.juego.tacticas import acciones_tacticas, clasificar_accion

from .minimax import ResultadoMinimax
from .orden_acciones import ordenar_acciones
from .resultado_busqueda import ResultadoBusqueda
from .utilidad import EvaluadorUtilidad, pesos_desde_configuracion

BANDOS = ("A", "B")
ESTADOS_PARTIDA = (EN_CURSO, EMPATE_BLOQUEO, "victoria_A", "victoria_B")
MAXIMO_DETALLES = 3


@dataclass(frozen=True)
class Comprobacion:
    """Resultado de comprobar una propiedad: nombre, si se cumple y un detalle legible."""

    nombre: str
    correcta: bool
    detalle: str


@dataclass(frozen=True)
class ReporteVerificacion:
    """Conjunto de comprobaciones realizadas sobre una respuesta."""

    sujeto: str
    comprobaciones: tuple[Comprobacion, ...]

    @property
    def es_valido(self) -> bool:
        """Verdadero solo si todas las comprobaciones se cumplen."""
        return all(c.correcta for c in self.comprobaciones)

    @property
    def fallidas(self) -> tuple[Comprobacion, ...]:
        """Comprobaciones que no se cumplen, en el orden en que se hicieron."""
        return tuple(c for c in self.comprobaciones if not c.correcta)


def _comprobacion(nombre: str, errores: list[str], detalle_correcto: str) -> Comprobacion:
    if not errores:
        return Comprobacion(nombre, True, detalle_correcto)
    resto = f" (y {len(errores) - MAXIMO_DETALLES} mas)" if len(errores) > MAXIMO_DETALLES else ""
    return Comprobacion(nombre, False, "; ".join(errores[:MAXIMO_DETALLES]) + resto)


def _texto(posicion: Posicion) -> str:
    return f"({posicion.fila}, {posicion.columna})"


def errores_de_estado(escenario: Escenario, estado: EstadoJuego, exigir_celdas_libres: bool = True) -> tuple[str, ...]:
    """Devuelve los motivos por los que ``estado`` no es un estado valido del juego (tupla vacia si es valido).

    Proposito: detectar estados invalidos generados por cualquier algoritmo, con las mismas invariantes que el validador
    de escenarios (E2.2) aplica al estado inicial, mas las de la dinamica del juego.
    Precondiciones: ``escenario`` fue validado. ``exigir_celdas_libres`` es falso para estados de navegacion, donde
    E1.2 decidio que las demas unidades no bloquean y dos unidades pueden compartir celda.
    Postcondiciones: comprueba ids unicos, bandos y turno validos, unidades dentro del mapa y sobre terreno transitable,
    celdas no compartidas (si se exige), coherencia entre ``portador_recurso`` y ``posicion_recurso``, que el recurso
    libre este dentro del mapa, que ``estado_partida`` sea un valor conocido y que una victoria registrada coincida
    con el portador en su base. No modifica nada.
    Complejidad: O(U) temporal y espacial, donde U es la cantidad de unidades.
    Uso de IA: Si.
    Intervencion de IA: Claude (Opus 5.5) definio las invariantes y las implemento en E10.2.
    Validacion del estudiante: el estudiante reviso y valido el codigo; ademas, las pruebas de
    tests/algoritmos/test_verificador.py construyen un estado invalido por cada invariante.
    """
    errores: list[str] = []
    identificadores = [u.identificador for u in estado.unidades]
    if len(set(identificadores)) != len(identificadores):
        errores.append("hay identificadores de unidad repetidos")
    if estado.turno_actual not in BANDOS:
        errores.append(f"turno invalido {estado.turno_actual!r}")
    posiciones: dict[Posicion, str] = {}
    for unidad in estado.unidades:
        if unidad.bando not in BANDOS:
            errores.append(f"la unidad {unidad.identificador} tiene bando invalido {unidad.bando!r}")
        if not escenario.contiene_posicion(unidad.posicion):
            errores.append(f"la unidad {unidad.identificador} esta fuera del mapa en {_texto(unidad.posicion)}")
            continue
        if not escenario.es_transitable(unidad.posicion):
            errores.append(f"la unidad {unidad.identificador} esta sobre un obstaculo en {_texto(unidad.posicion)}")
        if exigir_celdas_libres and unidad.posicion in posiciones:
            errores.append(
                f"{unidad.identificador} y {posiciones[unidad.posicion]} comparten la celda {_texto(unidad.posicion)}"
            )
        posiciones.setdefault(unidad.posicion, unidad.identificador)
    if estado.portador_recurso is None:
        if estado.posicion_recurso is None:
            errores.append("el recurso no tiene portador ni posicion")
        elif not escenario.contiene_posicion(estado.posicion_recurso):
            errores.append(f"el recurso libre esta fuera del mapa en {_texto(estado.posicion_recurso)}")
    else:
        if estado.portador_recurso not in identificadores:
            errores.append(f"el portador {estado.portador_recurso!r} no es una unidad del estado")
        if estado.posicion_recurso is not None:
            errores.append("el recurso tiene portador y a la vez una posicion libre")
    if estado.estado_partida not in ESTADOS_PARTIDA:
        errores.append(f"estado de partida desconocido {estado.estado_partida!r}")
    elif estado.estado_partida.startswith("victoria_") and not errores:
        ganador = obtener_ganador(escenario, estado)
        if f"victoria_{ganador}" != estado.estado_partida:
            errores.append(f"se registra {estado.estado_partida} pero el portador no esta en la base de ese bando")
    return tuple(errores)


def _manhattan(a: Posicion, b: Posicion) -> int:
    return abs(a.fila - b.fila) + abs(a.columna - b.columna)


def verificar_busqueda(problema: ProblemaNavegacion, resultado: ResultadoBusqueda) -> ReporteVerificacion:
    """Verifica la respuesta de un algoritmo de busqueda reproduciendo cada accion con las reglas del problema.

    Proposito: comprobar que la solucion reportada por BFS, DFS, UCS, A* o Beam Search es realmente una solucion: no
    basta con que el algoritmo haya terminado sin error.
    Precondiciones: ``resultado`` fue producido para ``problema``.
    Postcondiciones: devuelve un reporte con las comprobaciones ``movimientos_validos``, ``sin_obstaculos``,
    ``camino_coherente``, ``costo_coincide``, ``estado_final_objetivo``, ``estados_validos`` y
    ``metricas_coherentes``. Si el resultado es un fracaso, comprueba ``fracaso_coherente`` (camino y acciones vacios,
    costo nulo) y las metricas; no afirma que no exista ruta, porque Beam Search puede fracasar aunque exista. Si una
    accion no se puede reproducir, se detiene la reproduccion y las comprobaciones dependientes fallan con el motivo.
    No modifica nada.
    Complejidad: O(L * (U + T)) temporal y O(L) espacial, donde L es la longitud del camino, U las unidades y T el costo
    de una transicion.
    Uso de IA: Si.
    Intervencion de IA: Claude (Opus 5.5) diseno las comprobaciones y las implemento en E10.2.
    Validacion del estudiante: el estudiante reviso y valido el codigo; ademas, las pruebas de
    tests/algoritmos/test_verificador.py verifican las respuestas reales de los cinco algoritmos y detectan resultados
    alterados a proposito (movimiento invalido, muro, costo falso, objetivo no alcanzado).
    """
    sujeto = f"{resultado.algoritmo} (busqueda)"
    metricas: list[str] = []
    if resultado.estados_generados < 1:
        metricas.append("debe haber al menos un estado generado (el inicial)")
    if resultado.estados_expandidos > resultado.estados_generados:
        metricas.append("hay mas estados expandidos que generados")
    if not 1 <= resultado.maximo_frontera <= max(resultado.estados_generados, 1):
        metricas.append(f"maximo de frontera fuera de rango ({resultado.maximo_frontera})")
    if resultado.longitud != len(resultado.acciones):
        metricas.append("la longitud no coincide con la cantidad de acciones")
    comprobacion_metricas = _comprobacion("metricas_coherentes", metricas, "contadores y longitud consistentes")

    if not resultado.exito:
        fracaso = []
        if resultado.camino or resultado.acciones:
            fracaso.append("un fracaso no debe reportar camino ni acciones")
        if resultado.costo is not None:
            fracaso.append("un fracaso debe reportar costo nulo")
        return ReporteVerificacion(
            sujeto,
            (_comprobacion("fracaso_coherente", fracaso, "sin camino, sin acciones y costo nulo"), comprobacion_metricas),
        )

    movimientos: list[str] = []
    obstaculos: list[str] = []
    camino: list[str] = []
    estados: list[str] = []
    objetivo: list[str] = []
    costo: list[str] = []

    for posicion in resultado.camino:
        if not escenario_contiene_transitable(problema.escenario, posicion):
            obstaculos.append(f"el camino pasa por {_texto(posicion)}, fuera del mapa o no transitable")
    if len(resultado.camino) != len(resultado.acciones) + 1:
        camino.append("el camino debe tener una posicion mas que acciones")
    estado = problema.estado_inicial
    if not resultado.camino or resultado.camino[0] != problema.posicion(estado):
        camino.append("el camino no empieza en la posicion inicial de la unidad")
    estados.extend(errores_de_estado(problema.escenario, estado, exigir_celdas_libres=False))

    costo_total: int | float = 0
    reproducido = True
    for indice, accion in enumerate(resultado.acciones, start=1):
        actual = problema.posicion(estado)
        if accion.tipo != MOVER or accion.origen != actual or _manhattan(accion.origen, accion.destino) != 1:
            movimientos.append(f"paso {indice}: {_texto(accion.origen)} -> {_texto(accion.destino)} no es un movimiento ortogonal desde {_texto(actual)}")
        if not escenario_contiene_transitable(problema.escenario, accion.destino):
            obstaculos.append(f"paso {indice}: el destino {_texto(accion.destino)} es un obstaculo o esta fuera del mapa")
        if accion not in problema.acciones(estado):
            movimientos.append(f"paso {indice}: la accion no es legal en el estado alcanzado")
            reproducido = False
            break
        costo_total += problema.costo(estado, accion)
        estado = problema.resultado(estado, accion)
        estados.extend(f"paso {indice}: {e}" for e in errores_de_estado(problema.escenario, estado, exigir_celdas_libres=False))
        if indice < len(resultado.camino) and resultado.camino[indice] != problema.posicion(estado):
            camino.append(f"paso {indice}: el camino dice {_texto(resultado.camino[indice])} pero la unidad queda en {_texto(problema.posicion(estado))}")

    if not reproducido:
        costo.append("no se puede recalcular: el camino no se pudo reproducir")
        objetivo.append("no se puede comprobar: el camino no se pudo reproducir")
    else:
        if resultado.costo is None or not math.isclose(costo_total, resultado.costo):
            costo.append(f"el costo reportado es {resultado.costo} y las transiciones suman {costo_total}")
        if not problema.es_objetivo(estado):
            objetivo.append(f"el estado final deja la unidad en {_texto(problema.posicion(estado))}, no en el objetivo")

    return ReporteVerificacion(
        sujeto,
        (
            _comprobacion("movimientos_validos", movimientos, f"{len(resultado.acciones)} movimientos legales"),
            _comprobacion("sin_obstaculos", obstaculos, "ninguna celda del camino es un obstaculo"),
            _comprobacion("camino_coherente", camino, "el camino coincide con las acciones aplicadas"),
            _comprobacion("costo_coincide", costo, f"costo {costo_total} igual a la suma de las transiciones"),
            _comprobacion("estado_final_objetivo", objetivo, "el estado final cumple la condicion objetivo"),
            _comprobacion("estados_validos", estados, f"{len(resultado.acciones) + 1} estados validos"),
            comprobacion_metricas,
        ),
    )


def escenario_contiene_transitable(escenario: Escenario, posicion: Posicion) -> bool:
    """Verdadero si ``posicion`` esta dentro del mapa y su terreno es transitable segun el JSON."""
    return escenario.contiene_posicion(posicion) and escenario.es_transitable(posicion)


class _Arbol:
    """Recorrido independiente del arbol de juego con el que se contrastan las decisiones adversariales."""

    def __init__(self, escenario: Escenario, evaluador: EvaluadorUtilidad, profundidad_maxima: int, orden: str) -> None:
        """Prepara un recorrido completo del arbol de juego con contadores y listas de errores vacios.

        Proposito: disponer de una referencia independiente de Minimax y alfa-beta para verificar sus decisiones y
        metricas (E10.2).
        Precondiciones: ``evaluador.bando_max`` es el bando MAX de la decision a verificar; ``profundidad_maxima`` y
        ``orden`` son los mismos con los que se tomo esa decision.
        Postcondiciones: el recorrido queda con nodos, hojas, profundidad alcanzada y acciones revisadas en 0 y sin
        errores registrados (acciones ilegales, tipos tacticos incorrectos ni estados invalidos).
        Complejidad: O(1) temporal y espacial.
        Uso de IA: Si.
        Intervencion de IA: Claude (Opus 5.5) lo implemento en E10.2 y redacto esta documentacion en E11.1.
        Validacion del estudiante: revisado y aprobado por el equipo; cubierta por tests/algoritmos/test_verificador.py.
        """
        self.escenario = escenario
        self.evaluador = evaluador
        self.profundidad_maxima = profundidad_maxima
        self.orden = orden
        self.nodos = 0
        self.hojas = 0
        self.profundidad_alcanzada = 0
        self.acciones_revisadas = 0
        self.ilegales: list[str] = []
        self.tacticas: list[str] = []
        self.invalidos: list[str] = []

    def acciones(self, estado: EstadoJuego):
        """Devuelve las acciones que el algoritmo considera en ``estado`` y comprueba cada una contra las reglas.

        Proposito: verificar el requisito del enunciado de que toda accion considerada por Minimax sea legal, y que
        su tipo tactico sea el que asigna E8.1.
        Precondiciones: ``estado`` ya paso por ``preparar_turno`` y es coherente con el escenario.
        Postcondiciones: devuelve una tupla vacia si el estado es terminal; si no, las ``acciones_tacticas`` en el
        orden del recorrido. Por cada accion suma 1 a ``acciones_revisadas`` y registra en ``ilegales`` la que no
        sea valida y en ``tacticas`` la que tenga un tipo tactico distinto del de ``clasificar_accion``. No modifica
        ``estado``.
        Complejidad: O(A * U) temporal y O(A) espacial, con A acciones y U unidades.
        Uso de IA: Si.
        Intervencion de IA: Claude (Opus 5.5) lo implemento en E10.2 y redacto esta documentacion en E11.1.
        Validacion del estudiante: revisado y aprobado por el equipo; cubierta por tests/algoritmos/test_verificador.py,
        que comprueba decisiones reales y detecta acciones ilegales e intercepciones inventadas.
        """
        if es_terminal(self.escenario, estado):
            return ()
        acciones = ordenar_acciones(acciones_tacticas(self.escenario, estado), self.orden)
        for accion_tactica in acciones:
            self.acciones_revisadas += 1
            if not es_accion_valida(self.escenario, estado, accion_tactica.accion):
                self.ilegales.append(f"{accion_tactica.accion} no es legal")
            elif accion_tactica.tipo_tactico != clasificar_accion(self.escenario, estado, accion_tactica.accion):
                self.tacticas.append(f"{accion_tactica.accion} tiene tipo tactico incorrecto")
        return acciones

    def generar(self, estado: EstadoJuego, accion_tactica) -> EstadoJuego:
        sucesor = aplicar_accion(self.escenario, estado, accion_tactica.accion)
        self.nodos += 1
        self.invalidos.extend(errores_de_estado(self.escenario, sucesor))
        return sucesor

    def valor(self, estado: EstadoJuego, profundidad: int) -> float:
        """Calcula el valor Minimax exacto de ``estado`` recorriendo todo el subarbol, sin poda.

        Proposito: obtener la referencia con la que se comprueba que la decision, el valor y las metricas reportadas
        por Minimax o alfa-beta corresponden al arbol real.
        Precondiciones: ``0 <= profundidad <= profundidad_maxima``; ``estado`` es coherente con el escenario.
        Postcondiciones: devuelve el valor Minimax con las mismas reglas que E8.3: aplica ``preparar_turno``, evalua
        las hojas (profundidad maxima, estado terminal o sin acciones) y toma el maximo o el minimo segun quien
        mueve. Cuenta hojas, nodos generados y profundidad alcanzada, y revisa cada accion y cada sucesor generado.
        Complejidad: O(b^(d-p)) nodos, igual que Minimax, porque no poda; espacio O(d) por la recursion.
        Uso de IA: Si.
        Intervencion de IA: Claude (Opus 5.5) lo implemento en E10.2 y redacto esta documentacion en E11.1.
        Validacion del estudiante: revisado y aprobado por el equipo; cubierta por tests/algoritmos/test_verificador.py,
        que comprueba que Minimax reporta exactamente el arbol regenerado y detecta valores y metricas falsos.
        """
        self.profundidad_alcanzada = max(self.profundidad_alcanzada, profundidad)
        estado = preparar_turno(self.escenario, estado)
        if profundidad == self.profundidad_maxima:
            self.hojas += 1
            return self.evaluador.evaluar(estado)
        acciones = self.acciones(estado)
        if not acciones:
            self.hojas += 1
            return self.evaluador.evaluar(estado)
        es_max = estado.turno_actual == self.evaluador.bando_max
        valores = [self.valor(self.generar(estado, accion), profundidad + 1) for accion in acciones]
        return max(valores) if es_max else min(valores)


def verificar_decision(
    escenario: Escenario,
    estado: EstadoJuego,
    resultado: ResultadoMinimax,
    evaluador: EvaluadorUtilidad | None = None,
) -> ReporteVerificacion:
    """Verifica una decision de Minimax o alfa-beta regenerando el arbol de juego que debio explorar.

    Proposito: comprobar que las acciones consideradas por Minimax son legales en todo el arbol, no solo en la raiz, y
    que la decision y las metricas reportadas corresponden a ese arbol.
    Precondiciones: ``resultado`` fue producido por ``minimax`` o ``alfa_beta`` para ``estado`` y ``escenario``; si se
    paso un evaluador al algoritmo, debe pasarse el mismo aqui (si no, se usan los pesos del JSON, como el algoritmo).
    Postcondiciones: devuelve un reporte con ``acciones_consideradas_legales``, ``tacticas_coherentes``,
    ``estados_validos``, ``accion_seleccionada_legal``, ``valores_raiz_legales``, ``valor_correcto``,
    ``decision_optima`` y ``metricas_coherentes``. El arbol se regenera con la misma profundidad, orden de acciones y
    utilidad; para Minimax los nodos generados, evaluados y la profundidad alcanzada deben coincidir exactamente, y
    para alfa-beta no pueden superar a los del arbol completo. No modifica nada.
    Complejidad: la de Minimax completo, O(b^d) nodos con O(U^2) por nodo, porque recorre todo el arbol.
    Uso de IA: Si.
    Intervencion de IA: Claude (Opus 5.5) propuso contrastar con un recorrido independiente del arbol y lo implemento en
    E10.2.
    Validacion del estudiante: el estudiante reviso y valido el codigo; ademas, las pruebas de
    tests/algoritmos/test_verificador.py verifican decisiones reales de Minimax y alfa-beta con los tres ordenes y
    detectan decisiones alteradas a proposito (accion ilegal, valor falso, accion no optima, metricas falsas).
    """
    if evaluador is None:
        evaluador = EvaluadorUtilidad(escenario, resultado.bando_max, pesos_desde_configuracion(escenario.configuracion_juego))
    arbol = _Arbol(escenario, evaluador, resultado.profundidad_maxima, resultado.orden_acciones)
    estados = list(errores_de_estado(escenario, estado))
    arbol.nodos = 1
    raiz = preparar_turno(escenario, estado)
    puede_actuar = not es_terminal(escenario, raiz) and raiz.turno_actual == evaluador.bando_max
    acciones_raiz = arbol.acciones(raiz) if puede_actuar else ()
    if acciones_raiz:
        valores = [arbol.valor(arbol.generar(raiz, accion), 1) for accion in acciones_raiz]
        valor_exacto = max(valores)
        optima = acciones_raiz[valores.index(valor_exacto)]
    else:
        valor_exacto = arbol.valor(raiz, 0)
        optima = None
    estados.extend(arbol.invalidos)

    seleccion: list[str] = []
    seleccionada = resultado.accion_seleccionada
    if seleccionada is None:
        if acciones_raiz:
            seleccion.append("no se selecciono accion aunque el bando en turno tiene acciones legales")
    elif not puede_actuar or not es_accion_valida(escenario, raiz, seleccionada.accion):
        seleccion.append(f"la accion seleccionada {seleccionada.accion} no es legal en la raiz")

    raiz_ilegal = [
        f"{accion.accion} no es legal en la raiz"
        for accion, _ in resultado.valores_raiz
        if not puede_actuar or not es_accion_valida(escenario, raiz, accion.accion)
    ]
    if not raiz_ilegal and [a for a, _ in resultado.valores_raiz] != list(acciones_raiz):
        raiz_ilegal.append("las acciones de la raiz no coinciden con las acciones legales en el orden configurado")

    valor: list[str] = []
    if not math.isclose(resultado.valor, valor_exacto):
        valor.append(f"el valor reportado es {resultado.valor} y el valor Minimax exacto es {valor_exacto}")
    decision: list[str] = []
    if seleccionada != optima:
        decision.append(f"se eligio {None if seleccionada is None else seleccionada.accion} y la optima es {None if optima is None else optima.accion}")

    metricas: list[str] = []
    if resultado.nodos_evaluados > resultado.nodos_generados:
        metricas.append("hay mas nodos evaluados que generados")
    if not 0 <= resultado.profundidad_alcanzada <= resultado.profundidad_maxima:
        metricas.append("la profundidad alcanzada supera la maxima")
    if resultado.nodos_podados < 0:
        metricas.append("los nodos podados no pueden ser negativos")
    if resultado.algoritmo == "MINIMAX":
        esperado = (arbol.nodos, arbol.hojas, arbol.profundidad_alcanzada, 0)
        obtenido = (resultado.nodos_generados, resultado.nodos_evaluados, resultado.profundidad_alcanzada, resultado.nodos_podados)
        if obtenido != esperado:
            metricas.append(f"(generados, evaluados, profundidad, podados) = {obtenido}; el arbol da {esperado}")
    elif resultado.nodos_generados > arbol.nodos or resultado.nodos_evaluados > arbol.hojas:
        metricas.append("alfa-beta no puede generar ni evaluar mas nodos que el arbol completo de Minimax")

    return ReporteVerificacion(
        f"{resultado.algoritmo} (decision adversarial)",
        (
            _comprobacion("acciones_consideradas_legales", arbol.ilegales, f"{arbol.acciones_revisadas} acciones del arbol revisadas, todas legales"),
            _comprobacion("tacticas_coherentes", arbol.tacticas, "cada accion tiene el tipo tactico de E8.1"),
            _comprobacion("estados_validos", estados, f"{arbol.nodos} estados del arbol validos"),
            _comprobacion("accion_seleccionada_legal", seleccion, "la accion elegida es legal en la raiz"),
            _comprobacion("valores_raiz_legales", raiz_ilegal, f"{len(resultado.valores_raiz)} acciones de la raiz legales y en orden"),
            _comprobacion("valor_correcto", valor, f"valor {valor_exacto} igual al Minimax exacto"),
            _comprobacion("decision_optima", decision, "la accion elegida es la primera con el mejor valor exacto"),
            _comprobacion("metricas_coherentes", metricas, "metricas coherentes con el arbol"),
        ),
    )


def verificar_partida(escenario: Escenario, partida, verificar_arboles: bool = True) -> ReporteVerificacion:
    """Verifica una partida del modo ``partida`` jugada con Minimax o alfa-beta.

    Proposito: comprobar que cada jugada es legal y produce el estado siguiente, que no se genera ningun estado invalido
    y que el resultado declarado corresponde al estado final.
    Precondiciones: ``partida`` es un ``ResultadoPartida`` de ``jugar_partida`` para ``escenario``.
    Postcondiciones: devuelve un reporte con ``jugadas_legales``, ``estados_encadenados``, ``estados_validos``,
    ``resultado_coherente`` y, si ``verificar_arboles``, ``decisiones_verificadas`` (aplica :func:`verificar_decision`
    a cada jugada, lo que cuesta tanto como volver a jugar la partida). No modifica nada.
    Complejidad: O(T * U) sin verificar arboles; con ellos, la de T busquedas adversariales completas, donde T es la
    cantidad de jugadas.
    Uso de IA: Si.
    Intervencion de IA: Claude (Opus 5.5) diseno las comprobaciones y las implemento en E10.2.
    Validacion del estudiante: el estudiante reviso y valido el codigo; ademas, las pruebas de
    tests/algoritmos/test_verificador.py verifican partidas reales y detectan una partida alterada a proposito.
    """
    jugadas: list[str] = []
    cadena: list[str] = []
    estados = [f"estado inicial: {e}" for e in errores_de_estado(escenario, partida.estado_inicial)]
    decisiones: list[str] = []
    esperado_previo = preparar_turno(escenario, partida.estado_inicial)
    ultimo = partida.estado_inicial

    if len(partida.turnos) > partida.max_turnos:
        cadena.append(f"hay {len(partida.turnos)} jugadas y el limite es {partida.max_turnos}")
    for indice, turno in enumerate(partida.turnos, start=1):
        if turno.numero != indice:
            cadena.append(f"la jugada {indice} esta numerada como {turno.numero}")
        if turno.estado_previo != esperado_previo:
            cadena.append(f"jugada {indice}: no parte del estado en que termino la anterior")
        if turno.bando != turno.estado_previo.turno_actual:
            jugadas.append(f"jugada {indice}: la juega {turno.bando} pero el turno es de {turno.estado_previo.turno_actual}")
        accion = turno.decision.accion_seleccionada
        if accion is None or not es_accion_valida(escenario, turno.estado_previo, accion.accion):
            jugadas.append(f"jugada {indice}: la accion {None if accion is None else accion.accion} no es legal")
        elif turno.estado_resultante != aplicar_accion(escenario, turno.estado_previo, accion.accion):
            cadena.append(f"jugada {indice}: el estado resultante no es el que produce la accion")
        estados.extend(f"jugada {indice}: {e}" for e in errores_de_estado(escenario, turno.estado_resultante))
        if verificar_arboles:
            reporte = verificar_decision(escenario, turno.estado_previo, turno.decision)
            decisiones.extend(f"jugada {indice}: {c.nombre} ({c.detalle})" for c in reporte.fallidas)
        ultimo = turno.estado_resultante
        esperado_previo = preparar_turno(escenario, ultimo)

    resultado: list[str] = []
    if partida.estado_final not in (ultimo, preparar_turno(escenario, ultimo)):
        resultado.append("el estado final no es el de la ultima jugada")
    ganador = obtener_ganador(escenario, partida.estado_final)
    if ganador is not None:
        esperado = f"victoria_{ganador}"
    elif partida.estado_final.estado_partida == EMPATE_BLOQUEO:
        esperado = EMPATE_BLOQUEO
    else:
        esperado = "limite_turnos"
    if partida.resultado != esperado:
        resultado.append(f"el resultado declarado es {partida.resultado} y el estado final indica {esperado}")
    if esperado == "limite_turnos" and len(partida.turnos) != partida.max_turnos:
        resultado.append("la partida termino sin ganador ni empate antes del limite de jugadas")

    comprobaciones = [
        _comprobacion("jugadas_legales", jugadas, f"{len(partida.turnos)} jugadas legales"),
        _comprobacion("estados_encadenados", cadena, "cada jugada parte del estado anterior y produce el siguiente"),
        _comprobacion("estados_validos", estados, "ningun estado de la partida es invalido"),
        _comprobacion("resultado_coherente", resultado, f"resultado {partida.resultado} coherente con el estado final"),
    ]
    if verificar_arboles:
        comprobaciones.append(
            _comprobacion("decisiones_verificadas", decisiones, "cada decision supera la verificacion adversarial")
        )
    return ReporteVerificacion(f"partida con {partida.algoritmo}", tuple(comprobaciones))
