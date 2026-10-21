"""Minimax con profundidad limitada (E8.3) sobre las acciones tácticas legales y la utilidad de E8.2.

Decisiones de diseño:

- MAX es el bando en turno en el estado raíz y MIN es el otro. Son roles dentro del árbol, no capacidades distintas:
  ambos usan las mismas acciones (``acciones_tacticas``, E8.1) y la misma utilidad de suma cero (E8.2).
- Antes de expandir cada nodo se aplica ``preparar_turno`` (E3.1/E1.3): si el bando en turno está bloqueado, el
  turno pasa al adversario sin consumir profundidad, y si ambos están bloqueados la partida termina en empate.
- Un nodo es hoja si es terminal, si no tiene acciones o si alcanzó la profundidad máxima; en las hojas se calcula
  la utilidad con ``EvaluadorUtilidad``.
- Las acciones se exploran en el orden de ``acciones_tacticas`` o en el orden elegido con ``orden`` (E8.6, ver
  ``orden_acciones``). Ante empate de valor se conserva la primera acción, para que alfa-beta (E8.4) reproduzca
  exactamente la misma decisión con el mismo orden.
- Métricas: ``nodos_generados`` cuenta la raíz y cada sucesor creado; ``nodos_evaluados``, las hojas en las que se
  calculó la utilidad; ``nodos_podados`` es siempre 0 en Minimax y existe para comparar con alfa-beta;
  ``profundidad_alcanzada`` es la mayor profundidad de un nodo visitado (la raíz tiene profundidad 0).
"""

import time
from collections.abc import Mapping
from dataclasses import dataclass

from tacticalgrid.escenario.escenario import Escenario
from tacticalgrid.juego.estado import EstadoJuego
from tacticalgrid.juego.partida import preparar_turno
from tacticalgrid.juego.reglas import aplicar_accion, es_terminal
from tacticalgrid.juego.tacticas import AccionTactica, acciones_tacticas

from .orden_acciones import ORDEN_GENERACION, ordenar_acciones, validar_orden
from .utilidad import EvaluadorUtilidad, pesos_desde_configuracion

CLAVE_PROFUNDIDAD = "profundidad_maxima_minimax"


@dataclass(frozen=True)
class ResultadoMinimax:
    """Decisión y métricas de una búsqueda adversarial, según la tabla de métricas del enunciado."""

    algoritmo: str
    bando_max: str
    profundidad_maxima: int
    accion_seleccionada: AccionTactica | None
    valor: float
    nodos_generados: int
    nodos_evaluados: int
    nodos_podados: int
    profundidad_alcanzada: int
    tiempo_segundos: float
    valores_raiz: tuple[tuple[AccionTactica, float], ...] = ()
    # Alineado con ``valores_raiz``: True si ese valor es solo una cota superior porque alfa-beta podó parte de su
    # subárbol. Vacío en Minimax, donde todos los valores de la raíz son exactos.
    cotas_raiz: tuple[bool, ...] = ()
    orden_acciones: str = ORDEN_GENERACION

    def a_diccionario(self) -> dict[str, object]:
        """Exportar la decisión y sus métricas en una estructura serializable con ``json.dumps``.

        Proposito: hacer accesibles y reproducibles las métricas adversariales del enunciado (nodos generados, evaluados
        y podados, profundidad alcanzada, tiempo, acción seleccionada y valor) para el informe y E10.3.
        Precondiciones: ninguna adicional a las de la construcción del resultado.
        Postcondiciones: se devuelve un diccionario con el algoritmo, el bando MAX, la profundidad máxima, el orden de
        acciones y las siete métricas; la acción seleccionada se describe con unidad, tipo, origen, destino y tipo
        táctico, o es ``None`` si no hubo decisión. Solo contiene textos, números, listas y ``None``. El resultado no
        cambia.
        Complejidad: O(1) temporal y espacial.
        Uso de IA: Si.
        Intervencion de IA: Claude (Opus 5.5): implementación (E8.3), campo ``orden_acciones`` (E8.6) y documentación
        (E11.1).
        Validacion del estudiante: pruebas ``test_a_diccionario_tiene_las_metricas_del_enunciado`` de
        tests/algoritmos/test_minimax.py y ``test_a_diccionario_incluye_los_nodos_podados`` de
        tests/algoritmos/test_alfa_beta.py.
        """
        accion = self.accion_seleccionada
        return {
            "algoritmo": self.algoritmo,
            "bando_max": self.bando_max,
            "profundidad_maxima": self.profundidad_maxima,
            "orden_acciones": self.orden_acciones,
            "nodos_generados": self.nodos_generados,
            "nodos_evaluados": self.nodos_evaluados,
            "nodos_podados": self.nodos_podados,
            "profundidad_alcanzada": self.profundidad_alcanzada,
            "tiempo_segundos": self.tiempo_segundos,
            "accion_seleccionada": None
            if accion is None
            else {
                "unidad": accion.accion.identificador_unidad,
                "tipo": accion.accion.tipo,
                "origen": [accion.accion.origen.fila, accion.accion.origen.columna],
                "destino": [accion.accion.destino.fila, accion.accion.destino.columna],
                "tactica": accion.tipo_tactico,
            },
            "valor": self.valor,
        }


