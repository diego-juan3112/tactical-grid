"""Registro reproducible de experimentos (E10.3).

Reúne en una sola estructura serializable a JSON lo necesario para repetir y comparar una prueba: el escenario (con
una huella de su contenido), el modo, los parámetros ya resueltos (de la consola o del JSON), el comando que la
reproduce, los resultados con la estructura del enunciado y, si se pidió, la verificación de E10.2.

Este módulo no abre archivos, según la regla de la capa de modos: la huella del escenario la calcula quien lee el
archivo.
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

# Opción de consola de cada parámetro, en el orden en que se escribe el comando de reproducción.
_OPCIONES = (
    ("algoritmo", "--algoritmo"),
    ("unidad", "--unidad"),
    ("objetivo", "--objetivo"),
    ("k", "--k"),
    ("heuristica", "--heuristica"),
    ("profundidad", "--profundidad"),
    ("orden_acciones", "--orden"),
    ("max_turnos", "--turnos"),
)


@dataclass
class RegistroExperimento:
    """Acumulador del modo, los parámetros y los resultados de una ejecución para exportarlos juntos."""

    archivo: str
    huella_sha256: str
    escenario: Escenario
    modo: str | None = None
    parametros: dict[str, object] = field(default_factory=dict)
    resultados: list[dict[str, object]] = field(default_factory=list)
    verificaciones: list[dict[str, object]] = field(default_factory=list)
    verificar: bool = False

    def definir(self, modo: str, **parametros: object) -> None:
        """Registrar el modo y los parámetros ya resueltos, es decir, los que usó la ejecución."""
        self.modo = modo
        self.parametros = {clave: valor for clave, valor in parametros.items() if valor is not None}

    def agregar_resultado(self, resultado) -> None:
        """Agregar un resultado con ``a_diccionario`` (búsqueda, Minimax, alfa-beta, comparación o partida)."""
        self.resultados.append(resultado.a_diccionario())

    def agregar_verificacion(self, reporte) -> None:
        """Agregar un ``ReporteVerificacion`` de E10.2."""
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
        """Construir la línea de consola que reproduce este registro.

        Proposito: serializar escenario, modo, parámetros resueltos y verificación como un comando seguro para la shell.
        Precondiciones: ``archivo`` es una ruta representable como texto y ``parametros`` contiene valores ya resueltos
        por el orquestador; aquí no se comprueba que el comando se pueda ejecutar en otro entorno.
        Postcondiciones: se devuelve una línea que empieza con ``python main.py`` y conserva cada opción conocida en
        ``_OPCIONES``; las listas y tuplas se emiten como argumentos múltiples y ``shlex.join`` cita cada argumento. Se
        agregan ``--modo`` y ``--verificar`` cuando corresponden. El registro no cambia.
        Complejidad: O(P + S) temporal y espacial, con P la cantidad de valores emitidos y S la longitud total de sus
        representaciones de texto.
        Uso de IA: Si.
        Intervencion de IA: Claude (Opus 5.5): diseño del registro reproducible (E10.3). Codex: documentación del método
        durante la corrección de hallazgos.
        Validacion del estudiante: pruebas de tests/modos/test_registro.py: comando que reproduce los mismos resultados,
        citado de argumentos con espacios y omisión de parámetros que no son opciones de consola.
        """
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
        """Construir el documento reproducible del experimento.

        Proposito: exponer el resultado de cualquier prueba en una estructura equivalente a la del enunciado, con lo
        necesario para repetirla y compararla.
        Precondiciones: ``definir`` ya se llamó con el modo y los parámetros resueltos.
        Postcondiciones: se devuelve un diccionario serializable con ``json.dumps`` con las claves ``formato``,
        ``escenario`` (archivo, versión, dimensiones y huella SHA-256), ``modo``, ``parametros``, ``comando``, ``nota``,
        ``resultados`` (cada uno con las claves del enunciado para su tipo) y, si se verificó, ``verificacion``. El
        registro no cambia.
        Complejidad: O(R) temporal y espacial, con R el tamaño total de los resultados registrados.
        Uso de IA: Si.
        Intervencion de IA: Claude (Opus 5.5): estructura del registro e implementación (E10.3).
        Validacion del estudiante: pruebas de tests/modos/test_registro.py: claves del enunciado en los tres modos,
        comando que reproduce el mismo resultado y dos ejecuciones que solo difieren en el tiempo.
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
    """Indicar si una lista va en una sola línea: sus elementos son escalares o listas de escalares, como un camino."""
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
    """Convertir el registro en texto JSON legible: indentado, pero con las listas de valores en una sola línea.

    Proposito: presentar el registro como el ejemplo del enunciado, con ``camino`` en la forma ``[[3, 2], [3, 3]]`` en
    lugar de una coordenada por línea.
    Precondiciones: ``documento`` es serializable con ``json.dumps``.
    Postcondiciones: se devuelve texto JSON válido, que ``json.loads`` convierte de nuevo exactamente en ``documento``.
    Se recorre la estructura, sin expresiones regulares sobre el texto, de modo que el contenido de las cadenas no se
    altera.
    Complejidad: O(N) temporal y espacial, con N el tamaño del documento.
    Uso de IA: Si.
    Intervencion de IA: Claude (Opus 5.5): formateador recursivo (E10.3).
    Validacion del estudiante: prueba ``test_serializar_conserva_cualquier_contenido`` de tests/modos/test_registro.py,
    con cadenas que contienen comas y corchetes.
    """
    return _formatear(documento, 0)


def sin_tiempos(valor: object) -> object:
    """Copia de ``valor`` sin los campos ``tiempo_segundos``, para comparar dos ejecuciones del mismo experimento."""
    if isinstance(valor, dict):
        return {k: sin_tiempos(v) for k, v in valor.items() if k != "tiempo_segundos"}
    if isinstance(valor, list):
        return [sin_tiempos(v) for v in valor]
    return valor
