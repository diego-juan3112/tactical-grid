"""Pruebas del estado transitorio de los controles graficos."""

import json
from pathlib import Path

import pytest

from tacticalgrid.escenario import Posicion
from tacticalgrid.interfaz import control as modulo_control
from tacticalgrid.interfaz.control import ControlGrafico
from tacticalgrid.juego import crear_estado_inicial


RAIZ = Path(__file__).resolve().parents[2]
RUTA = RAIZ / "escenarios" / "ruta_corta_vs_economica.json"
OTRA_RUTA = RAIZ / "escenarios" / "campo_20x20.json"


def _control() -> ControlGrafico:
    return ControlGrafico.crear(RUTA, (RUTA, OTRA_RUTA))


def _crear_partida(
    tmp_path,
    *,
    portador=None,
    posicion=(1, 1),
    objetivo=(1, 2),
    muro=None,
    modo="partida",
    profundidad=2,
    algoritmo="minimax",
    orden="generacion",
) -> Path:
    terreno = [["llanura"] * 4 for _ in range(4)]
    if muro is not None:
        terreno[muro[0]][muro[1]] = "muro"
    escenario = {
        "version": "1.0",
        "mapa": {"filas": 4, "columnas": 4},
        "tipos_terreno": {"llanura": {"costo": 1, "transitable": True}, "muro": {"transitable": False}},
        "terreno": terreno,
        "bases": {"A": {"fila": 0, "columna": 0}, "B": {"fila": 3, "columna": 3}},
        "recurso": {"fila": objetivo[0], "columna": objetivo[1]},
        "unidades": [
            {"id": "unidad-norte", "bando": "A", "tipo": "exploradora", "fila": posicion[0], "columna": posicion[1]},
            {"id": "guardia-x", "bando": "B", "tipo": "estandar", "fila": 3, "columna": 2},
        ],
        "turno": "A",
        "juego": {
            "portador_recurso": portador,
            "profundidad_maxima_minimax": profundidad,
            "orden_acciones": orden,
        },
        "prueba": {"modo": modo, "algoritmo": algoritmo},
    }
    ruta = tmp_path / "partida_externa.json"
    ruta.write_text(json.dumps(escenario), encoding="utf-8")
    return ruta


def _crear_escenario_externo(tmp_path, *, costo_pantano=7, modo="partida", turno="B") -> Path:
    filas, columnas = 5, 7
    terreno = [["selva" for _ in range(columnas)] for _ in range(filas)]
    terreno[1][2] = "pantano"
    terreno[3][4] = "muro"
    escenario = {
        "version": "1.0",
        "mapa": {"filas": filas, "columnas": columnas},
        "tipos_terreno": {
            "selva": {"costo": 1, "transitable": True},
            "pantano": {"costo": costo_pantano, "transitable": True},
            "muro": {"transitable": False},
        },
        "terreno": terreno,
        "bases": {"A": {"fila": 0, "columna": 0}, "B": {"fila": 4, "columna": 6}},
        "recurso": {"fila": 2, "columna": 3},
        "unidades": [
            {"id": "unidad/A raro", "bando": "A", "tipo": "portadora", "fila": 1, "columna": 1},
            {"id": "unidad B ?", "bando": "B", "tipo": "vigía", "fila": 3, "columna": 5},
        ],
        "turno": turno,
        "juego": {"portador_recurso": None},
        "prueba": {"modo": modo, "unidad_inicio": "unidad/A raro", "objetivo": {"fila": 1, "columna": 2}},
    }
    ruta = tmp_path / f"externo_{modo}_{costo_pantano}.json"
    ruta.write_text(json.dumps(escenario), encoding="utf-8")
    return ruta


def test_crea_controles_desde_datos_reales_sin_ejecutar_busqueda():
    control = _control()

    assert control.ruta_escenario == RUTA.resolve()
    assert control.unidad in control.unidades
    assert control.objetivo == Posicion(2, 8)
    assert control.algoritmo in ("bfs", "dfs", "ucs", "astar", "beam")
    assert control.resultado is None
    assert control.origen is not None
    assert control.estado_busqueda == "sin ejecutar"
    assert control.estado == crear_estado_inicial(control.escenario)


