"""Renderizado Pygame del escenario y del estado dinamico de TacticalGrid."""

from dataclasses import dataclass
from hashlib import sha256

import pygame

from tacticalgrid.algoritmos.resultado_busqueda import ResultadoBusqueda
from tacticalgrid.escenario.escenario import Escenario, Posicion
from tacticalgrid.escenario.terreno import TipoTerreno
from tacticalgrid.juego.estado import EstadoJuego


Color = tuple[int, int, int]


@dataclass(frozen=True)
class DisposicionTablero:
    """Geometria calculada para ubicar el tablero y su panel informativo."""

    tablero: pygame.Rect
    panel: pygame.Rect
    tamano_celda: int


class RenderizadorTablero:
    """Compone una vista completa sin modificar el escenario ni el estado."""

    COLOR_FONDO: Color = (24, 31, 38)
    COLOR_PANEL: Color = (35, 44, 53)
    COLOR_TEXTO: Color = (238, 242, 246)
    COLOR_CUADRICULA: Color = (56, 65, 74)
    COLOR_OBSTACULO: Color = (20, 22, 25)
    COLOR_BASES: dict[str, Color] = {"A": (38, 117, 191), "B": (190, 68, 68)}
    COLOR_RECURSO: Color = (244, 196, 48)
    COLOR_CAMINO: Color = (22, 224, 238)
    COLOR_ORIGEN: Color = (68, 220, 112)
    COLOR_DESTINO: Color = (255, 112, 82)
    ANCHO_PANEL = 250
    MARGEN = 16

    def __init__(self) -> None:
        """Prepara fuentes reutilizables para las etiquetas del tablero.

        Purpose: inicializar los recursos tipograficos exclusivos de la interfaz.
        Preconditions: Pygame esta importado; no se requiere una ventana activa.
        Postconditions: la instancia dispone de fuentes y no altera el dominio.
        Complexity: O(1) temporal y espacial.
        AI usage: Yes.
        AI intervention: Codex diseño la inicializacion local de fuentes para E9.1.
        Student validation: pendiente de revision del equipo; cubierta por pruebas automatizadas sin pantalla.
        """
        if not pygame.font.get_init():
            pygame.font.init()
        self._fuente = pygame.font.Font(None, 22)
        self._fuente_pequena = pygame.font.Font(None, 17)
        self._fuente_unidad = pygame.font.Font(None, 18)

    def calcular_disposicion(self, superficie: pygame.Surface, escenario: Escenario) -> DisposicionTablero:
        """Calcula una cuadricula centrada y un panel lateral segun las dimensiones disponibles.

        Purpose: adaptar el tablero a cualquier cantidad valida de filas y columnas sin coordenadas de mapa fijas.
        Preconditions: ``superficie`` tiene dimensiones positivas y ``escenario`` tiene filas y columnas positivas.
        Postconditions: devuelve celdas cuadradas de al menos un pixel, contenidas en la superficie.
        Complexity: O(1) temporal y espacial.
        AI usage: Yes.
        AI intervention: Codex diseño el ajuste proporcional y la reserva del panel informativo para E9.1.
        Student validation: pendiente de revision del equipo; cubierta por pruebas de mapas 20x20 y rectangulares.
        """
        ancho, alto = superficie.get_size()
        ancho_panel = min(self.ANCHO_PANEL, max(0, ancho // 3))
        ancho_disponible = max(1, ancho - ancho_panel - self.MARGEN * 3)
        alto_disponible = max(1, alto - self.MARGEN * 2)
        tamano_celda = max(
            1,
            min(ancho_disponible // escenario.columnas, alto_disponible // escenario.filas),
        )
        ancho_tablero = tamano_celda * escenario.columnas
        alto_tablero = tamano_celda * escenario.filas
        origen_y = max(0, (alto - alto_tablero) // 2)
        tablero = pygame.Rect(self.MARGEN, origen_y, ancho_tablero, alto_tablero)
        panel_x = min(ancho, tablero.right + self.MARGEN)
        panel = pygame.Rect(
            panel_x,
            self.MARGEN,
            max(0, ancho - panel_x - self.MARGEN),
            max(0, alto - self.MARGEN * 2),
        )
        return DisposicionTablero(tablero=tablero, panel=panel, tamano_celda=tamano_celda)

    def color_para_terreno(self, nombre: str, tipo: TipoTerreno) -> Color:
        """Deriva un color estable de cualquier nombre de terreno cargado.

        Purpose: diferenciar terrenos conocidos o externos sin mantener un catalogo codificado en la interfaz.
        Preconditions: ``nombre`` no esta vacio y ``tipo`` pertenece al catalogo validado del escenario.
        Postconditions: devuelve siempre el mismo color RGB para el mismo nombre y transitabilidad.
        Complexity: O(L) temporal y O(1) espacial, donde L es la longitud UTF-8 del nombre.
        AI usage: Yes.
        AI intervention: Codex diseño la paleta determinista basada en SHA-256 para admitir tipos futuros.
        Student validation: pendiente de revision del equipo; cubierta por pruebas de estabilidad y terreno externo.
        """
        resumen = sha256(nombre.encode("utf-8")).digest()
        if tipo.transitable:
            return (80 + resumen[0] % 116, 80 + resumen[1] % 116, 80 + resumen[2] % 116)
        return (38 + resumen[0] % 35, 38 + resumen[1] % 35, 38 + resumen[2] % 35)

    def renderizar(
        self,
        superficie: pygame.Surface,
        escenario: Escenario,
        estado: EstadoJuego,
        resultado_busqueda: ResultadoBusqueda | None = None,
    ) -> DisposicionTablero:
        """Dibuja el tablero completo y su informacion vigente sobre una superficie Pygame.

        Purpose: representar terrenos, camino de busqueda opcional, obstaculos, bases, recurso, unidades, portador,
        turno y leyenda.
        Preconditions: ``escenario`` esta validado y ``estado`` es coherente con el escenario.
        Postconditions: la superficie refleja el estado recibido; escenario y estado permanecen inmutables.
        Complexity: O(F*C + U + T + L) temporal y O(F*C + L) espacial, con celdas, unidades, tipos de terreno y
        L posiciones del camino.
        AI usage: Yes.
        AI intervention: Codex implemento la composicion por capas, simbolos y panel para E9.1; en E9.2 agrego el
        camino proveniente de ``ResultadoBusqueda`` sin alterar su contenido.
        Student validation: pendiente de revision y validacion visual manual del equipo; cubierta por pruebas
        automatizadas del orden, fidelidad y superposicion de capas.
        """
        disposicion = self.calcular_disposicion(superficie, escenario)
        superficie.fill(self.COLOR_FONDO)
        celdas = self._dibujar_terrenos(superficie, escenario, disposicion)
        if resultado_busqueda is not None and resultado_busqueda.exito and resultado_busqueda.camino:
            self._dibujar_camino(superficie, resultado_busqueda.camino, celdas, disposicion.tamano_celda)
        self._dibujar_bases(superficie, escenario, celdas, disposicion.tamano_celda)
        if estado.portador_recurso is None and estado.posicion_recurso is not None:
            self._dibujar_recurso(superficie, celdas[estado.posicion_recurso], disposicion.tamano_celda)
        self._dibujar_unidades(superficie, estado, celdas, disposicion.tamano_celda)
        self._dibujar_cuadricula(superficie, escenario, disposicion)
        self._dibujar_panel(superficie, escenario, estado, resultado_busqueda, disposicion.panel)
        return disposicion

    def _dibujar_terrenos(
        self,
        superficie: pygame.Surface,
        escenario: Escenario,
        disposicion: DisposicionTablero,
    ) -> dict[Posicion, pygame.Rect]:
        """Dibuja cada terreno y marca visualmente los no transitables.

        Purpose: crear la capa base desde el catalogo real de terrenos del escenario.
        Preconditions: la disposicion corresponde al escenario y cabe en la superficie.
        Postconditions: devuelve el rectangulo de cada posicion y no modifica el escenario.
        Complexity: O(F*C) temporal y espacial por el indice de rectangulos.
        AI usage: Yes.
        AI intervention: Codex implemento el recorrido generico y la marca diagonal de obstaculos para E9.1.
        Student validation: pendiente de revision del equipo; cubierta por pruebas de colores y transitabilidad.
        """
        celdas: dict[Posicion, pygame.Rect] = {}
        lado = disposicion.tamano_celda
        grosor = max(1, lado // 10)
        for fila in range(escenario.filas):
            for columna in range(escenario.columnas):
                posicion = Posicion(fila, columna)
                nombre = escenario.terreno[fila][columna]
                tipo = escenario.obtener_tipo_terreno(posicion)
                rectangulo = pygame.Rect(
                    disposicion.tablero.x + columna * lado,
                    disposicion.tablero.y + fila * lado,
                    lado,
                    lado,
                )
                pygame.draw.rect(superficie, self.color_para_terreno(nombre, tipo), rectangulo)
                if not tipo.transitable:
                    pygame.draw.line(
                        superficie, self.COLOR_OBSTACULO, rectangulo.topleft, rectangulo.bottomright, grosor
                    )
                    pygame.draw.line(
                        superficie, self.COLOR_OBSTACULO, rectangulo.topright, rectangulo.bottomleft, grosor
                    )
                celdas[posicion] = rectangulo
        return celdas

    def _dibujar_camino(
        self,
        superficie: pygame.Surface,
        camino: tuple[Posicion, ...],
        celdas: dict[Posicion, pygame.Rect],
        lado: int,
    ) -> None:
        """Traza en orden el camino calculado y diferencia sus extremos.

        Purpose: convertir las posiciones ya calculadas en una linea visual sin recalcular ni corregir la ruta.
        Preconditions: cada posicion de ``camino`` pertenece a ``celdas`` y conserva el orden del resultado.
        Postconditions: los centros se conectan en el mismo orden; origen y destino quedan marcados y los datos de
        entrada permanecen sin modificaciones.
        Complexity: O(L) temporal y espacial por los L centros del camino.
        AI usage: Yes.
        AI intervention: Codex diseño e implemento para E9.2 la linea adaptable y los marcadores de extremos.
        Student validation: pendiente de revision y validacion visual manual del equipo; cubierta por pruebas
        automatizadas que comparan los centros trazados con ``ResultadoBusqueda.camino``.
        """
        centros = [celdas[posicion].center for posicion in camino]
        grosor_borde = max(3, lado // 4)
        grosor_linea = max(1, lado // 8)
        if len(centros) > 1:
            pygame.draw.lines(superficie, self.COLOR_OBSTACULO, False, centros, grosor_borde)
            pygame.draw.lines(superficie, self.COLOR_CAMINO, False, centros, grosor_linea)
        else:
            pygame.draw.circle(superficie, self.COLOR_CAMINO, centros[0], max(2, lado // 10))

        radio = max(4, lado // 2 - 3)
        grosor_marcador = max(2, lado // 12)
        pygame.draw.circle(superficie, self.COLOR_ORIGEN, centros[0], radio, grosor_marcador)
        pygame.draw.circle(superficie, self.COLOR_DESTINO, centros[-1], radio, grosor_marcador)

    def _dibujar_bases(
        self,
        superficie: pygame.Surface,
        escenario: Escenario,
        celdas: dict[Posicion, pygame.Rect],
        lado: int,
    ) -> None:
        """Superpone el contorno e identidad de ambas bases sin cubrir el contenido posterior.

        Purpose: mantener visibles Base A y Base B incluso cuando una unidad ocupa su celda.
        Preconditions: las bases del escenario existen en ``celdas``.
        Postconditions: cada base queda identificada mediante borde y etiqueta; no altera datos del dominio.
        Complexity: O(B) temporal y O(1) espacial, donde B es la cantidad de bases.
        AI usage: Yes.
        AI intervention: Codex diseño la capa de bordes persistentes y etiquetas para E9.1.
        Student validation: pendiente de revision del equipo; cubierta por pruebas de bases y superposicion.
        """
        for bando, posicion in escenario.bases.items():
            rectangulo = celdas[posicion]
            color = self.COLOR_BASES.get(bando, self.COLOR_TEXTO)
            pygame.draw.rect(superficie, color, rectangulo.inflate(-2, -2), max(2, lado // 8))
            self._dibujar_texto(superficie, f"B{bando}", color, rectangulo.topleft, self._fuente_pequena)

    def _dibujar_recurso(self, superficie: pygame.Surface, rectangulo: pygame.Rect, lado: int) -> None:
        """Dibuja un recurso libre como rombo central identificado.

        Purpose: mostrar el recurso solo cuando el estado declara que no tiene portador.
        Preconditions: ``rectangulo`` representa la posicion vigente del recurso libre.
        Postconditions: queda un simbolo dorado visible sin modificar el estado.
        Complexity: O(1) temporal y espacial.
        AI usage: Yes.
        AI intervention: Codex definio el simbolo de recurso libre para E9.1.
        Student validation: pendiente de revision del equipo; cubierta por pruebas de recurso libre y transportado.
        """
        centro = rectangulo.center
        radio = max(3, lado // 4)
        puntos = [
            (centro[0], centro[1] - radio),
            (centro[0] + radio, centro[1]),
            (centro[0], centro[1] + radio),
            (centro[0] - radio, centro[1]),
        ]
        pygame.draw.polygon(superficie, self.COLOR_RECURSO, puntos)
        self._dibujar_texto_centrado(superficie, "R", self.COLOR_OBSTACULO, rectangulo, self._fuente_pequena)

    def _dibujar_unidades(
        self,
        superficie: pygame.Surface,
        estado: EstadoJuego,
        celdas: dict[Posicion, pygame.Rect],
        lado: int,
    ) -> None:
        """Dibuja todas las unidades y agrega una insignia al portador.

        Purpose: representar posiciones, bandos, identificadores y posesion del recurso desde ``EstadoJuego``.
        Preconditions: cada unidad ocupa una posicion incluida en ``celdas``.
        Postconditions: todas las unidades quedan visibles y solo el portador recibe la insignia dorada.
        Complexity: O(U) temporal y O(1) espacial adicional.
        AI usage: Yes.
        AI intervention: Codex implemento circulos por bando, etiquetas e insignia de portador para E9.1.
        Student validation: pendiente de revision del equipo; cubierta por pruebas de bandos, cambios y portador.
        """
        for unidad in estado.unidades:
            rectangulo = celdas[unidad.posicion]
            color = self.COLOR_BASES.get(unidad.bando, self.COLOR_TEXTO)
            radio = max(3, lado // 3)
            pygame.draw.circle(superficie, color, rectangulo.center, radio)
            pygame.draw.circle(superficie, self.COLOR_TEXTO, rectangulo.center, radio, max(1, lado // 18))
            etiqueta = unidad.identificador if lado >= 22 else unidad.bando
            self._dibujar_texto_centrado(superficie, etiqueta, self.COLOR_TEXTO, rectangulo, self._fuente_unidad)
            if unidad.identificador == estado.portador_recurso:
                radio_insignia = max(3, lado // 7)
                centro_insignia = (rectangulo.right - radio_insignia - 2, rectangulo.top + radio_insignia + 2)
                pygame.draw.circle(superficie, self.COLOR_RECURSO, centro_insignia, radio_insignia)
                pygame.draw.circle(superficie, self.COLOR_OBSTACULO, centro_insignia, radio_insignia, 1)

    def _dibujar_cuadricula(
        self,
        superficie: pygame.Surface,
        escenario: Escenario,
        disposicion: DisposicionTablero,
    ) -> None:
        """Traza limites de filas y columnas sobre las capas de contenido.

        Purpose: conservar la lectura espacial de la cuadricula completa.
        Preconditions: la disposicion corresponde a las dimensiones del escenario.
        Postconditions: todas las celdas quedan delimitadas sin modificar el modelo.
        Complexity: O(F+C) temporal y O(1) espacial.
        AI usage: Yes.
        AI intervention: Codex implemento las lineas dimensionadas para E9.1.
        Student validation: pendiente de revision del equipo; cubierta por pruebas de dimensiones variables.
        """
        lado = disposicion.tamano_celda
        for fila in range(escenario.filas + 1):
            y = disposicion.tablero.y + fila * lado
            pygame.draw.line(
                superficie,
                self.COLOR_CUADRICULA,
                (disposicion.tablero.x, y),
                (disposicion.tablero.right, y),
            )
        for columna in range(escenario.columnas + 1):
            x = disposicion.tablero.x + columna * lado
            pygame.draw.line(
                superficie,
                self.COLOR_CUADRICULA,
                (x, disposicion.tablero.y),
                (x, disposicion.tablero.bottom),
            )

    def _dibujar_panel(
        self,
        superficie: pygame.Surface,
        escenario: Escenario,
        estado: EstadoJuego,
        resultado_busqueda: ResultadoBusqueda | None,
        panel: pygame.Rect,
    ) -> None:
        """Presenta turno y leyenda de terrenos y simbolos usados.

        Purpose: explicar la codificacion visual y destacar el bando activo sin duplicar el turno.
        Preconditions: el panel pertenece a la superficie y el estado contiene el turno vigente.
        Postconditions: se muestran turno, terrenos, obstaculos, bases, recurso y portador; cuando existe un
        resultado tambien se muestran algoritmo, exito y la leyenda del camino, siempre que haya espacio.
        Complexity: O(T) temporal y O(1) espacial adicional, donde T es la cantidad de terrenos.
        AI usage: Yes.
        AI intervention: Codex implemento el panel de E9.1 y agrego en E9.2 el estado minimo de la busqueda y la
        leyenda coherente con sus marcadores.
        Student validation: pendiente de revision y validacion visual manual del equipo; cubierta por pruebas de
        turno, resultado y leyenda.
        """
        if panel.width <= 0 or panel.height <= 0:
            return
        pygame.draw.rect(superficie, self.COLOR_PANEL, panel, border_radius=6)
        x = panel.x + 12
        y = panel.y + 12
        color_turno = self.COLOR_BASES.get(estado.turno_actual, self.COLOR_TEXTO)
        y = (
            self._dibujar_texto(
                superficie,
                f"Turno actual: {estado.turno_actual}",
                color_turno,
                (x, y),
                self._fuente,
            )
            + 12
        )
        if resultado_busqueda is not None:
            estado_busqueda = "exito" if resultado_busqueda.exito else "sin solucion"
            y = self._dibujar_texto(
                superficie,
                f"Busqueda: {resultado_busqueda.algoritmo}",
                self.COLOR_TEXTO,
                (x, y),
                self._fuente_pequena,
            ) + 2
            y = self._dibujar_texto(
                superficie,
                f"Estado: {estado_busqueda}",
                self.COLOR_TEXTO,
                (x, y),
                self._fuente_pequena,
            ) + 4
            if resultado_busqueda.exito:
                muestras = (
                    (self.COLOR_CAMINO, "camino"),
                    (self.COLOR_ORIGEN, "origen"),
                    (self.COLOR_DESTINO, "destino"),
                )
                for color, etiqueta in muestras:
                    pygame.draw.line(superficie, color, (x, y + 7), (x + 14, y + 7), 3)
                    y = self._dibujar_texto(
                        superficie,
                        etiqueta,
                        self.COLOR_TEXTO,
                        (x + 22, y),
                        self._fuente_pequena,
                    ) + 2
            y += 6
        y = self._dibujar_texto(superficie, "Terrenos", self.COLOR_TEXTO, (x, y), self._fuente) + 6
        for nombre, tipo in escenario.tipos_terreno.items():
            if y + 18 > panel.bottom:
                break
            muestra = pygame.Rect(x, y + 2, 14, 14)
            pygame.draw.rect(superficie, self.color_para_terreno(nombre, tipo), muestra)
            if not tipo.transitable:
                pygame.draw.line(superficie, self.COLOR_OBSTACULO, muestra.topleft, muestra.bottomright, 2)
            sufijo = " (obstaculo)" if not tipo.transitable else ""
            y = (
                self._dibujar_texto(
                    superficie,
                    nombre + sufijo,
                    self.COLOR_TEXTO,
                    (x + 22, y),
                    self._fuente_pequena,
                )
                + 3
            )
        for texto in ("BA / BB: bases", "R: recurso libre", "Punto dorado: portador", "A azul / B rojo: unidades"):
            if y + 18 > panel.bottom:
                break
            y = self._dibujar_texto(superficie, texto, self.COLOR_TEXTO, (x, y), self._fuente_pequena) + 2

    @staticmethod
    def _dibujar_texto(
        superficie: pygame.Surface,
        texto: str,
        color: Color,
        posicion: tuple[int, int],
        fuente: pygame.font.Font,
    ) -> int:
        imagen = fuente.render(texto, True, color)
        superficie.blit(imagen, posicion)
        return posicion[1] + imagen.get_height()

    @staticmethod
    def _dibujar_texto_centrado(
        superficie: pygame.Surface,
        texto: str,
        color: Color,
        rectangulo: pygame.Rect,
        fuente: pygame.font.Font,
    ) -> None:
        imagen = fuente.render(texto, True, color)
        superficie.blit(imagen, imagen.get_rect(center=rectangulo.center))
