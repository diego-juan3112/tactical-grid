"""Validación del contrato JSON de escenarios antes de construir el dominio."""

import math
from collections.abc import Mapping

BANDOS_VALIDOS = ("A", "B")


class ErrorValidacionEscenario(ValueError):
    """Error de un contenido JSON que no cumple el contrato de escenario."""


def validar_contenido_escenario(contenido: object) -> None:
    """Validar íntegramente un contenido JSON antes de aplicarlo.

    Proposito: comprobar el contrato externo y rechazar escenarios inconsistentes antes de crear un ``Escenario``, para
    que la carga sea todo o nada. Reglas: campos obligatorios presentes; ``version`` como cadena no vacía; filas y
    columnas enteras, positivas y consistentes con la matriz ``terreno``; todo terreno usado declarado en
    ``tipos_terreno``; todo terreno transitable con costo numérico, positivo y finito; bases, recurso y unidades dentro
    del mapa; ninguna unidad sobre una celda no transitable; identificadores de unidad únicos; cada unidad del bando
    ``A`` o ``B``; ``turno`` igual a ``A`` o ``B``; ``juego.portador_recurso`` nulo o igual a una unidad existente;
    ``prueba``, si existe, como objeto o nulo.
    Precondiciones: ``contenido`` es el valor decodificado desde JSON, de cualquier tipo.
    Postcondiciones: si no se lanza ninguna excepción, se cumplen todas las reglas anteriores. Ante la primera regla
    incumplida se lanza ``ErrorValidacionEscenario`` con el campo, el elemento y el valor que la incumplen, sin crear
    ni modificar estado; ``contenido`` no cambia. Los valores con tipos inesperados nunca producen otra excepción.
    Complejidad: O(F*C + T + U) temporal y O(U) espacial, con F y C las dimensiones, T los tipos de terreno y U las
    unidades.
    Uso de IA: Si.
    Intervencion de IA: Codex: validación inicial a partir del contrato del enunciado; rechazo de costos no finitos y
    de enteros que desbordan la conversión numérica (E6.1). Claude (Sonnet 5): validación de tipo de ``version``.
    Claude (Opus 5.5): rechazo de un ``prueba`` que no sea objeto; mensajes con el elemento y el valor que fallan, y
    corrección de los ``TypeError`` por valores no hashables en ``bando``, ``turno`` y ``portador_recurso`` (E2.2).
    Validacion del estudiante: pruebas de tests/escenario/test_validador.py para cada regla del contrato y para la
    atomicidad de la carga.
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
    """Validar el catálogo ``tipos_terreno``, origen de todos los costos y de la transitabilidad.

    Proposito: garantizar que los costos que usan UCS, A*, la utilidad y las reglas vienen del JSON y son utilizables
    (numéricos, positivos y finitos), para que ningún algoritmo necesite volver a comprobarlos.
    Precondiciones: ``valor`` es el contenido de ``tipos_terreno`` decodificado desde JSON, de cualquier tipo.
    Postcondiciones: se devuelve el catálogo si es un objeto no vacío en el que cada terreno es un objeto con
    ``transitable`` booleano y, si es transitable, un ``costo`` numérico no booleano, finito y mayor que 0. En otro
    caso se lanza ``ErrorValidacionEscenario`` con el terreno y el valor recibido. ``valor`` no cambia.
    Complejidad: O(T) temporal y O(1) espacial adicional, con T tipos de terreno.
    Uso de IA: Si.
    Intervencion de IA: Codex: validación inicial; rechazo de costos no finitos y de enteros que desbordan
    ``math.isfinite`` (E6.1). Claude (Opus 5.5): separación en esta función y mensajes (E2.2); documentación (E11.1).
    Validacion del estudiante: pruebas de tests/escenario/test_validador.py: catálogo vacío, ``transitable`` no
    booleano y costos nulos, negativos, no numéricos y no finitos.
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
    """Validar que la matriz ``terreno`` coincida con las dimensiones y use terrenos del catálogo.

    Proposito: asegurar que cada celda tenga un terreno conocido, para que las consultas de costo y transitabilidad
    del ``Escenario`` nunca fallen durante una búsqueda.
    Precondiciones: ``filas`` y ``columnas`` son enteros positivos ya validados y ``catalogo`` es el resultado de
    ``_validar_catalogo``; ``valor`` puede ser de cualquier tipo.
    Postcondiciones: se devuelve la matriz si es una lista de ``filas`` listas de ``columnas`` nombres de terreno
    presentes en ``catalogo``. En otro caso se lanza ``ErrorValidacionEscenario`` con la fila o la celda y el valor que
    falla. ``valor`` no cambia.
    Complejidad: O(F*C) temporal y O(1) espacial adicional, con F y C las dimensiones del mapa.
    Uso de IA: Si.
    Intervencion de IA: Codex: validación inicial. Claude (Opus 5.5): separación en esta función y mensajes con la
    celda (E2.2); documentación (E11.1).
    Validacion del estudiante: pruebas de tests/escenario/test_validador.py: filas y columnas inconsistentes y
    terrenos no declarados.
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
    """Validar la lista de unidades y devolver el conjunto de sus identificadores.

    Proposito: aplicar las reglas del enunciado sobre unidades (identificadores únicos, bando ``A`` o ``B``, posición
    dentro del mapa y sobre una celda transitable) antes de construir el estado del juego.
    Precondiciones: ``filas``, ``columnas``, ``matriz`` y ``catalogo`` ya están validados; ``valor`` puede ser de
    cualquier tipo.
    Postcondiciones: se devuelven los identificadores si ``valor`` es una lista de objetos con ``id`` de texto no vacío
    y único, ``bando`` ``A`` o ``B``, ``tipo`` de texto no vacío y ``fila``/``columna`` enteras dentro del mapa sobre
    un terreno transitable. En otro caso se lanza ``ErrorValidacionEscenario`` con la unidad y el valor que falla.
    ``valor`` no cambia.
    Complejidad: O(U) temporal y espacial, con U unidades; cada comprobación es O(1).
    Uso de IA: Si.
    Intervencion de IA: Codex: validación inicial. Claude (Opus 5.5): separación en esta función, mensajes y
    corrección del ``TypeError`` de un ``bando`` no hashable (E2.2); documentación (E11.1).
    Validacion del estudiante: pruebas de tests/escenario/test_validador.py: identificadores repetidos o vacíos,
    bandos inválidos y unidades fuera del mapa o sobre muros.
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
    """Validar que ``valor`` sea una posición ``{fila, columna}`` entera dentro del mapa.

    Proposito: comprobar con la misma regla y los mismos mensajes las posiciones de bases, recurso y unidades.
    Precondiciones: ``filas`` y ``columnas`` son enteros positivos; ``nombre`` identifica el elemento en el mensaje.
    Postcondiciones: si ``fila`` y ``columna`` son enteros no booleanos dentro de ``0..filas-1`` y ``0..columnas-1``, no
    hay efectos; en otro caso se lanza ``ErrorValidacionEscenario`` con la posición recibida y los límites del mapa.
    ``valor`` no cambia.
    Complejidad: O(1) temporal y espacial.
    Uso de IA: Si.
    Intervencion de IA: Codex: validación inicial. Claude (Opus 5.5): mensajes con los límites del mapa (E2.2);
    documentación (E11.1).
    Validacion del estudiante: pruebas de tests/escenario/test_validador.py: bases, recurso y unidades fuera del mapa y
    coordenadas no enteras.
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