def test_carga_invalida_conserva_sesion_completa(tmp_path):
    control = _control()
    control.ejecutar()
    previo = (
        control.ruta_escenario,
        control.escenario,
        control.estado,
        control.algoritmo,
        control.unidad,
        control.objetivo,
        control.k,
        control.resultado,
    )
    invalido = tmp_path / "invalido.json"
    invalido.write_text("{}", encoding="utf-8")

    assert not control.cargar_ruta(invalido)
    assert previo == (
        control.ruta_escenario,
        control.escenario,
        control.estado,
        control.algoritmo,
        control.unidad,
        control.objetivo,
        control.k,
        control.resultado,
    )
    assert control.error


def test_carga_valida_sustituye_estado_camino_traza_y_selecciones():
    control = _control()
    control.ejecutar()
    assert control.resultado is not None

    assert control.cargar_ruta(OTRA_RUTA)

    assert control.ruta_escenario == OTRA_RUTA.resolve()
    assert control.resultado is None
    assert not control.exploracion_visible
    assert control.unidad in control.unidades
    assert control.estado == crear_estado_inicial(control.escenario)


@pytest.mark.parametrize("algoritmo", ["bfs", "dfs", "ucs", "astar", "beam"])
def test_ejecuta_cinco_algoritmos_sin_mutar_estado(algoritmo):
    control = _control()
    estado_inicial = control.estado
    control.algoritmo = algoritmo
    control.k = 4

    control.ejecutar()

    assert control.resultado is not None
    assert control.resultado.exito
    assert control.resultado.traza_expansiones is not None
    assert control.estado is estado_inicial
    assert control.estado == crear_estado_inicial(control.escenario)


def test_verifica_independientemente_la_busqueda_y_limpia_el_reporte_al_cambiar_seleccion():
    control = _control()
    control.ejecutar()

    control.verificar()

    assert control.verificacion is not None
    assert control.verificacion.es_valido
    assert control.estado_busqueda == "verificacion valida"
    assert "todas las propiedades" in control.mensaje

    control.cambiar_algoritmo(1)

    assert control.verificacion is None


def test_verificacion_grafica_rechaza_un_costo_alterado():
    from dataclasses import replace

    control = _control()
    control.ejecutar()
    control.resultado = replace(control.resultado, costo=control.resultado.costo + 1)

    control.verificar()

    assert control.verificacion is not None
    assert not control.verificacion.es_valido
    assert control.estado_busqueda == "verificacion fallida"
    assert control.error


def test_modo_partida_del_json_inicia_turno_y_selecciona_unidad_activa(tmp_path):
    ruta = _crear_partida(tmp_path)
    control = ControlGrafico.crear(ruta, (ruta,))

    assert control.modo == "partida"
    assert control.estado.turno_actual == "A"
    assert control.estado.estado_partida == "en_curso"
    assert control.seleccionar_unidad_partida("unidad-norte")
    assert control.unidad_partida_actual.identificador == "unidad-norte"
    assert control.unidad_partida_actual.tipo == "exploradora"
    assert control.acciones_partida


def test_partida_aplica_movimiento_legal_y_cambia_turno_sin_mutar_estado_previo(tmp_path):
    ruta = _crear_partida(tmp_path)
    control = ControlGrafico.crear(ruta, (ruta,))
    previo = control.estado
    control.seleccionar_unidad_partida("unidad-norte")

    control.clic_partida(Posicion(0, 1))

    assert control.estado is not previo
    assert next(unidad for unidad in control.estado.unidades if unidad.identificador == "unidad-norte").posicion == Posicion(0, 1)
    assert control.estado.turno_actual == "B"
    assert control.unidad_partida is None
    assert control.acciones_partida == ()
    assert len(control.historial_partida) == 1
    assert control.historial_partida[0].bando == "A"
    assert control.historial_partida[0].accion.identificador_unidad == "unidad-norte"
    assert control.historial_partida[0].estado_resultante.turno_actual == "B"
    control.verificar()
    assert control.verificacion is not None and control.verificacion.es_valido


def test_partida_rechaza_unidad_rival_y_destino_no_legal_sin_consumir_turno(tmp_path):
    ruta = _crear_partida(tmp_path)
    control = ControlGrafico.crear(ruta, (ruta,))
    previo = control.estado

    assert not control.seleccionar_unidad_partida("guardia-x")
    assert control.estado is previo
    assert control.estado.turno_actual == "A"
    assert control.historial_partida == ()
    assert not control.acciones_partida

    control.seleccionar_unidad_partida("unidad-norte")
    control.clic_partida(Posicion(3, 0))
    assert control.estado is previo
    assert control.estado.turno_actual == "A"


