"""Genera la guía PDF y las capturas desde el renderizador Pygame actual.

Dependencias disponibles: pygame, Pillow y PyMuPDF. Las capturas usan los
controladores/renderizadores reales con SDL dummy y se identifican así en el PDF;
no se presentan como fotografías de una sesión manual.
Ejecución desde la raíz: PYTHONPATH=src python3 docs/entregables/generar_guia_rapida_tacticalgrid.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "src"))

import fitz
import pygame
from PIL import Image, ImageDraw, ImageFont

from tacticalgrid.interfaz.aplicacion import _procesar_evento
from tacticalgrid.interfaz.busquedas import ALGORITMOS
from tacticalgrid.interfaz.control import ControlGrafico
from tacticalgrid.interfaz.renderizador import EstadoPanelControl, RenderizadorTablero


SALIDA = RAIZ / "docs/entregables/guia-rapida-interfaz-tacticalgrid.pdf"
IMAGENES = RAIZ / "docs/entregables/imagenes-guia"
ANCHO, ALTO = 1400, 900
PW, PH = 595.28, 841.89
MARGEN = 42
CONTENIDO = PW - 2 * MARGEN
AZUL, CIAN, TINTA, GRIS = "173B63", "138EAA", "203247", "58697B"
CLARO, BLANCO = "EAF1F7", "FFFFFF"
FUENTE, NEGRITA = fitz.Font("helv"), fitz.Font("hebo")


def _rgb(color: str) -> tuple[float, float, float]:
    return tuple(int(color[i:i + 2], 16) / 255 for i in (0, 2, 4))


def _capturar(control: ControlGrafico, nombre: str, *, numerar: bool = False) -> Path:
    superficie = pygame.Surface((ANCHO, ALTO))
    render = RenderizadorTablero()
    disposicion = render.renderizar(
        superficie,
        control.escenario,
        control.estado,
        control.resultado,
        exploracion_visible=control.exploracion_visible,
        control=EstadoPanelControl.desde_control(control),
    )
    ruta = IMAGENES / nombre
    pygame.image.save(superficie, ruta)
    if numerar:
        _numerar(ruta, control, disposicion, render)
    return ruta


def _numerar(ruta: Path, control: ControlGrafico, disposicion, render: RenderizadorTablero) -> None:
    imagen = Image.open(ruta).convert("RGB")
    dibujo = ImageDraw.Draw(imagen)
    try:
        fuente = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 17)
    except OSError:
        fuente = ImageFont.load_default()
    rects = render.calcular_rectangulos_controles(disposicion.panel)
    centros = {
        1: (disposicion.tablero.x + 24, disposicion.tablero.y + 24),
        2: (disposicion.panel.x - 5, rects.escenario_anterior.centery),
        3: (disposicion.panel.x - 5, rects.algoritmo_anterior.centery),
        4: (disposicion.panel.x - 5, rects.unidad_anterior.centery),
        5: (disposicion.panel.x - 5, rects.ejecutar.centery),
        6: (disposicion.panel.x - 5, disposicion.panel.y + 560),
        7: (disposicion.panel.x - 5, disposicion.panel.y + 440),
        8: (disposicion.panel.x - 5, disposicion.panel.y + 680),
    }
    for numero, (x, y) in centros.items():
        r = 14
        dibujo.ellipse((x-r, y-r, x+r, y+r), fill=f"#{CIAN}", outline="white", width=3)
        caja = dibujo.textbbox((0, 0), str(numero), font=fuente)
        dibujo.text((x-(caja[2]-caja[0])/2, y-(caja[3]-caja[1])/2-caja[1]), str(numero), fill="white", font=fuente)
    imagen.save(ruta)


def _clic(control: ControlGrafico, posicion: tuple[int, int]) -> None:
    superficie = pygame.Surface((ANCHO, ALTO))
    render = RenderizadorTablero()
    disposicion = render.calcular_disposicion(superficie, control.escenario)
    rects = render.calcular_rectangulos_controles(disposicion.panel)
    fila, columna = posicion
    punto = (
        disposicion.tablero.x + columna * disposicion.tamano_celda + disposicion.tamano_celda // 2,
        disposicion.tablero.y + fila * disposicion.tamano_celda + disposicion.tamano_celda // 2,
    )
    _procesar_evento(
        control,
        pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"button": 1, "pos": punto}),
        disposicion,
        rects,
    )


def _tecla(control: ControlGrafico, tecla: int) -> None:
    superficie = pygame.Surface((ANCHO, ALTO))
    render = RenderizadorTablero()
    disposicion = render.calcular_disposicion(superficie, control.escenario)
    rects = render.calcular_rectangulos_controles(disposicion.panel)
    _procesar_evento(control, pygame.event.Event(pygame.KEYDOWN, {"key": tecla}), disposicion, rects)


def _capturas() -> dict[str, Path]:
    IMAGENES.mkdir(parents=True, exist_ok=True)
    pygame.init()
    pygame.display.set_mode((1, 1))
    rutas = tuple(sorted((RAIZ / "escenarios").glob("*.json")))
    imgs: dict[str, Path] = {}

    rb = RAIZ / "escenarios/ruta_corta_vs_economica.json"
    busqueda = ControlGrafico.crear(rb, rutas)
    busqueda.cambiar_algoritmo(ALGORITMOS.index("ucs") - ALGORITMOS.index(busqueda.algoritmo))
    if busqueda.objetivo is None:
        raise RuntimeError("Falta el objetivo del escenario de búsqueda.")
    _clic(busqueda, (busqueda.objetivo.fila, busqueda.objetivo.columna))
    _tecla(busqueda, pygame.K_RETURN)
    if not busqueda.resultado or not busqueda.resultado.exito:
        raise RuntimeError("No se obtuvo una ruta real para la captura.")
    _tecla(busqueda, pygame.K_e)
    layout_busqueda = RenderizadorTablero().calcular_disposicion(pygame.Surface((ANCHO, ALTO)), busqueda.escenario)
    imgs["general_sin_marcas"] = _capturar(busqueda, "interfaz-busqueda-pygame.png")
    imgs["general"] = _capturar(busqueda, "interfaz-busqueda-anotada.png", numerar=True)
    imgs["controles_zoom"] = IMAGENES / "busqueda-controles-ampliados.png"
    Image.open(imgs["general_sin_marcas"]).crop((layout_busqueda.panel.x, 15, 1395, 340)).save(imgs["controles_zoom"])
    busqueda.verificar()
    imgs["metricas"] = _capturar(busqueda, "busqueda-metricas.png")
    layout_busqueda = RenderizadorTablero().calcular_disposicion(pygame.Surface((ANCHO, ALTO)), busqueda.escenario)
    imgs["metricas_zoom"] = IMAGENES / "busqueda-metricas-ampliadas.png"
    Image.open(imgs["metricas"]).crop((layout_busqueda.panel.x, 465, 1395, 635)).save(imgs["metricas_zoom"])

    rp = RAIZ / "escenarios/prueba_gui_partida.json"
    partida = ControlGrafico.crear(rp, rutas)
    portadora = next(u for u in partida.estado.unidades if u.identificador == "portadora")
    _clic(partida, (portadora.posicion.fila, portadora.posicion.columna))
    imgs["carga"] = _capturar(partida, "escenario-cargado-partida.png")
    imgs["partida"] = _capturar(partida, "partida-unidad-activa.png")

    secuencia = (
        ("portadora", (0, 2)),
        ("defensa B-1", (3, 0)),
        ("portadora", (0, 1)),
        ("defensa B-1", (2, 0)),
        ("portadora", (0, 0)),
    )
    for id_unidad, destino in secuencia:
        unidad = next(u for u in partida.estado.unidades if u.identificador == id_unidad)
        _clic(partida, (unidad.posicion.fila, unidad.posicion.columna))
        _clic(partida, destino)
    if partida.estado.estado_partida != "victoria_A":
        raise RuntimeError(f"La secuencia comprobada no llegó a victoria_A: {partida.estado.estado_partida}")
    partida.verificar()
    imgs["victoria"] = _capturar(partida, "partida-victoria-a.png")
    imgs["victoria_panel"] = IMAGENES / "partida-victoria-panel.png"
    layout_partida = RenderizadorTablero().calcular_disposicion(pygame.Surface((ANCHO, ALTO)), partida.escenario)
    Image.open(imgs["victoria"]).crop((layout_partida.panel.x, 280, 1395, 620)).save(imgs["victoria_panel"])

    ra = RAIZ / "escenarios/decision_adversarial.json"
    adversarial = ControlGrafico.crear(ra, rutas)
    _tecla(adversarial, pygame.K_q)
    if adversarial.resultado_adversarial is None:
        raise RuntimeError("La evaluación adversarial no produjo recomendación.")
    _tecla(adversarial, pygame.K_e)
    _tecla(adversarial, pygame.K_v)
    imgs["adversarial"] = _capturar(adversarial, "adversarial-minimax-alfa-beta.png")
    imgs["adversarial_zoom"] = IMAGENES / "adversarial-panel-ampliado.png"
    layout_adversarial = RenderizadorTablero().calcular_disposicion(pygame.Surface((ANCHO, ALTO)), adversarial.escenario)
    Image.open(imgs["adversarial"]).crop((layout_adversarial.panel.x, 300, 1395, 640)).save(imgs["adversarial_zoom"])
    pygame.quit()
    return imgs


def _wrap(texto: str, ancho: float, tamano: float, negrita: bool = False) -> list[str]:
    fuente = NEGRITA if negrita else FUENTE
    linea = ""
    salida = []
    for palabra in texto.replace("`", "").split():
        nuevo = palabra if not linea else f"{linea} {palabra}"
        if fuente.text_length(nuevo, fontsize=tamano) <= ancho:
            linea = nuevo
        else:
            if linea:
                salida.append(linea)
            linea = palabra
    if linea:
        salida.append(linea)
    return salida or [""]


def _pagina(doc: fitz.Document):
    p = doc.new_page(width=PW, height=PH)
    p.draw_rect(p.rect, color=_rgb(BLANCO), fill=_rgb(BLANCO))
    p.insert_text((MARGEN, 24), "TACTICALGRID  |  GUÍA RÁPIDA DE LA INTERFAZ", fontname="hebo", fontsize=7.2, color=_rgb(GRIS))
    p.draw_line((MARGEN, 33), (PW-MARGEN, 33), color=_rgb("D7E1EA"), width=0.7)
    return p


def _parrafo(p, text: str, y: float, *, x: float = MARGEN, ancho: float = CONTENIDO, size: float = 9.2, color: str = TINTA, bold: bool = False, lead: float | None = None) -> float:
    font = "hebo" if bold else "helv"
    lead = lead or size * 1.38
    for line in _wrap(text, ancho, size, bold):
        y += size
        p.insert_text((x, y), line, fontname=font, fontsize=size, color=_rgb(color))
        y += lead-size
    return y + 2


def _titulo(p, text: str, subtitle: str | None = None) -> float:
    p.insert_text((MARGEN, 58), text, fontname="hebo", fontsize=17.5, color=_rgb(AZUL))
    y = 70
    if subtitle:
        y = _parrafo(p, subtitle, y, size=8.8, color=GRIS)
    return y + 4


def _pasos(p, items: list[str], y: float, *, x: float = MARGEN, width: float = CONTENIDO, start: int = 1) -> float:
    for n, text in enumerate(items, start=start):
        cx = x + 8
        p.draw_circle((cx, y + 8), 7.5, color=_rgb(CIAN), fill=_rgb(CIAN))
        p.insert_text((cx-2.3, y+10.8), str(n), fontname="hebo", fontsize=7.5, color=_rgb(BLANCO))
        y = _parrafo(p, text, y, x=x+22, ancho=width-22, size=8.7, lead=11.3) + 1
    return y


def _tabla(p, rows: list[list[str]], widths: list[float], y: float, *, size: float = 8.1, x0: float = MARGEN) -> float:
    heights, cell_lines = [], []
    for i, row in enumerate(rows):
        lines = [_wrap(value, widths[j]-12, size if i else size-0.1, i == 0) for j, value in enumerate(row)]
        cell_lines.append(lines)
        heights.append(max(map(len, lines)) * size * 1.25 + 9)
    for i, row in enumerate(rows):
        h = heights[i]
        fill = AZUL if i == 0 else ("F0F5F9" if i % 2 == 0 else BLANCO)
        p.draw_rect((x0, y, x0+sum(widths), y+h), color=_rgb("D8E1E8"), fill=_rgb(fill), width=0.45)
        x = x0
        for j, _ in enumerate(row):
            if j:
                p.draw_line((x, y), (x, y+h), color=_rgb("D8E1E8"), width=0.45)
            baseline = y + 12
            for line in cell_lines[i][j]:
                p.insert_text((x+6, baseline), line, fontname=("hebo" if i == 0 else "helv"), fontsize=size, color=_rgb(BLANCO if i == 0 else TINTA))
                baseline += size*1.25
            x += widths[j]
        y += h
    return y + 5


def _imagen(p, ruta: Path, rect: fitz.Rect) -> None:
    p.draw_rect(rect, color=_rgb("CFD9E2"), fill=_rgb("F4F7F9"), width=0.7)
    im = Image.open(ruta)
    scale = min((rect.width-6)/im.width, (rect.height-6)/im.height)
    w, h = im.width*scale, im.height*scale
    box = fitz.Rect(rect.x0+(rect.width-w)/2, rect.y0+(rect.height-h)/2, rect.x0+(rect.width+w)/2, rect.y0+(rect.height+h)/2)
    p.insert_image(box, filename=str(ruta), keep_proportion=True)


def _caption(p, text: str, y: float, *, x: float = MARGEN, width: float = CONTENIDO) -> float:
    for line in _wrap(text, width, 7.0):
        length = FUENTE.text_length(line, fontsize=7.0)
        p.insert_text((x+(width-length)/2, y+8), line, fontname="heit", fontsize=7.0, color=_rgb(GRIS))
        y += 10
    return y + 2


def _crear_pdf(imgs: dict[str, Path]) -> None:
    doc = fitz.open()
    doc.set_metadata({"title": "TacticalGrid - Guía rápida de la interfaz", "author": "Sistemas Inteligentes I"})

    # 1. Presentación.
    p = _pagina(doc)
    p.insert_text((MARGEN, 91), "TacticalGrid", fontname="hebo", fontsize=30, color=_rgb(AZUL))
    p.insert_text((MARGEN, 122), "Guía rápida de la interfaz", fontname="hebo", fontsize=19, color=_rgb(CIAN))
    p.insert_text((MARGEN, 147), "Sistemas Inteligentes I - Ingeniería de Sistemas y Computación", fontname="helv", fontsize=10, color=_rgb(GRIS))
    y = _parrafo(p, "TacticalGrid es un juego táctico por turnos que permite experimentar con algoritmos de búsqueda y toma de decisiones sobre escenarios configurables.", 164)
    y = _parrafo(p, "Aprende a cargar escenarios, ejecutar algoritmos, jugar partidas y verificar resultados.", y)
    _imagen(p, imgs["general"], fitz.Rect(MARGEN, y+7, PW-MARGEN, y+339))
    _caption(p, "Búsqueda con ruta UCS y exploración. Render automatizado con Pygame y SDL dummy; no es una foto de sesión manual.", y+341)
    p.draw_rect((MARGEN, 664, PW-MARGEN, 722), color=_rgb("D6E4EF"), fill=_rgb(CLARO), width=0.6)
    _parrafo(p, "Para comenzar: activa el entorno del proyecto y ejecuta python main.py desde la carpeta raíz.", 681, x=MARGEN+12, ancho=CONTENIDO-24, size=9.6, color=AZUL, bold=True)
    _parrafo(p, "Las capturas conservan el tablero, los controles y los datos del controlador real; la numeración se añadió solo como ayuda visual.", 735, size=8.2, color=GRIS)

    # 2. Interfaz anotada.
    p = _pagina(doc)
    y = _titulo(p, "1. Conociendo la interfaz", "El tablero ocupa la izquierda; las opciones y los resultados, la derecha.")
    _imagen(p, imgs["general"], fitz.Rect(MARGEN, y, MARGEN+334, y+216))
    _imagen(p, imgs["controles_zoom"], fitz.Rect(MARGEN+346, y, PW-MARGEN, y+216))
    y = _caption(p, "Vista completa numerada y ampliación de controles. Render automatizado Pygame/SDL dummy.", y+218)
    y = _tabla(p, [
        ["N.º", "Zona", "Qué muestra"],
        ["1", "Tablero", "Terrenos, obstáculos, bases, unidades, recurso y ruta."],
        ["2-4", "Selectores", "Escenario, algoritmo y unidad; usa < y >."],
        ["5", "Ejecución", "Operaciones disponibles para el modo activo."],
        ["6", "Resultados", "Longitud, costo, estados y tiempo."],
        ["7", "Turno", "Bando actual; en Partida también portador y estado."],
        ["8", "Terrenos", "Transitabilidad y costo según la leyenda."],
    ], [36, 86, CONTENIDO-122], y, size=7.9)
    _parrafo(p, "El camino es cian; origen verde; destino rojo; exploración violeta. Bases A/B: azul/rojo. Recurso y portador: dorado.", y, size=8.4)

    # 3. Carga de JSON y búsqueda.
    p = _pagina(doc)
    y = _titulo(p, "2. Cargar un escenario y buscar", "El JSON define mapa, terrenos, unidades, bases y recurso.")
    y = _pasos(p, [
        "Abre con python main.py o ejecuta python main.py --gui escenarios/ruta_corta_vs_economica.json desde la raíz.",
        "Para reemplazar el mapa, pulsa O - Abrir JSON y elige un archivo .json; también puedes arrastrarlo a la ventana.",
        "Comprueba el nombre en Escenario. Una carga inválida muestra el mensaje y conserva el mapa vigente.",
    ], y)
    _imagen(p, imgs["carga"], fitz.Rect(MARGEN, y, PW-MARGEN, y+298))
    y = _caption(p, "prueba_gui_partida.json cargado y una unidad seleccionada. Render automatizado con SDL dummy.", y+300)
    p.insert_text((MARGEN, y+13), "Ejecutar una búsqueda", fontname="hebo", fontsize=11, color=_rgb(CIAN))
    _pasos(p, [
        "Pulsa M hasta Búsqueda; elige unidad y algoritmo con < y >.",
        "Haz clic en una celda transitable para fijar el objetivo. El panel indica sus coordenadas.",
        "Pulsa Enter o Enter - Ejecutar búsqueda. Observa la ruta cian.",
        "Pulsa E para mostrar u ocultar la exploración disponible.",
    ], y+20)

    # 4. Algoritmos y métricas.
    p = _pagina(doc)
    y = _titulo(p, "3. Algoritmos y métricas", "Cambia la selección con los botones < y > de la fila Algoritmo.")
    y = _tabla(p, [
        ["Algoritmo", "Función principal"],
        ["BFS", "Busca una ruta con mínimo número de movimientos."],
        ["DFS", "Explora una alternativa en profundidad; no garantiza la ruta más corta."],
        ["UCS", "Minimiza el costo acumulado del terreno."],
        ["A*", "Combina el costo recorrido con una estimación hacia el objetivo."],
        ["Beam Search", "Limita las alternativas conservadas por nivel mediante k."],
    ], [105, CONTENIDO-105], y)
    y = _parrafo(p, "En A*, cambia Heurística A* entre Manhattan y HTO con < y >. En Beam, la fila Beam k cambia k en una unidad por clic.", y, size=8.5)
    _imagen(p, imgs["metricas_zoom"], fitz.Rect(MARGEN, y+7, MARGEN+250, y+207))
    p.insert_text((MARGEN+262, y+21), "Lectura de métricas", fontname="hebo", fontsize=10.5, color=_rgb(CIAN))
    end_table = _tabla(p, [
        ["Dato", "Significado"],
        ["Éxito", "Se encontró ruta."],
        ["Longitud", "Cantidad de movimientos."],
        ["Costo", "Suma del costo del terreno."],
        ["Estados generados", "Añadidos a la frontera."],
        ["Estados expandidos", "Procesados para continuar."],
        ["Máximo de frontera", "Mayor cantidad pendiente."],
        ["Tiempo", "Duración en segundos."],
    ], [110, 118], y+27, size=7.4, x0=MARGEN+262)
    _caption(p, "Ampliación del panel: valores de una ejecución real de UCS.", y+210, width=250)
    _parrafo(p, "En ruta_corta_vs_economica.json, BFS obtiene 8 movimientos y costo 50; UCS rodea el pantano con 12 movimientos y costo 12. Una ruta más corta no siempre es la más económica.", max(end_table, y+225)+9, size=8.6, color=AZUL, bold=True)

    # 5. Partida por turnos.
    p = _pagina(doc)
    y = _titulo(p, "4. Jugar una partida por turnos", "La secuencia del ejemplo se validó con el fixture gráfico.")
    _imagen(p, imgs["partida"], fitz.Rect(MARGEN, y, PW-MARGEN, y+296))
    y = _caption(p, "Unidad de A seleccionada; los destinos legales aparecen resaltados. Render automatizado Pygame/SDL dummy.", y+298)
    y = _pasos(p, [
        "Pulsa M hasta Partida e identifica el bando activo.",
        "Selecciona una unidad propia con un clic o con < y > en Unidad activa.",
        "Haz clic en un destino resaltado. Después de actuar, el turno pasa al otro bando.",
        "Al entrar en la celda del recurso, la unidad lo recoge y lo transporta.",
        "Lleva el portador a la base propia para ganar. El panel informa victoria o empate por bloqueo.",
    ], y)
    y = _parrafo(p, "Secuencia comprobada: portadora A recoge en (0,2); defensa B-1 mueve a (3,0); A vuelve a (0,1); B avanza a (2,0); A entrega en (0,0). Resultado: victoria_A.", y, size=8.0, color=GRIS)
    _imagen(p, imgs["victoria_panel"], fitz.Rect(MARGEN, y+3, MARGEN+248, y+183))
    _caption(p, "Panel final: victoria A y 5 acciones verificadas.", y+185, width=248)
    _parrafo(p, "El recurso aparece sobre la unidad portadora en la base A. El historial de la secuencia pasó la verificación de partida.", y+15, x=MARGEN+265, ancho=CONTENIDO-265, size=9.0, color=AZUL)

    # 6. Decisión adversarial.
    p = _pagina(doc)
    y = _titulo(p, "5. Minimax, alfa-beta y verificación", "La recomendación no mueve unidades automáticamente.")
    _imagen(p, imgs["adversarial_zoom"], fitz.Rect(MARGEN, y, MARGEN+235, y+286))
    _caption(p, "Controles, recomendación, métricas y verificación reales en modo Adversarial.", y+288, width=235)
    _pasos(p, [
        "Pulsa M hasta Adversarial. Elige Minimax o alfa-beta con < y >.",
        "Configura Profundidad y Orden: generación, inverso o táctico.",
        "Pulsa Q o Enter para evaluar; consulta acción, valor, profundidad y nodos.",
        "Pulsa C o E para comparar ambos algoritmos con los mismos parámetros.",
        "Pulsa V - Verificar decisión para comprobar la recomendación.",
        "Para aplicarla, pulsa A y vuelve a confirmarla cuando el panel lo pida.",
    ], y+4, x=MARGEN+251, width=CONTENIDO-251)
    p.draw_rect((MARGEN, y+354, PW-MARGEN, y+414), color=_rgb("D6E4EF"), fill=_rgb(CLARO), width=0.7)
    _parrafo(p, "Una recomendación solo se ejecuta después de la confirmación explícita con A.", y+371, x=MARGEN+12, ancho=CONTENIDO-24, size=9.2, color=AZUL, bold=True)
    _parrafo(p, "V verifica la ruta en Búsqueda, el historial en Partida y la decisión en Adversarial. Si cambia el estado, vuelve a evaluar antes de verificar o exportar.", y+430, size=8.9)
    p.draw_rect((MARGEN, y+488, PW-MARGEN, y+586), color=_rgb("D8E1E8"), fill=_rgb("F4F7F9"), width=0.6)
    p.insert_text((MARGEN+12, y+510), "En el resultado verás", fontname="hebo", fontsize=10.2, color=_rgb(CIAN))
    _parrafo(p, "Bando evaluado, algoritmo, profundidad configurada y alcanzada, orden de acciones, recomendación y valor. La comparación también muestra nodos generados, evaluados y podados, además del tiempo.", y+519, x=MARGEN+12, ancho=CONTENIDO-24, size=8.7)

    # 7. Atajos y recomendaciones.
    p = _pagina(doc)
    y = _titulo(p, "6. Atajos y recomendaciones", "Las funciones dependen del modo activo.")
    y = _tabla(p, [
        ["Control", "Acción comprobada"],
        ["O", "Abre selector JSON; también se acepta arrastrar y soltar."],
        ["M", "Recorre Búsqueda, Partida y Adversarial."],
        ["< y >", "Botones del mouse para cambiar opciones; no son flechas del teclado."],
        ["Enter", "Ejecuta búsqueda; en Adversarial evalúa la decisión."],
        ["E", "Búsqueda: exploración. Adversarial: comparación."],
        ["V", "Verifica búsqueda, partida o decisión según el modo."],
        ["J", "Abre selector para guardar un registro reproducible en la ubicación elegida."],
        ["Q / C / A", "Adversarial: evaluar / comparar / solicitar y confirmar aplicación."],
        ["R", "Partida: reinicia estado e historial manual."],
        ["Clic en tablero", "Búsqueda: fija objetivo. Partida: selecciona unidad o destino legal."],
    ], [100, CONTENIDO-100], y, size=7.9)
    p.insert_text((MARGEN, y+17), "Consejos de uso", fontname="hebo", fontsize=10.5, color=_rgb(CIAN))
    y = _pasos(p, [
        "Confirma el modo y el bando activo antes de una acción.",
        "Compara longitud y costo: BFS prioriza movimientos; UCS prioriza el costo.",
        "Usa V para comprobar resultados y J para guardar registros reproducibles.",
    ], y+25)
    p.draw_line((MARGEN, y+7), (PW-MARGEN, y+7), color=_rgb("D7E1EA"), width=0.7)
    _parrafo(p, "Más información: README del proyecto y Manual de usuario: docs/entregables/manual-de-usuario.docx.", y+17, size=8.5, color=AZUL, bold=True)

    for i, p in enumerate(doc, start=1):
        p.draw_line((MARGEN, 814), (PW-MARGEN, 814), color=_rgb("D7E1EA"), width=0.7)
        p.insert_text((PW-MARGEN-63, 829), f"Sistemas Inteligentes I  |  {i} / 7", fontname="helv", fontsize=7.1, color=_rgb(GRIS))
    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    doc.save(SALIDA, garbage=4, deflate=True)
    doc.close()


def main() -> None:
    imgs = _capturas()
    _crear_pdf(imgs)
    print(f"PDF: {SALIDA}")
    print(f"Capturas: {IMAGENES}")


if __name__ == "__main__":
    main()
