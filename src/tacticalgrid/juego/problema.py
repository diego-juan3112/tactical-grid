"""Contrato comun de problema de busqueda y su instancia de navegacion de una unidad."""

from typing import Protocol

from tacticalgrid.escenario.escenario import Escenario, Posicion

from .accion import Accion
from .estado import EstadoJuego, crear_estado_inicial
from .reglas import buscar_unidad, costo_accion, desplazar_unidad, generar_movimientos


class Problema(Protocol):
    """Interfaz que consumen los algoritmos de busqueda: estado inicial, acciones, sucesor, objetivo y costo."""

    estado_inicial: EstadoJuego

    def acciones(self, estado: EstadoJuego) -> tuple[Accion, ...]: ...

    def resultado(self, estado: EstadoJuego, accion: Accion) -> EstadoJuego: ...

    def es_objetivo(self, estado: EstadoJuego) -> bool: ...

    def costo(self, estado: EstadoJuego, accion: Accion) -> int | float: ...

    def posicion(self, estado: EstadoJuego) -> Posicion: ...


class ProblemaNavegacion:
    """Lleva una unidad desde su posicion actual hasta una celda objetivo ignorando al adversario.

    Reglas de la navegacion (modo ``busqueda``): solo se mueve la unidad indicada, el turno no cambia y las
    demas unidades no bloquean el paso, pues en esta etapa se ignora temporalmente el comportamiento del resto
    de unidades. El movimiento, la recogida del recurso y el costo son los mismos de la partida (``reglas``).
    """

    def __init__(
        self,
        escenario: Escenario,
        identificador_unidad: str,
        objetivo: Posicion,
        estado_inicial: EstadoJuego | None = None,
    ) -> None:
        """Define un problema de navegacion sobre un escenario cargado.

        Purpose: fijar de forma inequivoca estado inicial, unidad que actua, celda objetivo y la cota inferior
        de costo que puede usar una heuristica sobre esta navegacion.
        Preconditions: ``escenario`` fue validado por la capa de escenario.
        Postconditions: ``estado_inicial`` es el estado dado o el inicial del escenario; ``costo_minimo_paso``
        contiene el menor costo de terreno transitable; se lanza ``ValueError`` si la unidad no existe o si el
        objetivo esta fuera del mapa.
        Complexity: O(U log U + T) temporal y O(U) espacial al construir y normalizar el estado inicial y
        recorrer los T tipos de terreno.
        AI usage: Yes.
        AI intervention: Claude (Opus 5.5) propuso la construccion original; Codex incorporo en E6.1 el calculo
        unico de la cota minima de costo desde el escenario validado y actualizo esta documentacion.
        Student validation: pendiente de revision humana del cambio de E6.1.
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
        """Devuelve la cota inferior de costo para cualquier transicion de navegacion.

        Purpose: exponer a las heuristicas el menor costo transitable del escenario sin acoplar los algoritmos
        al catalogo de terrenos ni duplicar su lectura.
        Preconditions: el problema fue construido con un ``Escenario`` validado, cuyos terrenos transitables
        tienen costos individuales numericos, positivos y finitos.
        Postconditions: devuelve siempre el mismo valor positivo calculado durante la construccion; no modifica
        el problema ni el escenario.
        Complexity: O(1) temporal y O(1) espacial por consulta.
        AI usage: Yes.
        AI intervention: Codex implemento esta propiedad y aclaro en E6.1 que la finitud individual no garantiza
        por si sola que productos o acumulaciones posteriores sean representables.
        Student validation: pendiente de revision humana del equipo.
        """
        return self._costo_minimo_paso

    def acciones(self, estado: EstadoJuego) -> tuple[Accion, ...]:
        """Devuelve los movimientos de la unidad navegante a celdas adyacentes, dentro del mapa y transitables."""
        return generar_movimientos(self.escenario, buscar_unidad(estado, self.identificador_unidad))

    def resultado(self, estado: EstadoJuego, accion: Accion) -> EstadoJuego:
        """Aplica el movimiento con las reglas comunes y conserva el turno, ya que no hay adversario activo."""
        if accion not in self.acciones(estado):
            raise ValueError(f"La accion {accion} no es valida para la navegacion actual.")
        return desplazar_unidad(self.escenario, estado, accion)

    def es_objetivo(self, estado: EstadoJuego) -> bool:
        """Condicion objetivo: la unidad navegante ocupa la celda objetivo."""
        return self.posicion(estado) == self.objetivo

    def posicion(self, estado: EstadoJuego) -> Posicion:
        """Posicion de la unidad navegante; con ella se reporta el camino de una busqueda."""
        return buscar_unidad(estado, self.identificador_unidad).posicion

    def costo(self, estado: EstadoJuego, accion: Accion) -> int | float:
        """Costo del paso: el del terreno destino segun el JSON cargado."""
        return costo_accion(self.escenario, accion)
