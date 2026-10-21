"""Reproducción determinista de registros de partidas sobre los contratos del dominio."""

from collections.abc import Mapping
import base64
from dataclasses import dataclass
import hashlib

from tacticalgrid.algoritmos.alfa_beta import alfa_beta
from tacticalgrid.algoritmos.comparacion_adversarial import comparar_minimax_alfa_beta
from tacticalgrid.algoritmos.minimax import minimax
from tacticalgrid.algoritmos.verificador import ReporteVerificacion, verificar_decision, verificar_partida
from tacticalgrid.escenario.escenario import Escenario, Posicion
from tacticalgrid.juego.accion import Accion
from tacticalgrid.juego.estado import EstadoJuego, crear_estado_inicial
from tacticalgrid.juego.partida import preparar_turno
from tacticalgrid.juego.partida_manual import ResultadoPartidaManual, TurnoManual, huella_estado
from tacticalgrid.juego.reglas import aplicar_accion, costo_accion, es_accion_valida, obtener_ganador
from tacticalgrid.modos.registro_partida import FORMATO_PARTIDA, estado_a_diccionario, huella_contenido_registro


@dataclass(frozen=True)
class ResultadoReproduccion:
    """Estados finales y reportes reconstruidos al reproducir un registro."""

    estado_final: EstadoJuego
    reporte_partida: ReporteVerificacion
    resultado_evaluacion: dict[str, object] | None
    reporte_decision: ReporteVerificacion | None


