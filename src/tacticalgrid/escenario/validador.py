"""Validacion del contrato JSON de escenarios antes de construir el dominio."""

import math
from collections.abc import Mapping

BANDOS_VALIDOS = ("A", "B")


class ErrorValidacionEscenario(ValueError):
    """Indica que un contenido JSON no cumple el contrato de escenario."""


def validar_contenido_escenario(contenido: object) -> None:
    """Valida integralmente un contenido JSON antes de aplicarlo.

    Proposito: comprobar el contrato externo y rechazar escenarios inconsistentes antes de crear un
    ``Escenario``, de modo que la carga sea todo o nada. Reglas: campos obligatorios presentes; ``version``
    cadena no vacia; filas y columnas enteras positivas y consistentes con la matriz ``terreno``; todo terreno
    usado existe en ``tipos_terreno``; todo terreno transitable tiene costo numerico, positivo y finito; bases,
    recurso y unidades
    dentro del mapa; ninguna unidad sobre celda no transitable; identificadores de unidad unicos; cada unidad
    pertenece a ``A`` o ``B``; ``turno`` es ``A`` o ``B``; ``juego.portador_recurso`` es null o identifica una
    unidad existente; ``prueba``, si esta presente, es un objeto o null.
    Precondiciones: ``contenido`` es el valor decodificado desde JSON (de cualquier tipo).
    Postcondiciones: si retorna, se cumplen todas las reglas anteriores; si alguna falla, lanza
    ``ErrorValidacionEscenario`` con un mensaje que nombra el campo, el elemento y el valor que la incumple,
    sin crear ni modificar estado alguno (``contenido`` tampoco se modifica). Nunca lanza otro tipo de
    excepcion por valores con tipos inesperados.
    Complejidad: O(F*C + T + U) temporal y O(U) espacial, donde F y C son dimensiones, T tipos de terreno y
    U unidades.
    Uso de IA: Si.
    Intervencion de IA: Codex propuso la validacion inicial a partir del contrato del PDF; Claude (Sonnet 5)
    agrego la validacion de tipo del campo ``version``; Claude (Opus 5.5) agrego el rechazo de un ``prueba``
    que no sea objeto y, en E2.2, reescribio los mensajes para que indiquen el elemento y el valor que fallan,
    y corrigio los ``TypeError`` que producian valores no hashables en ``bando``, ``turno`` y
    ``portador_recurso``; Codex agrego en E6.1 el rechazo de costos no finitos y de enteros que desbordan la
    conversion numerica requerida para comprobarlos.
    Validacion del estudiante: el equipo reviso el cambio de E6.1; existen pruebas automatizadas en
    tests/escenario/test_validador.py para las reglas del contrato y la atomicidad de la carga.
    """
    raiz = _exigir_diccionario(contenido, "El escenario debe ser un objeto JSON.")
    for campo in ("version", "mapa", "tipos_terreno", "terreno", "bases", "recurso", "unidades", "turno", "juego"):
        if campo not in raiz:
            raise ErrorValidacionEscenario(f"Falta el campo obligatorio '{campo}'.")

    if not isinstance(raiz["version"], str) or not raiz["version"]:
        raise ErrorValidacionEscenario("El campo 'version' debe ser una cadena no vacia.")

    mapa = _exigir_diccionario(raiz["mapa"], "El campo 'mapa' debe ser un objeto.")
    filas = _exigir_entero_positivo(mapa, "filas")
    columnas = _exigir_entero_positivo(mapa, "columnas")
    catalogo = _validar_catalogo(raiz["tipos_terreno"])
    matriz = _validar_matriz(raiz["terreno"], filas, columnas, catalogo)

    bases = _exigir_diccionario(raiz["bases"], "El campo 'bases' debe ser un objeto.")
    for bando in BANDOS_VALIDOS:
        _validar_posicion(bases.get(bando), filas, columnas, f"La base '{bando}' (bases.{bando})")
    _validar_posicion(raiz["recurso"], filas, columnas, "El recurso")

    identificadores = _validar_unidades(raiz["unidades"], filas, columnas, matriz, catalogo)

    turno = raiz["turno"]
    if not _es_bando(turno):
        raise ErrorValidacionEscenario(f"El campo 'turno' debe ser 'A' o 'B' y se recibio {turno!r}.")
    juego = _exigir_diccionario(raiz["juego"], "El campo 'juego' debe ser un objeto.")
    if "portador_recurso" not in juego:
        raise ErrorValidacionEscenario("Falta el campo obligatorio 'juego.portador_recurso' (use null si nadie lo porta).")
    portador = juego["portador_recurso"]
    if portador is not None and (not isinstance(portador, str) or portador not in identificadores):
        raise ErrorValidacionEscenario(
            f"El campo 'juego.portador_recurso' debe ser null o el id de una unidad existente y se recibio {portador!r}."
        )
    if raiz.get("prueba") is not None and not isinstance(raiz["prueba"], Mapping):
        raise ErrorValidacionEscenario("El campo opcional 'prueba' debe ser un objeto o null.")


