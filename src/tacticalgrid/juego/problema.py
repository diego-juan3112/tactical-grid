"""Contrato común de problema de búsqueda y su instancia de navegación de una unidad."""

from typing import Protocol

from tacticalgrid.escenario.escenario import Escenario, Posicion

from .accion import Accion
from .estado import EstadoJuego, crear_estado_inicial
from .reglas import buscar_unidad, costo_accion, desplazar_unidad, generar_movimientos


class Problema(Protocol):
    """Interfaz que consumen los algoritmos de búsqueda: estado inicial, acciones, sucesor, objetivo y costo."""

    estado_inicial: EstadoJuego

    def acciones(self, estado: EstadoJuego) -> tuple[Accion, ...]: ...

    def resultado(self, estado: EstadoJuego, accion: Accion) -> EstadoJuego: ...

    def es_objetivo(self, estado: EstadoJuego) -> bool: ...

    def costo(self, estado: EstadoJuego, accion: Accion) -> int | float: ...

    def posicion(self, estado: EstadoJuego) -> Posicion: ...


class ProblemaNavegacion:
    """Llevar una unidad desde su posición actual hasta una celda objetivo, sin considerar al adversario.

    Reglas de la navegación (modo ``busqueda``): solo se mueve la unidad indicada, el turno no cambia y las demás
    unidades no bloquean el paso, porque en esta etapa se ignora el comportamiento del resto de las unidades. El
    movimiento, la recogida del recurso y el costo son los mismos de la partida (``reglas``).
    """

    def __init__(
        self,
        escenario: Escenario,
        identificador_unidad: str,
        objetivo: Posicion,
        estado_inicial: EstadoJuego | None = None,
    ) -> None:
        """Definir un problema de navegación sobre un escenario cargado.

        Proposito: fijar de forma inequívoca el estado inicial, la unidad que actúa, la celda objetivo y la cota
        inferior de costo disponible para las heurísticas.
        Precondiciones: ``escenario`` está validado por la capa de escenario.
        Postcondiciones: ``estado_inicial`` es el estado recibido o el inicial del escenario; ``costo_minimo_paso``
        contiene el menor costo de terreno transitable. Se lanza ``ValueError`` si la unidad no existe o si el objetivo
        está fuera del mapa.
        Complejidad: O(U log U + T) temporal y O(U) espacial por construir y normalizar el estado inicial y recorrer los
        T tipos de terreno.
        Uso de IA: Si.
        Intervencion de IA: Claude (Opus 5.5): construcción original. Codex: cálculo único de la cota mínima de costo
        desde el escenario validado y actualización de esta documentación (E6.1).
        Validacion del estudiante: pruebas de tests/juego/test_problema.py.
        """
        if not escenario.contiene_posicion(objetivo):
            raise ValueError(f"El objetivo {objetivo} esta fuera de los limites del escenario.")
        self.escenario = escenario
        self.identificador_unidad = identificador_unidad
        self.objetivo = objetivo
        self.estado_inicial = estado_inicial if estado_inicial is not None else crear_estado_inicial(escenario)
        buscar_unidad(self.estado_inicial, identificador_unidad)
        self._costo_minimo_paso = min(
            terreno.costo
            for terreno in escenario.tipos_terreno.values()
            if terreno.transitable and terreno.costo is not None
        )

    @property
    def costo_minimo_paso(self) -> int | float:
        """Devolver la cota inferior de costo de cualquier transición de navegación.

        Proposito: exponer a las heurísticas el menor costo transitable del escenario, sin acoplar los algoritmos al
        catálogo de terrenos ni duplicar su lectura.
        Precondiciones: el problema se construyó con un ``Escenario`` validado, cuyos terrenos transitables tienen
        costos numéricos, positivos y finitos.
        Postcondiciones: se devuelve siempre el mismo valor positivo calculado en la construcción; el problema y el
        escenario no cambian. La finitud de cada costo no garantiza que sus productos o acumulaciones sean
        representables.
        Complejidad: O(1) temporal y espacial por consulta.
        Uso de IA: Si.
        Intervencion de IA: Codex: implementación de la propiedad y aclaración sobre la finitud de los costos (E6.1).
        Validacion del estudiante: pruebas de tests/juego/test_problema.py y
        tests/algoritmos/test_heuristica_obstaculos.py.
        """
        return self._costo_minimo_paso

    def acciones(self, estado: EstadoJuego) -> tuple[Accion, ...]:
        """Devolver los movimientos de la unidad navegante a celdas adyacentes, dentro del mapa y transitables."""
        return generar_movimientos(self.escenario, buscar_unidad(estado, self.identificador_unidad))

    def resultado(self, estado: EstadoJuego, accion: Accion) -> EstadoJuego:
        """Aplicar el movimiento con las reglas comunes y conservar el turno, porque no hay adversario activo."""
        if accion not in self.acciones(estado):
            raise ValueError(f"La accion {accion} no es valida para la navegacion actual.")
        return desplazar_unidad(self.escenario, estado, accion)

    def es_objetivo(self, estado: EstadoJuego) -> bool:
        """Condición objetivo: la unidad navegante ocupa la celda objetivo."""
        return self.posicion(estado) == self.objetivo

    def posicion(self, estado: EstadoJuego) -> Posicion:
        """Posición de la unidad navegante, con la que se reporta el camino de una búsqueda."""
        return buscar_unidad(estado, self.identificador_unidad).posicion

    def costo(self, estado: EstadoJuego, accion: Accion) -> int | float:
        """Costo del paso: el del terreno destino según el JSON cargado."""
        return costo_accion(self.escenario, accion)
