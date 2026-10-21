"""Formato versionado para registrar partidas manuales sin cambiar el contrato del escenario."""

import hashlib
import json
import base64
from typing import Mapping

from tacticalgrid.juego.estado import EstadoJuego
from tacticalgrid.juego.partida_manual import TurnoManual, huella_estado

FORMATO_PARTIDA = "tacticalgrid.partida/1"


def estado_a_diccionario(estado: EstadoJuego) -> dict[str, object]:
    """Serializar los campos dinámicos del estado para el registro reproducible.

    Proposito: representar de forma estable las unidades, el turno, el recurso y la terminalidad.
    Precondiciones: ``estado`` es una instancia válida de ``EstadoJuego``.
    Postcondiciones: se devuelven estructuras básicas serializables; el estado no cambia.
    Complejidad: O(U) temporal y espacial para U unidades.
    Uso de IA: Si.
    Intervencion de IA: Codex: instantánea completa del estado en el registro de partidas.
    Validacion del estudiante: prueba ``test_exporta_y_reproduce_partida_manual_desde_escenario_embebido`` de
    tests/interfaz/test_control.py, que compara las instantáneas al reproducir.
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
    """Construir y sellar un registro reproducible de una partida manual o de una evaluación posterior.

    Proposito: conservar el escenario íntegro, los estados, la secuencia de acciones y la evaluación opcional en un
    formato aparte.
    Precondiciones: el texto JSON corresponde a ``huella_escenario``; los turnos se crearon a partir de acciones del
    dominio.
    Postcondiciones: se devuelve un diccionario versionado con la huella SHA-256 de integridad de su contenido; las
    entradas no cambian.
    Complejidad: O(N + T*U) temporal y espacial para N bytes de escenario, T eventos y U unidades.
    Uso de IA: Si.
    Intervencion de IA: Codex: exportación y reproducción de partidas manuales.
    Validacion del estudiante: pruebas de tests/interfaz/test_control.py: exportación y reproducción de una partida
    manual, reproducción de una evaluación adversarial y rechazo de un registro alterado.
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
    """Calcular la huella de integridad del registro sin incluir su propio campo de sello."""
    contenido = {clave: valor for clave, valor in registro.items() if clave != "integridad_sha256"}
    canonico = json.dumps(contenido, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonico.encode("utf-8")).hexdigest()
