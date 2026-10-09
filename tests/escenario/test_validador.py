"""Pruebas del validador: cada regla rechaza la carga completa con un error claro (todo o nada)."""

import copy
import json
from collections.abc import Callable

import pytest

from tacticalgrid.escenario.cargador import cargar_escenario
from tacticalgrid.escenario.validador import ErrorValidacionEscenario, validar_contenido_escenario

Mutacion = Callable[[dict], None]


def _poner(ruta: str, valor: object) -> Mutacion:
    """Devuelve una mutacion que asigna ``valor`` en la ruta separada por puntos (indices numericos en listas)."""

    def mutar(contenido: dict) -> None:
        *padres, ultimo = ruta.split(".")
        destino = contenido
        for clave in padres:
            destino = destino[int(clave)] if isinstance(destino, list) else destino[clave]
        if isinstance(destino, list):
            destino[int(ultimo)] = valor
        else:
            destino[ultimo] = valor

    return mutar


def _borrar(ruta: str) -> Mutacion:
    def mutar(contenido: dict) -> None:
        *padres, ultimo = ruta.split(".")
        destino = contenido
        for clave in padres:
            destino = destino[clave]
        del destino[ultimo]

    return mutar


# Escenario base (conftest): mapa 2x3, terreno [[camino, muro, camino], [camino, camino, camino]],
# unidades A1 en (0, 0) y B1 en (1, 2).
CASOS_INVALIDOS: dict[str, tuple[Mutacion, str]] = {
    # Filas/columnas positivas y consistentes con la matriz de terreno.
    "filas_cero": (_poner("mapa.filas", 0), r"'mapa\.filas' debe ser un entero positivo y se recibio 0"),
    "columnas_negativas": (_poner("mapa.columnas", -3), r"'mapa\.columnas' debe ser un entero positivo"),
    "filas_no_entero": (_poner("mapa.filas", "2"), r"'mapa\.filas' debe ser un entero positivo"),
    "filas_booleanas": (_poner("mapa.filas", True), r"'mapa\.filas' debe ser un entero positivo"),
    "filas_inconsistentes": (_poner("mapa.filas", 3), r"debe tener 3 filas \(mapa\.filas\) y tiene 2"),
    "columnas_inconsistentes": (
        _poner("terreno.1", ["camino", "camino"]),
        r"La fila 1 de 'terreno' debe tener 3 columnas \(mapa\.columnas\) y tiene 2",
    ),
    "terreno_no_es_matriz": (_poner("terreno", "camino"), r"debe tener 2 filas .* y tiene ninguna"),
    # Todos los terrenos usados en terreno existen en tipos_terreno.
    "terreno_no_declarado": (
        _poner("terreno.1.2", "lava"),
        r"La celda \(1, 2\) de 'terreno' usa 'lava', que no esta declarado en 'tipos_terreno'",
    ),
    "catalogo_vacio": (_poner("tipos_terreno", {}), r"'tipos_terreno' no puede estar vacio"),
    # Terrenos transitables tienen costo numerico, positivo y finito.
    "costo_cero": (_poner("tipos_terreno.camino.costo", 0), r"'camino'.*costo numerico positivo y finito.*0"),
    "costo_negativo": (_poner("tipos_terreno.camino.costo", -1), r"'camino' debe tener un costo numerico positivo"),
    "costo_booleano": (_poner("tipos_terreno.camino.costo", True), r"'camino' debe tener un costo numerico positivo"),
    "costo_entero_fuera_de_rango_float": (
        _poner("tipos_terreno.camino.costo", 10**400),
        r"'camino'.*positivo y finito",
    ),
    "costo_ausente": (_borrar("tipos_terreno.camino.costo"), r"'camino'.*costo numerico positivo y finito.*None"),
    "costo_texto": (_poner("tipos_terreno.camino.costo", "2"), r"'camino' debe tener un costo numerico positivo"),
    "transitable_no_booleano": (_poner("tipos_terreno.camino.transitable", "si"), r"'camino' debe declarar 'transitable'"),
    # Bases, recurso y unidades dentro del mapa.
    "base_a_fuera": (_poner("bases.A", {"fila": 2, "columna": 0}), r"La base 'A' .* esta en \(2, 0\), fuera del mapa de 2x3"),
    "base_b_ausente": (_borrar("bases.B"), r"La base 'B' .* debe ser un objeto con 'fila' y 'columna'"),
    "recurso_fuera": (_poner("recurso", {"fila": 0, "columna": 3}), r"El recurso esta en \(0, 3\), fuera del mapa"),
    "recurso_negativo": (_poner("recurso", {"fila": -1, "columna": 0}), r"El recurso esta en \(-1, 0\), fuera del mapa"),
    "unidad_fuera": (_poner("unidades.1.fila", 5), r"La unidad 'B1' esta en \(5, 2\), fuera del mapa"),
    "unidad_sin_columna": (_poner("unidades.0.columna", None), r"La unidad 'A1' debe tener 'fila' y 'columna' enteras"),
    # Ninguna unidad sobre celda no transitable.
    "unidad_sobre_muro": (
        _poner("unidades.0.columna", 1),
        r"La unidad 'A1' esta en \(0, 1\), sobre 'muro', que no es transitable",
    ),
    # IDs de unidad unicos.
    "id_repetido": (_poner("unidades.1.id", "A1"), r"El id de unidad 'A1' esta repetido"),
    "id_vacio": (_poner("unidades.0.id", ""), r"posicion 0 de 'unidades' debe tener un 'id' de texto no vacio"),
    # Cada unidad pertenece a A o B; turno es A o B.
    "bando_invalido": (_poner("unidades.0.bando", "C"), r"La unidad 'A1' debe pertenecer al bando 'A' o 'B' y tiene 'C'"),
    "bando_minuscula": (_poner("unidades.0.bando", "a"), r"bando 'A' o 'B' y tiene 'a'"),
    "bando_lista": (_poner("unidades.0.bando", ["A"]), r"bando 'A' o 'B' y tiene \['A'\]"),
    "turno_invalido": (_poner("turno", "C"), r"'turno' debe ser 'A' o 'B' y se recibio 'C'"),
    "turno_lista": (_poner("turno", ["A"]), r"'turno' debe ser 'A' o 'B'"),
    # Si portador_recurso no es null, identifica una unidad existente.
    "portador_inexistente": (
        _poner("juego.portador_recurso", "Z9"),
        r"'juego\.portador_recurso' debe ser null o el id de una unidad existente y se recibio 'Z9'",
    ),
    "portador_lista": (_poner("juego.portador_recurso", ["A1"]), r"'juego\.portador_recurso' debe ser null o el id"),
    "portador_ausente": (_borrar("juego.portador_recurso"), r"Falta el campo obligatorio 'juego\.portador_recurso'"),
    # Estructura general.
    "falta_unidades": (_borrar("unidades"), r"Falta el campo obligatorio 'unidades'"),
    "unidades_no_lista": (_poner("unidades", {}), r"'unidades' debe ser una lista"),
}