def _validar_catalogo(valor: object) -> Mapping[str, Mapping[str, object]]:
    """Valida el catalogo ``tipos_terreno``, del que salen todos los costos y la transitabilidad del juego.

    Proposito: garantizar que los costos que usaran UCS, A*, la utilidad y las reglas vienen del JSON y son
    utilizables (numericos, positivos y finitos), de modo que ningun algoritmo necesite volver a comprobarlos.
    Precondiciones: ``valor`` es el contenido de ``tipos_terreno`` decodificado desde JSON, de cualquier tipo.
    Postcondiciones: devuelve el catalogo si es un objeto no vacio en el que cada terreno es un objeto con
    ``transitable`` booleano y, si es transitable, un ``costo`` numerico (no booleano), finito y mayor que 0. Si
    no, lanza ``ErrorValidacionEscenario`` nombrando el terreno y el valor recibido. No modifica ``valor``.
    Complejidad: O(T) temporal y O(1) espacial adicional, donde T es la cantidad de tipos de terreno.
    Uso de IA: Si.
    Intervencion de IA: Codex propuso la validacion inicial; Claude (Opus 5.5) la separo en esta funcion y
    reescribio sus mensajes en E2.2; Codex agrego en E6.1 el rechazo de costos no finitos y de enteros que
    desbordan ``math.isfinite``. Claude (Opus 5.5) redacto esta documentacion en E11.1.
    Validacion del estudiante: revisado y aprobado por el equipo; cubierta por tests/escenario/test_validador.py,
    que comprueba catalogo vacio, ``transitable`` no booleano y costos nulos, negativos, no numericos y no finitos.
    """
    catalogo = _exigir_diccionario(valor, "El campo 'tipos_terreno' debe ser un objeto.")
    if not catalogo:
        raise ErrorValidacionEscenario("El catalogo 'tipos_terreno' no puede estar vacio.")
    for nombre, definicion in catalogo.items():
        datos = _exigir_diccionario(definicion, f"El terreno '{nombre}' de 'tipos_terreno' debe ser un objeto.")
        if not isinstance(datos.get("transitable"), bool):
            raise ErrorValidacionEscenario(f"El terreno '{nombre}' debe declarar 'transitable' como true o false.")
        if datos["transitable"]:
            costo = datos.get("costo")
            es_numero = not isinstance(costo, bool) and isinstance(costo, (int, float))
            try:
                es_finito = es_numero and math.isfinite(costo)
            except (OverflowError, TypeError, ValueError):
                es_finito = False
            if not es_numero or not es_finito or costo <= 0:
                raise ErrorValidacionEscenario(
                    f"El terreno transitable '{nombre}' debe tener un costo numerico positivo y finito "
                    f"y tiene {costo!r}."
                )
    return catalogo


