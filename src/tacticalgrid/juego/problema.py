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

        Proposito: fijar de forma inequivoca estado inicial, unidad que actua y celda objetivo.
        Precondiciones: ``escenario`` fue validado por la capa de escenario.
        Postcondiciones: ``estado_inicial`` es el estado dado o el inicial del escenario; se lanza
        ``ValueError`` si la unidad no existe o si el objetivo esta fuera del mapa.
        Complejidad: O(U log U) temporal y O(U) espacial al construir el estado inicial.
        Uso de IA: Si.
        Intervencion de IA: Claude (Opus 5.5) propuso la implementacion y su documentacion.
        Validacion del estudiante: el estudiante valido con pytest la construccion, el rechazo de unidad u
        objetivo invalidos y la exploracion completa de los escenarios del repositorio
        (tests/juego/test_problema.py y tests/juego/test_espacio_estados.py).
        """
        if not escenario.contiene_posicion(objetivo):
            raise ValueError(f"El objetivo {objetivo} esta fuera de los limites del escenario.")
        self.escenario = escenario
        self.identificador_unidad = identificador_unidad
        self.objetivo = objetivo
        self.estado_inicial = estado_inicial if estado_inicial is not None else crear_estado_inicial(escenario)
        buscar_unidad(self.estado_inicial, identificador_unidad)

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
        return buscar_unidad(estado, self.identificador_unidad).posicion == self.objetivo

    def costo(self, estado: EstadoJuego, accion: Accion) -> int | float:
        """Costo del paso: el del terreno destino segun el JSON cargado."""
        return costo_accion(self.escenario, accion)