@pytest.mark.parametrize(("mutacion", "mensaje"), CASOS_INVALIDOS.values(), ids=CASOS_INVALIDOS.keys())
def test_cada_regla_rechaza_la_carga_con_un_error_claro(tmp_path, contenido_escenario_valido, mutacion, mensaje) -> None:
    mutacion(contenido_escenario_valido)
    ruta = tmp_path / "invalido.json"
    ruta.write_text(json.dumps(contenido_escenario_valido), encoding="utf-8")

    with pytest.raises(ErrorValidacionEscenario, match=mensaje):
        cargar_escenario(ruta)


def test_raiz_que_no_es_objeto_se_rechaza() -> None:
    with pytest.raises(ErrorValidacionEscenario, match="debe ser un objeto JSON"):
        validar_contenido_escenario([1, 2, 3])


def test_escenario_valido_no_lanza_error(contenido_escenario_valido) -> None:
    validar_contenido_escenario(contenido_escenario_valido)


@pytest.mark.parametrize("costo", [1, 0.5, 0.1])
def test_costos_positivos_finitos_son_aceptados(contenido_escenario_valido, costo) -> None:
    contenido_escenario_valido["tipos_terreno"]["camino"]["costo"] = costo

    validar_contenido_escenario(contenido_escenario_valido)


