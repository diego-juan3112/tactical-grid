"""Carga y caché de los atlas gráficos de la interfaz Pygame."""

from pathlib import Path

import pygame


class RecursosGraficos:
    """Atlas originales y superficies escaladas, mantenidos fuera del estado del juego."""

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
        """Cargar los atlas una sola vez y preparar una caché de escalado.

        Proposito: resolver los recursos desde el paquete, sin depender del directorio de ejecución, y tolerar archivos
        ausentes mediante valores nulos que el renderizador convierte en sustitutos visibles.
        Precondiciones: Pygame puede decodificar PNG; ``ruta_recursos`` apunta al directorio raíz si se proporciona.
        Postcondiciones: cada atlas disponible queda cargado una vez y ``errores`` identifica los faltantes.
        Complejidad: O(P) temporal y espacial por los píxeles de ambos atlas.
        Uso de IA: Si.
        Intervencion de IA: Codex: carga empaquetable, recortes y caché de superficies escaladas.
        Validacion del estudiante: pruebas ``test_carga_atlas_empaquetados_y_cachea_escalados`` y
        ``test_fallback_visible_si_faltan_recursos`` de tests/interfaz/test_renderizador.py.
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
        """Cargar una imagen PNG y convertir los fallos admitidos en ausencia de recurso.

        Proposito: centralizar la decodificación de un atlas y permitir que el renderizador active su sustituto visible.
        Precondiciones: ``ruta`` es un ``Path`` que identifica el archivo candidato y ``pygame.image.load`` está
        disponible.
        Postcondiciones: se devuelve la superficie decodificada, o ``None`` ante ``FileNotFoundError`` o
        ``pygame.error``; cualquier otra excepción se propaga.
        Complejidad: O(L + P) temporal y espacial en una carga correcta, con L la longitud de la ruta y P los píxeles
        decodificados; O(L) temporal y espacial ante uno de los fallos admitidos.
        Uso de IA: Si.
        Intervencion de IA: Codex: documentación de la carga existente y de su política de sustitución, sin modificarla.
        Validacion del estudiante: pruebas ``test_carga_atlas_empaquetados_y_cachea_escalados`` y
        ``test_fallback_visible_si_faltan_recursos`` de tests/interfaz/test_renderizador.py.
        """
        try:
            return pygame.image.load(ruta.as_posix())
        except (FileNotFoundError, pygame.error):
            return None

    def terreno(self, nombre: str, lado: int, variante: int) -> pygame.Surface | None:
        """Obtener un tile conocido con una variación geométrica determinista.

        Proposito: reutilizar el atlas de terrenos y evitar que celdas iguales repitan exactamente la misma orientación.
        Precondiciones: ``lado`` es positivo y ``variante`` está normalizada por el consumidor.
        Postcondiciones: se devuelve una superficie cuadrada en caché, o ``None`` si el nombre o el atlas no están
        disponibles.
        Complejidad: O(lado^2) en el primer acceso a una combinación y O(1) en los siguientes.
        Uso de IA: Si.
        Intervencion de IA: Codex: recorte, reflejos y escalado en caché sin aleatoriedad global.
        Validacion del estudiante: prueba ``test_variacion_visual_es_determinista_y_no_muta_estado`` de
        tests/interfaz/test_renderizador.py.
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
        """Obtener un objeto transparente escalado y guardado en caché.

        Proposito: servir obstáculos, bases, unidades y recurso sin cargar ni escalar PNG en cada fotograma.
        Precondiciones: ``nombre`` pertenece al inventario y ``lado`` es positivo.
        Postcondiciones: se devuelve una superficie cuadrada en caché, o ``None`` si falta el atlas o el nombre.
        Complejidad: O(lado^2) en el primer acceso y O(1) después.
        Uso de IA: Si.
        Intervencion de IA: Codex: recorte uniforme del atlas y caché por tamaño.
        Validacion del estudiante: pruebas de tests/interfaz/test_renderizador.py: unidades de ambos bandos con
        identidad distinta, composición superpuesta de base, unidad y portador, y caché de escalados.
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
        """Cantidad de transformaciones almacenadas, expuesta para las pruebas de gestión de recursos."""
        return len(self._cache)