def _validar_matriz(
    valor: object, filas: int, columnas: int, catalogo: Mapping[str, object]
) -> list[list[str]]:
    """Valida que la matriz ``terreno`` coincida con las dimensiones declaradas y use terrenos del catalogo.

    Proposito: asegurar que cada celda del mapa tiene un terreno conocido, para que las consultas de costo y
    transitabilidad del ``Escenario`` nunca fallen durante una busqueda.
    Precondiciones: ``filas`` y ``columnas`` son enteros positivos ya validados y ``catalogo`` es el resultado de
    ``_validar_catalogo``; ``valor`` puede ser de cualquier tipo.
    Postcondiciones: devuelve la matriz si es una lista de ``filas`` listas de ``columnas`` nombres de terreno
    presentes en ``catalogo``. Si no, lanza ``ErrorValidacionEscenario`` indicando la fila o la celda y el valor
    que falla. No modifica ``valor``.
    Complejidad: O(F*C) temporal y O(1) espacial adicional, donde F y C son las dimensiones del mapa.
    Uso de IA: Si.
    Intervencion de IA: Codex propuso la validacion inicial; Claude (Opus 5.5) la separo en esta funcion y
    reescribio sus mensajes para indicar la celda en E2.2, y redacto esta documentacion en E11.1.
    Validacion del estudiante: revisado y aprobado por el equipo; cubierta por tests/escenario/test_validador.py,
    que comprueba filas y columnas inconsistentes y terrenos no declarados.
    """
    if not isinstance(valor, list) or len(valor) != filas:
        cantidad = len(valor) if isinstance(valor, list) else "ninguna"
        raise ErrorValidacionEscenario(
            f"La matriz 'terreno' debe tener {filas} filas (mapa.filas) y tiene {cantidad}."
        )
    for indice_fila, fila in enumerate(valor):
        if not isinstance(fila, list) or len(fila) != columnas:
            cantidad = len(fila) if isinstance(fila, list) else "ninguna"
            raise ErrorValidacionEscenario(
                f"La fila {indice_fila} de 'terreno' debe tener {columnas} columnas (mapa.columnas) y tiene {cantidad}."
            )
        for indice_columna, nombre in enumerate(fila):
            if not isinstance(nombre, str) or nombre not in catalogo:
                raise ErrorValidacionEscenario(
                    f"La celda ({indice_fila}, {indice_columna}) de 'terreno' usa {nombre!r}, "
                    "que no esta declarado en 'tipos_terreno'."
                )
    return valor


def _validar_unidades(
    valor: object, filas: int, columnas: int, matriz: list[list[str]], catalogo: Mapping[str, Mapping[str, object]]
) -> set[str]:
    """Valida la lista de unidades y devuelve el conjunto de sus identificadores.

    Proposito: aplicar las reglas del enunciado sobre unidades (identificadores unicos, bando ``A`` o ``B``,
    posicion dentro del mapa y sobre una celda transitable) antes de construir el estado del juego.
    Precondiciones: ``filas``, ``columnas``, ``matriz`` y ``catalogo`` ya fueron validados; ``valor`` puede ser de
    cualquier tipo.
    Postcondiciones: devuelve los identificadores si ``valor`` es una lista de objetos con ``id`` de texto no vacio
    y unico, ``bando`` ``A`` o ``B``, ``tipo`` de texto no vacio y ``fila``/``columna`` enteras dentro del mapa
    sobre un terreno transitable. Si no, lanza ``ErrorValidacionEscenario`` nombrando la unidad y el valor que
    falla. No modifica ``valor``.
    Complejidad: O(U) temporal y espacial, donde U es la cantidad de unidades (cada comprobacion es O(1)).
    Uso de IA: Si.
    Intervencion de IA: Codex propuso la validacion inicial; Claude (Opus 5.5) la separo en esta funcion,
    reescribio sus mensajes y corrigio el ``TypeError`` de un ``bando`` no hashable en E2.2, y redacto esta
    documentacion en E11.1.
    Validacion del estudiante: revisado y aprobado por el equipo; cubierta por tests/escenario/test_validador.py,
    que comprueba ids repetidos o vacios, bandos invalidos, unidades fuera del mapa y sobre muros.
    """
    if not isinstance(valor, list):
        raise ErrorValidacionEscenario("El campo 'unidades' debe ser una lista.")
    identificadores: set[str] = set()
    for indice, unidad in enumerate(valor):
        datos = _exigir_diccionario(unidad, f"La unidad en la posicion {indice} de 'unidades' debe ser un objeto.")
        identificador = datos.get("id")
        if not isinstance(identificador, str) or not identificador:
            raise ErrorValidacionEscenario(
                f"La unidad en la posicion {indice} de 'unidades' debe tener un 'id' de texto no vacio."
            )
        if identificador in identificadores:
            raise ErrorValidacionEscenario(f"El id de unidad '{identificador}' esta repetido; los ids deben ser unicos.")
        identificadores.add(identificador)
        if not _es_bando(datos.get("bando")):
            raise ErrorValidacionEscenario(
                f"La unidad '{identificador}' debe pertenecer al bando 'A' o 'B' y tiene {datos.get('bando')!r}."
            )
        if not isinstance(datos.get("tipo"), str) or not datos["tipo"]:
            raise ErrorValidacionEscenario(f"La unidad '{identificador}' debe tener un 'tipo' de texto no vacio.")
        _validar_posicion(datos, filas, columnas, f"La unidad '{identificador}'")
        fila, columna = datos["fila"], datos["columna"]
        nombre_terreno = matriz[fila][columna]
        if not catalogo[nombre_terreno]["transitable"]:
            raise ErrorValidacionEscenario(
                f"La unidad '{identificador}' esta en ({fila}, {columna}), sobre '{nombre_terreno}', "
                "que no es transitable."
            )
    return identificadores