@pytest.mark.parametrize("costo", [float("nan"), float("inf"), float("-inf")])
def test_validador_rechaza_costos_no_finitos(contenido_escenario_valido, costo) -> None:
    contenido_escenario_valido["tipos_terreno"]["camino"]["costo"] = costo

    with pytest.raises(ErrorValidacionEscenario, match=r"'camino'.*positivo y finito"):
        validar_contenido_escenario(contenido_escenario_valido)


@pytest.mark.parametrize("literal", ["1e400", "-1e400"])
def test_cargador_rechaza_exponentes_json_que_desbordan_a_infinito(
    tmp_path, contenido_escenario_valido, literal
) -> None:
    texto = json.dumps(contenido_escenario_valido).replace('"costo": 2', f'"costo": {literal}')
    ruta = tmp_path / "costo_no_finito.json"
    ruta.write_text(texto, encoding="utf-8")

    with pytest.raises(ErrorValidacionEscenario, match=r"'camino'.*positivo y finito"):
        cargar_escenario(ruta)


def test_portador_valido_es_aceptado(contenido_escenario_valido) -> None:
    contenido_escenario_valido["juego"]["portador_recurso"] = "B1"

    validar_contenido_escenario(contenido_escenario_valido)


def test_la_validacion_no_modifica_el_contenido(contenido_escenario_valido) -> None:
    original = copy.deepcopy(contenido_escenario_valido)
    contenido_escenario_valido["unidades"][1]["id"] = "A1"
    invalido = copy.deepcopy(contenido_escenario_valido)

    validar_contenido_escenario(original)
    with pytest.raises(ErrorValidacionEscenario):
        validar_contenido_escenario(contenido_escenario_valido)

    assert contenido_escenario_valido == invalido


def test_carga_fallida_no_altera_el_escenario_cargado_previamente(tmp_path, contenido_escenario_valido) -> None:
    """Todo o nada: el error ocurre antes de construir nada, el escenario vigente queda intacto."""
    ruta_valida = tmp_path / "valido.json"
    ruta_valida.write_text(json.dumps(contenido_escenario_valido), encoding="utf-8")
    vigente = cargar_escenario(ruta_valida)
    referencia = cargar_escenario(ruta_valida)

    # Cambio de costo valido, pero el error del portador (ultima regla) impide aplicar cualquier cambio.
    contenido_escenario_valido["tipos_terreno"]["camino"]["costo"] = 99
    contenido_escenario_valido["juego"]["portador_recurso"] = "Z9"
    ruta_invalida = tmp_path / "invalido.json"
    ruta_invalida.write_text(json.dumps(contenido_escenario_valido), encoding="utf-8")

    try:
        vigente = cargar_escenario(ruta_invalida)
    except ErrorValidacionEscenario:
        pass

    assert vigente == referencia


def test_costo_no_finito_no_altera_el_escenario_cargado_previamente(
    tmp_path, contenido_escenario_valido
) -> None:
    ruta_valida = tmp_path / "valido.json"
    ruta_valida.write_text(json.dumps(contenido_escenario_valido), encoding="utf-8")
    vigente = cargar_escenario(ruta_valida)
    referencia = cargar_escenario(ruta_valida)

    texto = json.dumps(contenido_escenario_valido).replace('"costo": 2', '"costo": 1e400')
    ruta_invalida = tmp_path / "costo_no_finito.json"
    ruta_invalida.write_text(texto, encoding="utf-8")

    try:
        vigente = cargar_escenario(ruta_invalida)
    except ErrorValidacionEscenario:
        pass

    assert vigente == referencia


@pytest.mark.parametrize("valor", [None, 1, 1.5, True, "texto", [], [1], {}, {"x": 1}])
@pytest.mark.parametrize(
    "ruta",
    ["mapa", "tipos_terreno", "terreno", "bases", "recurso", "unidades", "turno", "juego", "unidades.0", "terreno.0"],
)
def test_valores_de_tipo_inesperado_solo_producen_error_de_validacion(contenido_escenario_valido, ruta, valor) -> None:
    """Ningun tipo inesperado provoca TypeError, KeyError u otra excepcion sin explicacion."""
    _poner(ruta, valor)(contenido_escenario_valido)

    try:
        validar_contenido_escenario(contenido_escenario_valido)
    except ErrorValidacionEscenario:
        pass