def reproducir_registro_partida(escenario: Escenario, registro: Mapping[str, object]) -> ResultadoReproduccion:
    """Validar la integridad, aplicar las acciones legales y repetir la evaluación adversarial archivada.

    Proposito: reconstruir una sesión desde el estado inicial derivado del JSON y comprobar cada transición registrada.
    Precondiciones: ``escenario`` está validado y ``registro`` tiene el formato ``tacticalgrid.partida/1``.
    Postcondiciones: se devuelven el estado reconstruido y los reportes válidos; ante un formato, huella, secuencia o
    resultado discrepante se lanza ``ValueError`` con la causa concreta. Las comparaciones ignoran solo el tiempo.
    Complejidad: O(T*U + B^d), con T jugadas, U unidades y una evaluación opcional con factor de ramificación B y
    profundidad d.
    Uso de IA: Si.
    Intervencion de IA: Codex: reproducción verificable de partidas jugadas en la interfaz gráfica.
    Validacion del estudiante: pruebas de tests/interfaz/test_control.py: reproducción de una partida manual y de una
    evaluación adversarial, y rechazo de un registro alterado y de un escenario incompatible.
    """
    if registro.get("formato") != FORMATO_PARTIDA or registro.get("version") != 1:
        raise ValueError("Formato de registro de partida no admitido.")
    if registro.get("integridad_sha256") != huella_contenido_registro(registro):
        raise ValueError("La integridad SHA-256 del registro no coincide; el archivo pudo alterarse o truncarse.")
    datos_escenario = registro.get("escenario")
    if not isinstance(datos_escenario, Mapping):
        raise ValueError("El registro no contiene el escenario original.")
    huella_escenario = datos_escenario.get("huella_sha256")
    try:
        escenario_bytes = base64.b64decode(datos_escenario.get("contenido_base64", ""), validate=True)
    except (ValueError, TypeError) as error:
        raise ValueError("El registro no contiene una copia Base64 válida del escenario.") from error
    if hashlib.sha256(escenario_bytes).hexdigest() != huella_escenario:
        raise ValueError("La huella SHA-256 del escenario no coincide con su copia embebida.")
    inicial = crear_estado_inicial(escenario)
    datos_inicial = registro.get("estado_inicial")
    if (
        not isinstance(datos_inicial, Mapping)
        or datos_inicial.get("huella_sha256") != huella_estado(inicial)
        or datos_inicial.get("datos") != estado_a_diccionario(inicial)
    ):
        raise ValueError("El escenario cargado no produce el estado inicial registrado.")
    eventos = registro.get("acciones")
    if not isinstance(eventos, list):
        raise ValueError("La secuencia de acciones debe ser una lista.")

    actual = inicial
    turnos: list[TurnoManual] = []
    for indice, evento in enumerate(eventos, start=1):
        if not isinstance(evento, Mapping) or evento.get("numero") != indice:
            raise ValueError(f"La secuencia está truncada o desordenada en la acción {indice}.")
        previo_preparado = preparar_turno(escenario, actual)
        hubo_pase = previo_preparado != actual
        if evento.get("hubo_pase") is not hubo_pase:
            raise ValueError(f"La acción {indice} declara un pase de turno incorrecto.")
        if evento.get("huella_previa") != huella_estado(previo_preparado):
            raise ValueError(f"La acción {indice} no parte del estado reproducido.")
        try:
            origen = evento["origen"]
            destino = evento["destino"]
            accion = Accion(
                identificador_unidad=evento["unidad"],
                origen=Posicion(origen["fila"], origen["columna"]),
                destino=Posicion(destino["fila"], destino["columna"]),
                tipo=evento["tipo_accion"],
            )
        except (KeyError, TypeError) as error:
            raise ValueError(f"La acción {indice} tiene campos incompletos o inválidos.") from error
        if evento.get("bando") != previo_preparado.turno_actual:
            raise ValueError(f"La acción {indice} asigna el turno al bando incorrecto.")
        if not es_accion_valida(escenario, previo_preparado, accion):
            raise ValueError(f"La acción {indice} no es legal para el estado reproducido: {accion}.")
        costo = costo_accion(escenario, accion)
        if evento.get("costo") != costo:
            raise ValueError(f"La acción {indice} registra un costo diferente al terreno destino.")
        siguiente = aplicar_accion(escenario, previo_preparado, accion)
        if evento.get("huella_resultante") != huella_estado(siguiente):
            raise ValueError(f"La acción {indice} produce un estado diferente al registrado.")
        turnos.append(
            TurnoManual(indice, previo_preparado.turno_actual, hubo_pase, previo_preparado, accion, costo,
                        siguiente, huella_estado(previo_preparado), huella_estado(siguiente))
        )
        actual = siguiente

    final = preparar_turno(escenario, actual)
    datos_finales = registro.get("estado_final")
    if (
        not isinstance(datos_finales, Mapping)
        or datos_finales.get("huella_sha256") != huella_estado(final)
        or datos_finales.get("datos") != estado_a_diccionario(final)
    ):
        raise ValueError("El estado final reconstruido no coincide; la secuencia puede estar incompleta.")
    resultado = _resultado(escenario, final)
    if registro.get("resultado") != resultado:
        raise ValueError(f"El resultado registrado no coincide con el estado reconstruido ({resultado}).")
    partida = ResultadoPartidaManual.desde_estado(escenario, inicial, tuple(turnos), final)
    reporte = verificar_partida(escenario, partida, verificar_arboles=False)
    if not reporte.es_valido:
        raise ValueError("El verificador rechazó la partida: " + "; ".join(item.detalle for item in reporte.fallidas))

    evaluacion = registro.get("evaluacion")
    resultado_evaluacion = None
    reporte_decision = None
    if evaluacion is not None:
        if not isinstance(evaluacion, Mapping):
            raise ValueError("La configuración de evaluación debe ser un objeto.")
        algoritmo = evaluacion.get("algoritmo")
        profundidad = evaluacion.get("profundidad")
        orden = evaluacion.get("orden_acciones")
        if algoritmo == "minimax":
            decision = minimax(escenario, final, profundidad, orden=orden)
            resultado_evaluacion = decision.a_diccionario()
            reporte_decision = verificar_decision(escenario, final, decision)
        elif algoritmo == "alfa_beta":
            decision = alfa_beta(escenario, final, profundidad, orden=orden)
            resultado_evaluacion = decision.a_diccionario()
            reporte_decision = verificar_decision(escenario, final, decision)
        elif algoritmo == "minimax_alfa_beta":
            comparacion = comparar_minimax_alfa_beta(escenario, final, profundidad, orden=orden)
            resultado_evaluacion = comparacion.a_diccionario()
            reportes = (
                verificar_decision(escenario, final, comparacion.minimax),
                verificar_decision(escenario, final, comparacion.alfa_beta),
            )
            reporte_decision = reportes[0] if all(item.es_valido for item in reportes) else reportes[1]
        else:
            raise ValueError(f"Algoritmo adversarial de registro desconocido: {algoritmo!r}.")
        if not reporte_decision.es_valido:
            raise ValueError("La decisión reproducida no pasó verificar_decision.")
        if not _equivalentes_deterministas(resultado_evaluacion, evaluacion.get("resultado")):
            raise ValueError("La decisión reproducida difiere en campos deterministas del resultado archivado.")
    return ResultadoReproduccion(final, reporte, resultado_evaluacion, reporte_decision)


def _resultado(escenario: Escenario, estado: EstadoJuego) -> str:
    ganador = obtener_ganador(escenario, estado)
    if ganador is not None:
        return f"victoria_{ganador}"
    return estado.estado_partida


def _equivalentes_deterministas(actual, esperado) -> bool:
    def sin_tiempo(valor):
        if isinstance(valor, Mapping):
            return {clave: sin_tiempo(item) for clave, item in valor.items() if clave != "tiempo_segundos"}
        if isinstance(valor, (list, tuple)):
            return [sin_tiempo(item) for item in valor]
        return valor

    return isinstance(esperado, Mapping) and sin_tiempo(actual) == sin_tiempo(esperado)
