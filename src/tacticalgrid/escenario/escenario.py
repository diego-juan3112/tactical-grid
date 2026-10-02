"""Representacion interna e inmutable de la informacion estatica del escenario."""

from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping

from .terreno import TipoTerreno


@dataclass(frozen=True)
class Posicion:
    """Coordenada de una celda de la cuadricula."""

    fila: int
    columna: int


@dataclass(frozen=True)
class UnidadInicial:
    """Descripcion estatica de una unidad declarada en el escenario."""

    identificador: str
    bando: str
    tipo: str
    posicion: Posicion


@dataclass(frozen=True)
class Escenario:
    """Informacion estatica validada que provee el escenario externo al dominio."""

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
        """Protege los mapas internos contra modificaciones externas posteriores."""
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
        """Indica si una posicion pertenece a los limites del mapa.

        Proposito: ofrecer al dominio una verificacion de limites sin conocer JSON.
        Precondiciones: ``posicion`` es una instancia de :class:`Posicion`.
        Postcondiciones: no modifica el escenario y devuelve ``True`` solo dentro de la cuadricula.
        Complejidad: O(1) temporal y O(1) espacial.
        Uso de IA: Si.
        Intervencion de IA: Codex propuso la implementacion inicial de esta consulta de limites.
        Validacion del estudiante: pendiente de revision del equipo; cubierta por pruebas automatizadas.
        """
        return 0 <= posicion.fila < self.filas and 0 <= posicion.columna < self.columnas

    def obtener_tipo_terreno(self, posicion: Posicion) -> TipoTerreno:
        """Obtiene la definicion del terreno de una celda valida.

        Proposito: centralizar el acceso a propiedades de terrenos cargadas desde el escenario.
        Precondiciones: ``posicion`` pertenece al mapa.
        Postcondiciones: devuelve el tipo de terreno declarado para esa celda; no modifica el escenario.
        Complejidad: O(1) temporal y O(1) espacial.
        Uso de IA: Si.
        Intervencion de IA: Codex propuso la implementacion inicial y su documentacion.
        Validacion del estudiante: pendiente de revision del equipo; cubierta indirectamente por pytest.
        """
        if not self.contiene_posicion(posicion):
            raise ValueError("La posicion esta fuera de los limites del escenario.")
        return self.tipos_terreno[self.terreno[posicion.fila][posicion.columna]]

    def es_transitable(self, posicion: Posicion) -> bool:
        """Consulta la transitabilidad de una celda a partir del catalogo del escenario.

        Proposito: evitar que las capas consumidoras codifiquen reglas por nombre de terreno.
        Precondiciones: ``posicion`` pertenece al mapa.
        Postcondiciones: devuelve la transitabilidad declarada en el JSON; no modifica el escenario.
        Complejidad: O(1) temporal y O(1) espacial.
        Uso de IA: Si.
        Intervencion de IA: Codex propuso la implementacion inicial y su documentacion.
        Validacion del estudiante: pendiente de revision del equipo; cubierta por pruebas automatizadas.
        """
        return self.obtener_tipo_terreno(posicion).transitable

    def obtener_costo(self, posicion: Posicion) -> int | float:
        """Consulta el costo de una celda transitable declarado por el escenario.

        Proposito: suministrar costos a reglas y algoritmos sin constantes de terreno embebidas.
        Precondiciones: ``posicion`` pertenece al mapa y su terreno es transitable.
        Postcondiciones: devuelve el costo positivo del catalogo; no modifica el escenario.
        Complejidad: O(1) temporal y O(1) espacial.
        Uso de IA: Si.
        Intervencion de IA: Codex propuso la implementacion inicial y su documentacion.
        Validacion del estudiante: pendiente de revision del equipo; cubierta por pruebas automatizadas.
        """
        tipo_terreno = self.obtener_tipo_terreno(posicion)
        if not tipo_terreno.transitable or tipo_terreno.costo is None:
            raise ValueError("No se puede obtener costo de un terreno no transitable.")
        return tipo_terreno.costo
