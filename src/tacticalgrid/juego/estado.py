"""Representación del estado dinámico del juego."""

from dataclasses import dataclass

from tacticalgrid.escenario.escenario import Escenario, Posicion

from .unidad import Unidad


@dataclass(frozen=True)
class EstadoJuego:
    """Situación dinámica inmutable cuya identidad no depende del orden de las unidades."""

    unidades: tuple[Unidad, ...]
    turno_actual: str
    posicion_recurso: Posicion | None
    portador_recurso: str | None
    estado_partida: str = "en_curso"

    def __post_init__(self) -> None:
        """Normalizar las unidades para que su orden de entrada no altere el estado lógico.

        Proposito: construir una representación canónica ordenada por identificador de unidad.
        Precondiciones: ``unidades`` contiene instancias inmutables de ``Unidad`` con identificadores comparables.
        Postcondiciones: dos colecciones con las mismas unidades producen la misma tupla canónica; el estado es
        inmutable y hashable.
        Complejidad: O(U log U) temporal y O(U) espacial, con U unidades.
        Uso de IA: Si.
        Intervencion de IA: Codex: normalización por identificador para corregir la dependencia accidental del orden
        detectada en la auditoría de E1.1.
        Validacion del estudiante: pruebas de tests/juego/test_estado.py: igualdad, orden de las unidades, uso en
        conjuntos y diferencias por portador, turno y posición.
        """
        object.__setattr__(self, "unidades", tuple(sorted(self.unidades, key=lambda unidad: unidad.identificador)))


def crear_estado_inicial(escenario: Escenario) -> EstadoJuego:
    """Construir el estado dinámico inicial a partir de un escenario validado.

    Proposito: separar la representación estática cargada del estado que cambia durante la partida.
    Precondiciones: ``escenario`` proviene de la capa de escenario y cumple sus invariantes.
    Postcondiciones: se devuelve un ``EstadoJuego`` independiente, sin leer JSON ni iniciar Pygame.
    Complejidad: O(U log U) temporal y O(U) espacial, con U unidades iniciales.
    Uso de IA: Si.
    Intervencion de IA: Codex: conversión inicial sin reglas de movimiento y traslado a la capa de juego (E0.3).
    Claude (Sonnet 5): traducción al español del encabezado de precondiciones.
    Validacion del estudiante: prueba ``test_estado_inicial_separa_unidades_y_recurso_del_escenario`` de
    tests/juego/test_estado.py.
    """
    unidades = tuple(
        Unidad(
            identificador=unidad.identificador,
            bando=unidad.bando,
            tipo=unidad.tipo,
            posicion=unidad.posicion,
        )
        for unidad in escenario.unidades_iniciales
    )
    return EstadoJuego(
        unidades=unidades,
        turno_actual=escenario.turno_inicial,
        posicion_recurso=None if escenario.portador_recurso_inicial else escenario.recurso,
        portador_recurso=escenario.portador_recurso_inicial,
    )
