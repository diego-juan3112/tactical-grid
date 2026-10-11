"""Minimax con profundidad limitada (E8.3) sobre las acciones tacticas legales y la utilidad de E8.2.

Decisiones de diseno:

- MAX es el bando en turno en el estado raiz; MIN es el otro. Son roles dentro del arbol, no capacidades distintas:
  ambos usan las mismas acciones (``acciones_tacticas``, E8.1) y la misma utilidad de suma cero (E8.2).
- Antes de expandir cada nodo se aplica ``preparar_turno`` (E3.1/E1.3): si el bando en turno esta bloqueado, el
  turno pasa al adversario sin consumir profundidad, y si ambos estan bloqueados la partida termina en empate.
- Un nodo es hoja si es terminal, si no tiene acciones o si alcanzo la profundidad maxima; en las hojas se calcula
  la utilidad con ``EvaluadorUtilidad``.
- Las acciones se exploran en el orden de ``acciones_tacticas``. Ante empate de valor se conserva la primera accion,
  de modo que alfa-beta (E8.4) pueda reproducir exactamente la misma decision con el mismo orden.
- Metricas: ``nodos_generados`` cuenta la raiz y cada sucesor creado; ``nodos_evaluados`` las hojas en las que se
  calculo la utilidad; ``nodos_podados`` es siempre 0 en Minimax y existe para comparar con alfa-beta;
  ``profundidad_alcanzada`` es la mayor profundidad de un nodo visitado (la raiz tiene profundidad 0).
"""

import time
from collections.abc import Mapping
from dataclasses import dataclass

from tacticalgrid.escenario.escenario import Escenario
from tacticalgrid.juego.estado import EstadoJuego
from tacticalgrid.juego.partida import preparar_turno
from tacticalgrid.juego.reglas import aplicar_accion, es_terminal
from tacticalgrid.juego.tacticas import AccionTactica, acciones_tacticas

from .utilidad import EvaluadorUtilidad, pesos_desde_configuracion

CLAVE_PROFUNDIDAD = "profundidad_maxima_minimax"


@dataclass(frozen=True)
class ResultadoMinimax:
    """Decision y metricas de una busqueda adversarial, segun la tabla de metricas del enunciado."""

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

    def a_diccionario(self) -> dict[str, object]:
        """Exporta las metricas con nombres equivalentes a la tabla del enunciado, listas para ``json.dumps``."""
        accion = self.accion_seleccionada
        return {
            "algoritmo": self.algoritmo,
            "bando_max": self.bando_max,
            "profundidad_maxima": self.profundidad_maxima,
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
    """Devuelve ``profundidad`` si es un entero (no booleano) mayor o igual que 1; si no, lanza ``ValueError``."""
    if isinstance(profundidad, bool) or not isinstance(profundidad, int) or profundidad < 1:
        raise ValueError(
            f"La profundidad maxima de Minimax debe ser un entero mayor o igual que 1 y se recibio {profundidad!r}."
        )
    return profundidad


def profundidad_desde_configuracion(configuracion_juego: Mapping[str, object] | None) -> int | None:
    """Lee ``juego.profundidad_maxima_minimax`` del escenario cargado.

    Purpose: permitir cambiar la profundidad de Minimax editando el JSON del escenario, sin modificar codigo.
    Preconditions: ``configuracion_juego`` es ``Escenario.configuracion_juego`` o ``None``.
    Postconditions: devuelve ``None`` si el campo no esta; devuelve la profundidad si es un entero mayor o igual que
    1; lanza ``ValueError`` con un mensaje claro si el valor no es valido. No modifica nada.
    Complexity: O(1) temporal y espacial.
    AI usage: Yes.
    AI intervention: Claude (Opus 5.5) implemento la lectura y validacion en E8.3.
    Student validation: el estudiante reviso y valido el codigo; ademas, las pruebas de
    tests/algoritmos/test_minimax.py leen la profundidad de escenarios del repositorio y rechazan valores invalidos.
    """
    if configuracion_juego is None or CLAVE_PROFUNDIDAD not in configuracion_juego:
        return None
    return validar_profundidad(configuracion_juego[CLAVE_PROFUNDIDAD])


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
) -> float:
    """Valor Minimax de ``estado`` visto a ``profundidad`` desde la raiz (recursivo, en profundidad)."""
    contadores.profundidad_alcanzada = max(contadores.profundidad_alcanzada, profundidad)
    estado = preparar_turno(escenario, estado)
    acciones = () if es_terminal(escenario, estado) else acciones_tacticas(escenario, estado)
    if profundidad == profundidad_maxima or not acciones:
        contadores.evaluados += 1
        return evaluador.evaluar(estado)

    es_max = estado.turno_actual == evaluador.bando_max
    mejor = float("-inf") if es_max else float("inf")
    for accion_tactica in acciones:
        sucesor = aplicar_accion(escenario, estado, accion_tactica.accion)
        contadores.generados += 1
        valor = _valor_minimax(escenario, evaluador, sucesor, profundidad + 1, profundidad_maxima, contadores)
        mejor = max(mejor, valor) if es_max else min(mejor, valor)
    return mejor


