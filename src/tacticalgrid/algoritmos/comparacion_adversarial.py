"""Métricas comparables de Minimax y alfa-beta (E8.5) sobre el mismo estado, profundidad y utilidad.

Reúne en un solo objeto las siete métricas que exige el enunciado para la búsqueda adversarial, para ambos
algoritmos, de modo que se presenten lado a lado (consola, interfaz o modo de prueba ``adversarial``) y se exporten
a JSON para el informe técnico. No contiene reglas ni algoritmos propios: ejecuta los de E8.3 y E8.4 y compara sus
resultados.
"""

from dataclasses import dataclass

from tacticalgrid.escenario.escenario import Escenario
from tacticalgrid.juego.estado import EstadoJuego

from .alfa_beta import alfa_beta
from .minimax import ResultadoMinimax, minimax, validar_profundidad
from .orden_acciones import ORDEN_GENERACION, validar_orden

# (etiqueta para mostrar, campo de ResultadoMinimax), en el orden de la tabla de métricas del enunciado.
METRICAS_COMPARABLES: tuple[tuple[str, str], ...] = (
    ("Nodos generados", "nodos_generados"),
    ("Nodos evaluados", "nodos_evaluados"),
    ("Nodos podados", "nodos_podados"),
    ("Profundidad alcanzada", "profundidad_alcanzada"),
    ("Tiempo (s)", "tiempo_segundos"),
    ("Acción seleccionada", "accion_seleccionada"),
    ("Valor obtenido", "valor"),
)

# Métricas de trabajo sobre las que tiene sentido medir el ahorro de la poda.
METRICAS_DE_TRABAJO: tuple[str, ...] = ("nodos_generados", "nodos_evaluados", "tiempo_segundos")


@dataclass(frozen=True)
class ComparacionAdversarial:
    """Resultados de Minimax y alfa-beta obtenidos sobre el mismo estado y con la misma profundidad."""

    minimax: ResultadoMinimax
    alfa_beta: ResultadoMinimax

    @property
    def misma_accion(self) -> bool:
        """Indicar si ambos algoritmos eligieron la misma acción (criterio de E8.4)."""
        return self.minimax.accion_seleccionada == self.alfa_beta.accion_seleccionada

    @property
    def mismo_valor(self) -> bool:
        """Indicar si ambos algoritmos obtuvieron el mismo valor para la raíz."""
        return self.minimax.valor == self.alfa_beta.valor

    def reduccion_porcentual(self, campo: str) -> float | None:
        """Calcular en porcentaje cuánto reduce alfa-beta una métrica de trabajo respecto de Minimax.

        Proposito: cuantificar el ahorro de la poda con un número comparable entre escenarios y profundidades.
        Precondiciones: ``campo`` es uno de ``METRICAS_DE_TRABAJO``; si no, se lanza ``ValueError``.
        Postcondiciones: se devuelve ``100 * (1 - alfa_beta / minimax)``, positivo si alfa-beta hace menos trabajo, o
        ``None`` si el valor de Minimax es 0, porque no hay referencia contra la cual medir. Nada cambia.
        Complejidad: O(1) temporal y espacial.
        Uso de IA: Si.
        Intervencion de IA: Claude (Opus 5.5): métrica e implementación (E8.5).
        Validacion del estudiante: pruebas de tests/algoritmos/test_comparacion_adversarial.py: árbol del pasillo
        calculado a mano y reducción aplicada solo a métricas de trabajo.
        """
        if campo not in METRICAS_DE_TRABAJO:
            raise ValueError(f"La metrica {campo!r} no admite reduccion; use una de {METRICAS_DE_TRABAJO}.")
        referencia = getattr(self.minimax, campo)
        if referencia == 0:
            return None
        return 100 * (1 - getattr(self.alfa_beta, campo) / referencia)

    def a_diccionario(self) -> dict[str, object]:
        """Exportar ambas mediciones y su comparación en una estructura serializable con ``json.dumps``.

        Proposito: dejar las métricas listas para reproducirlas y analizarlas en el informe técnico.
        Precondiciones: ninguna adicional a las de la construcción.
        Postcondiciones: se devuelven el bando MAX, la profundidad, las métricas de cada algoritmo con los nombres de la
        tabla del enunciado (``ResultadoMinimax.a_diccionario``), la coincidencia de acción y valor, y la reducción
        porcentual de cada métrica de trabajo. Nada cambia.
        Complejidad: O(1) temporal y espacial.
        Uso de IA: Si.
        Intervencion de IA: Claude (Opus 5.5): estructura e implementación (E8.5).
        Validacion del estudiante: prueba ``test_a_diccionario_expone_las_siete_metricas_de_ambos_y_es_json`` de
        tests/algoritmos/test_comparacion_adversarial.py.
        """
        return {
            "bando_max": self.minimax.bando_max,
            "profundidad_maxima": self.minimax.profundidad_maxima,
            "orden_acciones": self.minimax.orden_acciones,
            "minimax": self.minimax.a_diccionario(),
            "alfa_beta": self.alfa_beta.a_diccionario(),
            "misma_accion": self.misma_accion,
            "mismo_valor": self.mismo_valor,
            "reduccion_porcentual": {campo: self.reduccion_porcentual(campo) for campo in METRICAS_DE_TRABAJO},
        }


def comparar_minimax_alfa_beta(
    escenario: Escenario, estado: EstadoJuego, profundidad_maxima: int, orden: str = ORDEN_GENERACION
) -> ComparacionAdversarial:
    """Ejecutar Minimax y alfa-beta sobre el mismo estado y profundidad y reunir sus métricas.

    Proposito: producir las métricas comparables de E8.5 con una sola llamada, para la consola, la interfaz o el modo
    de prueba ``adversarial``.
    Precondiciones: ``estado`` es coherente con ``escenario``; ``profundidad_maxima`` es un entero mayor o igual que 1
    (si no, se lanza ``ValueError`` antes de ejecutar nada).
    Postcondiciones: se devuelve una ``ComparacionAdversarial`` con un resultado de cada algoritmo. Ambos usan la misma
    utilidad (los pesos de ``juego.pesos_utilidad`` del escenario) y el mismo ``orden`` de acciones, pero cada uno
    construye su propio evaluador, de modo que ninguno hereda las distancias ya calculadas por el otro y los tiempos
    son comparables. ``estado`` no cambia.
    Complejidad: la suma de ambas búsquedas: O(b^d) para Minimax más, en el peor caso, O(b^d) para alfa-beta, con b
    acciones por nodo y d la profundidad máxima.
    Uso de IA: Si.
    Intervencion de IA: Claude (Opus 5.5): función, evaluadores independientes para medir tiempos comparables e
    implementación (E8.5); parámetro ``orden`` aplicado a ambos algoritmos (E8.6).
    Validacion del estudiante: prueba ``test_coincide_con_ejecutar_cada_algoritmo_por_separado`` de
    tests/algoritmos/test_comparacion_adversarial.py, que contrasta cada métrica con la ejecución por separado en los
    escenarios del repositorio.
    """
    profundidad_maxima = validar_profundidad(profundidad_maxima)
    orden = validar_orden(orden)
    return ComparacionAdversarial(
        minimax=minimax(escenario, estado, profundidad_maxima, orden=orden),
        alfa_beta=alfa_beta(escenario, estado, profundidad_maxima, orden=orden),
    )
