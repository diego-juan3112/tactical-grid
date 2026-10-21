"""Despacho entre la interfaz gráfica predeterminada y la consola."""

import sys
from collections.abc import Sequence


def _ejecutar_gui(argumentos: Sequence[str]) -> int:
    """Importar Pygame solo cuando se elige el modo gráfico y delegar en su parser."""
    from tacticalgrid.interfaz.aplicacion import ejecutar_desde_argumentos

    return ejecutar_desde_argumentos(argumentos)


def _ejecutar_consola(argumentos: Sequence[str]) -> int:
    """Importar el ejecutor de consola sin cargar la interfaz gráfica."""
    from tacticalgrid.consola import ejecutar_consola

    return ejecutar_consola(argumentos)


def ejecutar(argumentos: Sequence[str] | None = None) -> int:
    """Elegir el modo de la aplicación sin mezclar los parsers de interfaz y consola.

    Proposito: abrir Pygame por defecto y conservar en la consola cada invocación histórica de ``main.py``.
    Precondiciones: ``argumentos`` contiene los argumentos sin el nombre del programa, o es ``None`` para usar
    ``sys.argv``.
    Postcondiciones: sin argumentos o con ``--gui`` se delega en el parser gráfico; con ``--consola`` o cualquier otra
    sintaxis histórica se delega en el parser de consola y se devuelve exactamente su código de salida.
    Complejidad: O(A) temporal y espacial por copiar A argumentos; no ejecuta algoritmos.
    Uso de IA: Si.
    Intervencion de IA: Codex: diseño e implementación del despacho compatible en la integración final de E9.3.
    Validacion del estudiante: pruebas de tests/test_despachador.py: despacho a interfaz y consola, códigos de salida e
    importación diferida de Pygame.
    """
    recibidos = list(sys.argv[1:] if argumentos is None else argumentos)
    if not recibidos:
        return _ejecutar_gui(())
    if recibidos[0] == "--gui":
        return _ejecutar_gui(recibidos[1:])
    if recibidos[0] == "--consola":
        return _ejecutar_consola(recibidos[1:])
    return _ejecutar_consola(recibidos)