def test_partida_rechaza_destino_con_obstaculo_sin_consumir_turno(tmp_path):
    ruta = _crear_partida(tmp_path, muro=(0, 1))
    control = ControlGrafico.crear(ruta, (ruta,))
    previo = control.estado
    control.seleccionar_unidad_partida("unidad-norte")

    control.clic_partida(Posicion(0, 1))

    assert control.estado is previo
    assert control.estado.turno_actual == "A"
    assert control.error


def test_partida_recoge_recurso_y_actualiza_su_portador(tmp_path):
    ruta = _crear_partida(tmp_path)
    control = ControlGrafico.crear(ruta, (ruta,))
    control.seleccionar_unidad_partida("unidad-norte")

    control.clic_partida(Posicion(1, 2))

    assert control.estado.portador_recurso == "unidad-norte"
    assert control.estado.posicion_recurso is None
    assert control.estado.turno_actual == "B"
    control.verificar()
    assert control.verificacion is not None and control.verificacion.es_valido


def test_partida_entrega_recurso_muestra_victoria_y_bloquea_acciones(tmp_path):
    ruta = _crear_partida(tmp_path, portador="unidad-norte", posicion=(0, 1), objetivo=(2, 2))
    control = ControlGrafico.crear(ruta, (ruta,))
    control.seleccionar_unidad_partida("unidad-norte")

    control.clic_partida(Posicion(0, 0))

    assert control.estado.estado_partida == "victoria_A"
    assert "Victoria del bando A" in control.mensaje
    assert not control.unidades_partida
    assert not control.seleccionar_unidad_partida("unidad-norte")
    control.verificar()
    assert control.verificacion is not None and control.verificacion.es_valido
    assert control.verificacion.es_valido


def test_partida_manual_completa_se_reconstruye_y_verifica_recogida_transporte_y_victoria(tmp_path):
    ruta = _crear_partida(tmp_path)
    control = ControlGrafico.crear(ruta, (ruta,))
    jugadas = (
        ("unidad-norte", Posicion(1, 2)),
        ("guardia-x", Posicion(3, 1)),
        ("unidad-norte", Posicion(1, 1)),
        ("guardia-x", Posicion(3, 0)),
        ("unidad-norte", Posicion(0, 1)),
        ("guardia-x", Posicion(2, 0)),
        ("unidad-norte", Posicion(0, 0)),
    )
    for identificador, destino in jugadas:
        assert control.seleccionar_unidad_partida(identificador)
        control.clic_partida(destino)
        assert not control.error, control.mensaje

    assert len(control.historial_partida) == len(jugadas)
    assert control.historial_partida[0].estado_resultante.portador_recurso == "unidad-norte"
    assert control.estado.estado_partida == "victoria_A"
    control.verificar()
    assert control.verificacion is not None and control.verificacion.es_valido


def test_verificacion_de_partida_detecta_evento_o_transicion_alterados(tmp_path):
    from dataclasses import replace

    ruta = _crear_partida(tmp_path)
    control = ControlGrafico.crear(ruta, (ruta,))
    control.seleccionar_unidad_partida("unidad-norte")
    control.clic_partida(Posicion(0, 1))
    evento = control.historial_partida[0]
    control.historial_partida = (replace(evento, costo=evento.costo + 4),)

    control.verificar()

    assert control.verificacion is not None and not control.verificacion.es_valido
    assert any("costo registrado" in item.detalle for item in control.verificacion.fallidas)


def test_reinicio_y_cambio_de_escenario_separan_historiales(tmp_path):
    ruta = _crear_partida(tmp_path)
    control = ControlGrafico.crear(ruta, (ruta, OTRA_RUTA))
    estado_inicial = control.estado_inicial_partida
    control.seleccionar_unidad_partida("unidad-norte")
    control.clic_partida(Posicion(0, 1))
    assert control.historial_partida

    control.reiniciar_partida()
    assert control.estado == estado_inicial
    assert control.historial_partida == ()
    control.seleccionar_unidad_partida("unidad-norte")
    control.clic_partida(Posicion(0, 1))
    assert control.cargar_ruta(OTRA_RUTA)
    assert control.historial_partida == ()
    assert control.estado_inicial_partida == crear_estado_inicial(control.escenario)


