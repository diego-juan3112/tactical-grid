"""Aplicación ASGI mínima para ejecutar TacticalGrid con Uvicorn."""


async def aplicacion(alcance: dict, recibir, enviar) -> None:
    """Responder una confirmación técnica sin acceder al dominio ni a Pygame.

    Proposito: exponer un punto de entrada ASGI real y aislado para Uvicorn.
    Precondiciones: Uvicorn invoca la función con los objetos del protocolo ASGI.
    Postcondiciones: se completan los eventos de ciclo de vida o se responde HTTP 200 en texto plano.
    Complejidad: O(1) temporal y espacial por solicitud.
    Uso de IA: Si.
    Intervencion de IA: Codex: esqueleto ASGI mínimo, sin framework web adicional. Claude (Sonnet 5): traducción al
    español de los encabezados de esta documentación.
    Validacion del estudiante: prueba ASGI de tests/servidor/test_asgi.py.
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
    """Completar los eventos de inicio y cierre que Uvicorn envía a la aplicación ASGI."""
    while True:
        evento = await recibir()
        if evento["type"] == "lifespan.startup":
            await enviar({"type": "lifespan.startup.complete"})
        if evento["type"] == "lifespan.shutdown":
            await enviar({"type": "lifespan.shutdown.complete"})
            return
