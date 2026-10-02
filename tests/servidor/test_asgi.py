"""Pruebas del punto ASGI sin iniciar Uvicorn ni Pygame."""

import asyncio

from tacticalgrid.servidor.asgi import aplicacion


def test_aplicacion_asgi_responde_confirmacion() -> None:
    mensajes_enviados: list[dict] = []

    async def recibir() -> dict:
        return {"type": "http.request", "body": b"", "more_body": False}

    async def enviar(mensaje: dict) -> None:
        mensajes_enviados.append(mensaje)

    asyncio.run(
        aplicacion(
            {"type": "http", "method": "GET", "path": "/", "headers": []},
            recibir,
            enviar,
        )
    )

    assert mensajes_enviados[0]["status"] == 200
    assert mensajes_enviados[1]["body"] == b"TacticalGrid ASGI activo"
