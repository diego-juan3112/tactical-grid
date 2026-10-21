"""Genera un resumen visual del funcionamiento de TacticalGrid.

Ejecución desde la raíz: python3 docs/entregables/generar_resumen_funcionamiento_tacticalgrid.py
Requiere PyMuPDF; reutiliza capturas reales del renderizador Pygame, generadas con SDL dummy.
"""

from pathlib import Path

import fitz


RAIZ = Path(__file__).resolve().parents[2]
IMAGENES = RAIZ / "docs/entregables/imagenes-guia"
SALIDA = RAIZ / "docs/entregables/resumen-funcionamiento-tacticalgrid.pdf"
PW, PH = 595.28, 841.89
M, W = 42, 511.28
AZUL, CIAN, TINTA, GRIS, CLARO = "173B63", "138EAA", "203247", "58697B", "EAF1F7"
FUENTE, NEGRITA = fitz.Font("helv"), fitz.Font("hebo")


def rgb(color):
    return tuple(int(color[i:i + 2], 16) / 255 for i in (0, 2, 4))


def envolver(texto, ancho, size, bold=False):
    fuente = NEGRITA if bold else FUENTE
    lineas, linea = [], ""
    for palabra in texto.split():
        nueva = palabra if not linea else f"{linea} {palabra}"
        if fuente.text_length(nueva, fontsize=size) <= ancho:
            linea = nueva
        else:
            if linea:
                lineas.append(linea)
            linea = palabra
    if linea:
        lineas.append(linea)
    return lineas or [""]


def pagina(doc, numero):
    p = doc.new_page(width=PW, height=PH)
    p.draw_rect(p.rect, color=rgb("FFFFFF"), fill=rgb("FFFFFF"))
    p.insert_text((M, 24), "TACTICALGRID  |  RESUMEN DE FUNCIONAMIENTO", fontname="hebo", fontsize=7.2, color=rgb(GRIS))
    p.draw_line((M, 33), (PW-M, 33), color=rgb("D7E1EA"), width=.7)
    p.draw_line((M, 814), (PW-M, 814), color=rgb("D7E1EA"), width=.6)
    p.insert_text((PW-M-20, 829), str(numero), fontname="helv", fontsize=8, color=rgb(GRIS))
    return p


def parrafo(p, text, y, *, x=M, ancho=W, size=9, color=TINTA, bold=False, lead=None):
    font = "hebo" if bold else "helv"
    lead = lead or size * 1.38
    for line in envolver(text, ancho, size, bold):
        y += size
        p.insert_text((x, y), line, fontname=font, fontsize=size, color=rgb(color))
        y += lead-size
    return y + 2


def titulo(p, text, subtitle=None):
    p.insert_text((M, 59), text, fontname="hebo", fontsize=18, color=rgb(AZUL))
    y = 72
    if subtitle:
        y = parrafo(p, subtitle, y, size=8.8, color=GRIS)
    return y + 5


def pasos(p, items, y, *, start=1, size=8.7):
    for n, item in enumerate(items, start):
        cx = M + 8
        p.draw_circle((cx, y + 8), 7.5, color=rgb(CIAN), fill=rgb(CIAN))
        p.insert_text((cx-2.4, y+10.8), str(n), fontname="hebo", fontsize=7.3, color=rgb("FFFFFF"))
        y = parrafo(p, item, y, x=M+22, ancho=W-22, size=size, lead=size*1.31) + 2
    return y


