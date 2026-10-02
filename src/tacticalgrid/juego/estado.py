"""Representacion de alto nivel del estado dinamico del juego."""

from dataclasses import dataclass

from tacticalgrid.escenario.escenario import Escenario, Posicion

from .unidad import Unidad


@dataclass(frozen=True)
class EstadoJuego:
    """Situacion dinamica completa, sin decidir aun las reglas detalladas de transicion."""

    unidades: tuple[Unidad, ...]
    turno_actual: str
    posicion_recurso: Posicion | None
    portador_recurso: str | None
    estado_partida: str = "en_curso"


def crear_estado_inicial(escenario: Escenario) -> EstadoJuego:
    """Construye el estado dinamico inicial a partir de un escenario ya validado.

    Proposito: separar la representacion estatica cargada del estado que cambiara durante la partida.
    Precondiciones: ``escenario`` fue construido por la capa de escenario y cumple sus invariantes.
    Postcondiciones: devuelve un ``EstadoJuego`` independiente, sin leer JSON ni iniciar Pygame.
    Complejidad: O(U) temporal y espacial, donde U es el numero de unidades iniciales.
    Uso de IA: Si.
    Intervencion de IA: Codex propuso esta conversion inicial sin introducir reglas de movimiento; Claude
    (Sonnet 5) tradujo el encabezado de precondiciones a espanol y reubico este modulo de
    ``interfaz/juego/`` a ``juego/`` (nivel superior) para cumplir la separacion de capas exigida por el
    enunciado y documentada en AGENTS.md/README.md.
    Validacion del estudiante: pendiente de revision del equipo; cubierta por pruebas automatizadas.
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
