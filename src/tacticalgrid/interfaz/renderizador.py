"""Renderizado Pygame del escenario y del estado dinámico de TacticalGrid."""

from dataclasses import dataclass
from hashlib import sha256
from textwrap import wrap

import pygame

from tacticalgrid.algoritmos.resultado_busqueda import ResultadoBusqueda
from tacticalgrid.escenario.escenario import Escenario, Posicion
from tacticalgrid.escenario.terreno import TipoTerreno
from tacticalgrid.interfaz.recursos import RecursosGraficos
from tacticalgrid.juego.accion import INTERCEPTAR
from tacticalgrid.juego.estado import EstadoJuego


Color = tuple[int, int, int]


@dataclass(frozen=True)
class DisposicionTablero:
    """Geometría calculada para ubicar el tablero y su panel informativo."""

    tablero: pygame.Rect
    panel: pygame.Rect
    tamano_celda: int


@dataclass(frozen=True)
class EstadoPanelControl:
    """Datos mínimos que el renderizador necesita para dibujar los controles sin ejecutar acciones."""

    escenario: str
    algoritmo: str
    unidad: str
    origen: Posicion | None
    objetivo: Posicion | None
    k: int
    estado_busqueda: str
    ayuda_descripcion: tuple[str, ...]
    criterio: str
    detalle: str | None
    mensaje: str
    error: bool
    modo: str = "busqueda"
    unidad_partida: str | None = None
    tipo_unidad_partida: str | None = None
    cantidad_acciones: int = 0
    jugadas_registradas: int = 0
    estado_partida: str = "en_curso"
    destinos_legales: tuple[tuple[Posicion, str], ...] = ()
    posicion_unidad_partida: Posicion | None = None
    algoritmo_adversarial: str = "MINIMAX"
    profundidad_adversarial: int = 1
    orden_adversarial: str = "generacion"
    decision_lineas: tuple[str, ...] = ()
    decision_verificada: str | None = None
    recomendacion_aplicable: bool = False
    confirmar_aplicacion: bool = False
    busquedas_comparables: tuple[str, ...] = ()
    heuristica_astar: str = "manhattan"

    @classmethod
    def desde_control(cls, control) -> "EstadoPanelControl":
        """Proyectar el controlador mutable a datos inmutables de presentación."""
        unidad_partida = control.unidad_partida_actual
        return cls(
            escenario=control.ruta_escenario.name,
            algoritmo=control.algoritmo,
            unidad=control.unidad or "sin unidades",
            origen=control.origen,
            objetivo=control.objetivo,
            k=control.k,
            estado_busqueda=control.estado_busqueda,
            ayuda_descripcion=control.ayuda_algoritmo.descripcion,
            criterio=control.ayuda_algoritmo.criterio,
            detalle=control.ayuda_algoritmo.detalle,
            mensaje=control.mensaje,
            error=control.error,
            modo=control.modo,
            unidad_partida=control.unidad_partida,
            tipo_unidad_partida=(unidad_partida.tipo if unidad_partida else None),
            cantidad_acciones=len(control.acciones_partida),
            jugadas_registradas=len(control.historial_partida),
            estado_partida=control.estado.estado_partida,
            destinos_legales=tuple((accion.destino, accion.tipo) for accion in control.acciones_partida),
            posicion_unidad_partida=(unidad_partida.posicion if unidad_partida else None),
            algoritmo_adversarial=control.algoritmo_adversarial,
            profundidad_adversarial=control.profundidad_adversarial,
            orden_adversarial=control.orden_adversarial,
            decision_lineas=_lineas_decision(control),
            decision_verificada=(
                "válida" if control.verificacion and control.verificacion.es_valido else
                "inválida" if control.verificacion else None
            ),
            recomendacion_aplicable=(
                control.resultado_adversarial is not None
                and control.resultado_adversarial.accion_seleccionada is not None
            ),
            confirmar_aplicacion=control.aplicar_confirmacion_pendiente,
            busquedas_comparables=tuple(
                linea
                for etiqueta, resultado in control.historial_busquedas[-2:-1]
                for linea in (
                    f"{etiqueta}: éxito {'sí' if resultado.exito else 'no'}; longitud exacta {resultado.longitud}; "
                    f"costo {resultado.costo if resultado.costo is not None else '—'}",
                    f"Estados generados: {resultado.estados_generados}; estados expandidos: {resultado.estados_expandidos}",
                    f"Máximo de frontera: {resultado.maximo_frontera}; tiempo: {resultado.tiempo_segundos:.6f} s",
                )
            ),
            heuristica_astar=control.heuristica_astar,
        )


def _lineas_decision(control) -> tuple[str, ...]:
    """Preparar los textos de métricas exclusivamente a partir de los resultados adversariales almacenados.

    Proposito: exponer en el panel las métricas reportadas por Minimax y alfa-beta sin recalcular decisiones.
    Precondiciones: ``control`` tiene los campos de resultado definidos por ``ControlGrafico``.
    Postcondiciones: se devuelven líneas con el algoritmo, el bando, las profundidades, la acción, el valor, los nodos y
    el tiempo; en una comparación se presentan las mediciones de ambas ejecuciones. El controlador no cambia.
    Complejidad: O(L) temporal y espacial para la longitud total de los textos generados.
    Uso de IA: Si.
    Intervencion de IA: Codex: presentación de métricas adversariales comparables en el panel Pygame.
    Validacion del estudiante: prueba ``test_panel_presenta_metricas_decision_y_estado_de_confirmacion`` de
    tests/interfaz/test_renderizador.py.
    """
    resultado = control.resultado_adversarial
    if resultado is None:
        return ()
    comparacion = control.comparacion_adversarial
    if comparacion is not None:
        lineas_comparacion = [
            f"Bando evaluado: {resultado.bando_max} | Profundidad configurada: {resultado.profundidad_maxima} "
            f"| Orden: {resultado.orden_acciones}"
        ]
        for etiqueta, medicion in (("Minimax", comparacion.minimax), ("Alfa-beta", comparacion.alfa_beta)):
            seleccion = medicion.accion_seleccionada
            accion_texto = "ninguna" if seleccion is None else (
                f"{seleccion.accion.identificador_unidad} ({seleccion.accion.origen.fila},{seleccion.accion.origen.columna})"
                f" → ({seleccion.accion.destino.fila},{seleccion.accion.destino.columna})"
            )
            lineas_comparacion.extend(
                (
                    f"{etiqueta}: profundidad alcanzada {medicion.profundidad_alcanzada}; "
                    f"acción seleccionada {accion_texto}; valor obtenido {medicion.valor:.6g}",
                    f"{etiqueta}: nodos generados {medicion.nodos_generados}; nodos evaluados "
                    f"{medicion.nodos_evaluados}; nodos podados {medicion.nodos_podados}; "
                    f"tiempo {medicion.tiempo_segundos:.6f} s",
                )
            )
        lineas_comparacion.append(
            f"Comparación: misma acción {comparacion.misma_accion}; mismo valor {comparacion.mismo_valor}"
        )
        return tuple(lineas_comparacion)
    accion = resultado.accion_seleccionada
    descripcion = "sin acción legal" if accion is None else (
        f"{accion.accion.identificador_unidad}: {accion.accion.tipo} "
        f"({accion.accion.origen.fila},{accion.accion.origen.columna}) → "
        f"({accion.accion.destino.fila},{accion.accion.destino.columna})"
    )
    lineas = [
        f"Algoritmo: {resultado.algoritmo} | Bando evaluado: {resultado.bando_max}",
        f"Profundidad configurada: {resultado.profundidad_maxima}",
        f"Profundidad alcanzada: {resultado.profundidad_alcanzada}",
        f"Acción seleccionada: {descripcion}",
        f"Valor obtenido: {resultado.valor:.6g}",
        f"Nodos generados: {resultado.nodos_generados}",
        f"Nodos evaluados: {resultado.nodos_evaluados}",
        f"Nodos podados: {resultado.nodos_podados}",
        f"Tiempo: {resultado.tiempo_segundos:.6f} s | Orden: {resultado.orden_acciones}",
    ]
    return tuple(lineas)


