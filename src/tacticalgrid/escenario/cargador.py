"""Carga atómica de archivos JSON hacia la representación de escenario."""

import json
from pathlib import Path
from typing import Mapping

from .escenario import Escenario, Posicion, UnidadInicial
from .terreno import TipoTerreno
from .validador import ErrorValidacionEscenario, validar_contenido_escenario


def cargar_escenario(ruta: str | Path) -> Escenario:
    """Leer, validar y convertir un archivo JSON en un ``Escenario`` inmutable.

    Proposito: separar la carga externa, la validación y la representación interna de los escenarios.
    Precondiciones: ``ruta`` identifica un archivo JSON legible, codificado en UTF-8 con o sin BOM.
    Postcondiciones: se devuelve un escenario completamente validado, incluidos ``version`` y ``prueba``, o se lanza
    ``ErrorValidacionEscenario`` con un mensaje claro, sin modificar ningún estado existente. Los valores no estándar
    ``NaN`` e ``Infinity`` se rechazan.
    Complejidad: O(F*C + U) temporal y espacial por la decodificación y la conversión.
    Uso de IA: Si.
    Intervencion de IA: Codex: implementación inicial conforme al contrato del enunciado. Claude (Sonnet 5): lectura
    del campo ``version``. Claude (Opus 5.5): lectura UTF-8 con BOM, error claro para archivos no UTF-8 y rechazo de
    ``NaN`` e ``Infinity``.
    Validacion del estudiante: pruebas de tests/escenario/test_cargador.py: ejemplo del enunciado, dimensiones
    distintas de 20x20, campos propios adicionales, codificación y constantes no estándar.
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
    # json acepta NaN e Infinity aunque no son JSON estándar, y NaN supera la comparación "costo <= 0".
    raise ErrorValidacionEscenario(f"El valor '{constante}' no es un numero JSON valido.")


def _crear_escenario(contenido: Mapping[str, object]) -> Escenario:
    """Convertir un contenido JSON ya validado en la representación interna ``Escenario``.

    Proposito: separar la validación del contrato externo (``validar_contenido_escenario``) de la construcción del
    modelo, para que el resto del sistema nunca trabaje con el JSON crudo.
    Precondiciones: ``contenido`` superó ``validar_contenido_escenario``; los ``assert`` solo documentan tipos que la
    validación ya garantiza.
    Postcondiciones: se devuelve un ``Escenario`` inmutable con versión, dimensiones, catálogo de terrenos y costos,
    matriz de terreno, bases, recurso, unidades iniciales, turno, portador inicial, la configuración de ``juego``
    completa (con sus campos propios) y ``prueba`` o ``None``. ``contenido`` no cambia.
    Complejidad: O(F*C + T + U) temporal y espacial, con F y C las dimensiones, T los tipos de terreno y U las
    unidades.
    Uso de IA: Si.
    Intervencion de IA: Codex: implementación inicial (E0.3). Claude (Sonnet 5): lectura de ``version`` (E2.1).
    Claude (Opus 5.5): documentación (E11.1).
    Validacion del estudiante: pruebas de tests/escenario/test_cargador.py: carga del ejemplo del enunciado y
    comprobación de cada campo, incluidos ``prueba`` y los campos propios.
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
