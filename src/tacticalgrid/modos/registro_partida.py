"""Formato experimental versionado para registrar partidas manuales sin cambiar el contrato del escenario."""

import hashlib
import json
import base64
from typing import Mapping

from tacticalgrid.juego.estado import EstadoJuego
from tacticalgrid.juego.partida_manual import TurnoManual, huella_estado

FORMATO_PARTIDA = "tacticalgrid.partida/1"


def estado_a_diccionario(estado: EstadoJuego) -> dict[str, object]:
    """Serializa los campos dinámicos del estado para el registro reproducible.

    Proposito: representar unidades, turno, recurso y terminalidad de forma estable.
    Precondiciones: ``estado`` es una instancia válida de EstadoJuego.
    Postcondiciones: devuelve estructuras básicas serializables sin modificar el estado.
    Complejidad: O(U) temporal y espacial para U unidades.
    Uso de IA: Si.
    Intervencion de IA: Codex agregó la instantánea completa al registro de partidas.
    Validacion del estudiante: no puedo confirmar revisión del equipo; pruebas de reproducción comparan instantáneas.
    """
    return {
        "unidades": [
            {"id": u.identificador, "bando": u.bando, "tipo": u.tipo,
             "fila": u.posicion.fila, "columna": u.posicion.columna}
            for u in estado.unidades
        ],
        "turno": estado.turno_actual,
        "recurso": None if estado.posicion_recurso is None else {
            "fila": estado.posicion_recurso.fila, "columna": estado.posicion_recurso.columna
        },
        "portador": estado.portador_recurso,
        "estado_partida": estado.estado_partida,
    }


def crear_registro_partida(
    escenario_base64: str,
    huella_escenario: str,
    estado_inicial: EstadoJuego,
    turnos: tuple[TurnoManual, ...],
    estado_final: EstadoJuego,
    resultado: str,
    modo: str,
    evaluacion: Mapping[str, object] | None = None,
    verificaciones: Mapping[str, object] | None = None,
) -> dict[str, object]:
    """Construye y sella un registro replayable de una partida manual o evaluación posterior.

    Proposito: preservar escenario íntegro, estados, secuencia de acciones y evaluación opcional en un formato aparte.
    Precondiciones: el texto JSON corresponde a ``huella_escenario``; turnos fueron creados tras acciones de dominio.
    Postcondiciones: devuelve un diccionario versionado con integridad SHA-256 del contenido; no altera sus entradas.
    Complejidad: O(N + T*U) temporal y espacial para N bytes de escenario, T eventos y U unidades.
    Uso de IA: Si.
    Intervencion de IA: Codex agregó exportación y reproducción de partidas manuales en esta continuación.
    Validacion del estudiante: no puedo confirmar revisión del equipo; pruebas prueban integridad y replay.
    """
    try:
        bytes_escenario = base64.b64decode(escenario_base64, validate=True)
    except (ValueError, TypeError) as error:
        raise ValueError("El contenido embebido del escenario no es Base64 válido.") from error
    if hashlib.sha256(bytes_escenario).hexdigest() != huella_escenario:
        raise ValueError("La huella del escenario no corresponde al contenido incluido.")
    registro: dict[str, object] = {
        "formato": FORMATO_PARTIDA,
        "version": 1,
        "modo": modo,
        "escenario": {"contenido_base64": escenario_base64, "huella_sha256": huella_escenario},
        "estado_inicial": {"datos": estado_a_diccionario(estado_inicial), "huella_sha256": huella_estado(estado_inicial)},
        "acciones": [turno.a_diccionario() for turno in turnos],
        "estado_final": {"datos": estado_a_diccionario(estado_final), "huella_sha256": huella_estado(estado_final)},
        "resultado": resultado,
        "evaluacion": None if evaluacion is None else dict(evaluacion),
        "verificaciones": {} if verificaciones is None else dict(verificaciones),
    }
    canonico = json.dumps(registro, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    registro["integridad_sha256"] = hashlib.sha256(canonico.encode("utf-8")).hexdigest()
    return registro


def huella_contenido_registro(registro: Mapping[str, object]) -> str:
    """Calcula la huella de integridad del registro excluyendo su propio campo de sello."""
    contenido = {clave: valor for clave, valor in registro.items() if clave != "integridad_sha256"}
    canonico = json.dumps(contenido, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonico.encode("utf-8")).hexdigest()