def test_exporta_y_reproduce_partida_manual_desde_escenario_embebido(tmp_path, capsys):
    import json

    from tacticalgrid.modos.reproduccion import reproducir_registro_partida
    from tacticalgrid.consola import reproducir_archivo_partida

    ruta = _crear_partida(tmp_path)
    control = ControlGrafico.crear(ruta, (ruta,))
    control.seleccionar_unidad_partida("unidad-norte")
    control.clic_partida(Posicion(0, 1))
    registro_path = tmp_path / "partida.tg.json"

    assert control.exportar_experimento(registro_path)
    registro = json.loads(registro_path.read_text(encoding="utf-8"))
    reproducido = reproducir_registro_partida(control.escenario, registro)

    assert registro["formato"] == "tacticalgrid.partida/1"
    assert reproducido.estado_final == control.estado
    assert reproducido.reporte_partida.es_valido
    assert reproducir_archivo_partida(registro_path) == 0
    assert "Partida reproducida y verificada" in capsys.readouterr().out


def test_reproduce_evaluacion_adversarial_sobre_partida_previamente_jugada(tmp_path):
    import json

    from tacticalgrid.modos.reproduccion import reproducir_registro_partida

    ruta = _crear_partida(tmp_path)
    control = ControlGrafico.crear(ruta, (ruta,))
    control.seleccionar_unidad_partida("unidad-norte")
    control.clic_partida(Posicion(0, 1))
    control.cambiar_modo()
    control.evaluar_decision()
    registro_path = tmp_path / "partida-decision.tg.json"

    assert control.exportar_experimento(registro_path)
    registro = json.loads(registro_path.read_text(encoding="utf-8"))
    reproducido = reproducir_registro_partida(control.escenario, registro)

    assert registro["evaluacion"]["algoritmo"] == "minimax"
    assert reproducido.estado_final == control.estado
    assert reproducido.reporte_partida.es_valido
    assert reproducido.reporte_decision is not None and reproducido.reporte_decision.es_valido


def test_reproduccion_rechaza_registro_alterado_y_escenario_incompatible(tmp_path):
    import json

    from tacticalgrid.modos.reproduccion import reproducir_registro_partida
    from tacticalgrid.modos.registro_partida import huella_contenido_registro

    ruta = _crear_partida(tmp_path)
    control = ControlGrafico.crear(ruta, (ruta,))
    control.seleccionar_unidad_partida("unidad-norte")
    control.clic_partida(Posicion(0, 1))
    registro_path = tmp_path / "partida.tg.json"
    assert control.exportar_experimento(registro_path)
    registro = json.loads(registro_path.read_text(encoding="utf-8"))
    registro["acciones"] = []
    registro["integridad_sha256"] = huella_contenido_registro(registro)

    with pytest.raises(ValueError, match="estado final reconstruido"):
        reproducir_registro_partida(control.escenario, registro)
    otro = ControlGrafico.crear(OTRA_RUTA, (OTRA_RUTA,))
    with pytest.raises(ValueError, match="estado inicial registrado"):
        reproducir_registro_partida(otro.escenario, json.loads(registro_path.read_text(encoding="utf-8")))


def test_cambiar_modo_inicia_partida_y_cargar_otro_escenario_limpia_seleccion(tmp_path):
    ruta_partida = _crear_partida(tmp_path)
    control = _control()
    control.cambiar_modo()
    assert control.modo == "partida"

    control.seleccionar_unidad_partida("A1")
    assert control.unidad_partida is not None
    assert control.cargar_ruta(ruta_partida)
    assert control.modo == "partida"
    assert control.unidad_partida is None
    assert control.estado.turno_actual == "A"


def test_evaluacion_adversarial_usa_configuracion_json_y_no_muta_estado(tmp_path):
    ruta = _crear_partida(tmp_path, modo="adversarial", profundidad=2, algoritmo="minimax", orden="tactico")
    control = ControlGrafico.crear(ruta, (ruta,))
    estado_inicial = control.estado

    assert control.modo == "adversarial"
    assert control.algoritmo_adversarial == "MINIMAX"
    assert control.profundidad_adversarial == 2
    assert control.orden_adversarial == "tactico"
    control.evaluar_decision()

    assert control.resultado_adversarial is not None
    assert control.resultado_adversarial.accion_seleccionada is not None
    assert control.resultado_adversarial.profundidad_maxima == 2
    assert control.resultado_adversarial.orden_acciones == "tactico"
    assert control.estado is estado_inicial
    assert control.estado_evaluado is estado_inicial
    assert "No se ejecuto" in control.mensaje


