"""Función de utilidad propia (E8.2) para evaluar estados del árbol de juego desde la perspectiva de MAX.

La utilidad es de suma cero: cada criterio se calcula como "lo bueno para MAX menos lo bueno para MIN". Por eso,
intercambiar los roles cambia exactamente el signo del valor; MAX y MIN son roles, no capacidades distintas.

Criterios, todos con peso configurable en :class:`PesosUtilidad`:

- ``terminal``: victoria de MAX = ``+victoria``, victoria de MIN = ``-victoria``, empate por bloqueo = 0.
- ``posesion``: ``+posesion`` si el recurso lo porta MAX y ``-posesion`` si lo porta MIN.
- ``entrega``: costo de terreno que le falta al portador para llegar a su base (``-entrega * costo`` si porta MAX,
  ``+entrega * costo`` si porta MIN). Mide el progreso hacia la victoria.
- ``carrera_recurso``: con el recurso libre, diferencia entre el menor costo de una unidad de MIN y el de una de MAX
  para llegar a él (``carrera_recurso * (costo_MIN - costo_MAX)``).
- ``amenaza``: unidades rivales adyacentes al portador, que pueden interceptarlo en su turno (E8.1).
- ``bloqueo``: unidades rivales dentro del rectángulo entre el portador y su base (sobre sus rutas más cortas).
- ``movilidad``: unidades con al menos un movimiento legal (unidades disponibles) de MAX menos las de MIN.

Las distancias se miden con el costo de los terrenos del JSON y respetan los muros: para cada destino relevante
(bases y posición del recurso) se calcula una sola vez el costo mínimo desde cada celda. Si una celda no alcanza el
destino, se usa un costo mayor que cualquier costo alcanzable del mapa.
"""

import heapq
import math
from collections.abc import Mapping
from dataclasses import dataclass, fields

from tacticalgrid.escenario.escenario import Escenario, Posicion
from tacticalgrid.juego.accion import DESPLAZAMIENTOS
from tacticalgrid.juego.estado import EstadoJuego
from tacticalgrid.juego.recurso import obtener_portador
from tacticalgrid.juego.reglas import EMPATE_BLOQUEO, aplicar_accion, generar_movimientos, obtener_ganador
from tacticalgrid.juego.tacticas import AccionTactica, acciones_tacticas

BANDOS = ("A", "B")
CLAVE_PESOS = "pesos_utilidad"


@dataclass(frozen=True)
class PesosUtilidad:
    """Pesos de cada criterio de la utilidad.

    Los valores por defecto se justifican en docs/tecnico/04-decision-adversarial.md (E8.2).
    """

    victoria: float = 10_000
    posesion: float = 100
    entrega: float = 2
    carrera_recurso: float = 2
    amenaza: float = 60
    bloqueo: float = 10
    movilidad: float = 1

    def __post_init__(self) -> None:
        """Validar los pesos de la función de utilidad al crearlos.

        Proposito: impedir que un peso inválido del JSON (``juego.pesos_utilidad``) produzca utilidades no finitas o una
        victoria que no domine al resto de los criterios.
        Precondiciones: los campos tienen los valores por defecto o los recibidos.
        Postcondiciones: no hay efectos si todos los pesos son números finitos no booleanos y ``victoria`` es positiva;
        en otro caso se lanza ``ValueError`` con el nombre del peso y el valor recibido.
        Complejidad: O(P) temporal y O(1) espacial, con P la cantidad de criterios (siete).
        Uso de IA: Si.
        Intervencion de IA: Claude (Opus 5.5): implementación (E8.2) y documentación (E11.1).
        Validacion del estudiante: pruebas de tests/algoritmos/test_utilidad.py: rechazo de pesos booleanos, infinitos y
        de una victoria no positiva, tanto desde el JSON como al construir los pesos.
        """
        for campo in fields(self):
            valor = getattr(self, campo.name)
            if isinstance(valor, bool) or not isinstance(valor, (int, float)) or not math.isfinite(valor):
                raise ValueError(f"El peso '{campo.name}' debe ser un numero finito y se recibio {valor!r}.")
        if self.victoria <= 0:
            raise ValueError(f"El peso 'victoria' debe ser positivo y se recibio {self.victoria!r}.")


