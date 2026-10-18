"""Carga atomica de archivos JSON hacia la representacion de escenario."""

import json
from pathlib import Path
from typing import Mapping

from .escenario import Escenario, Posicion, UnidadInicial
from .terreno import TipoTerreno
from .validador import ErrorValidacionEscenario, validar_contenido_escenario


def cargar_escenario(ruta: str | Path) -> Escenario:
    """Lee, valida y convierte un archivo JSON en un ``Escenario`` inmutable.

    Proposito: separar carga externa, validacion y representacion interna de escenarios. Precondiciones:
    ``ruta`` identifica un archivo JSON legible, codificado en UTF-8 con o sin BOM. Postcondiciones:
    devuelve un escenario completamente validado (incluidos ``version`` y ``prueba``) o lanza
    ``ErrorValidacionEscenario`` con un mensaje claro, sin modificar ningun estado existente; los valores
    no estandar ``NaN``/``Infinity`` se rechazan. Complejidad: O(F*C + U) temporal y espacial por la
    decodificacion y conversion. Uso de IA: Si. Intervencion de IA: Codex propuso la implementacion
    inicial conforme al contrato del PDF; Claude (Sonnet 5) agrego la captura del campo ``version``;
    Claude (Opus 5.5) agrego la lectura UTF-8 con BOM, el error claro para archivos no UTF-8 y el rechazo
    de ``NaN``/``Infinity``. Validacion del estudiante: revisado y aprobado por el equipo; cubierta por
    pruebas automatizadas de carga del ejemplo del enunciado, dimensiones distintas de 20x20, campos
    adicionales propios, codificacion y constantes no estandar.
    """
    try:
        with Path(ruta).open(encoding="utf-8-sig") as archivo:
            contenido = json.load(archivo, parse_constant=_rechazar_constante_no_estandar)
    except OSError as error:
        raise ErrorValidacionEscenario(f"No se pudo leer el escenario: {error}") from error
    except UnicodeDecodeError as error:
        raise ErrorValidacionEscenario(
            f"El archivo debe estar codificado en UTF-8 (byte invalido en la posicion {error.start})."
        ) from error
    except json.JSONDecodeError as error:
        raise ErrorValidacionEscenario(f"El archivo no contiene JSON valido: {error.msg}") from error

    validar_contenido_escenario(contenido)
    return _crear_escenario(contenido)


def _rechazar_constante_no_estandar(constante: str) -> float:
    # json acepta NaN e Infinity aunque no son JSON estandar, y NaN supera la comparacion "costo <= 0".
    raise ErrorValidacionEscenario(f"El valor '{constante}' no es un numero JSON valido.")


def _crear_escenario(contenido: Mapping[str, object]) -> Escenario:
    """Convierte un contenido JSON ya validado en la representacion interna ``Escenario``.

    Proposito: separar la validacion del contrato externo (``validar_contenido_escenario``) de la construccion del
    modelo, de modo que el resto del sistema nunca trabaje con el JSON crudo.
    Precondiciones: ``contenido`` paso ``validar_contenido_escenario``; por eso los ``assert`` solo documentan tipos
    que la validacion ya garantiza.
    Postcondiciones: devuelve un ``Escenario`` inmutable con version, dimensiones, catalogo de terrenos con sus
    costos, matriz de terreno, bases, recurso, unidades iniciales, turno, portador inicial, la configuracion de
    ``juego`` completa (incluidos sus campos propios) y ``prueba`` (o ``None``). No modifica ``contenido``.
    Complejidad: O(F*C + T + U) temporal y espacial, donde F y C son las dimensiones, T los tipos de terreno y U las
    unidades.
    Uso de IA: Si.
    Intervencion de IA: Codex propuso la implementacion inicial en E0.3; Claude (Sonnet 5) agrego la captura de
    ``version`` en E2.1; Claude (Opus 5.5) redacto esta documentacion en E11.1.
    Validacion del estudiante: revisado y aprobado por el equipo; cubierta por tests/escenario/test_cargador.py, que
    carga el ejemplo del enunciado y comprueba cada campo, incluidos ``prueba`` y los campos propios.
    """
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
        version=contenido["version"],
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
