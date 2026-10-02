"""Carga atomica de archivos JSON hacia la representacion de escenario."""

import json
from pathlib import Path
from typing import Mapping

from .escenario import Escenario, Posicion, UnidadInicial
from .terreno import TipoTerreno
from .validador import ErrorValidacionEscenario, validar_contenido_escenario


def cargar_escenario(ruta: str | Path) -> Escenario:
    """Lee, valida y convierte un archivo JSON en un ``Escenario`` inmutable.

    Proposito: separar carga externa, validacion y representacion interna de escenarios. Preconditions:
    ``ruta`` identifica un archivo JSON legible. Postcondiciones: devuelve un escenario completamente
    validado o lanza una excepcion sin modificar ningun estado existente. Complejidad: O(F*C + U) temporal
    y espacial por la decodificacion y conversion. Uso de IA: Si. Intervencion de IA: Codex propuso la
    implementacion inicial conforme al contrato del PDF. Validacion del estudiante: pendiente de revision
    del equipo; cubierta por pruebas automatizadas de carga y consultas.
    """
    try:
        with Path(ruta).open(encoding="utf-8") as archivo:
            contenido = json.load(archivo)
    except OSError as error:
        raise ErrorValidacionEscenario(f"No se pudo leer el escenario: {error}") from error
    except json.JSONDecodeError as error:
        raise ErrorValidacionEscenario(f"El archivo no contiene JSON valido: {error.msg}") from error

    validar_contenido_escenario(contenido)
    return _crear_escenario(contenido)


def _crear_escenario(contenido: Mapping[str, object]) -> Escenario:
    mapa = contenido["mapa"]
    tipos_json = contenido["tipos_terreno"]
    bases_json = contenido["bases"]
    juego = contenido["juego"]
    assert isinstance(mapa, Mapping)
    assert isinstance(tipos_json, Mapping)
    assert isinstance(bases_json, Mapping)
    assert isinstance(juego, Mapping)
    tipos = {
        nombre: TipoTerreno(costo=datos.get("costo"), transitable=datos["transitable"])
        for nombre, datos in tipos_json.items()
        if isinstance(nombre, str) and isinstance(datos, Mapping)
    }
    unidades = tuple(
        UnidadInicial(
            identificador=datos["id"],
            bando=datos["bando"],
            tipo=datos["tipo"],
            posicion=Posicion(datos["fila"], datos["columna"]),
        )
        for datos in contenido["unidades"]
        if isinstance(datos, Mapping)
    )
    recurso = contenido["recurso"]
    prueba = contenido.get("prueba")
    assert isinstance(recurso, Mapping)
    return Escenario(
        filas=mapa["filas"],
        columnas=mapa["columnas"],
        tipos_terreno=tipos,
        terreno=tuple(tuple(fila) for fila in contenido["terreno"]),
        bases={bando: Posicion(datos["fila"], datos["columna"]) for bando, datos in bases_json.items() if isinstance(datos, Mapping)},
        recurso=Posicion(recurso["fila"], recurso["columna"]),
        unidades_iniciales=unidades,
        turno_inicial=contenido["turno"],
        portador_recurso_inicial=juego["portador_recurso"],
        configuracion_juego=juego,
        configuracion_prueba=prueba if isinstance(prueba, Mapping) else None,
    )
