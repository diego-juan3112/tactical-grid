"""Validacion del contrato JSON de escenarios antes de construir el dominio."""

from collections.abc import Mapping


class ErrorValidacionEscenario(ValueError):
    """Indica que un contenido JSON no cumple el contrato de escenario."""


def validar_contenido_escenario(contenido: object) -> None:
    """Valida integralmente un contenido JSON antes de aplicarlo.

    Proposito: comprobar el contrato externo y rechazar escenarios inconsistentes antes de crear un
    ``Escenario``. Preconditions: ``contenido`` es el valor decodificado desde JSON. Postcondiciones:
    si retorna, se cumplen las invariantes estructurales validadas; si falla, no se crea ni altera estado
    de juego alguno. Complejidad: O(F*C + U) temporal y O(U) espacial, donde F y C son dimensiones y U
    unidades. Uso de IA: Si. Intervencion de IA: Codex propuso la validacion inicial a partir del contrato
    del PDF. Validacion del estudiante: pendiente de revision del equipo; cubierta por pruebas de carga.
    """
    raiz = _exigir_diccionario(contenido, "El escenario debe ser un objeto JSON.")
    for campo in ("version", "mapa", "tipos_terreno", "terreno", "bases", "recurso", "unidades", "turno", "juego"):
        _exigir_campo(raiz, campo)

    mapa = _exigir_diccionario(raiz["mapa"], "El campo 'mapa' debe ser un objeto.")
    filas = _exigir_entero_positivo(mapa, "filas")
    columnas = _exigir_entero_positivo(mapa, "columnas")
    catalogo = _exigir_diccionario(raiz["tipos_terreno"], "El campo 'tipos_terreno' debe ser un objeto.")
    if not catalogo:
        raise ErrorValidacionEscenario("El catalogo de tipos_terreno no puede estar vacio.")
    for nombre, definicion in catalogo.items():
        datos = _exigir_diccionario(definicion, f"El terreno '{nombre}' debe ser un objeto.")
        if not isinstance(datos.get("transitable"), bool):
            raise ErrorValidacionEscenario(f"El terreno '{nombre}' debe declarar 'transitable' booleano.")
        if datos["transitable"]:
            costo = datos.get("costo")
            if isinstance(costo, bool) or not isinstance(costo, (int, float)) or costo <= 0:
                raise ErrorValidacionEscenario(f"El terreno transitable '{nombre}' debe tener costo positivo.")

    matriz = raiz["terreno"]
    if not isinstance(matriz, list) or len(matriz) != filas:
        raise ErrorValidacionEscenario("La matriz 'terreno' no coincide con la cantidad de filas.")
    for fila in matriz:
        if not isinstance(fila, list) or len(fila) != columnas:
            raise ErrorValidacionEscenario("Cada fila de 'terreno' debe coincidir con las columnas declaradas.")
        for nombre in fila:
            if not isinstance(nombre, str) or nombre not in catalogo:
                raise ErrorValidacionEscenario("La matriz 'terreno' usa un tipo de terreno no declarado.")

    bases = _exigir_diccionario(raiz["bases"], "El campo 'bases' debe ser un objeto.")
    for bando in ("A", "B"):
        _validar_posicion(bases.get(bando), filas, columnas, f"La base {bando}")
    _validar_posicion(raiz["recurso"], filas, columnas, "El recurso")

    unidades = raiz["unidades"]
    if not isinstance(unidades, list):
        raise ErrorValidacionEscenario("El campo 'unidades' debe ser una lista.")
    identificadores: set[str] = set()
    for unidad in unidades:
        datos_unidad = _exigir_diccionario(unidad, "Cada unidad debe ser un objeto.")
        identificador = datos_unidad.get("id")
        if not isinstance(identificador, str) or not identificador or identificador in identificadores:
            raise ErrorValidacionEscenario("Los identificadores de unidad deben ser unicos y no vacios.")
        identificadores.add(identificador)
        if datos_unidad.get("bando") not in {"A", "B"}:
            raise ErrorValidacionEscenario("Cada unidad debe pertenecer al bando 'A' o 'B'.")
        if not isinstance(datos_unidad.get("tipo"), str) or not datos_unidad["tipo"]:
            raise ErrorValidacionEscenario("Cada unidad debe tener un tipo no vacio.")
        _validar_posicion(datos_unidad, filas, columnas, f"La unidad '{identificador}'")
        nombre_terreno = matriz[datos_unidad["fila"]][datos_unidad["columna"]]
        if not catalogo[nombre_terreno]["transitable"]:
            raise ErrorValidacionEscenario(f"La unidad '{identificador}' esta sobre terreno no transitable.")

    if raiz["turno"] not in {"A", "B"}:
        raise ErrorValidacionEscenario("El turno debe ser 'A' o 'B'.")
    juego = _exigir_diccionario(raiz["juego"], "El campo 'juego' debe ser un objeto.")
    if "portador_recurso" not in juego:
        raise ErrorValidacionEscenario("El campo 'juego.portador_recurso' es obligatorio.")
    if juego["portador_recurso"] is not None and juego["portador_recurso"] not in identificadores:
        raise ErrorValidacionEscenario("El portador_recurso debe identificar una unidad existente o ser null.")


def _exigir_diccionario(valor: object, mensaje: str) -> Mapping[str, object]:
    if not isinstance(valor, Mapping):
        raise ErrorValidacionEscenario(mensaje)
    return valor


def _exigir_campo(datos: Mapping[str, object], campo: str) -> None:
    if campo not in datos:
        raise ErrorValidacionEscenario(f"Falta el campo obligatorio '{campo}'.")


def _exigir_entero_positivo(datos: Mapping[str, object], campo: str) -> int:
    valor = datos.get(campo)
    if isinstance(valor, bool) or not isinstance(valor, int) or valor <= 0:
        raise ErrorValidacionEscenario(f"El campo 'mapa.{campo}' debe ser un entero positivo.")
    return valor


def _validar_posicion(valor: object, filas: int, columnas: int, nombre: str) -> None:
    datos = _exigir_diccionario(valor, f"{nombre} debe ser un objeto con fila y columna.")
    fila, columna = datos.get("fila"), datos.get("columna")
    if isinstance(fila, bool) or not isinstance(fila, int) or isinstance(columna, bool) or not isinstance(columna, int):
        raise ErrorValidacionEscenario(f"{nombre} debe tener fila y columna enteras.")
    if not (0 <= fila < filas and 0 <= columna < columnas):
        raise ErrorValidacionEscenario(f"{nombre} esta fuera de los limites del mapa.")
