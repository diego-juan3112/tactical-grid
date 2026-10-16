"""Carga y cache de los atlas graficos usados por la interfaz Pygame."""

from pathlib import Path

import pygame


class RecursosGraficos:
    """Mantiene atlas originales y superficies escaladas fuera del estado del juego."""

    TERRENOS = {
        "camino": (0, 0),
        "pasto": (1, 0),
        "llanura": (1, 0),
        "bosque": (0, 1),
        "pantano": (1, 1),
    }
    OBJETOS = {
        "obstaculo": (0, 0),
        "base_a": (1, 0),
        "base_b": (2, 0),
        "unidad_a": (0, 1),
        "unidad_b": (1, 1),
        "recurso": (2, 1),
    }

    def __init__(self, ruta_recursos: Path | None = None) -> None:
        """Carga los atlas una vez y prepara una cache de escalado.

        Purpose: resolver recursos desde el paquete, sin depender del directorio de ejecucion, y tolerar archivos
        ausentes mediante valores nulos que el renderizador convierte en fallbacks visibles.
        Preconditions: Pygame puede decodificar PNG; ``ruta_recursos`` apunta al directorio raiz si se proporciona.
        Postconditions: cada atlas disponible queda cargado una vez y ``errores`` identifica los faltantes.
        Complexity: O(P) temporal y espacial por los pixeles de ambos atlas.
        AI usage: Yes.
        AI intervention: Codex diseño la carga empaquetable, los recortes y la cache de superficies escaladas.
        Student validation: pendiente de revision del equipo; cubierta por pruebas de carga, escalado y fallback.
        """
        raiz = ruta_recursos or Path(__file__).with_name("recursos")
        self._atlas_terrenos = self._cargar(raiz / "terrenos" / "atlas_terrenos.png")
        self._atlas_objetos = self._cargar(raiz / "objetos" / "atlas_objetos.png")
        self.errores = tuple(
            nombre
            for nombre, atlas in (
                ("atlas_terrenos.png", self._atlas_terrenos),
                ("atlas_objetos.png", self._atlas_objetos),
            )
            if atlas is None
        )
        self._cache: dict[tuple[str, int, int], pygame.Surface] = {}

    @staticmethod
    def _cargar(ruta: Path) -> pygame.Surface | None:
        """Carga una imagen PNG y convierte los fallos admitidos en ausencia de recurso.

        Purpose: centralizar la decodificacion de un atlas y permitir que el renderizador active su fallback.
        Preconditions: ``ruta`` es un ``Path`` que identifica el archivo candidato y ``pygame.image.load`` esta
        disponible.
        Postconditions: devuelve la superficie decodificada; devuelve ``None`` ante ``FileNotFoundError`` o
        ``pygame.error``; cualquier otra excepcion se propaga.
        Complexity: O(L + P) temporal y espacial al cargar correctamente, donde L es la longitud de la ruta y P la
        cantidad de pixeles decodificados; O(L) temporal y espacial cuando ocurre uno de los fallos admitidos.
        AI usage: Yes.
        AI intervention: Codex documento la carga existente y su politica de fallback sin modificarla.
        Student validation: pendiente de revision del equipo; el comportamiento esta cubierto por pruebas automatizadas
        de carga de atlas y archivos ausentes.
        """
        try:
            return pygame.image.load(ruta.as_posix())
        except (FileNotFoundError, pygame.error):
            return None

    def terreno(self, nombre: str, lado: int, variante: int) -> pygame.Surface | None:
        """Obtiene un tile conocido con una variacion geometrica determinista.

        Purpose: reutilizar el atlas de terrenos y evitar que celdas iguales repitan exactamente la orientacion.
        Preconditions: ``lado`` es positivo y ``variante`` esta normalizada por el consumidor.
        Postconditions: devuelve una superficie cuadrada cacheada, o ``None`` para un nombre/atlas no disponible.
        Complexity: O(lado^2) en el primer acceso a una combinacion y O(1) en accesos posteriores.
        AI usage: Yes.
        AI intervention: Codex implemento recorte, reflejos y escalado cacheado sin aleatoriedad global.
        Student validation: pendiente de revision del equipo; cubierta por pruebas de determinismo y cache.
        """
        clave_nombre = nombre.casefold()
        coordenada = self.TERRENOS.get(clave_nombre)
        if self._atlas_terrenos is None or coordenada is None:
            return None
        clave = (f"terreno:{clave_nombre}", lado, variante % 4)
        if clave not in self._cache:
            ancho = self._atlas_terrenos.get_width() // 2
            alto = self._atlas_terrenos.get_height() // 2
            recorte = self._atlas_terrenos.subsurface(
                pygame.Rect(coordenada[0] * ancho, coordenada[1] * alto, ancho, alto)
            )
            if variante & 1:
                recorte = pygame.transform.flip(recorte, True, False)
            if variante & 2:
                recorte = pygame.transform.flip(recorte, False, True)
            self._cache[clave] = pygame.transform.scale(recorte, (lado, lado))
        return self._cache[clave]

    def objeto(self, nombre: str, lado: int) -> pygame.Surface | None:
        """Obtiene un objeto transparente escalado y cacheado.

        Purpose: servir obstaculos, bases, unidades y recurso sin cargar ni escalar PNG en cada fotograma.
        Preconditions: ``nombre`` pertenece al inventario y ``lado`` es positivo.
        Postconditions: devuelve una superficie cuadrada cacheada, o ``None`` si falta el atlas o el nombre.
        Complexity: O(lado^2) en el primer acceso y O(1) despues.
        AI usage: Yes.
        AI intervention: Codex implemento el recorte uniforme del atlas y su cache por tamaño.
        Student validation: pendiente de revision del equipo; cubierta por pruebas de sprites y escalado.
        """
        coordenada = self.OBJETOS.get(nombre)
        if self._atlas_objetos is None or coordenada is None:
            return None
        clave = (f"objeto:{nombre}", lado, 0)
        if clave not in self._cache:
            ancho = self._atlas_objetos.get_width() // 3
            alto = self._atlas_objetos.get_height() // 2
            recorte = self._atlas_objetos.subsurface(
                pygame.Rect(coordenada[0] * ancho, coordenada[1] * alto, ancho, alto)
            )
            self._cache[clave] = pygame.transform.smoothscale(recorte, (lado, lado))
        return self._cache[clave]

    @property
    def cantidad_cacheada(self) -> int:
        """Expone la cantidad de transformaciones almacenadas para pruebas de gestion de recursos."""
        return len(self._cache)
