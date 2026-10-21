"""Registro inmutable de una partida ejecutada por una persona desde la GUI."""

import hashlib
import json
from dataclasses import asdict, dataclass

from tacticalgrid.escenario.escenario import Escenario
from tacticalgrid.juego.accion import Accion
from tacticalgrid.juego.estado import EstadoJuego
from tacticalgrid.juego.reglas import costo_accion


def huella_estado(estado: EstadoJuego) -> str:
    """Calcula una huella canónica de todos los campos dinámicos del estado.

    Proposito: detectar alteraciones en estados registrados sin depender del orden de almacenamiento de unidades.
    Precondiciones: ``estado`` es una instancia de ``EstadoJuego``.
    Postcondiciones: devuelve el SHA-256 de una representación JSON estable; no modifica el estado.
    Complejidad: O(U log U) temporal y O(U) espacial para U unidades.
    Uso de IA: Si.
    Intervencion de IA: Codex agregó el registro verificable de partidas manuales en esta continuación.
    Validacion del estudiante: no puedo confirmar revisión del equipo; pruebas verifican estabilidad y detección de cambios.
    """
    contenido = {
        "unidades": [
            [u.identificador, u.bando, u.tipo, u.posicion.fila, u.posicion.columna] for u in estado.unidades
        ],
        "turno": estado.turno_actual,
        "recurso": None if estado.posicion_recurso is None else [estado.posicion_recurso.fila, estado.posicion_recurso.columna],
        "portador": estado.portador_recurso,
        "estado": estado.estado_partida,
    }
    bytes_estado = json.dumps(contenido, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(bytes_estado).hexdigest()


@dataclass(frozen=True)
class TurnoManual:
    """Accion realmente ejecutada y transición observada en una partida manual."""

    numero: int
    bando: str
    hubo_pase: bool
    estado_previo: EstadoJuego
    accion: Accion
    costo: int | float
    estado_resultante: EstadoJuego
    huella_previa: str
    huella_resultante: str

    def a_diccionario(self) -> dict[str, object]:
        """Convierte un evento ejecutado a campos serializables.

        Proposito: exponer acción, costo, turno y huellas para el registro externo.
        Precondiciones: la instancia representa una transición aplicada por el dominio.
        Postcondiciones: devuelve un diccionario sin referencias mutables a objetos de juego.
        Complejidad: O(1) temporal y espacial respecto del tamaño del evento.
        Uso de IA: Si.
        Intervencion de IA: Codex documentó el formato de historial manual en esta continuación.
        Validacion del estudiante: no puedo confirmar revisión del equipo; tests/modos/test_registro_partida.py valida campos.
        """
        return {
            "numero": self.numero,
            "bando": self.bando,
            "hubo_pase": self.hubo_pase,
            "unidad": self.accion.identificador_unidad,
            "tipo_accion": self.accion.tipo,
            "origen": asdict(self.accion.origen),
            "destino": asdict(self.accion.destino),
            "costo": self.costo,
            "huella_previa": self.huella_previa,
            "huella_resultante": self.huella_resultante,
        }


@dataclass(frozen=True)
class ResultadoPartidaManual:
    """Historial de acciones humanas con contrato de lectura compatible con el verificador de partidas."""

    estado_inicial: EstadoJuego
    turnos: tuple[TurnoManual, ...]
    estado_final: EstadoJuego
    resultado: str
    max_turnos: int
    algoritmo: str = "manual"
    profundidad: int = 0
    orden_acciones: str = "generacion"

    @classmethod
    def desde_estado(
        cls, escenario: Escenario, estado_inicial: EstadoJuego, turnos: tuple[TurnoManual, ...], estado_final: EstadoJuego
    ) -> "ResultadoPartidaManual":
        """Construye el resultado de la sesión y deriva su marcador del estado final real.

        Proposito: entregar al verificador el estado inicial, los eventos ejecutados y el estado visible final.
        Precondiciones: el escenario está validado y los estados pertenecen a la misma sesión.
        Postcondiciones: devuelve un registro completo; un resultado no terminal se representa como ``en_curso``.
        Complejidad: O(U) temporal por localizar el ganador, con U unidades.
        Uso de IA: Si.
        Intervencion de IA: Codex agregó el registro verificable de partidas manuales en esta continuación.
        Validacion del estudiante: no puedo confirmar revisión del equipo; pruebas lo contrastan con reglas y verificador.
        """
        from tacticalgrid.juego.reglas import EMPATE_BLOQUEO, obtener_ganador

        ganador = obtener_ganador(escenario, estado_final)
        resultado = f"victoria_{ganador}" if ganador else EMPATE_BLOQUEO if estado_final.estado_partida == EMPATE_BLOQUEO else "en_curso"
        return cls(estado_inicial, turnos, estado_final, resultado, max(1, len(turnos)))
