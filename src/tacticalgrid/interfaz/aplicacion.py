"""Punto de inicio minimo y aislado de la interfaz Pygame."""


def ejecutar_aplicacion() -> None:
    """Inicia una ventana vacia de Pygame para comprobar la dependencia de interfaz.

    Proposito: ofrecer un punto de entrada exclusivo de la capa de interfaz, preparado para recibir estado
    y resultados en historias posteriores. Preconditions: Pygame esta instalado y existe un entorno grafico.
    Postcondiciones: al cerrar la ventana se libera Pygame; no carga escenarios ni modifica el dominio.
    Complejidad: O(E) temporal, donde E son eventos procesados, y O(1) espacial adicional.
    Uso de IA: Si. Intervencion de IA: Codex propuso el esqueleto de inicializacion aislada. Validacion del
    estudiante: pendiente de prueba manual en un entorno grafico; no se ejecuta desde pytest.
    """
    import pygame

    pygame.init()
    try:
        pygame.display.set_caption("TacticalGrid")
        ventana = pygame.display.set_mode((800, 600))
        en_ejecucion = True
        while en_ejecucion:
            for evento in pygame.event.get():
                if evento.type == pygame.QUIT:
                    en_ejecucion = False
            ventana.fill((24, 31, 38))
            pygame.display.flip()
    finally:
        pygame.quit()


if __name__ == "__main__":
    ejecutar_aplicacion()
