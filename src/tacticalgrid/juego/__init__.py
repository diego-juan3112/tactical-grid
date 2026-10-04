"""Estado dinamico y reglas del dominio de TacticalGrid."""

from .accion import Accion
from .estado import EstadoJuego, crear_estado_inicial
from .problema import Problema, ProblemaNavegacion
from .reglas import (
    acciones_validas,
    aplicar_accion,
    costo_accion,
    es_accion_valida,
    es_terminal,
    generar_sucesores,
    obtener_ganador,
)
from .unidad import Unidad

__all__ = [
    "Accion",
    "EstadoJuego",
    "Problema",
    "ProblemaNavegacion",
    "Unidad",
    "acciones_validas",
    "aplicar_accion",
    "costo_accion",
    "crear_estado_inicial",
    "es_accion_valida",
    "es_terminal",
    "generar_sucesores",
    "obtener_ganador",
]