def _es_bando(valor: object) -> bool:
    return isinstance(valor, str) and valor in BANDOS_VALIDOS


def _exigir_diccionario(valor: object, mensaje: str) -> Mapping[str, object]:
    if not isinstance(valor, Mapping):
        raise ErrorValidacionEscenario(mensaje)
    return valor


def _exigir_entero_positivo(datos: Mapping[str, object], campo: str) -> int:
    valor = datos.get(campo)
    if isinstance(valor, bool) or not isinstance(valor, int) or valor <= 0:
        raise ErrorValidacionEscenario(f"El campo 'mapa.{campo}' debe ser un entero positivo y se recibio {valor!r}.")
    return valor


def _validar_posicion(valor: object, filas: int, columnas: int, nombre: str) -> None:
    """Valida que ``valor`` sea una posicion ``{fila, columna}`` entera dentro del mapa.

    Proposito: comprobar con la misma regla y los mismos mensajes las posiciones de bases, recurso y unidades.
    Precondiciones: ``filas`` y ``columnas`` son enteros positivos; ``nombre`` describe el elemento para el mensaje.
    Postcondiciones: retorna sin efectos si ``fila`` y ``columna`` son enteros (no booleanos) dentro de
    ``0..filas-1`` y ``0..columnas-1``; si no, lanza ``ErrorValidacionEscenario`` con la posicion recibida y los
    limites del mapa. No modifica ``valor``.
    Complejidad: O(1) temporal y espacial.
    Uso de IA: Si.
    Intervencion de IA: Codex propuso la validacion inicial; Claude (Opus 5.5) reescribio sus mensajes con los
    limites del mapa en E2.2 y redacto esta documentacion en E11.1.
    Validacion del estudiante: revisado y aprobado por el equipo; cubierta por tests/escenario/test_validador.py,
    que comprueba bases, recurso y unidades fuera del mapa y coordenadas no enteras.
    """
    datos = _exigir_diccionario(valor, f"{nombre} debe ser un objeto con 'fila' y 'columna'.")
    fila, columna = datos.get("fila"), datos.get("columna")
    if isinstance(fila, bool) or not isinstance(fila, int) or isinstance(columna, bool) or not isinstance(columna, int):
        raise ErrorValidacionEscenario(f"{nombre} debe tener 'fila' y 'columna' enteras.")
    if not (0 <= fila < filas and 0 <= columna < columnas):
        raise ErrorValidacionEscenario(
            f"{nombre} esta en ({fila}, {columna}), fuera del mapa de {filas}x{columnas} "
            f"(filas 0-{filas - 1}, columnas 0-{columnas - 1})."
        )
