"""Registro inmutable de una partida jugada por una persona desde la interfaz gráfica."""

import hashlib
import json
from dataclasses import asdict, dataclass

from tacticalgrid.escenario.escenario import Escenario
from tacticalgrid.juego.accion import Accion
from tacticalgrid.juego.estado import EstadoJuego
from tacticalgrid.juego.reglas import costo_accion


def huella_estado(estado: EstadoJuego) -> str:
    """Calcular una huella canónica de todos los campos dinámicos del estado.

    Proposito: detectar alteraciones en estados registrados sin depender del orden de almacenamiento de las unidades.
    Precondiciones: ``estado`` es una instancia de ``EstadoJuego``.
    Postcondiciones: se devuelve el SHA-256 de una representación JSON estable; el estado no cambia.
    Complejidad: O(U log U) temporal y O(U) espacial, con U unidades.
    Uso de IA: Si.
    Intervencion de IA: Codex: registro verificable de partidas manuales.
    Validacion del estudiante: prueba de exportación y reproducción de una partida manual en
    tests/interfaz/test_control.py, cuya verificación compara las huellas de cada transición.
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
    """Acción ejecutada y transición observada en una partida manual."""

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
        """Convertir un evento ejecutado en campos serializables.

        Proposito: exponer acción, costo, turno y huellas para el registro externo.
        Precondiciones: la instancia representa una transición aplicada por el dominio.
        Postcondiciones: se devuelve un diccionario sin referencias mutables a objetos del juego.
        Complejidad: O(1) temporal y espacial respecto del tamaño del evento.
        Uso de IA: Si.
        Intervencion de IA: Codex: formato del historial manual y su documentación.
        Validacion del estudiante: prueba de exportación y reproducción de tests/interfaz/test_control.py, que lee el
        registro exportado y lo vuelve a aplicar.
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
    """Historial de acciones manuales, legible por el verificador de partidas."""

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
        """Construir el resultado de la sesión y derivar su marcador del estado final.

        Proposito: entregar al verificador el estado inicial, los eventos ejecutados y el estado final visible.
        Precondiciones: el escenario está validado y los estados pertenecen a la misma sesión.
        Postcondiciones: se devuelve un registro completo; un resultado no terminal se representa como ``en_curso``.
        Complejidad: O(U) temporal por localizar al ganador, con U unidades.
        Uso de IA: Si.
        Intervencion de IA: Codex: registro verificable de partidas manuales.
        Validacion del estudiante: pruebas de tests/interfaz/test_control.py que verifican el historial con
        ``verificar_partida`` y detectan un costo alterado.
        """
        from tacticalgrid.juego.reglas import EMPATE_BLOQUEO, obtener_ganador

        ganador = obtener_ganador(escenario, estado_final)
        resultado = f"victoria_{ganador}" if ganador else EMPATE_BLOQUEO if estado_final.estado_partida == EMPATE_BLOQUEO else "en_curso"
        return cls(estado_inicial, turnos, estado_final, resultado, max(1, len(turnos)))
