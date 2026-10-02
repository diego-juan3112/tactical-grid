"""Representacion de alto nivel del estado dinamico del juego."""

from dataclasses import dataclass

from tacticalgrid.escenario.escenario import Escenario, Posicion

from .unidad import Unidad


@dataclass(frozen=True)
class EstadoJuego:
    """Situacion dinamica inmutable cuya identidad no depende del orden de las unidades."""

    unidades: tuple[Unidad, ...]
    turno_actual: str
    posicion_recurso: Posicion | None
    portador_recurso: str | None
    estado_partida: str = "en_curso"

    def __post_init__(self) -> None:
        """Normaliza las unidades para que su orden de entrada no altere el estado logico.

        Proposito: construir una representacion canonica ordenada por identificador de unidad.
        Precondiciones: ``unidades`` contiene instancias inmutables de ``Unidad`` con identificadores comparables.
        Postcondiciones: dos colecciones con las mismas unidades producen la misma tupla canonica; el estado
        permanece inmutable y hashable.
        Complejidad: O(U log U) temporal y O(U) espacial, donde U es el numero de unidades.
        Uso de IA: Si.
        Intervencion de IA: Codex propuso normalizar por identificador para corregir la dependencia accidental
        del orden detectada durante la auditoria de E1.1.
        Validacion del estudiante: cubierta por pruebas de igualdad, orden, hashing y diferencias dinamicas.
        """
        object.__setattr__(self, "unidades", tuple(sorted(self.unidades, key=lambda unidad: unidad.identificador)))


def crear_estado_inicial(escenario: Escenario) -> EstadoJuego:
    """Construye el estado dinamico inicial a partir de un escenario ya validado.

    Proposito: separar la representacion estatica cargada del estado que cambiara durante la partida.
    Precondiciones: ``escenario`` fue construido por la capa de escenario y cumple sus invariantes.
    Postcondiciones: devuelve un ``EstadoJuego`` independiente, sin leer JSON ni iniciar Pygame.
    Complejidad: O(U log U) temporal y O(U) espacial, donde U es el numero de unidades iniciales.
    Uso de IA: Si.
    Intervencion de IA: Codex propuso esta conversion inicial sin introducir reglas de movimiento y actualizo
    su ubicacion a la capa de juego conforme a E0.3; Claude (Sonnet 5) tradujo el encabezado de
    precondiciones a espanol.
    Validacion del estudiante: cubierta por pruebas automatizadas de construccion e identidad del estado.
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