def tabla(p, rows, widths, y, *, size=8.0, x=M):
    lineas = [[envolver(c, widths[j]-12, size if i else size-.1, i == 0) for j, c in enumerate(row)] for i, row in enumerate(rows)]
    alturas = [max(map(len, row))*size*1.24+9 for row in lineas]
    for i, row in enumerate(lineas):
        h, xx = alturas[i], x
        fill = AZUL if i == 0 else ("F0F5F9" if i % 2 == 0 else "FFFFFF")
        p.draw_rect((x, y, x+sum(widths), y+h), color=rgb("D8E1E8"), fill=rgb(fill), width=.45)
        for j, cell in enumerate(row):
            if j:
                p.draw_line((xx, y), (xx, y+h), color=rgb("D8E1E8"), width=.45)
            base = y+12
            for line in cell:
                p.insert_text((xx+6, base), line, fontname="hebo" if i == 0 else "helv", fontsize=size, color=rgb("FFFFFF" if i == 0 else TINTA))
                base += size*1.24
            xx += widths[j]
        y += h
    return y+5


def imagen(p, nombre, rect):
    ruta = IMAGENES / nombre
    if not ruta.is_file():
        raise FileNotFoundError(ruta)
    p.draw_rect(rect, color=rgb("CFD9E2"), fill=rgb("F4F7F9"), width=.7)
    from PIL import Image
    with Image.open(ruta) as im:
        escala = min((rect.width-6)/im.width, (rect.height-6)/im.height)
        ancho, alto = im.width*escala, im.height*escala
    caja = fitz.Rect(rect.x0+(rect.width-ancho)/2, rect.y0+(rect.height-alto)/2,
                     rect.x0+(rect.width+ancho)/2, rect.y0+(rect.height+alto)/2)
    p.insert_image(caja, filename=str(ruta), keep_proportion=True)


def pie_imagen(p, texto, y):
    parrafo(p, texto, y, size=7, color=GRIS, ancho=W)