def test_comparacion_verifica_misma_decision_y_muestra_metricas(tmp_path):
    ruta = _crear_partida(tmp_path, modo="adversarial", profundidad=2)
    control = ControlGrafico.crear(ruta, (ruta,))

    control.evaluar_decision(comparar=True)

    assert control.comparacion_adversarial is not None
    assert control.comparacion_adversarial.misma_accion
    assert control.comparacion_adversarial.mismo_valor
    assert control.resultado_adversarial is control.comparacion_adversarial.minimax
    control.verificar_decision_actual()
    assert control.verificacion is not None and control.verificacion.es_valido


def test_recomendacion_requiere_confirmacion_y_se_aplica_una_vez(tmp_path):
    ruta = _crear_partida(tmp_path, modo="adversarial", profundidad=1)
    control = ControlGrafico.crear(ruta, (ruta,))
    estado_inicial = control.estado
    control.evaluar_decision()
    recomendacion = control.resultado_adversarial.accion_seleccionada.accion
    control.verificar_decision_actual()

    control.aplicar_decision_recomendada()
    assert control.estado is estado_inicial
    assert control.aplicar_confirmacion_pendiente

    control.aplicar_decision_recomendada(confirmar=True)
    assert control.estado is not estado_inicial
    assert control.estado.turno_actual == "B"
    assert control.estado.unidades != estado_inicial.unidades
    assert control.modo == "partida"
    assert control.resultado_adversarial is None
    assert recomendacion not in control.acciones_partida
    assert len(control.historial_partida) == 1
    control.verificar()
    assert control.verificacion is not None and control.verificacion.es_valido


def test_recomendacion_se_invalida_si_cambia_estado_o_configuracion(tmp_path):
    from dataclasses import replace

    ruta = _crear_partida(tmp_path, modo="adversarial", profundidad=1)
    control = ControlGrafico.crear(ruta, (ruta,))
    control.evaluar_decision()
    control.estado = replace(control.estado, turno_actual="B")

    control.aplicar_decision_recomendada()

    assert control.resultado_adversarial is None
    assert control.estado.turno_actual == "B"
    assert control.error


def test_escenario_externo_variable_respeta_dimensiones_identificadores_turno_y_obstaculo(tmp_path):
    ruta = _crear_escenario_externo(tmp_path)
    control = ControlGrafico.crear(ruta, (ruta,))

    assert (control.escenario.filas, control.escenario.columnas) == (5, 7)
    assert control.estado.turno_actual == "B"
    assert control.estado.portador_recurso is None
    assert control.seleccionar_unidad_partida("unidad B ?")
    assert control.unidad_partida_actual.tipo == "vigía"
    assert all(accion.destino != Posicion(3, 4) for accion in control.acciones_partida)


def test_cambio_de_costo_externo_de_7_a_15_se_refleja_en_busqueda(tmp_path):
    ruta_7 = _crear_escenario_externo(tmp_path, costo_pantano=7, modo="busqueda", turno="A")
    ruta_15 = _crear_escenario_externo(tmp_path, costo_pantano=15, modo="busqueda", turno="A")
    control = ControlGrafico.crear(ruta_7, (ruta_7, ruta_15))
    control.algoritmo = "ucs"
    control.ejecutar()
    costo_7 = control.resultado.costo

    assert control.cargar_ruta(ruta_15)
    control.algoritmo = "ucs"
    control.ejecutar()

    assert costo_7 == 7
    assert control.resultado.costo == 15


def test_exporta_registro_gui_con_heuristica_y_comando_reproducible(tmp_path):
    control = _control()
    control.algoritmo = "astar"
    control.heuristica_astar = "hto"
    control.ejecutar()
    control.verificar()
    destino = tmp_path / "registro.json"

    assert control.exportar_experimento(destino)
    registro = json.loads(destino.read_text(encoding="utf-8"))

    assert registro["formato"] == "tacticalgrid.resultados/1"
    assert registro["escenario"]["huella_sha256"] == control.huella_escenario
    assert registro["parametros"]["heuristica"] == "hto"
    assert "--heuristica hto" in registro["comando"]
    assert registro["resultados"][0]["algoritmo"] == "A_ESTRELLA"
    assert registro["verificacion"]["valida"]