@dataclass(frozen=True)
class RectangulosControles:
    """Zonas clicables calculadas a partir del panel vigente."""

    escenario_anterior: pygame.Rect
    escenario_siguiente: pygame.Rect
    algoritmo_anterior: pygame.Rect
    algoritmo_siguiente: pygame.Rect
    unidad_anterior: pygame.Rect
    unidad_siguiente: pygame.Rect
    k_menor: pygame.Rect
    k_mayor: pygame.Rect
    ejecutar: pygame.Rect
    exploracion: pygame.Rect
    abrir: pygame.Rect
    verificar: pygame.Rect
    modo: pygame.Rect
    aplicar: pygame.Rect


class RenderizadorTablero:
    """Compositor de una vista completa que no modifica el escenario ni el estado."""

    COLOR_FONDO: Color = (20, 25, 29)
    COLOR_PANEL: Color = (31, 39, 43)
    COLOR_PANEL_BORDE: Color = (75, 88, 86)
    COLOR_TEXTO: Color = (235, 232, 216)
    COLOR_CUADRICULA: Color = (48, 55, 52)
    COLOR_OBSTACULO: Color = (20, 22, 25)
    COLOR_BASES: dict[str, Color] = {"A": (38, 117, 191), "B": (190, 68, 68)}
    COLOR_RECURSO: Color = (244, 196, 48)
    COLOR_CAMINO: Color = (22, 224, 238)
    COLOR_ORIGEN: Color = (68, 220, 112)
    COLOR_DESTINO: Color = (255, 112, 82)
    COLOR_EXPLORACION: Color = (176, 92, 255)
    COLOR_BOTON: Color = (48, 63, 67)
    COLOR_BOTON_BORDE: Color = (100, 131, 133)
    ALFA_EXPLORACION = 92
    ANCHO_PANEL = 272
    MARGEN = 16

    def __init__(self, recursos: RecursosGraficos | None = None) -> None:
        """Preparar las fuentes reutilizables y los recursos gráficos del tablero.

        Proposito: inicializar las fuentes y el proveedor en caché de recursos gráficos exclusivos de la interfaz.
        Precondiciones: Pygame está importado; no se requiere una ventana activa.
        Postcondiciones: la instancia dispone de fuentes y atlas; el dominio no cambia.
        Complejidad: O(P) temporal y espacial por los píxeles de los atlas cuando no se inyecta un proveedor existente.
        Uso de IA: Si.
        Intervencion de IA: Codex: ampliación de la inicialización de E9.1 con un proveedor de PNG inyectable y en
        caché.
        Validacion del estudiante: pruebas de tests/interfaz/test_renderizador.py ejecutadas sin pantalla (SDL dummy).
        """
        if not pygame.font.get_init():
            pygame.font.init()
        self._fuente = pygame.font.Font(None, 22)
        self._fuente_pequena = pygame.font.Font(None, 17)
        self._fuente_unidad = pygame.font.Font(None, 18)
        self.recursos = recursos or RecursosGraficos()

    def calcular_disposicion(self, superficie: pygame.Surface, escenario: Escenario) -> DisposicionTablero:
        """Calcular una cuadrícula centrada y un panel lateral según las dimensiones disponibles.

        Proposito: adaptar el tablero a cualquier cantidad válida de filas y columnas sin coordenadas de mapa fijas.
        Precondiciones: ``superficie`` tiene dimensiones positivas y ``escenario`` tiene filas y columnas positivas.
        Postcondiciones: se devuelven celdas cuadradas de al menos un píxel, contenidas en la superficie.
        Complejidad: O(1) temporal y espacial.
        Uso de IA: Si.
        Intervencion de IA: Codex: ajuste proporcional y reserva del panel informativo (E9.1).
        Validacion del estudiante: pruebas ``test_renderiza_escenario_20x20_con_cuadricula_completa`` y
        ``test_ajusta_mapa_rectangular_y_dimensiones_variables_sin_coordenadas_fijas`` de
        tests/interfaz/test_renderizador.py.
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

    def calcular_rectangulos_controles(self, panel: pygame.Rect) -> RectangulosControles:
        """Calcular controles compactos dentro del panel lateral.

        Proposito: compartir exactamente las mismas zonas entre el dibujo y el manejo de clics.
        Precondiciones: ``panel`` se calculó para la superficie vigente.
        Postcondiciones: se devuelven rectángulos contenidos horizontalmente en el panel; el panel no cambia.
        Complejidad: O(1) temporal y espacial.
        Uso de IA: Si.
        Intervencion de IA: Codex: zonas compactas para integrar controles sin invadir el tablero y botón de
        verificación. Claude (Opus 5.5): botón para abrir un escenario JSON en la fila del título (E9.4).
        Validacion del estudiante: prueba ``test_boton_abrir_json_esta_en_la_fila_del_titulo_sin_tapar_otros_controles``
        de tests/interfaz/test_renderizador.py y pruebas de eventos de tests/interfaz/test_aplicacion.py, incluidas la
        apertura y la verificación.
        """
        x = panel.x + 12
        ancho = max(1, panel.width - 24)
        lado = 24
        ancho_abrir = min(104, ancho)

        def flechas(y: int) -> tuple[pygame.Rect, pygame.Rect]:
            return pygame.Rect(x, y, lado, 22), pygame.Rect(x + ancho - lado, y, lado, 22)

        modo = pygame.Rect(x, panel.y + 38, ancho, 22)
        escenario_anterior, escenario_siguiente = flechas(panel.y + 70)
        algoritmo_anterior, algoritmo_siguiente = flechas(panel.y + 102)
        unidad_anterior, unidad_siguiente = flechas(panel.y + 134)
        k_menor, k_mayor = flechas(panel.y + 166)
        return RectangulosControles(
            escenario_anterior,
            escenario_siguiente,
            algoritmo_anterior,
            algoritmo_siguiente,
            unidad_anterior,
            unidad_siguiente,
            k_menor,
            k_mayor,
            pygame.Rect(x, panel.y + 196, ancho, 26),
            pygame.Rect(x, panel.y + 228, ancho, 24),
            pygame.Rect(x + ancho - ancho_abrir, panel.y + 8, ancho_abrir, 22),
            pygame.Rect(x, panel.y + 258, ancho, 24),
            modo,
            pygame.Rect(x, panel.y + 290, ancho, 24),
        )

    def color_para_terreno(self, nombre: str, tipo: TipoTerreno) -> Color:
        """Derivar un color estable para cualquier nombre de terreno cargado.

        Proposito: diferenciar terrenos conocidos o externos sin mantener un catálogo codificado en la interfaz.
        Precondiciones: ``nombre`` no está vacío y ``tipo`` pertenece al catálogo validado del escenario.
        Postcondiciones: se devuelve siempre el mismo color RGB para el mismo nombre y la misma transitabilidad.
        Complejidad: O(L) temporal y O(1) espacial, con L la longitud UTF-8 del nombre.
        Uso de IA: Si.
        Intervencion de IA: Codex: paleta determinista basada en SHA-256 y tono neutro para los obstáculos.
        Validacion del estudiante: pruebas ``test_diferencia_tipos_de_terreno_y_marca_no_transitable`` y
        ``test_admite_tipo_externo_con_color_determinista_y_leyenda_visible`` de tests/interfaz/test_renderizador.py.
        """
        resumen = sha256(nombre.encode("utf-8")).digest()
        if tipo.transitable:
            return (80 + resumen[0] % 116, 80 + resumen[1] % 116, 80 + resumen[2] % 116)
        nivel = 42 + resumen[0] % 22
        return (nivel + 5, nivel + 2, nivel)

    def renderizar(
        self,
        superficie: pygame.Surface,
        escenario: Escenario,
        estado: EstadoJuego,
        resultado_busqueda: ResultadoBusqueda | None = None,
        *,
        exploracion_visible: bool = False,
        control: EstadoPanelControl | None = None,
    ) -> DisposicionTablero:
        """Dibujar el tablero completo y su información vigente sobre una superficie Pygame.

        Proposito: representar terrenos, exploración, objetivo, camino, entidades, controles, turno y leyenda.
        Precondiciones: ``escenario`` está validado y ``estado`` es coherente con el escenario.
        Postcondiciones: la superficie refleja el estado, las acciones legales de la partida y, si se solicita, la
        proyección de la traza; el escenario, el estado y el resultado no cambian.
        Complejidad: O(F*C + U + T + L + P) temporal y O(F*C + L + lado^2) espacial, con L posiciones del camino y P
        posiciones expandidas únicas almacenadas.
        Uso de IA: Si.
        Intervencion de IA: Codex: E9.1 y E9.2, rediseño con sprites y capa de E9.3 sin cambiar el camino.
        Validacion del estudiante: pruebas de tests/interfaz/test_renderizador.py: segundo renderizado sin retener el
        estado anterior, camino de cada algoritmo trazado en orden, renderizado sin modificar el resultado ni el estado
        y exploración que conserva camino y entidades.
        """
        disposicion = self.calcular_disposicion(superficie, escenario)
        superficie.fill(self.COLOR_FONDO)
        celdas = self._dibujar_terrenos(superficie, escenario, disposicion)
        if (
            exploracion_visible
            and resultado_busqueda is not None
            and resultado_busqueda.traza_expansiones is not None
        ):
            self._dibujar_exploracion(
                superficie,
                resultado_busqueda.traza_expansiones.posiciones_unicas,
                celdas,
                disposicion.tamano_celda,
            )
        if control is not None and control.objetivo is not None and control.objetivo in celdas:
            pygame.draw.rect(
                superficie,
                self.COLOR_RECURSO,
                celdas[control.objetivo].inflate(-4, -4),
                max(2, disposicion.tamano_celda // 10),
            )
        if resultado_busqueda is not None and resultado_busqueda.exito and resultado_busqueda.camino:
            self._dibujar_camino(superficie, resultado_busqueda.camino, celdas, disposicion.tamano_celda)
        self._dibujar_bases(superficie, escenario, celdas, disposicion.tamano_celda)
        if estado.portador_recurso is None and estado.posicion_recurso is not None:
            self._dibujar_recurso(superficie, celdas[estado.posicion_recurso], disposicion.tamano_celda)
        self._dibujar_unidades(superficie, estado, celdas, disposicion.tamano_celda)
        if control is not None:
            self._dibujar_acciones_legales(superficie, control, celdas, disposicion.tamano_celda)
        self._dibujar_cuadricula(superficie, escenario, disposicion)
        self._dibujar_panel(
            superficie,
            escenario,
            estado,
            resultado_busqueda,
            disposicion.panel,
            exploracion_visible,
            control,
        )
        return disposicion

    def _dibujar_exploracion(
        self,
        superficie: pygame.Surface,
        posiciones: tuple[Posicion, ...],
        celdas: dict[Posicion, pygame.Rect],
        lado: int,
    ) -> None:
        """Superponer las posiciones proyectadas de las expansiones reales.

        Proposito: distinguir la exploración del camino mediante una capa semitransparente adaptable a la celda.
        Precondiciones: cada posición procede de la traza asociada al mismo escenario representado por ``celdas``.
        Postcondiciones: solo se resaltan las posiciones observadas; los tiles y los datos de entrada no cambian.
        Complejidad: O(P) temporal y O(lado^2) espacial, con P posiciones únicas almacenadas.
        Uso de IA: Si.
        Intervencion de IA: Codex: capa visual bajo demanda (E9.3).
        Validacion del estudiante: pruebas ``test_exploracion_proyecta_eventos_reales_y_conserva_camino_y_entidades`` y
        ``test_fracaso_con_traza_permite_mostrar_exploracion_y_panel`` de tests/interfaz/test_renderizador.py.
        """
        capa = pygame.Surface((lado, lado), pygame.SRCALPHA)
        capa.fill((*self.COLOR_EXPLORACION, self.ALFA_EXPLORACION))
        grosor = max(1, lado // 12)
        for posicion in posiciones:
            rectangulo = celdas.get(posicion)
            if rectangulo is None:
                continue
            superficie.blit(capa, rectangulo)
            pygame.draw.rect(superficie, self.COLOR_EXPLORACION, rectangulo.inflate(-2, -2), grosor)

    def _dibujar_terrenos(
        self,
        superficie: pygame.Surface,
        escenario: Escenario,
        disposicion: DisposicionTablero,
    ) -> dict[Posicion, pygame.Rect]:
        """Dibujar cada terreno y marcar visualmente los no transitables.

        Proposito: crear la capa base a partir del catálogo real de terrenos del escenario.
        Precondiciones: la disposición corresponde al escenario y cabe en la superficie.
        Postcondiciones: se devuelve el rectángulo de cada posición; el escenario no cambia.
        Complejidad: O(F*C) temporal y espacial por el índice de rectángulos.
        Uso de IA: Si.
        Intervencion de IA: Codex: tiles variados, obstáculos físicos y respaldo genérico sobre el recorrido original de
        E9.1.
        Validacion del estudiante: prueba ``test_diferencia_tipos_de_terreno_y_marca_no_transitable`` de
        tests/interfaz/test_renderizador.py.
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
                color_respaldo = self.color_para_terreno(nombre, tipo)
                pygame.draw.rect(superficie, color_respaldo, rectangulo)
                variante = self._variante_visual(nombre, posicion)
                tile = self.recursos.terreno(nombre, lado, variante)
                if tile is not None:
                    superficie.blit(tile, rectangulo)
                else:
                    self._dibujar_textura_respaldo(superficie, rectangulo, nombre, tipo, variante)
                if not tipo.transitable:
                    obstaculo = self.recursos.objeto("obstaculo", max(1, lado - 2))
                    if obstaculo is not None:
                        superficie.blit(obstaculo, obstaculo.get_rect(center=rectangulo.center))
                    else:
                        pygame.draw.line(
                            superficie, self.COLOR_OBSTACULO, rectangulo.topleft, rectangulo.bottomright, grosor
                        )
                        pygame.draw.line(
                            superficie, self.COLOR_OBSTACULO, rectangulo.topright, rectangulo.bottomleft, grosor
                        )
                celdas[posicion] = rectangulo
        return celdas

    @staticmethod
    def _variante_visual(nombre: str, posicion: Posicion) -> int:
        """Derivar una variante local estable sin usar el generador aleatorio global.

        Proposito: distribuir los reflejos de textura de forma repetible entre celdas del mismo terreno.
        Precondiciones: el nombre y la posición proceden del escenario validado.
        Postcondiciones: se devuelve un entero entre 0 y 3, estable para la misma entrada.
        Complejidad: O(L) temporal y O(1) espacial por el nombre codificado.
        Uso de IA: Si.
        Intervencion de IA: Codex: variación visual mediante SHA-256 y coordenadas.
        Validacion del estudiante: prueba ``test_variacion_visual_es_determinista_y_no_muta_estado`` de
        tests/interfaz/test_renderizador.py.
        """
        datos = f"{nombre}:{posicion.fila}:{posicion.columna}".encode("utf-8")
        return sha256(datos).digest()[0] % 4

    def _dibujar_textura_respaldo(
        self,
        superficie: pygame.Surface,
        rectangulo: pygame.Rect,
        nombre: str,
        tipo: TipoTerreno,
        variante: int,
    ) -> None:
        """Agregar detalle determinista a terrenos externos o a atlas ausentes.

        Proposito: conservar la identidad, la transitabilidad y la legibilidad cuando no existe un sprite específico.
        Precondiciones: el rectángulo ya tiene el color estable del terreno.
        Postcondiciones: la celda recibe marcas visibles sin alterar el escenario ni atribuirle otra semántica.
        Complejidad: O(1) temporal y espacial.
        Uso de IA: Si.
        Intervencion de IA: Codex: patrón de respaldo determinista y neutral.
        Validacion del estudiante: pruebas ``test_admite_tipo_externo_con_color_determinista_y_leyenda_visible`` y
        ``test_fallback_visible_si_faltan_recursos`` de tests/interfaz/test_renderizador.py.
        """
        color = self.color_para_terreno(nombre, tipo)
        detalle = tuple(max(0, componente - 28) for componente in color)
        radio = max(1, rectangulo.width // 14)
        desplazamientos = ((1, 1), (3, 2), (2, 4))
        for x_factor, y_factor in desplazamientos:
            x = rectangulo.left + (rectangulo.width * (x_factor + variante) // 6) % max(1, rectangulo.width)
            y = rectangulo.top + (rectangulo.height * (y_factor + variante) // 6) % max(1, rectangulo.height)
            pygame.draw.circle(superficie, detalle, (x, y), radio)

    def _dibujar_camino(
        self,
        superficie: pygame.Surface,
        camino: tuple[Posicion, ...],
        celdas: dict[Posicion, pygame.Rect],
        lado: int,
    ) -> None:
        """Trazar en orden el camino calculado y diferenciar sus extremos.

        Proposito: convertir las posiciones ya calculadas en una línea visual sin recalcular ni corregir la ruta.
        Precondiciones: cada posición de ``camino`` pertenece a ``celdas`` y conserva el orden del resultado.
        Postcondiciones: los centros se conectan en el mismo orden; el origen y el destino quedan marcados y los datos
        de entrada no cambian.
        Complejidad: O(L) temporal y espacial por los L centros del camino.
        Uso de IA: Si.
        Intervencion de IA: Codex: diseño e implementación de la línea adaptable y de los marcadores de extremos (E9.2).
        Validacion del estudiante: pruebas de tests/interfaz/test_renderizador.py que comparan los centros trazados con
        ``ResultadoBusqueda.camino`` y comprueban que no se marcan celdas ajenas al camino.
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
        """Superponer el contorno y la identidad de ambas bases sin cubrir el contenido posterior.

        Proposito: mantener visibles la base A y la base B incluso cuando una unidad ocupa su celda.
        Precondiciones: las bases del escenario existen en ``celdas``.
        Postcondiciones: cada base queda identificada con borde y etiqueta; los datos del dominio no cambian.
        Complejidad: O(B) temporal y O(1) espacial, con B la cantidad de bases.
        Uso de IA: Si.
        Intervencion de IA: Codex: fortalezas por bando sin retirar el borde persistente de E9.1.
        Validacion del estudiante: pruebas ``test_identifica_bases_y_conserva_base_debajo_de_unidad`` y
        ``test_composicion_superpuesta_mantiene_base_unidad_identificador_y_portador`` de
        tests/interfaz/test_renderizador.py.
        """
        for bando, posicion in escenario.bases.items():
            rectangulo = celdas[posicion]
            color = self.COLOR_BASES.get(bando, self.COLOR_TEXTO)
            sprite = self.recursos.objeto(f"base_{bando.casefold()}", max(1, lado - 2))
            if sprite is not None:
                superficie.blit(sprite, sprite.get_rect(center=rectangulo.center))
            pygame.draw.rect(superficie, color, rectangulo.inflate(-2, -2), max(2, lado // 10))
            if lado >= 24:
                self._dibujar_texto(superficie, f"B{bando}", color, rectangulo.topleft, self._fuente_pequena)

    def _dibujar_recurso(self, superficie: pygame.Surface, rectangulo: pygame.Rect, lado: int) -> None:
        """Dibujar el cristal PNG del recurso libre con un contorno circular dorado.

        Proposito: mostrar el recurso solo cuando el estado declara que no tiene portador.
        Precondiciones: ``rectangulo`` representa la posición vigente del recurso libre.
        Postcondiciones: si el sprite está disponible, queda centrado; en todos los casos se dibuja su contorno circular
        dorado sin modificar el estado.
        Complejidad: O(1) temporal y espacial.
        Uso de IA: Si.
        Intervencion de IA: Codex: cristal PNG con contorno de contraste en lugar del símbolo abstracto de E9.1.
        Validacion del estudiante: pruebas ``test_muestra_recurso_libre_sin_duplicarlo_en_unidades`` y
        ``test_recurso_transportado_solo_aparece_como_insignia_del_portador`` de tests/interfaz/test_renderizador.py.
        """
        sprite = self.recursos.objeto("recurso", max(1, int(lado * 0.78)))
        if sprite is not None:
            superficie.blit(sprite, sprite.get_rect(center=rectangulo.center))
        centro = rectangulo.center
        radio = max(3, lado // 4)
        pygame.draw.circle(superficie, self.COLOR_RECURSO, centro, radio, max(1, lado // 14))

    def _dibujar_unidades(
        self,
        superficie: pygame.Surface,
        estado: EstadoJuego,
        celdas: dict[Posicion, pygame.Rect],
        lado: int,
    ) -> None:
        """Dibujar todas las unidades y agregar una insignia al portador.

        Proposito: representar posiciones, bandos, identificadores y posesión del recurso a partir de ``EstadoJuego``.
        Precondiciones: cada unidad ocupa una posición incluida en ``celdas``.
        Postcondiciones: todas las unidades quedan visibles y solo el portador recibe la insignia dorada.
        Complejidad: O(U) temporal y O(1) espacial adicional.
        Uso de IA: Si.
        Intervencion de IA: Codex: sprites por bando, etiquetas con fondo e insignia de cristal para el portador, sobre
        la semántica de E9.1.
        Validacion del estudiante: pruebas ``test_dibuja_unidades_de_ambos_bandos_con_identidad_distinta`` y
        ``test_recurso_transportado_solo_aparece_como_insignia_del_portador`` de tests/interfaz/test_renderizador.py.
        """
        for unidad in estado.unidades:
            rectangulo = celdas[unidad.posicion]
            color = self.COLOR_BASES.get(unidad.bando, self.COLOR_TEXTO)
            sprite = self.recursos.objeto(f"unidad_{unidad.bando.casefold()}", max(1, int(lado * 0.82)))
            if sprite is not None:
                superficie.blit(sprite, sprite.get_rect(center=rectangulo.center))
            radio = max(3, lado // 3)
            pygame.draw.circle(superficie, color, rectangulo.center, radio, max(1, lado // 14))
            etiqueta = unidad.identificador if lado >= 22 else unidad.bando
            etiqueta_imagen = self._fuente_unidad.render(etiqueta, True, self.COLOR_TEXTO)
            fondo_etiqueta = etiqueta_imagen.get_rect(midbottom=(rectangulo.centerx, rectangulo.bottom - 2)).inflate(4, 1)
            pygame.draw.rect(superficie, self.COLOR_OBSTACULO, fondo_etiqueta, border_radius=2)
            superficie.blit(etiqueta_imagen, etiqueta_imagen.get_rect(center=fondo_etiqueta.center))
            if unidad.identificador == estado.portador_recurso:
                radio_insignia = max(4, lado // 7)
                centro_insignia = (rectangulo.right - radio_insignia - 2, rectangulo.top + radio_insignia + 2)
                pygame.draw.circle(superficie, self.COLOR_RECURSO, centro_insignia, radio_insignia + 1)
                insignia = self.recursos.objeto("recurso", radio_insignia * 2)
                if insignia is not None:
                    superficie.blit(insignia, insignia.get_rect(center=centro_insignia))
                pygame.draw.circle(superficie, self.COLOR_OBSTACULO, centro_insignia, radio_insignia + 1, 1)

    def _dibujar_acciones_legales(
        self,
        superficie: pygame.Surface,
        control: EstadoPanelControl,
        celdas: dict[Posicion, pygame.Rect],
        lado: int,
    ) -> None:
        """Resaltar solo los destinos que el dominio ofrece para la unidad seleccionada.

        Proposito: mostrar las opciones legales antes de ejecutar un turno.
        Precondiciones: ``destinos_legales`` proviene del estado y del escenario renderizados.
        Postcondiciones: cada destino legal queda delineado; el tablero y el estado del juego no cambian.
        Complejidad: O(A) temporal y O(1) espacial adicional, para A acciones legales.
        Uso de IA: Si.
        Intervencion de IA: Codex: resaltado de las acciones de partida.
        Validacion del estudiante: prueba ``test_gui_juega_un_turno_con_clics_en_unidad_y_destino_legal`` de
        tests/interfaz/test_aplicacion.py bajo SDL dummy.
        """
        for posicion, tipo in control.destinos_legales:
            rectangulo = celdas.get(posicion)
            if rectangulo is None:
                continue
            color = self.COLOR_EXPLORACION if tipo == INTERCEPTAR else self.COLOR_ORIGEN
            pygame.draw.rect(superficie, color, rectangulo.inflate(-4, -4), max(2, lado // 12))
        if control.posicion_unidad_partida in celdas:
            pygame.draw.rect(
                superficie,
                self.COLOR_TEXTO,
                celdas[control.posicion_unidad_partida].inflate(-2, -2),
                max(2, lado // 9),
            )

    def _dibujar_cuadricula(
        self,
        superficie: pygame.Surface,
        escenario: Escenario,
        disposicion: DisposicionTablero,
    ) -> None:
        """Trazar los límites de filas y columnas sobre las capas de contenido.

        Proposito: conservar la lectura espacial de la cuadrícula completa.
        Precondiciones: la disposición corresponde a las dimensiones del escenario.
        Postcondiciones: todas las celdas quedan delimitadas; el modelo no cambia.
        Complejidad: O(F+C) temporal y O(1) espacial.
        Uso de IA: Si.
        Intervencion de IA: Codex: líneas dimensionadas (E9.1).
        Validacion del estudiante: pruebas ``test_renderiza_escenario_20x20_con_cuadricula_completa`` y
        ``test_ajusta_mapa_rectangular_y_dimensiones_variables_sin_coordenadas_fijas`` de
        tests/interfaz/test_renderizador.py.
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
        exploracion_visible: bool,
        control: EstadoPanelControl | None = None,
    ) -> None:
        """Presentar el turno y la leyenda de terrenos y símbolos usados.

        Proposito: explicar la codificación visual y destacar el bando activo sin duplicar el turno.
        Precondiciones: el panel pertenece a la superficie y el estado contiene el turno vigente.
        Postcondiciones: se muestran el turno o la terminalidad, el estado de la partida, los terrenos, las entidades y
        las ayudas; con un resultado, también el algoritmo, el éxito, el camino, la longitud, el costo, los contadores,
        el máximo de frontera y el tiempo.
        Complejidad: O(T) temporal y O(1) espacial adicional, con T la cantidad de terrenos.
        Uso de IA: Si.
        Intervencion de IA: Codex: conservación de los datos de E9.1 y E9.2 con jerarquía, muestras de tiles, textos y
        aviso de recursos ausentes; estado, métricas e instrucción de la capa de exploración (E9.3); métricas completas,
        comparación de búsquedas y resultados adversariales.
        Validacion del estudiante: pruebas de tests/interfaz/test_renderizador.py: turno actual, resultado sin solución
        informado en el panel, métricas completas de búsqueda y comparación, y métricas reales de cada algoritmo.
        """
        if panel.width <= 0 or panel.height <= 0:
            return
        pygame.draw.rect(superficie, self.COLOR_PANEL, panel, border_radius=8)
        pygame.draw.rect(superficie, self.COLOR_PANEL_BORDE, panel, 1, border_radius=8)
        x = panel.x + 12
        y = (
            self._dibujar_controles(superficie, panel, control, exploracion_visible)
            if control is not None
            else panel.y + 12
        )
        color_turno = self.COLOR_BASES.get(estado.turno_actual, self.COLOR_TEXTO)
        texto_turno = (
            f"Turno actual: {estado.turno_actual}"
            if control is None or control.modo != "partida" or estado.estado_partida == "en_curso"
            else "Partida finalizada"
        )
        y = (
            self._dibujar_texto(
                superficie,
                texto_turno,
                color_turno,
                (x, y),
                self._fuente,
            )
            + 12
        )
        if control is not None and control.modo == "partida":
            estado_partida = control.estado_partida.removeprefix("victoria_").replace(
                "empate_bloqueo", "empate por bloqueo"
            )
            if control.estado_partida.startswith("victoria_"):
                estado_partida = f"victoria del bando {estado_partida}"
            y = self._dibujar_texto(
                superficie,
                f"Partida: {estado_partida}",
                self.COLOR_TEXTO,
                (x, y),
                self._fuente_pequena,
            ) + 2
            detalle_turno = (
                f"Bando activo: {estado.turno_actual} | Portador: {estado.portador_recurso or 'ninguno'}"
                if estado.estado_partida == "en_curso"
                else f"Portador: {estado.portador_recurso or 'ninguno'}"
            )
            y = self._dibujar_texto(superficie, detalle_turno, self.COLOR_TEXTO, (x, y), self._fuente_pequena) + 4
        pygame.draw.line(superficie, self.COLOR_PANEL_BORDE, (x, y - 5), (panel.right - 12, y - 5))
        if resultado_busqueda is not None:
            y = self._dibujar_texto(
                superficie,
                f"Busqueda: {resultado_busqueda.algoritmo}",
                self.COLOR_TEXTO,
                (x, y),
                self._fuente_pequena,
            ) + 2
            y = self._dibujar_texto(
                superficie,
                f"Éxito: {'sí' if resultado_busqueda.exito else 'no'}",
                self.COLOR_TEXTO,
                (x, y),
                self._fuente_pequena,
            ) + 2
            y = self._dibujar_texto(
                superficie,
                f"Longitud exacta: {resultado_busqueda.longitud}",
                self.COLOR_TEXTO,
                (x, y),
                self._fuente_pequena,
            ) + 2
            costo = "no aplica" if resultado_busqueda.costo is None else f"{resultado_busqueda.costo:g}"
            y = self._dibujar_texto(
                superficie,
                f"Costo: {costo}",
                self.COLOR_TEXTO,
                (x, y),
                self._fuente_pequena,
            ) + 4
            y = self._dibujar_texto(
                superficie,
                f"Estados generados: {resultado_busqueda.estados_generados}",
                self.COLOR_TEXTO,
                (x, y),
                self._fuente_pequena,
            ) + 2
            y = self._dibujar_texto(
                superficie,
                f"Estados expandidos: {resultado_busqueda.estados_expandidos}",
                self.COLOR_TEXTO,
                (x, y),
                self._fuente_pequena,
            ) + 2
            y = self._dibujar_texto(
                superficie,
                f"Máximo de frontera: {resultado_busqueda.maximo_frontera}",
                self.COLOR_TEXTO,
                (x, y),
                self._fuente_pequena,
            ) + 2
            y = self._dibujar_texto(
                superficie,
                f"Tiempo: {resultado_busqueda.tiempo_segundos:.6f} s",
                self.COLOR_TEXTO,
                (x, y),
                self._fuente_pequena,
            ) + 4
            if resultado_busqueda.exito:
                pygame.draw.line(superficie, self.COLOR_CAMINO, (x, y + 7), (x + 14, y + 7), 3)
                y = self._dibujar_texto(
                    superficie,
                    "camino final (verde: origen; rojo: fin)",
                    self.COLOR_TEXTO,
                    (x + 22, y),
                    self._fuente_pequena,
                ) + 2
            traza = resultado_busqueda.traza_expansiones
            if traza is None:
                y = self._dibujar_texto(
                    superficie,
                    "Exploracion no disponible",
                    self.COLOR_TEXTO,
                    (x, y),
                    self._fuente_pequena,
                ) + 2
            else:
                if exploracion_visible:
                    y = self._dibujar_texto(
                        superficie,
                        "Exploracion visible (estados != posiciones)",
                        self.COLOR_EXPLORACION,
                        (x, y),
                        self._fuente_pequena,
                    ) + 2
                    y = self._dibujar_texto(
                        superficie,
                        f"Posiciones resaltadas: {len(traza.posiciones_unicas)}",
                        self.COLOR_TEXTO,
                        (x, y),
                        self._fuente_pequena,
                    ) + 2
                    if traza.truncada:
                        y = self._dibujar_texto(
                            superficie,
                            f"Traza parcial (limite: {traza.limite})",
                            self.COLOR_DESTINO,
                            (x, y),
                            self._fuente_pequena,
                        ) + 2
            y += 6
        if control is not None and control.modo == "busqueda" and control.busquedas_comparables:
            y = self._dibujar_texto(superficie, "Ejecución anterior para comparar", self.COLOR_TEXTO, (x, y), self._fuente) + 3
            for resumen in control.busquedas_comparables:
                for fragmento in wrap(resumen, width=37):
                    y = self._dibujar_texto(superficie, fragmento, self.COLOR_TEXTO, (x, y), self._fuente_pequena) + 1
        if control is None:
            traza_disponible = resultado_busqueda is not None and resultado_busqueda.traza_expansiones is not None
            texto_control = (
                "E — Ocultar exploracion"
                if exploracion_visible and traza_disponible
                else "E — Mostrar exploracion"
            )
            y = self._dibujar_texto(
                superficie, texto_control, self.COLOR_EXPLORACION, (x, y), self._fuente_pequena
            ) + 2
            y = self._dibujar_texto(
                superficie, "Resalta las posiciones exploradas", self.COLOR_TEXTO, (x, y), self._fuente_pequena
            ) + 1
            y = self._dibujar_texto(
                superficie, "durante la busqueda.", self.COLOR_TEXTO, (x, y), self._fuente_pequena
            ) + 2
            if resultado_busqueda is None:
                y = self._dibujar_texto(
                    superficie, "Requiere ejecutar una busqueda.", self.COLOR_DESTINO, (x, y), self._fuente_pequena
                ) + 2
            y += 6
        y = self._dibujar_texto(superficie, "Terrenos", self.COLOR_TEXTO, (x, y), self._fuente) + 6
        for nombre, tipo in escenario.tipos_terreno.items():
            if y + 18 > panel.bottom:
                break
            muestra = pygame.Rect(x, y + 2, 14, 14)
            pygame.draw.rect(superficie, self.color_para_terreno(nombre, tipo), muestra)
            tile = self.recursos.terreno(nombre, muestra.width, 0)
            if tile is not None:
                superficie.blit(tile, muestra)
            if not tipo.transitable:
                pygame.draw.line(superficie, self.COLOR_OBSTACULO, muestra.topleft, muestra.bottomright, 2)
            sufijo = " (obstaculo)" if not tipo.transitable else f" (costo {tipo.costo:g})"
            y = (
                self._dibujar_texto(
                    superficie,
                    nombre + sufijo,
                    self.COLOR_TEXTO,
                    (x + 22, y),
                    self._fuente_pequena,
                )
                + 1
            )
        for texto in ("Fortalezas A/B | Cristal: recurso", "Dorado: portador | Azul/rojo: unidades"):
            if y + 18 > panel.bottom:
                break
            y = self._dibujar_texto(superficie, texto, self.COLOR_TEXTO, (x, y), self._fuente_pequena) + 2
        if self.recursos.errores and y + 18 <= panel.bottom:
            self._dibujar_texto(
                superficie,
                "Recursos: fallback activo",
                self.COLOR_DESTINO,
                (x, y + 4),
                self._fuente_pequena,
            )

    def _dibujar_controles(
        self,
        superficie: pygame.Surface,
        panel: pygame.Rect,
        control: EstadoPanelControl,
        exploracion_visible: bool,
    ) -> int:
        """Dibujar los selectores, las acciones y la ayuda contextual de la sesión gráfica.

        Proposito: hacer operables desde Pygame los modos de búsqueda, partida manual y evaluación adversarial.
        Precondiciones: ``control`` representa el mismo escenario que el tablero y ``panel`` tiene ancho positivo.
        Postcondiciones: los botones coinciden con sus áreas sensibles y el resumen explica el modo, la selección y las
        opciones vigentes sin ejecutar acciones ni presentar resultados invalidados.
        Complejidad: O(L) temporal y espacial por renderizar textos de longitud total L.
        Uso de IA: Si.
        Intervencion de IA: Codex: controles, atajos, explicaciones y verificación de búsquedas; partida manual,
        ejecución y comparación adversarial, verificación y confirmación de acciones. Claude (Opus 5.5): botón "O —
        Abrir JSON" junto al título (E9.4).
        Validacion del estudiante: pruebas de tests/interfaz/test_renderizador.py: selectores, ayuda y objetivo sin
        ocultar el tablero, parámetro k solo con Beam y botón de abrir JSON en la fila del título.
        """
        rectangulos = self.calcular_rectangulos_controles(panel)
        x = panel.x + 12
        self._dibujar_texto(superficie, "TACTICALGRID", self.COLOR_TEXTO, (x, panel.y + 10), self._fuente)
        self._dibujar_boton(superficie, rectangulos.abrir, "O — Abrir JSON")
        modos = {"busqueda": "Búsqueda", "partida": "Partida", "adversarial": "Adversarial"}
        self._dibujar_boton(superficie, rectangulos.modo, f"M — Modo: {modos[control.modo]}")
        etiqueta_algoritmo = {"astar": "A*", "beam": "BEAM SEARCH"}.get(
            control.algoritmo, control.algoritmo.upper()
        )
        filas = [(rectangulos.escenario_anterior, rectangulos.escenario_siguiente, f"Escenario: {control.escenario[:18]}")]
        if control.modo == "busqueda":
            filas.append((rectangulos.algoritmo_anterior, rectangulos.algoritmo_siguiente, f"Algoritmo: {etiqueta_algoritmo}"))
            filas.append((rectangulos.unidad_anterior, rectangulos.unidad_siguiente, f"Unidad: {control.unidad}"))
        elif control.modo == "partida":
            unidad = control.unidad_partida or "elige unidad activa"
            tipo = f" ({control.tipo_unidad_partida})" if control.tipo_unidad_partida else ""
            filas.append((rectangulos.unidad_anterior, rectangulos.unidad_siguiente, f"Unidad activa: {unidad}{tipo}"))
        else:
            filas.append((rectangulos.algoritmo_anterior, rectangulos.algoritmo_siguiente, control.algoritmo_adversarial))
            filas.append((rectangulos.unidad_anterior, rectangulos.unidad_siguiente, f"Profundidad: {control.profundidad_adversarial}"))
            filas.append((rectangulos.k_menor, rectangulos.k_mayor, f"Orden: {control.orden_adversarial}"))
        if control.modo == "busqueda" and control.algoritmo == "beam":
            filas.append((rectangulos.k_menor, rectangulos.k_mayor, f"Beam k: {control.k}"))
        elif control.modo == "busqueda" and control.algoritmo == "astar":
            etiqueta_heuristica = "Manhattan" if control.heuristica_astar == "manhattan" else "HTO"
            filas.append((rectangulos.k_menor, rectangulos.k_mayor, f"Heurística A*: {etiqueta_heuristica}"))
        for anterior, siguiente, etiqueta in filas:
            self._dibujar_boton(superficie, anterior, "<")
            self._dibujar_boton(superficie, siguiente, ">")
            centro = pygame.Rect(
                anterior.right + 2,
                anterior.y,
                max(1, siguiente.left - anterior.right - 4),
                anterior.height,
            )
            self._dibujar_texto_centrado(superficie, etiqueta, self.COLOR_TEXTO, centro, self._fuente_pequena)
        if control.modo == "busqueda":
            self._dibujar_boton(superficie, rectangulos.ejecutar, "Enter — Ejecutar busqueda")
            texto_e = "E — Ocultar exploracion" if exploracion_visible else "E — Mostrar exploracion"
            self._dibujar_boton(superficie, rectangulos.exploracion, texto_e, self.COLOR_EXPLORACION)
            self._dibujar_boton(superficie, rectangulos.verificar, "V — Verificar busqueda")
            objetivo = (
                "sin seleccionar"
                if control.objetivo is None
                else f"{control.objetivo.fila}, {control.objetivo.columna}"
            )
            indicacion = f"Objetivo: {objetivo} | J: exportar registro"
        elif control.modo == "partida":
            self._dibujar_boton(superficie, rectangulos.verificar, "V — Verificar partida")
            self._dibujar_boton(superficie, rectangulos.exploracion, "R — Reiniciar partida")
            self._dibujar_texto_centrado(
                superficie,
                "Clic en una unidad activa para seleccionarla",
                self.COLOR_TEXTO,
                rectangulos.ejecutar,
                self._fuente_pequena,
            )
            indicacion = f"Acciones legales: {control.cantidad_acciones} | {control.jugadas_registradas} jugadas"
        elif control.modo == "adversarial":
            self._dibujar_boton(superficie, rectangulos.ejecutar, "Q — Evaluar")
            self._dibujar_boton(superficie, rectangulos.exploracion, "C — Comparar ambos")
            self._dibujar_boton(superficie, rectangulos.verificar, "V — Verificar decisión")
            self._dibujar_boton(
                superficie,
                rectangulos.aplicar,
                "A — Confirmar acción" if control.confirmar_aplicacion else "A — Aplicar recomendación",
                self.COLOR_DESTINO if control.confirmar_aplicacion else self.COLOR_TEXTO,
            )
            indicacion = "A: aplicar (2 clics) | J: exportar registro"
        else:
            indicacion = "El modo adversarial se integra en la fase siguiente."
        y = (
            rectangulos.aplicar.bottom + 5
            if control.modo == "adversarial"
            else rectangulos.verificar.bottom + 5
        )
        for linea in wrap(indicacion, width=36):
            y = self._dibujar_texto(superficie, linea, self.COLOR_TEXTO, (x, y), self._fuente_pequena) + 1
        if control.modo == "busqueda":
            origen = "sin unidad" if control.origen is None else f"{control.origen.fila}, {control.origen.columna}"
            y = self._dibujar_texto(
                superficie,
                f"Origen de {control.unidad}: {origen}",
                self.COLOR_TEXTO,
                (x, y),
                self._fuente_pequena,
            ) + 1
            for linea in control.ayuda_descripcion:
                y = self._dibujar_texto(superficie, linea, self.COLOR_TEXTO, (x, y), self._fuente_pequena) + 1
            y = self._dibujar_texto(
                superficie, f"Prioriza: {control.criterio}", self.COLOR_TEXTO, (x, y), self._fuente_pequena
            ) + 1
            if control.detalle is not None:
                y = self._dibujar_texto(superficie, control.detalle, self.COLOR_TEXTO, (x, y), self._fuente_pequena) + 1
            y = self._dibujar_texto(
                superficie,
                "Exploracion: posiciones analizadas",
                self.COLOR_TEXTO,
                (x, y + 2),
                self._fuente_pequena,
            ) + 1
            y = self._dibujar_texto(
                superficie,
                "antes de obtener el resultado.",
                self.COLOR_TEXTO,
                (x, y),
                self._fuente_pequena,
            ) + 1
        elif control.modo == "partida" and control.unidad_partida is not None:
            if control.posicion_unidad_partida is not None:
                posicion = control.posicion_unidad_partida
                y = self._dibujar_texto(
                    superficie,
                    f"Posición: {posicion.fila}, {posicion.columna}",
                    self.COLOR_TEXTO,
                    (x, y),
                    self._fuente_pequena,
                ) + 1
            y = self._dibujar_texto(
                superficie,
                "Destinos verdes: movimiento; violeta: intercepcion.",
                self.COLOR_TEXTO,
                (x, y),
                self._fuente_pequena,
            ) + 1
        elif control.modo == "adversarial":
            if control.decision_verificada is not None:
                y = self._dibujar_texto(
                    superficie,
                    f"Verificación: {control.decision_verificada}",
                    self.COLOR_ORIGEN if control.decision_verificada == "válida" else self.COLOR_DESTINO,
                    (x, y),
                    self._fuente_pequena,
                ) + 1
            for linea in control.decision_lineas:
                for fragmento in wrap(linea, width=37):
                    y = self._dibujar_texto(superficie, fragmento, self.COLOR_TEXTO, (x, y), self._fuente_pequena) + 1
        y = self._dibujar_texto(
            superficie,
            f"Estado: {control.estado_busqueda}",
            self.COLOR_EXPLORACION if not control.error else self.COLOR_DESTINO,
            (x, y + 2),
            self._fuente_pequena,
        ) + 1
        color_mensaje = self.COLOR_DESTINO if control.error else self.COLOR_TEXTO
        if control.error or control.estado_busqueda in (
            "sin ejecutar",
            "verificacion valida",
            "registro exportado",
            "exportacion cancelada",
        ) or control.modo != "busqueda":
            lineas_mensaje = wrap(control.mensaje, width=36)[:2]
            for linea in lineas_mensaje:
                y = self._dibujar_texto(superficie, linea, color_mensaje, (x, y), self._fuente_pequena)
        return y + 10

    def _dibujar_boton(
        self,
        superficie: pygame.Surface,
        rectangulo: pygame.Rect,
        texto: str,
        color_texto: Color | None = None,
    ) -> None:
        """Dibujar un botón coherente con el panel, sin asociarle comportamiento."""
        pygame.draw.rect(superficie, self.COLOR_BOTON, rectangulo, border_radius=4)
        pygame.draw.rect(superficie, self.COLOR_BOTON_BORDE, rectangulo, 1, border_radius=4)
        self._dibujar_texto_centrado(
            superficie,
            texto,
            color_texto or self.COLOR_TEXTO,
            rectangulo,
            self._fuente_pequena,
        )

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