def crear_pdf():
    doc = fitz.open()
    doc.set_metadata({"title": "TacticalGrid - Resumen de funcionamiento", "author": "Sistemas Inteligentes I"})

    # 1. Vista general del ciclo de uso.
    p = pagina(doc, 1)
    p.insert_text((M, 93), "TacticalGrid", fontname="hebo", fontsize=30, color=rgb(AZUL))
    p.insert_text((M, 123), "Cómo funciona la aplicación", fontname="hebo", fontsize=18, color=rgb(CIAN))
    p.insert_text((M, 148), "Resumen visual · Sistemas Inteligentes I", fontname="helv", fontsize=10, color=rgb(GRIS))
    y = parrafo(p, "TacticalGrid es un entorno táctico por turnos para explorar rutas, comparar costos y estudiar decisiones frente a un adversario. El mapa y sus reglas se configuran en escenarios JSON.", 169, size=10)
    imagen(p, "interfaz-busqueda-anotada.png", fitz.Rect(M, y+5, PW-M, y+300))
    pie_imagen(p, "Interfaz actual de Pygame con tablero, controles y resultados. Captura del renderizador usando SDL dummy; no corresponde a una sesión manual.", y+305)
    y += 335
    p.insert_text((M, y), "El recorrido de una sesión", fontname="hebo", fontsize=12, color=rgb(AZUL))
    tabla(p, [["Entrada", "Proceso", "Salida"], ["Escenario JSON", "Cargar y validar", "Mapa y estado inicial"], ["Modo + parámetros", "Buscar, jugar o evaluar", "Ruta, acción o partida"], ["Verificación / registro", "Comprobar y guardar", "Reporte reproducible"]], [130, 180, W-310], y+10, size=8)
    parrafo(p, "La interfaz presenta los resultados; las reglas del juego y los algoritmos determinan qué acciones son válidas y cómo se calcula cada resultado.", y+155, size=8.8, color=AZUL, bold=True)

    # 2. Carga y modelo de la aplicación.
    p = pagina(doc, 2)
    y = titulo(p, "1. Inicio, escenario y estado", "La GUI se abre por defecto; el JSON configura el tablero y la prueba inicial.")
    y = parrafo(p, "Desde la raíz, python main.py abre Pygame. Para cargar un escenario desde el inicio: python main.py --gui escenarios/ruta_corta_vs_economica.json. También puedes abrir un JSON con O o arrastrarlo a la ventana.", y, size=8.8)
    y = pasos(p, [
        "El cargador lee y valida el escenario completo: dimensiones, terrenos, costos, bases, recurso y unidades.",
        "Si el JSON es válido, se construyen el escenario estático y el estado dinámico: posiciones, turno y portador.",
        "La configuración prueba.modo propone Búsqueda, Partida o Adversarial; si no existe, la GUI inicia en Búsqueda. M permite cambiar de modo.",
        "Si la validación falla, aparece un mensaje y no se sustituye el escenario vigente.",
    ], y)
    imagen(p, "interfaz-busqueda-anotada.png", fitz.Rect(M, y+5, PW-M, y+220))
    pie_imagen(p, "El mapa se muestra a la izquierda y el panel de control a la derecha. Los números corresponden a la guía de interfaz.", y+224)
    y = parrafo(p, "En el tablero, cada celda tiene terreno y costo definidos por el escenario. Las unidades se mueven ortogonalmente; un destino debe ser transitable y estar libre. Al entrar en el recurso se recoge, y el portador gana al llegar a su propia base. Si ambos bandos quedan sin acciones, la partida termina en empate por bloqueo.", y+235, size=8.8)
    tabla(p, [["Parte", "Responsabilidad resumida"], ["Escenario", "Carga y valida datos JSON."], ["Juego", "Estado, turnos, acciones legales y transición."], ["Algoritmos", "Búsqueda de rutas, decisión y verificación."], ["Modos / interfaz", "Orquestan la prueba y muestran controles, resultados y registros."]], [126, W-126], y+2, size=7.9)

    # 3. Búsqueda de rutas.
    p = pagina(doc, 3)
    y = titulo(p, "2. Búsqueda: de parámetros a ruta", "El modo Búsqueda estudia navegación desde una unidad a una celda objetivo.")
    y = pasos(p, [
        "Selecciona unidad y algoritmo en el panel; usa los botones < y >.",
        "Haz clic en una celda transitable para fijar el objetivo.",
        "Pulsa Enter o Ejecutar búsqueda. El proceso usa el mapa, los costos JSON y el algoritmo elegido; no cambia la partida.",
        "Revisa el camino, el resultado y sus métricas; V solicita la verificación.",
    ], y)
    y = tabla(p, [["Método", "Qué prioriza"], ["BFS", "Menos movimientos, bajo el modelo de búsqueda."], ["DFS", "Profundiza una alternativa antes de retroceder."], ["UCS", "Menor costo acumulado del recorrido."], ["A*", "Costo recorrido y estimación; Manhattan o HTO."], ["Beam", "Conserva un ancho k de alternativas por nivel."]], [105, W-105], y+2, size=7.9)
    y = parrafo(p, "Una ruta puede tener menos pasos y costar más si atraviesa terrenos caros. En ruta_corta_vs_economica.json, BFS encuentra 8 movimientos con costo 50; UCS encuentra 12 movimientos con costo 12.", y+5, size=8.6, color=AZUL, bold=True)
    imagen(p, "busqueda-metricas-ampliadas.png", fitz.Rect(M, y+8, M+265, y+178))
    p.insert_text((M+280, y+22), "Cómo leer el resultado", fontname="hebo", fontsize=10, color=rgb(CIAN))
    tabla(p, [["Métrica", "Lectura"], ["Éxito", "Si se encontró ruta."], ["Longitud", "Cantidad de movimientos."], ["Costo", "Suma de costos del terreno."], ["Generados / expandidos", "Estados descubiertos / procesados."], ["Máximo frontera", "Mayor cantidad pendiente."], ["Tiempo", "Duración de la búsqueda."]], [108, 145], y+30, size=7.1, x=M+278)
    pie_imagen(p, "Panel de métricas real de una ejecución UCS; valores dependen del escenario y los parámetros.", y+181)
    parrafo(p, "E alterna la visualización de exploración cuando hay traza disponible. El color cian señala la ruta calculada; el resultado se puede verificar con V.", y+201, size=8.5)

    # 4. Partida manual.
    p = pagina(doc, 4)
    y = titulo(p, "3. Partida manual: jugar y cerrar el objetivo", "Cada clic que ejecuta una acción válida hace avanzar el turno.")
    imagen(p, "partida-unidad-activa.png", fitz.Rect(M, y, PW-M, y+315))
    pie_imagen(p, "Unidad seleccionada y destinos legales destacados por la interfaz. Render Pygame automatizado con SDL dummy.", y+319)
    y = pasos(p, [
        "Cambia a Partida con M e identifica el bando activo en el panel.",
        "Selecciona una unidad propia disponible con clic o con < y > en Unidad activa.",
        "Haz clic en un destino legal destacado para moverla. La acción mueve una celda ortogonal y pasa el turno.",
        "Al entrar en la celda del recurso, la unidad lo recoge. Lleva al portador a la base propia para ganar.",
        "El panel indica victoria, empate por bloqueo o el estado actual. R reinicia la partida.",
    ], y+326)
    imagen(p, "partida-victoria-panel.png", fitz.Rect(M, y+3, M+255, y+170))
    parrafo(p, "La victoria ocurre cuando quien lleva el recurso alcanza su propia base. La GUI conserva un historial de acciones que V puede verificar y J puede exportar.", y+28, x=M+270, ancho=W-270, size=9, color=AZUL)
    pie_imagen(p, "Panel de una partida de ejemplo que terminó en victoria A.", y+173)

    # 5. Decisión, validación y reproducibilidad.
    p = pagina(doc, 5)
    y = titulo(p, "4. Decisión adversarial y trazabilidad", "Minimax y alfa-beta recomiendan una jugada; la aplicación es una operación aparte.")
    imagen(p, "adversarial-panel-ampliado.png", fitz.Rect(M, y, M+260, y+250))
    y = parrafo(p, "En modo Adversarial se elige Minimax o alfa-beta y se configura la profundidad con los controles de la fila correspondiente. Enter evalúa; E compara ambos algoritmos. El panel informa la acción recomendada, valor, nodos y profundidad alcanzada.", y+4, x=M+275, ancho=W-275, size=8.7)
    y = parrafo(p, "Una recomendación no modifica la partida automáticamente. Para ejecutarla hay que pulsar A y confirmar cuando la interfaz lo solicite. V verifica la decisión recomendada.", max(y+20, 382), x=M+275, ancho=W-275, size=8.7, color=AZUL, bold=True)
    y = parrafo(p, "Verificación y registros", 447, size=12, color=AZUL, bold=True)
    y = pasos(p, [
        "V verifica una búsqueda, la decisión adversarial vigente o el historial de una partida, según el modo.",
        "J abre un selector de destino y exporta un registro JSON. No hay una carpeta fija: la persona elige dónde guardarlo.",
        "Los registros contienen parámetros y datos necesarios para reproducir; los de partida incluyen acciones y verificación.",
        "La consola puede reproducir un registro con python main.py --consola --reproducir-registro ruta/al/registro.tg.json.",
    ], y, size=8.5)
    y = tabla(p, [["Atajo", "Efecto principal"], ["O / M", "Abrir JSON / cambiar modo."], ["Enter / E", "Ejecutar operación / exploración o comparación adversarial."], ["V / J", "Verificar / exportar registro."], ["R / Q / C / A", "Reiniciar partida / evaluar / comparar / aplicar recomendación con confirmación."], ["Clic en tablero", "Objetivo en Búsqueda; unidad o destino legal en Partida."]], [93, W-93], y+3, size=7.6)
    parrafo(p, "Para ampliar: README.md y docs/entregables/manual-de-usuario.docx. Los controles varían según el modo activo.", y+9, size=8.2, color=GRIS)

    doc.save(SALIDA, garbage=4, deflate=True)
    doc.close()
    print(SALIDA)


if __name__ == "__main__":
    crear_pdf()