def validar_profundidad(profundidad: object) -> int:
    """Devolver ``profundidad`` si es un entero no booleano mayor o igual que 1; si no, lanzar ``ValueError``."""
    if isinstance(profundidad, bool) or not isinstance(profundidad, int) or profundidad < 1:
        raise ValueError(
            f"La profundidad maxima de Minimax debe ser un entero mayor o igual que 1 y se recibio {profundidad!r}."
        )
    return profundidad


def profundidad_desde_configuracion(configuracion_juego: Mapping[str, object] | None) -> int | None:
    """Leer ``juego.profundidad_maxima_minimax`` del escenario cargado.

    Proposito: permitir cambiar la profundidad de Minimax editando el JSON del escenario, sin modificar código.
    Precondiciones: ``configuracion_juego`` es ``Escenario.configuracion_juego`` o ``None``.
    Postcondiciones: se devuelve ``None`` si el campo no está y la profundidad si es un entero mayor o igual que 1; se
    lanza ``ValueError`` con un mensaje claro si el valor no es válido. Nada cambia.
    Complejidad: O(1) temporal y espacial.
    Uso de IA: Si.
    Intervencion de IA: Claude (Opus 5.5): lectura y validación (E8.3).
    Validacion del estudiante: pruebas de tests/algoritmos/test_minimax.py: lectura de la profundidad desde el JSON,
    profundidad válida en todos los escenarios del repositorio y rechazo de valores inválidos.
    """
    if configuracion_juego is None or CLAVE_PROFUNDIDAD not in configuracion_juego:
        return None
    return validar_profundidad(configuracion_juego[CLAVE_PROFUNDIDAD])


def preparar_evaluador(
    escenario: Escenario, estado: EstadoJuego, evaluador: EvaluadorUtilidad | None
) -> EvaluadorUtilidad:
    """Devolver el evaluador con el que se valora el árbol de juego desde el estado raíz.

    Proposito: garantizar que Minimax (E8.3) y alfa-beta (E8.4) usen exactamente la misma función de utilidad, condición
    para que produzcan la misma decisión.
    Precondiciones: ``estado`` es coherente con ``escenario``.
    Postcondiciones: sin ``evaluador``, se crea uno con MAX igual al bando en turno y los pesos de
    ``juego.pesos_utilidad`` del escenario; con ``evaluador``, se devuelve si su ``bando_max`` es el bando en turno y,
    en otro caso, se lanza ``ValueError``. Nada cambia.
    Complejidad: O(F*C log(F*C)) temporal y O(F*C) espacial al crear un evaluador, porque precalcula los costos hacia
    las bases; O(1) si se recibe uno.
    Uso de IA: Si.
    Intervencion de IA: Claude (Opus 5.5): extracción desde ``minimax`` para compartirla con alfa-beta, sin cambiar su
    comportamiento (E8.4).
    Validacion del estudiante: pruebas ``test_evaluador_debe_tener_como_max_al_bando_en_turno`` de
    tests/algoritmos/test_minimax.py y tests/algoritmos/test_alfa_beta.py.
    """
    if evaluador is None:
        return EvaluadorUtilidad(escenario, estado.turno_actual, pesos_desde_configuracion(escenario.configuracion_juego))
    if evaluador.bando_max != estado.turno_actual:
        raise ValueError("El bando MAX del evaluador debe ser el bando en turno del estado raiz.")
    return evaluador


