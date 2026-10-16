"""Metricas comparables de Minimax y alfa-beta (E8.5) sobre el mismo estado, profundidad y utilidad.

Reune en un solo objeto las siete metricas que exige el enunciado para la busqueda adversarial, para ambos
algoritmos, de modo que puedan presentarse lado a lado (consola, interfaz o modo de prueba ``adversarial``) y
exportarse a JSON para el informe tecnico. No contiene reglas ni algoritmos propios: solo ejecuta los de E8.3 y
E8.4 y compara sus resultados.
"""

from dataclasses import dataclass

from tacticalgrid.escenario.escenario import Escenario
from tacticalgrid.juego.estado import EstadoJuego

from .alfa_beta import alfa_beta
from .minimax import ResultadoMinimax, minimax, validar_profundidad

# (etiqueta para mostrar, campo de ResultadoMinimax), en el orden de la tabla de metricas del enunciado.
METRICAS_COMPARABLES: tuple[tuple[str, str], ...] = (
    ("Nodos generados", "nodos_generados"),
    ("Nodos evaluados", "nodos_evaluados"),
    ("Nodos podados", "nodos_podados"),
    ("Profundidad alcanzada", "profundidad_alcanzada"),
    ("Tiempo (s)", "tiempo_segundos"),
    ("Acción seleccionada", "accion_seleccionada"),
    ("Valor obtenido", "valor"),
)

# Metricas de trabajo sobre las que tiene sentido medir cuanto ahorra la poda.
METRICAS_DE_TRABAJO: tuple[str, ...] = ("nodos_generados", "nodos_evaluados", "tiempo_segundos")


@dataclass(frozen=True)
class ComparacionAdversarial:
    """Resultados de Minimax y alfa-beta obtenidos sobre el mismo estado y con la misma profundidad."""

    minimax: ResultadoMinimax
    alfa_beta: ResultadoMinimax

    @property
    def misma_accion(self) -> bool:
        """Indica si ambos algoritmos eligieron la misma accion (criterio de E8.4)."""
        return self.minimax.accion_seleccionada == self.alfa_beta.accion_seleccionada

    @property
    def mismo_valor(self) -> bool:
        """Indica si ambos algoritmos obtuvieron el mismo valor para la raiz."""
        return self.minimax.valor == self.alfa_beta.valor

    def reduccion_porcentual(self, campo: str) -> float | None:
        """Devuelve cuanto reduce alfa-beta una metrica de trabajo respecto de Minimax, en porcentaje.

        Proposito: cuantificar el ahorro de la poda con un numero comparable entre escenarios y profundidades.
        Precondiciones: ``campo`` es uno de ``METRICAS_DE_TRABAJO``; si no, se lanza ``ValueError``.
        Postcondiciones: devuelve ``100 * (1 - alfa_beta / minimax)``; es positivo si alfa-beta hace menos trabajo
        y ``None`` si el valor de Minimax es 0, porque no hay referencia contra la cual medir. No modifica nada.
        Complejidad: O(1) temporal y espacial.
        Uso de IA: Si.
        Intervencion de IA: Claude (Opus 5.5) propuso la metrica y su implementacion en E8.5.
        Validacion del estudiante: esta implementacion es valida y cubierta de forma adecuada respecto a la metrica, por
        tests/algoritmos/test_comparacion_adversarial.py con el arbol del pasillo calculado a mano.
        """
        if campo not in METRICAS_DE_TRABAJO:
            raise ValueError(f"La metrica {campo!r} no admite reduccion; use una de {METRICAS_DE_TRABAJO}.")
        referencia = getattr(self.minimax, campo)
        if referencia == 0:
            return None
        return 100 * (1 - getattr(self.alfa_beta, campo) / referencia)

    def a_diccionario(self) -> dict[str, object]:
        """Exporta ambas mediciones y su comparacion en una estructura serializable con ``json.dumps``.

        Proposito: dejar las metricas listas para reproducirlas y analizarlas en el informe tecnico.
        Precondiciones: ninguna adicional a las de la construccion.
        Postcondiciones: devuelve el bando MAX, la profundidad, las metricas de cada algoritmo con los nombres de la
        tabla del enunciado (``ResultadoMinimax.a_diccionario``), si coinciden accion y valor, y la reduccion
        porcentual de cada metrica de trabajo. No modifica nada.
        Complejidad: O(1) temporal y espacial.
        Uso de IA: Si.
        Intervencion de IA: Claude (Opus 5.5) propuso la estructura y la implementacion en E8.5.
        Validacion del estudiante: pendiente de revision del equipo; cubierta por
        tests/algoritmos/test_comparacion_adversarial.py, que comprueba las siete metricas y la serializacion.
        """
        return {
            "bando_max": self.minimax.bando_max,
            "profundidad_maxima": self.minimax.profundidad_maxima,
            "minimax": self.minimax.a_diccionario(),
            "alfa_beta": self.alfa_beta.a_diccionario(),
            "misma_accion": self.misma_accion,
            "mismo_valor": self.mismo_valor,
            "reduccion_porcentual": {campo: self.reduccion_porcentual(campo) for campo in METRICAS_DE_TRABAJO},
        }


def comparar_minimax_alfa_beta(
    escenario: Escenario, estado: EstadoJuego, profundidad_maxima: int
) -> ComparacionAdversarial:
    """Ejecuta Minimax y alfa-beta sobre el mismo estado y profundidad y reune sus metricas.

    Proposito: producir las metricas comparables de E8.5 a partir de una sola llamada, para la consola, la
    interfaz o el modo de prueba ``adversarial``.
    Precondiciones: ``estado`` es coherente con ``escenario``; ``profundidad_maxima`` es un entero mayor o igual que
    1 (si no, ``ValueError`` antes de ejecutar nada).
    Postcondiciones: devuelve una ``ComparacionAdversarial`` con un resultado de cada algoritmo. Ambos usan la
    misma utilidad (los pesos de ``juego.pesos_utilidad`` del escenario) y el mismo orden de acciones, pero cada
    uno construye su propio evaluador: asi ninguno hereda las distancias ya calculadas por el otro y los tiempos
    son comparables. ``estado`` no se modifica.
    Complejidad: la suma de ambas busquedas: O(b^d) para Minimax mas, en el peor caso, O(b^d) para alfa-beta,
    con b acciones por nodo y d la profundidad maxima.
    Uso de IA: Si.
    Intervencion de IA: Claude (Opus 5.5) propuso la funcion, la decision de usar evaluadores independientes para
    medir tiempos comparables y su implementacion en E8.5.
    Validacion del estudiante: implementacion validada por tests/algoritmos/test_comparacion_adversarial.py, 
    que contrasta cada metrica con ejecutar cada algoritmo por separado en los escenarios del repositorio.
    """
    profundidad_maxima = validar_profundidad(profundidad_maxima)
    return ComparacionAdversarial(
        minimax=minimax(escenario, estado, profundidad_maxima),
        alfa_beta=alfa_beta(escenario, estado, profundidad_maxima),
    )
