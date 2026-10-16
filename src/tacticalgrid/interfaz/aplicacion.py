"""Punto de entrada de la visualizacion Pygame de TacticalGrid."""

from pathlib import Path

from tacticalgrid.escenario.cargador import cargar_escenario
from tacticalgrid.juego.estado import crear_estado_inicial

from .renderizador import RenderizadorTablero


def ejecutar_aplicacion(ruta_escenario: str | Path | None = None) -> None:
    """Carga un escenario y mantiene visible su estado inicial hasta cerrar la ventana.

    Purpose: integrar carga validada, estado de dominio y renderizado sin incorporar mecanicas de interaccion.
    Preconditions: Pygame esta instalado, existe un entorno grafico y la ruta identifica un escenario valido.
    Postconditions: cada fotograma refleja el estado entregado al renderizador y Pygame se libera al cerrar.
    Complexity: O(E*(F*C + U + T)) temporal durante el ciclo y O(F*C + T) espacial de renderizado.
    AI usage: Yes.
    AI intervention: Codex integro E9.1 sobre el punto de entrada existente y agrego seleccion de escenario.
    Student validation: pendiente de validacion visual manual; cubierta por pruebas automatizadas del renderizador.
    """
    import pygame

    if ruta_escenario is None:
        ruta_escenario = _leer_ruta_escenario()
    escenario = cargar_escenario(ruta_escenario)
    estado = crear_estado_inicial(escenario)

    pygame.init()
    try:
        pygame.display.set_caption("TacticalGrid")
        ancho = max(800, min(1400, escenario.columnas * 32 + RenderizadorTablero.ANCHO_PANEL + 48))
        alto = max(600, min(1000, escenario.filas * 32 + 32))
        ventana = pygame.display.set_mode((ancho, alto), pygame.RESIZABLE)
        renderizador = RenderizadorTablero()
        en_ejecucion = True
        while en_ejecucion:
            for evento in pygame.event.get():
                if evento.type == pygame.QUIT:
                    en_ejecucion = False
            renderizador.renderizar(ventana, escenario, estado)
            pygame.display.flip()
    finally:
        pygame.quit()


def _leer_ruta_escenario() -> Path:
    """Obtiene la ruta posicional o usa el escenario principal del repositorio.

    Purpose: ofrecer seleccion explicita de JSON sin acoplar el cargador a argumentos de consola.
    Preconditions: los argumentos del proceso siguen la sintaxis documentada por el comando ``tacticalgrid``.
    Postconditions: devuelve una ruta; la existencia y validez quedan a cargo del cargador existente.
    Complexity: O(A) temporal y espacial, donde A es la cantidad de argumentos recibidos.
    AI usage: Yes.
    AI intervention: Codex agrego la entrada posicional minima requerida por E9.1.
    Student validation: pendiente de revision del equipo; validada mediante la ayuda del comando.
    """
    import argparse

    analizador = argparse.ArgumentParser(description="Visualiza un escenario JSON de TacticalGrid.")
    analizador.add_argument(
        "escenario",
        nargs="?",
        type=Path,
        default=Path("escenarios/campo_20x20.json"),
        help="ruta al escenario JSON (predeterminado: escenarios/campo_20x20.json)",
    )
    return analizador.parse_args().escenario


if __name__ == "__main__":
    ejecutar_aplicacion()