class _Contadores:
    def __init__(self) -> None:
        self.generados = 0
        self.evaluados = 0
        self.profundidad_alcanzada = 0


def _valor_minimax(
    escenario: Escenario,
    evaluador: EvaluadorUtilidad,
    estado: EstadoJuego,
    profundidad: int,
    profundidad_maxima: int,
    contadores: _Contadores,
    orden: str,
) -> float:
    """Calcular recursivamente el valor Minimax de ``estado`` a ``profundidad`` desde la raíz.

    Proposito: resolver el núcleo de Minimax: en los nodos de MAX tomar el máximo de los hijos, en los de MIN el mínimo
    y en las hojas devolver la utilidad de E8.2.
    Precondiciones: ``estado`` es coherente con ``escenario``; ``0 <= profundidad <= profundidad_maxima``;
    ``evaluador.bando_max`` es el bando MAX de la búsqueda; ``orden`` es uno de ``ORDENES``, ya validado.
    Postcondiciones: primero se aplica ``preparar_turno`` (el pase por bloqueo no consume profundidad). Si el estado es
    terminal, no tiene acciones o ``profundidad`` es la máxima, ``contadores.evaluados`` aumenta en 1 y se devuelve
    ``evaluador.evaluar(estado)``; en otro caso se genera cada sucesor en el orden indicado (``contadores.generados``
    aumenta en 1 por cada uno) y se devuelve el máximo o el mínimo de sus valores según quién mueve. Se actualiza
    ``contadores.profundidad_alcanzada``; ``estado`` no cambia.
    Complejidad: O(b^(d-p)) nodos, con b acciones por nodo y d-p niveles restantes; cada nodo cuesta O(U^2) por generar
    acciones y, en las hojas, evaluar la utilidad. Espacio O(d) por la recursión, más las acciones de cada nivel
    abierto.
    Uso de IA: Si.
    Intervencion de IA: Claude (Opus 5.5): implementación (E8.3), parámetro ``orden`` (E8.6) y documentación (E11.1).
    Validacion del estudiante: pruebas de tests/algoritmos/test_minimax.py con el árbol calculado a mano en el corredor
    1x4 (profundidades 1 a 3) y pruebas de tests/algoritmos/test_casos_minimos_adversariales.py.
    """
    contadores.profundidad_alcanzada = max(contadores.profundidad_alcanzada, profundidad)
    estado = preparar_turno(escenario, estado)
    acciones = () if es_terminal(escenario, estado) else ordenar_acciones(acciones_tacticas(escenario, estado), orden)
    if profundidad == profundidad_maxima or not acciones:
        contadores.evaluados += 1
        return evaluador.evaluar(estado)

    es_max = estado.turno_actual == evaluador.bando_max
    mejor = float("-inf") if es_max else float("inf")
    for accion_tactica in acciones:
        sucesor = aplicar_accion(escenario, estado, accion_tactica.accion)
        contadores.generados += 1
        valor = _valor_minimax(escenario, evaluador, sucesor, profundidad + 1, profundidad_maxima, contadores, orden)
        mejor = max(mejor, valor) if es_max else min(mejor, valor)
    return mejor


