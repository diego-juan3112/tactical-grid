"""Registro reproducible de experimentos (E10.3).

Reune en una sola estructura serializable a JSON todo lo necesario para repetir y comparar una prueba: el escenario
(con una huella de su contenido), el modo, los parametros ya resueltos (de la consola o del JSON), el comando que la
reproduce, los resultados con la estructura del enunciado y, si se pidio, la verificacion de E10.2.

Este modulo no abre archivos (regla de la capa de modos): la huella del escenario la calcula quien lee el archivo.
"""

import json
import shlex
from dataclasses import dataclass, field

from tacticalgrid.escenario.escenario import Escenario

FORMATO = "tacticalgrid.resultados/1"
NOTA_REPRODUCIBILIDAD = (
    "Todos los algoritmos son deterministas: con el mismo escenario (misma huella) y los mismos parametros, los "
    "resultados son identicos salvo los campos tiempo_segundos, que dependen de la maquina."
)
CLAVES_ENUNCIADO_BUSQUEDA = (
    "algoritmo",
    "exito",
    "camino",
    "costo",
    "estados_generados",
    "estados_expandidos",
    "maximo_frontera",
)
CLAVES_ENUNCIADO_ADVERSARIAL = (
    "nodos_generados",
    "nodos_evaluados",
    "nodos_podados",
    "profundidad_alcanzada",
    "tiempo_segundos",
    "accion_seleccionada",
    "valor",
)

# Opcion de consola de cada parametro, en el orden en que se escribe el comando de reproduccion.
_OPCIONES = (
    ("algoritmo", "--algoritmo"),
    ("unidad", "--unidad"),
    ("objetivo", "--objetivo"),
    ("k", "--k"),
    ("profundidad", "--profundidad"),
    ("orden_acciones", "--orden"),
    ("max_turnos", "--turnos"),
)


@dataclass
class RegistroExperimento:
    """Acumula el modo, los parametros y los resultados de una ejecucion para exportarlos juntos."""

    archivo: str
    huella_sha256: str
    escenario: Escenario
    modo: str | None = None
    parametros: dict[str, object] = field(default_factory=dict)
    resultados: list[dict[str, object]] = field(default_factory=list)
    verificaciones: list[dict[str, object]] = field(default_factory=list)
    verificar: bool = False

    def definir(self, modo: str, **parametros: object) -> None:
        """Registra el modo y los parametros ya resueltos (los que realmente uso la ejecucion)."""
        self.modo = modo
        self.parametros = {clave: valor for clave, valor in parametros.items() if valor is not None}

    def agregar_resultado(self, resultado) -> None:
        """Agrega un resultado con ``a_diccionario`` (busqueda, Minimax, alfa-beta, comparacion o partida)."""
        self.resultados.append(resultado.a_diccionario())

    def agregar_verificacion(self, reporte) -> None:
        """Agrega un ``ReporteVerificacion`` de E10.2."""
        self.verificaciones.append(
            {
                "sujeto": reporte.sujeto,
                "valido": reporte.es_valido,
                "comprobaciones": [
                    {"nombre": c.nombre, "correcta": c.correcta, "detalle": c.detalle} for c in reporte.comprobaciones
                ],
            }
        )

    def comando(self) -> str:
        """Comando de consola que repite la ejecucion con los mismos parametros resueltos."""
        partes = ["python", "main.py", self.archivo]
        if self.modo is not None:
            partes += ["--modo", self.modo]
        for clave, opcion in _OPCIONES:
            valor = self.parametros.get(clave)
            if valor is None:
                continue
            valores = valor if isinstance(valor, (list, tuple)) else [valor]
            partes += [opcion, *(str(v) for v in valores)]
        if self.verificar:
            partes.append("--verificar")
        return shlex.join(partes)

    def a_diccionario(self) -> dict[str, object]:
        """Construye el documento reproducible del experimento.

        Purpose: hacer accesible el resultado de cualquier prueba en una estructura equivalente a la del enunciado,
        con lo necesario para repetirla y compararla.
        Preconditions: ``definir`` ya se llamo con el modo y los parametros resueltos.
        Postconditions: devuelve un diccionario serializable con ``json.dumps`` con las claves ``formato``,
        ``escenario`` (archivo, version, dimensiones y huella SHA-256), ``modo``, ``parametros``, ``comando``,
        ``nota``, ``resultados`` (cada uno con las claves del enunciado para su tipo) y, si se verifico,
        ``verificacion``. No modifica el registro.
        Complexity: O(R) temporal y espacial, donde R es el tamano total de los resultados registrados.
        AI usage: Yes.
        AI intervention: Claude (Opus 5.5) diseno la estructura del registro y la implemento en E10.3.
        Student validation: el estudiante reviso y valido el codigo; ademas, las pruebas de
        tests/modos/test_registro.py comprueban las claves del enunciado en los tres modos, que el comando reproduce
        el mismo resultado y que dos ejecuciones coinciden salvo el tiempo.
        """
        documento: dict[str, object] = {
            "formato": FORMATO,
            "escenario": {
                "archivo": self.archivo,
                "version": self.escenario.version,
                "filas": self.escenario.filas,
                "columnas": self.escenario.columnas,
                "huella_sha256": self.huella_sha256,
            },
            "modo": self.modo,
            "parametros": self.parametros,
            "comando": self.comando(),
            "nota": NOTA_REPRODUCIBILIDAD,
            "resultados": self.resultados,
        }
        if self.verificar:
            documento["verificacion"] = {
                "valida": all(v["valido"] for v in self.verificaciones),
                "reportes": self.verificaciones,
            }
        return documento


