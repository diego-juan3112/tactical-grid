"""Pruebas observables del renderizado E9.1 sobre superficies sin ventana real."""

import os
from dataclasses import replace
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame
import pytest

from tacticalgrid.algoritmos.resultado_busqueda import ResultadoBusqueda
from tacticalgrid.escenario import cargar_escenario
from tacticalgrid.escenario.escenario import Escenario, Posicion, UnidadInicial
from tacticalgrid.escenario.terreno import TipoTerreno
from tacticalgrid.interfaz.renderizador import RenderizadorTablero
from tacticalgrid.interfaz.aplicacion import preparar_busqueda
from tacticalgrid.juego.estado import EstadoJuego, crear_estado_inicial
from tacticalgrid.juego.unidad import Unidad


@pytest.fixture(autouse=True)
def pygame_inicializado():
    pygame.init()
    yield
    pygame.quit()


def _escenario(
    filas: int = 4,
    columnas: int = 6,
    *,
    terreno_externo: bool = False,
    portador: str | None = None,
) -> Escenario:
    tipos = {
        "llanura": TipoTerreno(costo=1, transitable=True),
        "bosque": TipoTerreno(costo=3, transitable=True),
        "muro": TipoTerreno(costo=None, transitable=False),
    }
    if terreno_externo:
        tipos["cristal_externo"] = TipoTerreno(costo=7, transitable=True)
    terreno = [["llanura" for _ in range(columnas)] for _ in range(filas)]
    if columnas >= 3:
        terreno[0][2] = "bosque"
    if filas >= 2 and columnas >= 4:
        terreno[1][3] = "muro"
    if terreno_externo:
        terreno[-1][-1] = "cristal_externo"
    unidades = (
        UnidadInicial("A1", "A", "explorador", Posicion(0, 0)),
        UnidadInicial("B1", "B", "explorador", Posicion(filas - 1, columnas - 1)),
    )
    return Escenario(
        version="1.0",
        filas=filas,
        columnas=columnas,
        tipos_terreno=tipos,
        terreno=tuple(tuple(fila) for fila in terreno),
        bases={"A": Posicion(0, 0), "B": Posicion(filas - 1, columnas - 1)},
        recurso=Posicion(filas // 2, columnas // 2),
        unidades_iniciales=unidades,
        turno_inicial="A",
        portador_recurso_inicial=portador,
        configuracion_juego={"portador_recurso": portador},
        configuracion_prueba=None,
    )


def _superficie() -> pygame.Surface:
    return pygame.Surface((960, 720))


def _celda(disposicion, posicion: Posicion) -> pygame.Rect:
    lado = disposicion.tamano_celda
    return pygame.Rect(
        disposicion.tablero.x + posicion.columna * lado,
        disposicion.tablero.y + posicion.fila * lado,
        lado,
        lado,
    )


def _pixel(superficie: pygame.Surface, punto: tuple[int, int]) -> tuple[int, int, int]:
    return tuple(superficie.get_at(punto)[:3])


def _colores_en(superficie: pygame.Surface, rectangulo: pygame.Rect, margen: int = 0) -> set[tuple[int, int, int]]:
    return {
        _pixel(superficie, (x, y))
        for x in range(rectangulo.left + margen, rectangulo.right - margen)
        for y in range(rectangulo.top + margen, rectangulo.bottom - margen)
    }


def test_renderiza_escenario_20x20_con_cuadricula_completa():
    escenario = _escenario(20, 20)
    superficie = _superficie()
    renderizador = RenderizadorTablero()

    disposicion = renderizador.renderizar(superficie, escenario, crear_estado_inicial(escenario))

    assert disposicion.tablero.width == 20 * disposicion.tamano_celda
    assert disposicion.tablero.height == 20 * disposicion.tamano_celda
    assert _pixel(superficie, disposicion.tablero.topleft) == renderizador.COLOR_CUADRICULA
    assert _pixel(superficie, (disposicion.tablero.right, disposicion.tablero.bottom)) == renderizador.COLOR_CUADRICULA


def test_ajusta_mapa_rectangular_y_dimensiones_variables_sin_coordenadas_fijas():
    renderizador = RenderizadorTablero()
    superficie = _superficie()

    disposicion_ancha = renderizador.renderizar(superficie, _escenario(3, 11), crear_estado_inicial(_escenario(3, 11)))
    escenario_alto = _escenario(13, 4)
    disposicion_alta = renderizador.renderizar(superficie, escenario_alto, crear_estado_inicial(escenario_alto))

    assert disposicion_ancha.tablero.size == (11 * disposicion_ancha.tamano_celda, 3 * disposicion_ancha.tamano_celda)
    assert disposicion_alta.tablero.size == (4 * disposicion_alta.tamano_celda, 13 * disposicion_alta.tamano_celda)
    assert disposicion_ancha.tablero.right <= superficie.get_width()
    assert disposicion_alta.tablero.bottom <= superficie.get_height()


def test_diferencia_tipos_de_terreno_y_marca_no_transitable():
    escenario = _escenario()
    superficie = _superficie()
    renderizador = RenderizadorTablero()
    disposicion = renderizador.renderizar(superficie, escenario, crear_estado_inicial(escenario))
    llanura = _celda(disposicion, Posicion(0, 1))
    bosque = _celda(disposicion, Posicion(0, 2))
    muro = _celda(disposicion, Posicion(1, 3))

    assert _pixel(superficie, llanura.center) == renderizador.color_para_terreno(
        "llanura", escenario.tipos_terreno["llanura"]
    )
    assert _pixel(superficie, bosque.center) == renderizador.color_para_terreno(
        "bosque", escenario.tipos_terreno["bosque"]
    )
    assert _pixel(superficie, llanura.center) != _pixel(superficie, bosque.center)
    assert _pixel(superficie, muro.center) == renderizador.COLOR_OBSTACULO


def test_admite_tipo_externo_con_color_determinista_y_leyenda_visible():
    escenario = _escenario(5, 7, terreno_externo=True)
    superficie = _superficie()
    renderizador = RenderizadorTablero()
    estado = crear_estado_inicial(escenario)

    disposicion = renderizador.renderizar(superficie, escenario, estado)
    color = renderizador.color_para_terreno("cristal_externo", escenario.tipos_terreno["cristal_externo"])
    celda = _celda(disposicion, Posicion(4, 6))

    assert color == renderizador.color_para_terreno("cristal_externo", escenario.tipos_terreno["cristal_externo"])
    assert color in _colores_en(superficie, celda, margen=1)
    assert superficie.get_bounding_rect().contains(disposicion.panel)


def test_identifica_bases_y_conserva_base_debajo_de_unidad():
    escenario = _escenario()
    superficie = _superficie()
    renderizador = RenderizadorTablero()
    disposicion = renderizador.renderizar(superficie, escenario, crear_estado_inicial(escenario))
    base_a = _celda(disposicion, escenario.bases["A"])
    base_b = _celda(disposicion, escenario.bases["B"])

    assert renderizador.COLOR_BASES["A"] in {
        _pixel(superficie, (x, base_a.bottom - 3)) for x in range(base_a.left + 2, base_a.right - 2)
    }
    assert renderizador.COLOR_BASES["B"] in {
        _pixel(superficie, (x, base_b.top + 3)) for x in range(base_b.left + 2, base_b.right - 2)
    }
    assert renderizador.COLOR_TEXTO in _colores_en(superficie, base_a)


def test_muestra_recurso_libre_sin_duplicarlo_en_unidades():
    escenario = _escenario()
    superficie = _superficie()
    renderizador = RenderizadorTablero()
    estado = crear_estado_inicial(escenario)
    disposicion = renderizador.renderizar(superficie, escenario, estado)
    celda_recurso = _celda(disposicion, estado.posicion_recurso)
    celda_unidad = _celda(disposicion, estado.unidades[0].posicion)

    assert renderizador.COLOR_RECURSO in _colores_en(superficie, celda_recurso)
    assert renderizador.COLOR_RECURSO not in _colores_en(superficie, celda_unidad)


def test_recurso_transportado_solo_aparece_como_insignia_del_portador():
    escenario = _escenario(portador="A1")
    superficie = _superficie()
    renderizador = RenderizadorTablero()
    estado = crear_estado_inicial(escenario)
    disposicion = renderizador.renderizar(superficie, escenario, estado)
    celda_original = _celda(disposicion, escenario.recurso)
    celda_portador = _celda(disposicion, estado.unidades[0].posicion)

    assert renderizador.COLOR_RECURSO not in _colores_en(superficie, celda_original)
    assert renderizador.COLOR_RECURSO in _colores_en(superficie, celda_portador)


def test_dibuja_unidades_de_ambos_bandos_con_identidad_distinta():
    escenario = _escenario()
    superficie = _superficie()
    renderizador = RenderizadorTablero()
    estado = crear_estado_inicial(escenario)
    disposicion = renderizador.renderizar(superficie, escenario, estado)

    colores_a = _colores_en(superficie, _celda(disposicion, estado.unidades[0].posicion))
    colores_b = _colores_en(superficie, _celda(disposicion, estado.unidades[1].posicion))

    assert renderizador.COLOR_BASES["A"] in colores_a
    assert renderizador.COLOR_BASES["B"] in colores_b
    assert renderizador.COLOR_TEXTO in colores_a and renderizador.COLOR_TEXTO in colores_b


@pytest.mark.parametrize(("turno", "color"), [("A", (38, 117, 191)), ("B", (190, 68, 68))])
def test_panel_refleja_turno_actual(turno: str, color: tuple[int, int, int]):
    escenario = _escenario()
    superficie = _superficie()
    renderizador = RenderizadorTablero()
    estado = replace(crear_estado_inicial(escenario), turno_actual=turno)
    disposicion = renderizador.renderizar(superficie, escenario, estado)
    region_turno = pygame.Rect(disposicion.panel.x, disposicion.panel.y, disposicion.panel.width, 50)

    assert color in _colores_en(superficie, region_turno)


def test_segundo_renderizado_refleja_nuevo_estado_sin_retener_el_anterior():
    escenario = _escenario()
    superficie = _superficie()
    renderizador = RenderizadorTablero()
    estado_a = crear_estado_inicial(escenario)
    nueva_posicion = Posicion(2, 1)
    unidad_movida = replace(estado_a.unidades[0], posicion=nueva_posicion)
    estado_b = EstadoJuego(
        unidades=(unidad_movida, estado_a.unidades[1]),
        turno_actual="B",
        posicion_recurso=estado_a.posicion_recurso,
        portador_recurso=None,
    )
    disposicion = renderizador.renderizar(superficie, escenario, estado_a)
    origen = _celda(disposicion, estado_a.unidades[0].posicion)
    punto_unidad_original = (origen.centerx + disposicion.tamano_celda // 3 - 10, origen.centery)
    assert _pixel(superficie, punto_unidad_original) == renderizador.COLOR_BASES["A"]
    renderizador.renderizar(superficie, escenario, estado_b)
    destino = _celda(disposicion, nueva_posicion)

    assert renderizador.COLOR_BASES["A"] in _colores_en(superficie, destino)
    assert _pixel(superficie, punto_unidad_original) == renderizador.color_para_terreno(
        "llanura", escenario.tipos_terreno["llanura"]
    )


def test_composicion_superpuesta_mantiene_base_unidad_identificador_y_portador():
    escenario = _escenario(portador="A1")
    superficie = _superficie()
    renderizador = RenderizadorTablero()
    estado = crear_estado_inicial(escenario)
    disposicion = renderizador.renderizar(superficie, escenario, estado)
    celda = _celda(disposicion, Posicion(0, 0))
    colores = _colores_en(superficie, celda)

    assert renderizador.COLOR_BASES["A"] in colores
    assert renderizador.COLOR_TEXTO in colores
    assert renderizador.COLOR_RECURSO in colores
    assert renderizador.COLOR_CUADRICULA in colores


RAIZ = Path(__file__).resolve().parents[2]
RUTA_COMPARACION = RAIZ / "escenarios" / "ruta_corta_vs_economica.json"


@pytest.mark.parametrize(
    ("algoritmo", "k"),
    [("bfs", None), ("dfs", None), ("ucs", None), ("astar", None), ("beam", 4)],
)
def test_traza_en_orden_el_camino_real_de_cada_algoritmo(monkeypatch, algoritmo: str, k: int | None):
    escenario = cargar_escenario(RUTA_COMPARACION)
    estado = crear_estado_inicial(escenario)
    resultado = preparar_busqueda(escenario, estado, algoritmo, k=k)
    superficie = _superficie()
    renderizador = RenderizadorTablero()
    llamadas = []
    dibujar_lineas = pygame.draw.lines

    def registrar_lineas(superficie_destino, color, cerrada, puntos, grosor):
        llamadas.append((color, tuple(puntos), grosor))
        return dibujar_lineas(superficie_destino, color, cerrada, puntos, grosor)

    monkeypatch.setattr(pygame.draw, "lines", registrar_lineas)
    disposicion = renderizador.renderizar(superficie, escenario, estado, resultado)
    centros_esperados = tuple(_celda(disposicion, posicion).center for posicion in resultado.camino)

    assert resultado is not None and resultado.exito
    assert llamadas[0][0] == renderizador.COLOR_OBSTACULO
    assert llamadas[1][0] == renderizador.COLOR_CAMINO
    assert llamadas[0][1] == llamadas[1][1] == centros_esperados


def test_identifica_origen_destino_y_no_marca_celdas_ajenas_al_camino():
    escenario = cargar_escenario(RUTA_COMPARACION)
    estado = crear_estado_inicial(escenario)
    resultado = preparar_busqueda(escenario, estado, "bfs")
    superficie = _superficie()
    renderizador = RenderizadorTablero()

    disposicion = renderizador.renderizar(superficie, escenario, estado, resultado)
    colores_origen = _colores_en(superficie, _celda(disposicion, resultado.camino[0]))
    colores_destino = _colores_en(superficie, _celda(disposicion, resultado.camino[-1]))
    colores_ajenos = _colores_en(superficie, _celda(disposicion, Posicion(4, 4)), margen=2)

    assert renderizador.COLOR_ORIGEN in colores_origen
    assert renderizador.COLOR_DESTINO in colores_destino
    assert renderizador.COLOR_CAMINO not in colores_ajenos
    assert renderizador.COLOR_ORIGEN not in colores_ajenos
    assert renderizador.COLOR_DESTINO not in colores_ajenos


def test_renderizar_camino_no_modifica_resultado_estado_ni_metricas():
    escenario = cargar_escenario(RUTA_COMPARACION)
    estado = crear_estado_inicial(escenario)
    resultado = preparar_busqueda(escenario, estado, "ucs")
    datos_antes = resultado.a_diccionario()
    acciones_antes = resultado.acciones

    RenderizadorTablero().renderizar(_superficie(), escenario, estado, resultado)

    assert resultado.a_diccionario() == datos_antes
    assert resultado.acciones == acciones_antes
    assert estado == crear_estado_inicial(escenario)


def test_resultado_real_sin_solucion_no_dibuja_camino_y_lo_informa_en_panel(monkeypatch):
    escenario = cargar_escenario(RUTA_COMPARACION)
    estado = crear_estado_inicial(escenario)
    resultado = preparar_busqueda(escenario, estado, "bfs", "A1", (1, 1))
    superficie = _superficie()
    renderizador = RenderizadorTablero()
    textos = []
    dibujar_texto = renderizador._dibujar_texto

    def registrar_texto(superficie_destino, texto, color, posicion, fuente):
        textos.append(texto)
        return dibujar_texto(superficie_destino, texto, color, posicion, fuente)

    monkeypatch.setattr(renderizador, "_dibujar_texto", registrar_texto)
    disposicion = renderizador.renderizar(superficie, escenario, estado, resultado)

    assert not resultado.exito and resultado.camino == ()
    assert "Estado: sin solucion" in textos
    assert renderizador.COLOR_CAMINO not in _colores_en(superficie, disposicion.tablero)


def test_resultado_exitoso_vacio_no_falla_ni_inventa_un_camino():
    escenario = _escenario()
    resultado = ResultadoBusqueda("PRUEBA", True, (), 0, 1, 0, 1)
    superficie = _superficie()
    renderizador = RenderizadorTablero()

    disposicion = renderizador.renderizar(superficie, escenario, crear_estado_inicial(escenario), resultado)

    assert renderizador.COLOR_CAMINO not in _colores_en(superficie, disposicion.tablero)


def test_sin_busqueda_no_muestra_estado_de_resultado(monkeypatch):
    escenario = _escenario()
    renderizador = RenderizadorTablero()
    textos = []
    dibujar_texto = renderizador._dibujar_texto

    def registrar_texto(superficie_destino, texto, color, posicion, fuente):
        textos.append(texto)
        return dibujar_texto(superficie_destino, texto, color, posicion, fuente)

    monkeypatch.setattr(renderizador, "_dibujar_texto", registrar_texto)
    renderizador.renderizar(_superficie(), escenario, crear_estado_inicial(escenario))

    assert not any(texto.startswith(("Busqueda:", "Estado:")) for texto in textos)


def test_resultado_nuevo_y_fracaso_sustituyen_completamente_el_camino_anterior():
    escenario = cargar_escenario(RUTA_COMPARACION)
    estado = crear_estado_inicial(escenario)
    bfs = preparar_busqueda(escenario, estado, "bfs")
    ucs = preparar_busqueda(escenario, estado, "ucs")
    fracaso = preparar_busqueda(escenario, estado, "bfs", "A1", (1, 1))
    superficie = _superficie()
    renderizador = RenderizadorTablero()

    renderizador.renderizar(superficie, escenario, estado, bfs)
    disposicion = renderizador.renderizar(superficie, escenario, estado, ucs)
    celda_exclusiva_bfs = _celda(disposicion, Posicion(2, 4))
    assert renderizador.COLOR_CAMINO not in _colores_en(superficie, celda_exclusiva_bfs, margen=2)

    renderizador.renderizar(superficie, escenario, estado, fracaso)
    assert renderizador.COLOR_CAMINO not in _colores_en(superficie, disposicion.tablero)


def test_cambiar_escenario_y_omitir_resultado_no_conserva_la_ruta_anterior():
    escenario = cargar_escenario(RUTA_COMPARACION)
    estado = crear_estado_inicial(escenario)
    resultado = preparar_busqueda(escenario, estado, "bfs")
    superficie = _superficie()
    renderizador = RenderizadorTablero()
    renderizador.renderizar(superficie, escenario, estado, resultado)

    escenario_nuevo = _escenario(3, 11)
    disposicion = renderizador.renderizar(
        superficie,
        escenario_nuevo,
        crear_estado_inicial(escenario_nuevo),
    )

    assert renderizador.COLOR_CAMINO not in _colores_en(superficie, disposicion.tablero)