def minimax(
    escenario: Escenario,
    estado: EstadoJuego,
    profundidad_maxima: int,
    evaluador: EvaluadorUtilidad | None = None,
    orden: str = ORDEN_GENERACION,
) -> ResultadoMinimax:
    """Elegir la mejor acción para el bando en turno explorando el árbol de juego hasta ``profundidad_maxima``.

    Proposito: implementar Minimax con profundidad limitada y reportar las métricas adversariales del enunciado.
    Precondiciones: ``estado`` es coherente con ``escenario``; ``profundidad_maxima`` es un entero mayor o igual que 1
    (si no, ``ValueError``); si se pasa ``evaluador``, su ``bando_max`` es el bando en turno de ``estado``.
    Postcondiciones: se devuelve un ``ResultadoMinimax`` con la acción de la raíz de mayor valor Minimax (la primera en
    el orden de exploración si hay empate), su valor, el valor de cada acción de la raíz, los nodos generados (incluida
    la raíz), los nodos evaluados (hojas), 0 nodos podados, la profundidad alcanzada y el tiempo. Si la raíz es
    terminal o el bando en turno no puede actuar, ``accion_seleccionada`` es ``None`` y el valor es el de la raíz tras
    el posible pase de turno. Sin evaluador se usan los pesos de ``juego.pesos_utilidad`` del escenario. Toda acción
    considerada es legal y ``estado`` no cambia.
    Complejidad: O(b^d) nodos en el peor caso, con b acciones por nodo (a lo sumo 5 por unidad del bando en turno) y
    d = ``profundidad_maxima``; cada nodo cuesta O(U^2) por generar acciones, aplicar una y, en las hojas, evaluar la
    utilidad. Espacio O(d * b) por la recursión y las acciones de cada nivel.
    Uso de IA: Si.
    Intervencion de IA: Claude (Opus 5.5): diseño (MAX como bando en turno, pase de turno sin consumir profundidad,
    desempate por la primera acción), implementación y documentación (E8.3); traslado de la construcción del evaluador
    a ``preparar_evaluador`` sin cambiar el resultado (E8.4); parámetro ``orden``, por defecto ``generacion``, para el
    caso mínimo 9 (E8.6).
    Validacion del estudiante: pruebas de tests/algoritmos/test_minimax.py: árbol del corredor 1x4 calculado a mano
    para las profundidades 1 a 3, legalidad de la acción elegida, simetría entre bandos, más nodos con más profundidad,
    raíz terminal y lectura de la profundidad desde el JSON.
    """
    profundidad_maxima = validar_profundidad(profundidad_maxima)
    orden = validar_orden(orden)
    inicio = time.perf_counter()
    evaluador = preparar_evaluador(escenario, estado, evaluador)

    contadores = _Contadores()
    contadores.generados = 1
    raiz = preparar_turno(escenario, estado)
    puede_actuar = not es_terminal(escenario, raiz) and raiz.turno_actual == evaluador.bando_max
    acciones = ordenar_acciones(acciones_tacticas(escenario, raiz), orden) if puede_actuar else ()

    if not acciones:
        valor = _valor_minimax(escenario, evaluador, raiz, 0, profundidad_maxima, contadores, orden)
        seleccionada = None
        valores_raiz: tuple[tuple[AccionTactica, float], ...] = ()
    else:
        valores = []
        for accion_tactica in acciones:
            sucesor = aplicar_accion(escenario, raiz, accion_tactica.accion)
            contadores.generados += 1
            valores.append(
                (accion_tactica, _valor_minimax(escenario, evaluador, sucesor, 1, profundidad_maxima, contadores, orden))
            )
        seleccionada, valor = valores[0]
        for accion_tactica, valor_accion in valores[1:]:
            if valor_accion > valor:
                seleccionada, valor = accion_tactica, valor_accion
        valores_raiz = tuple(valores)

    return ResultadoMinimax(
        algoritmo="MINIMAX",
        bando_max=evaluador.bando_max,
        profundidad_maxima=profundidad_maxima,
        accion_seleccionada=seleccionada,
        valor=valor,
        nodos_generados=contadores.generados,
        nodos_evaluados=contadores.evaluados,
        nodos_podados=0,
        profundidad_alcanzada=contadores.profundidad_alcanzada,
        tiempo_segundos=time.perf_counter() - inicio,
        valores_raiz=valores_raiz,
        orden_acciones=orden,
    )
