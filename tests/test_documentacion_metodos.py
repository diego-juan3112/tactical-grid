"""Convencion de documentacion de metodos (E11.1), verificada sobre todo el codigo fuente.

El enunciado exige documentar con siete elementos (proposito, precondiciones, postcondiciones, complejidad, uso de
IA, intervencion de IA y validacion del estudiante) los metodos de busqueda, heuristicas, generacion de sucesores,
calculo de costos, utilidad, Minimax, alfa-beta y validadores, y que la documentacion corresponda al metodo real.
Estas pruebas no pueden juzgar si el texto es correcto, pero si impiden que la convencion se degrade: encabezados en
otro idioma, documentacion parcial, uso de IA sin declarar, validaciones pendientes o metodos relevantes sin
documentar.
"""

import ast
import re
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
FUENTES = sorted((RAIZ / "src" / "tacticalgrid").rglob("*.py")) + [RAIZ / "main.py"]

ENCABEZADOS = (
    "Proposito",
    "Precondiciones",
    "Postcondiciones",
    "Complejidad",
    "Uso de IA",
    "Intervencion de IA",
    "Validacion del estudiante",
)
ENCABEZADOS_EN_INGLES = (
    "Purpose",
    "Preconditions",
    "Postconditions",
    "Complexity",
    "AI usage",
    "AI intervention",
    "Student validation",
)

# Modulos con las categorias obligatorias del enunciado: busqueda, heuristicas, sucesores, costos, utilidad,
# Minimax, alfa-beta y validadores.
MODULOS_OBLIGATORIOS = (
    "algoritmos/alfa_beta.py",
    "algoritmos/busqueda_a_estrella.py",
    "algoritmos/busqueda_anchura.py",
    "algoritmos/busqueda_costo_uniforme.py",
    "algoritmos/busqueda_haz.py",
    "algoritmos/busqueda_profundidad.py",
    "algoritmos/comparacion_adversarial.py",
    "algoritmos/heuristica_obstaculos.py",
    "algoritmos/instrumentacion.py",
    "algoritmos/minimax.py",
    "algoritmos/orden_acciones.py",
    "algoritmos/utilidad.py",
    "algoritmos/verificador.py",
    "escenario/cargador.py",
    "escenario/escenario.py",
    "escenario/validador.py",
    "juego/problema.py",
    "juego/recurso.py",
    "juego/reglas.py",
    "juego/tacticas.py",
)
# El enunciado no exige este nivel de detalle para metodos triviales: se considera trivial una funcion de menos de
# ocho lineas (firma, documentacion y cuerpo incluidos), como un acceso a un atributo o una delegacion directa.
LINEAS_MINIMAS_NO_TRIVIAL = 8


def _relativo(archivo: Path) -> str:
    if archivo.name == "main.py" and archivo.parent == RAIZ:
        return "main.py"
    return archivo.relative_to(RAIZ / "src" / "tacticalgrid").as_posix()


def _funciones():
    for archivo in FUENTES:
        arbol = ast.parse(archivo.read_text(encoding="utf-8"))
        for nodo in ast.walk(arbol):
            if isinstance(nodo, (ast.FunctionDef, ast.AsyncFunctionDef)):
                yield _relativo(archivo), nodo, ast.get_docstring(nodo) or ""


def _id(relativo: str, nodo) -> str:
    return f"{relativo}:{nodo.lineno} {nodo.name}"


def _encabezados_presentes(documentacion: str) -> set[str]:
    return {encabezado for encabezado in ENCABEZADOS if re.search(rf"\b{encabezado}\s*:", documentacion)}


FUNCIONES = list(_funciones())
DOCUMENTADAS = [(r, n, d) for r, n, d in FUNCIONES if _encabezados_presentes(d)]


def test_ningun_docstring_usa_los_encabezados_en_ingles() -> None:
    infractoras = [
        _id(relativo, nodo)
        for relativo, nodo, documentacion in FUNCIONES
        if any(re.search(rf"\b{encabezado}\s*:", documentacion) for encabezado in ENCABEZADOS_EN_INGLES)
    ]

    assert infractoras == [], f"Encabezados en ingles (la convencion de AGENTS.md es en espanol): {infractoras}"


def test_la_documentacion_de_metodos_esta_completa_cuando_se_usa() -> None:
    incompletas = [
        f"{_id(relativo, nodo)} sin {sorted(set(ENCABEZADOS) - _encabezados_presentes(documentacion))}"
        for relativo, nodo, documentacion in DOCUMENTADAS
        if _encabezados_presentes(documentacion) != set(ENCABEZADOS)
    ]

    assert incompletas == []


def test_los_metodos_no_triviales_de_las_categorias_obligatorias_estan_documentados() -> None:
    sin_documentar = [
        _id(relativo, nodo)
        for relativo, nodo, documentacion in FUNCIONES
        if relativo in MODULOS_OBLIGATORIOS
        and (nodo.end_lineno - nodo.lineno + 1) >= LINEAS_MINIMAS_NO_TRIVIAL
        and _encabezados_presentes(documentacion) != set(ENCABEZADOS)
    ]

    assert sin_documentar == []


def test_el_uso_de_ia_se_declara_explicitamente() -> None:
    sin_declarar = []
    for relativo, nodo, documentacion in DOCUMENTADAS:
        uso = re.search(r"\bUso de IA\s*:\s*(\S+)", documentacion)
        if uso is None or uso.group(1).rstrip(".") not in ("Si", "No"):
            sin_declarar.append(_id(relativo, nodo))

    assert sin_declarar == [], "'Uso de IA' debe ser exactamente 'Si' o 'No'"


def test_si_hubo_ia_se_describe_su_intervencion() -> None:
    sin_descripcion = []
    for relativo, nodo, documentacion in DOCUMENTADAS:
        if re.search(r"\bUso de IA\s*:\s*Si\b", documentacion):
            intervencion = re.search(r"\bIntervencion de IA\s*:\s*(.+?)(?:\bValidacion del estudiante\s*:|$)", documentacion, re.S)
            if intervencion is None or len(intervencion.group(1).strip(" .\n")) < 10:
                sin_descripcion.append(_id(relativo, nodo))

    assert sin_descripcion == []


def test_ninguna_validacion_del_estudiante_queda_pendiente() -> None:
    pendientes = [
        _id(relativo, nodo)
        for relativo, nodo, documentacion in DOCUMENTADAS
        if re.search(r"\bValidacion del estudiante\s*:[^\n]*(\n[^\n]*)*?\bpendiente\b", documentacion, re.I)
    ]

    assert pendientes == []


@pytest.mark.parametrize("modulo", MODULOS_OBLIGATORIOS)
def test_los_modulos_obligatorios_existen(modulo) -> None:
    assert (RAIZ / "src" / "tacticalgrid" / modulo).is_file()
