"""Validacion del contrato JSON de escenarios antes de construir el dominio."""

from collections.abc import Mapping

BANDOS_VALIDOS = ("A", "B")


class ErrorValidacionEscenario(ValueError):
    """Indica que un contenido JSON no cumple el contrato de escenario."""


def validar_contenido_escenario(contenido: object) -> None:
    """Valida integralmente un contenido JSON antes de aplicarlo.

    Proposito: comprobar el contrato externo y rechazar escenarios inconsistentes antes de crear un
    ``Escenario``, de modo que la carga sea todo o nada. Reglas: campos obligatorios presentes; ``version``
    cadena no vacia; filas y columnas enteras positivas y consistentes con la matriz ``terreno``; todo terreno
    usado existe en ``tipos_terreno``; todo terreno transitable tiene costo positivo; bases, recurso y unidades
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
    ``portador_recurso``.
    Validacion del estudiante: cubierto por las pruebas de tests/escenario/test_validador.py, con un caso de
    rechazo por cada regla del criterio de aceptacion, la comprobacion de que el contenido no se modifica y la
    de que una carga fallida no altera un escenario cargado previamente.
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
    catalogo = _exigir_diccionario(valor, "El campo 'tipos_terreno' debe ser un objeto.")
    if not catalogo:
        raise ErrorValidacionEscenario("El catalogo 'tipos_terreno' no puede estar vacio.")
    for nombre, definicion in catalogo.items():
        datos = _exigir_diccionario(definicion, f"El terreno '{nombre}' de 'tipos_terreno' debe ser un objeto.")
        if not isinstance(datos.get("transitable"), bool):
            raise ErrorValidacionEscenario(f"El terreno '{nombre}' debe declarar 'transitable' como true o false.")
        if datos["transitable"]:
            costo = datos.get("costo")
            if isinstance(costo, bool) or not isinstance(costo, (int, float)) or costo <= 0:
                raise ErrorValidacionEscenario(
                    f"El terreno transitable '{nombre}' debe tener un costo numerico positivo y tiene {costo!r}."
                )
    return catalogo


def _validar_matriz(
    valor: object, filas: int, columnas: int, catalogo: Mapping[str, object]
) -> list[list[str]]:
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
    datos = _exigir_diccionario(valor, f"{nombre} debe ser un objeto con 'fila' y 'columna'.")
    fila, columna = datos.get("fila"), datos.get("columna")
    if isinstance(fila, bool) or not isinstance(fila, int) or isinstance(columna, bool) or not isinstance(columna, int):
        raise ErrorValidacionEscenario(f"{nombre} debe tener 'fila' y 'columna' enteras.")
    if not (0 <= fila < filas and 0 <= columna < columnas):
        raise ErrorValidacionEscenario(
            f"{nombre} esta en ({fila}, {columna}), fuera del mapa de {filas}x{columnas} "
            f"(filas 0-{filas - 1}, columnas 0-{columnas - 1})."
        )
