"""Estado dinámico y reglas del dominio de TacticalGrid."""

from .accion import INTERCEPTAR, MOVER, Accion
from .estado import EstadoJuego, crear_estado_inicial
from .problema import Problema, ProblemaNavegacion
from .partida import acciones_para_unidad, preparar_turno, unidades_seleccionables
from .recurso import bando_que_entrego_recurso, obtener_portador, posicion_del_recurso, recoger_recurso
from .reglas import (
    acciones_validas,
    aplicar_accion,
    costo_accion,
    es_accion_valida,
    es_terminal,
    generar_sucesores,
    obtener_ganador,
)
from .tacticas import TIPOS_TACTICOS, AccionTactica, acciones_tacticas, clasificar_accion
from .unidad import Unidad

__all__ = [
    "INTERCEPTAR",
    "MOVER",
    "TIPOS_TACTICOS",
    "Accion",
    "AccionTactica",
    "EstadoJuego",
    "Problema",
    "ProblemaNavegacion",
    "Unidad",
    "acciones_para_unidad",
    "acciones_tacticas",
    "acciones_validas",
    "aplicar_accion",
    "bando_que_entrego_recurso",
    "clasificar_accion",
    "costo_accion",
    "crear_estado_inicial",
    "es_accion_valida",
    "es_terminal",
    "generar_sucesores",
    "obtener_ganador",
    "obtener_portador",
    "posicion_del_recurso",
    "preparar_turno",
    "recoger_recurso",
    "unidades_seleccionables",
]