def pesos_desde_configuracion(configuracion_juego: Mapping[str, object] | None) -> PesosUtilidad:
    """Construir los pesos a partir del campo propio opcional ``juego.pesos_utilidad`` del escenario.

    Proposito: permitir cambiar los pesos de la utilidad editando el JSON, sin modificar código, para estudiar cómo
    cambia el comportamiento de Minimax.
    Precondiciones: ``configuracion_juego`` es ``Escenario.configuracion_juego`` o ``None``.
    Postcondiciones: se devuelven los pesos por defecto si no hay ``pesos_utilidad``; si lo hay, se devuelven los pesos
    por defecto con solo los indicados reemplazados. Se lanza ``ValueError`` si ``pesos_utilidad`` no es un objeto, si
    incluye un criterio desconocido o si algún peso no es un número finito (o ``victoria`` no es positiva).
    Complejidad: O(P) temporal y espacial, con P la cantidad de criterios.
    Uso de IA: Si.
    Intervencion de IA: Claude (Opus 5.5): campo propio e implementación (E8.2).
    Validacion del estudiante: pruebas de tests/algoritmos/test_utilidad.py: pesos por defecto sin configuración, pesos
    parciales desde el JSON y rechazo de criterios y valores inválidos.
    """
    if configuracion_juego is None or CLAVE_PESOS not in configuracion_juego:
        return PesosUtilidad()
    datos = configuracion_juego[CLAVE_PESOS]
    if not isinstance(datos, Mapping):
        raise ValueError(f"El campo 'juego.{CLAVE_PESOS}' debe ser un objeto con pesos por criterio.")
    validos = {campo.name for campo in fields(PesosUtilidad)}
    desconocidos = sorted(set(datos) - validos)
    if desconocidos:
        raise ValueError(
            f"Criterios de utilidad desconocidos en 'juego.{CLAVE_PESOS}': {desconocidos}. Validos: {sorted(validos)}."
        )
    return PesosUtilidad(**dict(datos))


def costos_hacia(escenario: Escenario, destino: Posicion) -> dict[Posicion, int | float]:
    """Calcular el costo mínimo de terreno desde cada celda transitable hasta ``destino``.

    Proposito: medir las distancias de la utilidad con los costos del JSON y respetando obstáculos, en lugar de usar
    distancias en línea recta que ignoran muros y terrenos caros.
    Precondiciones: ``destino`` está dentro del mapa; los costos transitables son positivos (validados en E2.2).
    Postcondiciones: se devuelve un diccionario con el costo de la ruta más barata desde cada celda alcanzable hasta
    ``destino``, sumando el costo de cada celda en la que se entra (el destino vale 0); las celdas que no alcanzan el
    destino no aparecen. El escenario no cambia.
    Complejidad: O(F*C log(F*C)) temporal y O(F*C) espacial: Dijkstra desde el destino sobre las F*C celdas, con
    aristas invertidas (pasar de x a y cuesta el terreno de y).
    Uso de IA: Si.
    Intervencion de IA: Claude (Opus 5.5): Dijkstra invertido desde cada destino e implementación (E8.2).
    Validacion del estudiante: pruebas de tests/algoritmos/test_utilidad.py: costos iguales al óptimo de UCS y cambio
    de los costos al modificar el costo de un terreno en el JSON.
    """
    costos: dict[Posicion, int | float] = {destino: 0}
    cola: list[tuple[int | float, int, int]] = [(0, destino.fila, destino.columna)]
    while cola:
        costo, fila, columna = heapq.heappop(cola)
        actual = Posicion(fila, columna)
        if costo > costos[actual]:
            continue
        # Desde un vecino, entrar en ``actual`` cuesta el terreno de ``actual``; desde ahí faltan ``costo``.
        nuevo = costo + escenario.obtener_costo(actual)
        for delta_fila, delta_columna in DESPLAZAMIENTOS:
            vecino = Posicion(fila + delta_fila, columna + delta_columna)
            if not escenario.contiene_posicion(vecino) or not escenario.es_transitable(vecino):
                continue
            if vecino not in costos or nuevo < costos[vecino]:
                costos[vecino] = nuevo
                heapq.heappush(cola, (nuevo, vecino.fila, vecino.columna))
    return costos


def _manhattan(a: Posicion, b: Posicion) -> int:
    return abs(a.fila - b.fila) + abs(a.columna - b.columna)


def _dentro_del_rectangulo(posicion: Posicion, esquina_a: Posicion, esquina_b: Posicion) -> bool:
    return (
        min(esquina_a.fila, esquina_b.fila) <= posicion.fila <= max(esquina_a.fila, esquina_b.fila)
        and min(esquina_a.columna, esquina_b.columna) <= posicion.columna <= max(esquina_a.columna, esquina_b.columna)
    )


