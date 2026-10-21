"""Representación interna e inmutable de la información estática del escenario."""

from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping

from .terreno import TipoTerreno


@dataclass(frozen=True)
class Posicion:
    """Coordenada de una celda de la cuadrícula."""

    fila: int
    columna: int


@dataclass(frozen=True)
class UnidadInicial:
    """Descripción estática de una unidad declarada en el escenario."""

    identificador: str
    bando: str
    tipo: str
    posicion: Posicion


@dataclass(frozen=True)
class Escenario:
    """Información estática validada que el escenario externo entrega al dominio."""

    version: str
    filas: int
    columnas: int
    tipos_terreno: Mapping[str, TipoTerreno]
    terreno: tuple[tuple[str, ...], ...]
    bases: Mapping[str, Posicion]
    recurso: Posicion
    unidades_iniciales: tuple[UnidadInicial, ...]
    turno_inicial: str
    portador_recurso_inicial: str | None
    configuracion_juego: Mapping[str, object]
    configuracion_prueba: Mapping[str, object] | None

    def __post_init__(self) -> None:
        """Proteger los mapas internos del escenario contra modificaciones posteriores a la carga.

        Proposito: impedir que reglas, algoritmos o interfaz alteren costos, bases o configuración de un escenario ya
        validado, para que todas las capas lean los mismos datos.
        Precondiciones: los campos provienen de ``cargar_escenario`` y de un JSON validado.
        Postcondiciones: ``tipos_terreno``, ``bases``, ``configuracion_juego`` y, si existe, ``configuracion_prueba``
        quedan como copias de solo lectura (``MappingProxyType``): asignar una clave lanza ``TypeError`` y los campos
        del dataclass congelado no se pueden reasignar. La protección es superficial: los objetos anidados de
        ``configuracion_juego`` y ``configuracion_prueba``, como ``pesos_utilidad`` u ``objetivo``, siguen siendo
        diccionarios comunes.
        Complejidad: O(T + P) temporal y espacial, con T tipos de terreno y P claves de configuración.
        Uso de IA: Si.
        Intervencion de IA: Codex: implementación inicial (E0.3). Claude (Opus 5.5): documentación (E11.1).
        Validacion del estudiante: prueba ``test_el_escenario_protege_sus_mapas_contra_modificaciones`` de
        tests/escenario/test_cargador.py: los mapas no aceptan claves nuevas y los campos no se pueden reasignar.
        """
        object.__setattr__(self, "tipos_terreno", MappingProxyType(dict(self.tipos_terreno)))
        object.__setattr__(self, "bases", MappingProxyType(dict(self.bases)))
        object.__setattr__(self, "configuracion_juego", MappingProxyType(dict(self.configuracion_juego)))
        if self.configuracion_prueba is not None:
            object.__setattr__(
                self,
                "configuracion_prueba",
                MappingProxyType(dict(self.configuracion_prueba)),
            )

    def contiene_posicion(self, posicion: Posicion) -> bool:
        """Indicar si una posición pertenece a los límites del mapa.

        Proposito: ofrecer al dominio una comprobación de límites sin depender del JSON.
        Precondiciones: ``posicion`` es una instancia de :class:`Posicion`.
        Postcondiciones: se devuelve ``True`` solo para posiciones dentro de la cuadrícula; el escenario no cambia.
        Complejidad: O(1) temporal y espacial.
        Uso de IA: Si.
        Intervencion de IA: Codex: implementación inicial de la consulta de límites.
        Validacion del estudiante: pruebas de tests/escenario/test_cargador.py y tests/juego/test_espacio_estados.py.
        """
        return 0 <= posicion.fila < self.filas and 0 <= posicion.columna < self.columnas

    def obtener_tipo_terreno(self, posicion: Posicion) -> TipoTerreno:
        """Obtener la definición del terreno de una celda válida.

        Proposito: centralizar el acceso a las propiedades de terreno cargadas desde el escenario.
        Precondiciones: ``posicion`` pertenece al mapa.
        Postcondiciones: se devuelve el tipo de terreno declarado para la celda; el escenario no cambia.
        Complejidad: O(1) temporal y espacial.
        Uso de IA: Si.
        Intervencion de IA: Codex: implementación inicial y documentación.
        Validacion del estudiante: cobertura indirecta mediante ``es_transitable`` y ``obtener_costo``, que lo usan y se
        prueban en tests/escenario/test_cargador.py y tests/juego/test_espacio_estados.py.
        """
        if not self.contiene_posicion(posicion):
            raise ValueError("La posicion esta fuera de los limites del escenario.")
        return self.tipos_terreno[self.terreno[posicion.fila][posicion.columna]]

    def es_transitable(self, posicion: Posicion) -> bool:
        """Consultar la transitabilidad de una celda en el catálogo del escenario.

        Proposito: evitar que las capas consumidoras codifiquen reglas por nombre de terreno.
        Precondiciones: ``posicion`` pertenece al mapa.
        Postcondiciones: se devuelve la transitabilidad declarada en el JSON; el escenario no cambia.
        Complejidad: O(1) temporal y espacial.
        Uso de IA: Si.
        Intervencion de IA: Codex: implementación inicial y documentación.
        Validacion del estudiante: pruebas de tests/escenario/test_cargador.py, tests/juego/test_espacio_estados.py y de
        las búsquedas en tests/algoritmos/.
        """
        return self.obtener_tipo_terreno(posicion).transitable

    def obtener_costo(self, posicion: Posicion) -> int | float:
        """Consultar el costo de una celda transitable declarado por el escenario.

        Proposito: suministrar costos a reglas y algoritmos sin constantes de terreno en el código.
        Precondiciones: ``posicion`` pertenece al mapa y su terreno es transitable.
        Postcondiciones: se devuelve el costo positivo del catálogo; el escenario no cambia.
        Complejidad: O(1) temporal y espacial.
        Uso de IA: Si.
        Intervencion de IA: Codex: implementación inicial y documentación.
        Validacion del estudiante: pruebas de tests/escenario/test_cargador.py, tests/juego/test_espacio_estados.py y
        tests/algoritmos/test_instrumentacion.py.
        """
        tipo_terreno = self.obtener_tipo_terreno(posicion)
        if not tipo_terreno.transitable or tipo_terreno.costo is None:
            raise ValueError("No se puede obtener costo de un terreno no transitable.")
        return tipo_terreno.costo
