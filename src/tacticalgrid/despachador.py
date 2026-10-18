"""Despacho entre la interfaz grafica predeterminada y la consola historica."""

import sys
from collections.abc import Sequence


def _ejecutar_gui(argumentos: Sequence[str]) -> int:
    """Importa Pygame solo cuando el modo grafico fue seleccionado."""
    from tacticalgrid.interfaz.aplicacion import ejecutar_desde_argumentos

    return ejecutar_desde_argumentos(argumentos)


def _ejecutar_consola(argumentos: Sequence[str]) -> int:
    """Importa el ejecutor textual sin cargar la interfaz grafica."""
    from tacticalgrid.consola import ejecutar_consola

    return ejecutar_consola(argumentos)


def ejecutar(argumentos: Sequence[str] | None = None) -> int:
    """Selecciona el modo de aplicacion sin mezclar sus parsers.

    Proposito: abrir Pygame por defecto y conservar cada invocacion historica de ``main.py`` en la consola.
    Precondiciones: ``argumentos`` contiene argumentos sin el nombre del programa o es ``None`` para usar ``sys.argv``.
    Postcondiciones: sin argumentos o con ``--gui`` delega al parser grafico; con ``--consola`` o cualquier sintaxis
    historica delega al parser de consola y devuelve exactamente su codigo de salida.
    Complejidad: O(A) temporal y espacial por copiar A argumentos; no ejecuta algoritmos por si mismo.
    Uso de IA: Si.
    Intervencion de IA: Codex diseño e implemento el despacho compatible durante la integracion final de E9.3.
    Validacion del estudiante: revisado y aprobado por el equipo; cubierta por pruebas automatizadas de despacho e
    importacion.
    """
    recibidos = list(sys.argv[1:] if argumentos is None else argumentos)
    if not recibidos:
        return _ejecutar_gui(())
    if recibidos[0] == "--gui":
        return _ejecutar_gui(recibidos[1:])
    if recibidos[0] == "--consola":
        return _ejecutar_consola(recibidos[1:])
    return _ejecutar_consola(recibidos)