class EvaluadorUtilidad:
    """Evaluador de estados desde la perspectiva de ``bando_max``, con los pesos dados y distancias precalculadas."""

    def __init__(self, escenario: Escenario, bando_max: str, pesos: PesosUtilidad | None = None) -> None:
        """Preparar el evaluador para un escenario, un bando MAX y unos pesos.

        Proposito: precalcular una sola vez lo que no depende del estado (costos hacia cada base) para que evaluar un
        nodo del árbol de Minimax sea rápido.
        Precondiciones: ``escenario`` está validado; ``bando_max`` es ``"A"`` o ``"B"``.
        Postcondiciones: el evaluador queda listo; los costos hacia una posición del recurso se calculan la primera vez
        que se necesitan y se reutilizan. Se lanza ``ValueError`` si ``bando_max`` no es un bando válido.
        Complejidad: O(F*C log(F*C)) temporal y O(F*C) espacial por los dos mapas de costos hacia las bases.
        Uso de IA: Si.
        Intervencion de IA: Claude (Opus 5.5): precomputación e implementación (E8.2).
        Validacion del estudiante: pruebas de tests/algoritmos/test_utilidad.py, incluido el rechazo de un bando MAX
        inválido.
        """
        if bando_max not in BANDOS:
            raise ValueError(f"El bando MAX debe ser 'A' o 'B' y se recibio {bando_max!r}.")
        self.escenario = escenario
        self.bando_max = bando_max
        self.pesos = pesos if pesos is not None else PesosUtilidad()
        self._costos: dict[Posicion, dict[Posicion, int | float]] = {}
        for bando in BANDOS:
            self._costos_hacia(escenario.bases[bando])

    def _costos_hacia(self, destino: Posicion) -> dict[Posicion, int | float]:
        if destino not in self._costos:
            self._costos[destino] = costos_hacia(self.escenario, destino)
        return self._costos[destino]

    def _costo(self, origen: Posicion, destino: Posicion) -> int | float:
        """Obtener el costo mínimo desde ``origen`` hasta ``destino`` en el escenario.

        Proposito: consultar la distancia ponderada que usa la utilidad, respetando los muros y los costos del JSON.
        Precondiciones: ambos argumentos son posiciones del escenario; ``destino`` es transitable y el escenario está
        validado. Si el destino aún no está preparado, la llamada interna calcula y guarda en caché sus distancias.
        Postcondiciones: se devuelve el costo óptimo si ``origen`` alcanza el destino; si no, uno más que el mayor costo
        alcanzable de ese mapa. El escenario no cambia.
        Complejidad: O(1) temporal con el mapa en caché, y O(V log V + E) temporal y O(V) espacial si se calcula el
        mapa, con V celdas transitables y E sus adyacencias. Para un origen inalcanzable, el máximo agrega O(V)
        temporal.
        Uso de IA: Si.
        Intervencion de IA: Claude (Opus 5.5): cálculo de distancias de la utilidad (E8.2). Codex: documentación del
        método durante la corrección de hallazgos.
        Validacion del estudiante: cobertura indirecta en tests/algoritmos/test_utilidad.py, cuyas pruebas de entrega y
        de carrera por el recurso leen las distancias a través de este método.
        """
        mapa = self._costos_hacia(destino)
        if origen in mapa:
            return mapa[origen]
        # Inalcanzable: más caro que cualquier ruta posible del mapa.
        return max(mapa.values()) + 1

    def _signo(self, bando: str) -> int:
        return 1 if bando == self.bando_max else -1

    def desglosar(self, estado: EstadoJuego) -> dict[str, float]:
        """Devolver el aporte de cada criterio a la utilidad del estado desde la perspectiva de MAX.

        Proposito: hacer explicable la evaluación: mostrar por qué un estado, o la acción que lleva a él, vale más que
        otro y cómo cambia al variar un peso.
        Precondiciones: ``estado`` es coherente con el escenario del evaluador.
        Postcondiciones: en un estado terminal se devuelve solo ``{"terminal": v}``, con ``v`` igual a ``+victoria``,
        ``-victoria`` o 0. En otro caso se devuelven los criterios ``posesion``, ``entrega``, ``carrera_recurso``,
        ``amenaza``, ``bloqueo`` y ``movilidad`` (los que no aplican valen 0). La suma de los valores es
        :meth:`evaluar`. Intercambiar MAX y MIN cambia el signo de cada valor. El estado no cambia.
        Complejidad: O(U^2) temporal por las comparaciones entre unidades y O(U) espacial; las distancias se leen de
        mapas precalculados en O(1), salvo la primera vez que aparece una nueva posición libre del recurso.
        Uso de IA: Si.
        Intervencion de IA: Claude (Opus 5.5): criterios, formulación de suma cero e implementación (E8.2).
        Validacion del estudiante: pruebas de tests/algoritmos/test_utilidad.py: cada criterio por separado,
        antisimetría entre roles, valores terminales y cambio de preferencia al variar los pesos.
        """
        pesos = self.pesos
        ganador = obtener_ganador(self.escenario, estado)
        if ganador is not None:
            return {"terminal": self._signo(ganador) * pesos.victoria}
        if estado.estado_partida == EMPATE_BLOQUEO:
            return {"terminal": 0.0}

        rival = BANDOS[1] if self.bando_max == BANDOS[0] else BANDOS[0]
        desglose = {nombre: 0.0 for nombre in ("posesion", "entrega", "carrera_recurso", "amenaza", "bloqueo", "movilidad")}
        portador = obtener_portador(estado)
        if portador is not None:
            signo = self._signo(portador.bando)
            base = self.escenario.bases[portador.bando]
            rivales = [u for u in estado.unidades if u.bando != portador.bando]
            desglose["posesion"] = signo * pesos.posesion
            desglose["entrega"] = -signo * pesos.entrega * self._costo(portador.posicion, base)
            adyacentes = sum(_manhattan(u.posicion, portador.posicion) == 1 for u in rivales)
            desglose["amenaza"] = -signo * pesos.amenaza * adyacentes
            bloqueadores = sum(_dentro_del_rectangulo(u.posicion, portador.posicion, base) for u in rivales)
            desglose["bloqueo"] = -signo * pesos.bloqueo * bloqueadores
        elif estado.posicion_recurso is not None:
            mejor = {
                bando: min(
                    (self._costo(u.posicion, estado.posicion_recurso) for u in estado.unidades if u.bando == bando),
                    default=self._costo(self.escenario.bases[bando], estado.posicion_recurso),
                )
                for bando in BANDOS
            }
            desglose["carrera_recurso"] = pesos.carrera_recurso * (mejor[rival] - mejor[self.bando_max])

        ocupadas = frozenset(u.posicion for u in estado.unidades)
        disponibles = {bando: 0 for bando in BANDOS}
        for unidad in estado.unidades:
            if generar_movimientos(self.escenario, unidad, ocupadas):
                disponibles[unidad.bando] += 1
        desglose["movilidad"] = pesos.movilidad * (disponibles[self.bando_max] - disponibles[rival])
        return desglose

    def evaluar(self, estado: EstadoJuego) -> float:
        """Utilidad del estado para MAX: la suma de :meth:`desglosar`. Un valor mayor es mejor para MAX."""
        return sum(self.desglosar(estado).values())