def test_exportacion_rechaza_archivo_de_escenario_modificado(tmp_path):
    ruta = _crear_escenario_externo(tmp_path, modo="busqueda", turno="A")
    control = ControlGrafico.crear(ruta, (ruta,))
    control.algoritmo = "ucs"
    control.ejecutar()
    datos = json.loads(ruta.read_text(encoding="utf-8"))
    datos["tipos_terreno"]["pantano"]["costo"] = 15
    ruta.write_text(json.dumps(datos), encoding="utf-8")
    destino = tmp_path / "registro-obsoleto.json"

    assert not control.exportar_experimento(destino)
    assert not destino.exists()
    assert "cambio desde que se cargo" in control.mensaje


def test_cambiar_modo_o_escenario_invalida_decision_y_verificacion(tmp_path):
    adversarial = _crear_partida(tmp_path, modo="adversarial", profundidad=1)
    externo = _crear_escenario_externo(tmp_path)
    control = ControlGrafico.crear(adversarial, (adversarial, externo))
    control.evaluar_decision()
    control.verificar_decision_actual()
    assert control.resultado_adversarial is not None
    assert control.verificacion is not None

    control.cambiar_modo()
    assert control.resultado_adversarial is None
    assert control.verificacion is None
    assert not control.aplicar_confirmacion_pendiente

    assert control.cargar_ruta(externo)
    assert control.modo == "partida"
    assert control.resultado_adversarial is None
    assert control.verificacion is None


def test_astar_permite_comparar_manhattan_y_hto_sobre_el_mismo_estado():
    control = _control()
    control.algoritmo = "astar"
    control.ejecutar()
    assert control.resultado is not None
    manhattan = control.resultado

    control.cambiar_heuristica_astar(1)
    assert control.heuristica_astar == "hto"
    control.ejecutar()

    assert control.resultado is not None
    assert control.resultado.exito == manhattan.exito
    assert control.historial_busquedas[-2][0] == "ASTAR (manhattan)"
    assert control.historial_busquedas[-1][0] == "ASTAR (hto)"
    assert control.historial_busquedas[-2][1].traza_expansiones is None


@pytest.mark.parametrize("k", [1, 2, 4, 8])
def test_beam_permite_comparar_anchos_requeridos_en_una_sesion(k):
    control = _control()
    control.algoritmo = "beam"
    control.k = k

    control.ejecutar()

    assert control.resultado is not None
    assert control.historial_busquedas[-1][0] == f"BEAM k={k}"


def test_beam_conserva_los_cuatro_anchos_para_comparacion():
    control = _control()
    control.algoritmo = "beam"
    for k in (1, 2, 4, 8):
        control.k = k
        control.ejecutar()

    assert [etiqueta for etiqueta, _ in control.historial_busquedas] == ["BEAM k=4", "BEAM k=8"]


def test_selecciones_invalidan_resultado_y_objetivo_rechaza_obstaculo():
    control = _control()
    control.ejecutar()
    control.exploracion_visible = True

    control.cambiar_algoritmo(1)
    assert control.resultado is None and not control.exploracion_visible
    control.seleccionar_objetivo(Posicion(1, 1))
    assert control.error
    assert control.objetivo == Posicion(2, 8)
    control.seleccionar_objetivo(Posicion(0, 1))
    assert control.objetivo == Posicion(0, 1)
    assert not control.error


def test_tecla_y_boton_pueden_compartir_unico_alternado_sin_recalcular():
    control = _control()
    control.ejecutar()
    resultado = control.resultado

    control.alternar_exploracion()
    assert control.exploracion_visible
    control.alternar_exploracion()
    assert not control.exploracion_visible
    assert control.resultado is resultado


def test_selectores_recorrren_algoritmos_unidades_escenarios_y_validan_k():
    control = _control()
    algoritmos = []
    for _ in range(5):
        algoritmos.append(control.algoritmo)
        control.cambiar_algoritmo(1)
    assert set(algoritmos) == {"bfs", "dfs", "ucs", "astar", "beam"}

    unidad_inicial = control.unidad
    control.cambiar_unidad(1)
    assert control.unidad in control.unidades
    if len(control.unidades) > 1:
        assert control.unidad != unidad_inicial

    control.algoritmo = "beam"
    control.k = 1
    control.cambiar_k(-1)
    assert control.k == 1
    ruta_inicial = control.ruta_escenario
    control.cambiar_escenario(1)
    assert control.ruta_escenario != ruta_inicial