def _es_escalar(valor: object) -> bool:
    return not isinstance(valor, (dict, list, tuple))


def _en_linea(valor: object) -> bool:
    """Una lista va en una sola linea si sus elementos son escalares o listas de escalares (por ejemplo, un camino)."""
    return all(
        _es_escalar(elemento) or (isinstance(elemento, (list, tuple)) and all(_es_escalar(e) for e in elemento))
        for elemento in valor
    )


def _formatear(valor: object, nivel: int) -> str:
    sangria, interior = "  " * nivel, "  " * (nivel + 1)
    if isinstance(valor, dict):
        if not valor:
            return "{}"
        lineas = [f"{interior}{json.dumps(clave, ensure_ascii=False)}: {_formatear(v, nivel + 1)}" for clave, v in valor.items()]
        return "{\n" + ",\n".join(lineas) + f"\n{sangria}}}"
    if isinstance(valor, (list, tuple)):
        if _en_linea(valor):
            return json.dumps(list(valor), ensure_ascii=False, separators=(", ", ": "))
        return "[\n" + ",\n".join(f"{interior}{_formatear(v, nivel + 1)}" for v in valor) + f"\n{sangria}]"
    return json.dumps(valor, ensure_ascii=False)


def serializar(documento: dict[str, object]) -> str:
    """Convierte el registro en texto JSON legible: indentado, pero con las listas de valores en una sola linea.

    Purpose: que el registro se lea como el ejemplo del enunciado, con ``camino`` en la forma ``[[3, 2], [3, 3]]`` en
    lugar de una coordenada por linea.
    Preconditions: ``documento`` es serializable con ``json.dumps``.
    Postconditions: devuelve texto JSON valido; ``json.loads`` lo convierte de nuevo exactamente en ``documento``.
    Recorre la estructura (no modifica el texto con expresiones regulares), asi que el contenido de las cadenas nunca
    se altera.
    Complexity: O(N) temporal y espacial, donde N es el tamano del documento.
    AI usage: Yes.
    AI intervention: Claude (Opus 5.5) implemento este formateador recursivo en E10.3.
    Student validation: el estudiante reviso y valido el codigo; ademas, las pruebas de tests/modos/test_registro.py
    comprueban que el texto vuelve a producir el mismo documento, incluidas cadenas con comas y corchetes.
    """
    return _formatear(documento, 0)


def sin_tiempos(valor: object) -> object:
    """Copia de ``valor`` sin los campos ``tiempo_segundos``, para comparar dos ejecuciones del mismo experimento."""
    if isinstance(valor, dict):
        return {k: sin_tiempos(v) for k, v in valor.items() if k != "tiempo_segundos"}
    if isinstance(valor, list):
        return [sin_tiempos(v) for v in valor]
    return valor