def minimax(
    escenario: Escenario,
    estado: EstadoJuego,
    profundidad_maxima: int,
    evaluador: EvaluadorUtilidad | None = None,
) -> ResultadoMinimax:
    """Elige la mejor accion para el bando en turno explorando el arbol de juego hasta ``profundidad_maxima``.

    Purpose: implementar Minimax con profundidad limitada y reportar las metricas adversariales del enunciado.
    Preconditions: ``estado`` es coherente con ``escenario``; ``profundidad_maxima`` es un entero mayor o igual que 1
    (si no, ``ValueError``); si se pasa ``evaluador``, su ``bando_max`` debe ser el bando en turno de ``estado``.
    Postconditions: devuelve un ``ResultadoMinimax`` con la accion de la raiz de mayor valor Minimax (la primera en el
    orden de ``acciones_tacticas`` si hay empate), su valor, el valor de cada accion de la raiz, nodos generados
    (incluida la raiz), nodos evaluados (hojas), 0 nodos podados, profundidad alcanzada y tiempo. Si la raiz es
    terminal o el bando en turno no puede actuar, ``accion_seleccionada`` es ``None`` y el valor es el de la raiz
    (tras el posible pase de turno). Sin evaluador, usa los pesos de ``juego.pesos_utilidad`` del escenario. Toda
    accion considerada es legal y ``estado`` no se modifica.
    Complexity: O(b^d) nodos en el peor caso, con b acciones por nodo (a lo sumo 5 por unidad del bando en turno) y
    d = ``profundidad_maxima``; cada nodo cuesta O(U^2) por generar acciones, aplicar una y, en las hojas, evaluar la
    utilidad. Espacio O(d * b) por la recursion y las acciones de cada nivel.
    AI usage: Yes.
    AI intervention: Claude (Opus 5.5) propuso el diseno (MAX como bando en turno, pase de turno sin consumir
    profundidad, desempate por la primera accion), la implementacion y esta documentacion en E8.3.
    Student validation: el estudiante reviso y valido el codigo; ademas, las pruebas de tests/algoritmos/test_minimax.py
    comparan el resultado con un arbol pequeno calculado a mano, verifican la legalidad de la accion elegida, la
    simetria entre bandos, las metricas por profundidad y la lectura de la profundidad desde el JSON.
    """
    profundidad_maxima = validar_profundidad(profundidad_maxima)
    inicio = time.perf_counter()
    if evaluador is None:
        evaluador = EvaluadorUtilidad(
            escenario, estado.turno_actual, pesos_desde_configuracion(escenario.configuracion_juego)
        )
    elif evaluador.bando_max != estado.turno_actual:
        raise ValueError("El bando MAX del evaluador debe ser el bando en turno del estado raiz.")

    contadores = _Contadores()
    contadores.generados = 1
    raiz = preparar_turno(escenario, estado)
    puede_actuar = not es_terminal(escenario, raiz) and raiz.turno_actual == evaluador.bando_max
    acciones = acciones_tacticas(escenario, raiz) if puede_actuar else ()

    if not acciones:
        valor = _valor_minimax(escenario, evaluador, raiz, 0, profundidad_maxima, contadores)
        seleccionada = None
        valores_raiz: tuple[tuple[AccionTactica, float], ...] = ()
    else:
        valores = []
        for accion_tactica in acciones:
            sucesor = aplicar_accion(escenario, raiz, accion_tactica.accion)
            contadores.generados += 1
            valores.append(
                (accion_tactica, _valor_minimax(escenario, evaluador, sucesor, 1, profundidad_maxima, contadores))
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
    )