@pytest.mark.parametrize(
    ("algoritmo", "texto", "criterio", "detalle"),
    [
        ("bfs", "menos movimientos", "menor cantidad", None),
        ("dfs", "Profundiza", "profundizar", None),
        ("ucs", "costo acumulado", "menor costo", None),
        ("astar", "estimacion", "heuristica", "Manhattan"),
        ("beam", "k opciones", "limitada", "k indica"),
    ],
)
def test_ayuda_contextual_corresponde_al_algoritmo(algoritmo, texto, criterio, detalle):
    control = _control()
    control.algoritmo = algoritmo

    ayuda = control.ayuda_algoritmo

    assert any(texto in linea for linea in ayuda.descripcion)
    assert criterio in ayuda.criterio
    assert (detalle is None and ayuda.detalle is None) or detalle in ayuda.detalle


def test_configuracion_invalida_no_ejecuta_y_elimina_resultado_anterior(monkeypatch):
    control = _control()
    control.ejecutar()
    assert control.resultado is not None
    control.objetivo = None
    llamadas = 0

    def contar(*argumentos, **opciones):
        nonlocal llamadas
        llamadas += 1

    monkeypatch.setattr(modulo_control, "preparar_busqueda", contar)

    control.ejecutar()

    assert llamadas == 0
    assert control.resultado is None
    assert control.estado_busqueda == "error de configuracion"
    assert "Seleccione primero" in control.mensaje


def test_bloqueo_reentrante_evitar_ejecuciones_simultaneas(monkeypatch):
    control = _control()
    control.ejecutando = True
    llamadas = 0

    def contar(*argumentos, **opciones):
        nonlocal llamadas
        llamadas += 1

    monkeypatch.setattr(modulo_control, "preparar_busqueda", contar)

    control.ejecutar()

    assert llamadas == 0


def _copia_externa(tmp_path, nombre="escenario_profesor.json"):
    externo = tmp_path / nombre
    externo.write_text((RAIZ / "escenarios" / "obstaculo_rodeo.json").read_text(encoding="utf-8"), encoding="utf-8")
    return externo


def test_abrir_escenario_externo_lo_carga_y_lo_agrega_a_los_selectores(tmp_path):
    control = _control()
    externo = _copia_externa(tmp_path)

    assert control.abrir_escenario(externo)
    assert control.ruta_escenario == externo.resolve()
    assert externo.resolve() in control.rutas_escenarios
    assert not control.error
    assert control.resultado is None
    for _ in control.rutas_escenarios:
        control.cambiar_escenario(1)
    assert control.ruta_escenario == externo.resolve()


def test_abrir_escenario_ya_listado_no_lo_duplica():
    control = _control()

    assert control.abrir_escenario(OTRA_RUTA)
    assert control.rutas_escenarios.count(OTRA_RUTA.resolve()) == 1


def test_abrir_escenario_invalido_conserva_la_sesion_y_explica_el_error(tmp_path):
    control = _control()
    rutas = control.rutas_escenarios
    invalido = tmp_path / "con_error.json"
    invalido.write_text('{"version": "1.0"}', encoding="utf-8")

    assert not control.abrir_escenario(invalido)
    assert control.ruta_escenario == RUTA.resolve()
    assert control.rutas_escenarios == rutas
    assert control.error
    assert "No se pudo cargar" in control.mensaje


def test_abrir_con_dialogo_carga_el_archivo_elegido(tmp_path):
    control = _control()
    externo = _copia_externa(tmp_path)
    directorios = []

    def seleccionar(directorio):
        directorios.append(directorio)
        return externo

    assert control.abrir_con_dialogo(seleccionar)
    assert control.ruta_escenario == externo.resolve()
    assert directorios == [RUTA.resolve().parent]


def test_abrir_con_dialogo_cancelado_no_cambia_nada():
    control = _control()

    assert not control.abrir_con_dialogo(lambda directorio: None)
    assert control.ruta_escenario == RUTA.resolve()
    assert not control.error
    assert "cancelada" in control.mensaje


def test_abrir_con_dialogo_no_disponible_sugiere_arrastrar_el_archivo():
    control = _control()

    def sin_dialogo(directorio):
        raise modulo_control.DialogoNoDisponible("sin tkinter")

    assert not control.abrir_con_dialogo(sin_dialogo)
    assert control.ruta_escenario == RUTA.resolve()
    assert control.error
    assert "arrastra" in control.mensaje.lower()