@dataclass(frozen=True)
class AccionValorada:
    """Acción táctica legal, utilidad del estado al que lleva y desglose de esa utilidad."""

    accion_tactica: AccionTactica
    utilidad: float
    desglose: dict[str, float]


def valorar_acciones(evaluador: EvaluadorUtilidad, estado: EstadoJuego) -> tuple[AccionValorada, ...]:
    """Valorar cada acción legal del bando en turno por la utilidad, para MAX, del estado que produce.

    Proposito: explicar a un paso por qué una acción recibe mejor valoración que otra y qué criterio cambia; es la
    evaluación que Minimax hace en las hojas, sin considerar la respuesta del adversario.
    Precondiciones: ``estado`` es coherente con el escenario del evaluador.
    Postcondiciones: se devuelve una ``AccionValorada`` por cada acción de ``acciones_tacticas``, en el mismo orden, o
    una tupla vacía si no hay acciones. El estado no cambia.
    Complejidad: O(A * (U + U^2)) temporal y O(A * U) espacial, con A la cantidad de acciones legales.
    Uso de IA: Si.
    Intervencion de IA: Claude (Opus 5.5): consulta e implementación (E8.2).
    Validacion del estudiante: pruebas de tests/algoritmos/test_utilidad.py: orden de las acciones, evaluación del
    sucesor y comparación de acciones con la mejor explicada.
    """
    valoradas = []
    for accion_tactica in acciones_tacticas(evaluador.escenario, estado):
        sucesor = aplicar_accion(evaluador.escenario, estado, accion_tactica.accion)
        desglose = evaluador.desglosar(sucesor)
        valoradas.append(AccionValorada(accion_tactica, sum(desglose.values()), desglose))
    return tuple(valoradas)
