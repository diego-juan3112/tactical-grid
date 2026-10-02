"""Aplicacion ASGI minima para ejecutar TacticalGrid mediante Uvicorn."""


async def aplicacion(alcance: dict, recibir, enviar) -> None:
    """Responde una confirmacion tecnica sin acceder al dominio ni a Pygame.

    Purpose: exponer un punto de entrada ASGI real y aislado para Uvicorn.
    Preconditions: Uvicorn invoca la funcion con los objetos del protocolo ASGI.
    Postconditions: completa eventos de ciclo de vida o responde HTTP 200 en texto plano.
    Complexity: O(1) temporal y espacial por solicitud.
    AI usage: Yes.
    AI intervention: Codex genero el esqueleto ASGI minimo, sin framework web adicional.
    Student validation: pendiente de revision del equipo; cubierto por una prueba ASGI automatizada.
    """
    if alcance["type"] == "lifespan":
        await _gestionar_ciclo_vida(recibir, enviar)
        return

    if alcance["type"] != "http":
        return

    cuerpo = b"TacticalGrid ASGI activo"
    await enviar(
        {
            "type": "http.response.start",
            "status": 200,
            "headers": [
                (b"content-type", b"text/plain; charset=utf-8"),
                (b"content-length", str(len(cuerpo)).encode()),
            ],
        }
    )
    await enviar({"type": "http.response.body", "body": cuerpo})


async def _gestionar_ciclo_vida(recibir, enviar) -> None:
    """Completa los eventos de inicio y cierre que Uvicorn envia a ASGI."""
    while True:
        evento = await recibir()
        if evento["type"] == "lifespan.startup":
            await enviar({"type": "lifespan.startup.complete"})
        if evento["type"] == "lifespan.shutdown":
            await enviar({"type": "lifespan.shutdown.complete"})
            return
