"""Pruebas de la partida por turnos entre algoritmos en el controlador gráfico (E9.5)."""

import json
from pathlib import Path

from tacticalgrid.escenario import Posicion
from tacticalgrid.interfaz.control import ControlGrafico
from tacticalgrid.juego.reglas import es_accion_valida, es_terminal
from tacticalgrid.modos.agentes import ALGORITMOS_AGENTE

RAIZ = Path(__file__).resolve().parents[2]
RUTA = RAIZ / "escenarios" / "prueba_gui_partida.json"
OTRA_RUTA = RAIZ / "escenarios" / "campo_20x20.json"


def _control(algoritmo_a: str = "astar", algoritmo_b: str = "ucs") -> ControlGrafico:
    control = ControlGrafico.crear(RUTA, (RUTA, OTRA_RUTA))
    control.cambiar_control_partida(1)
    control.algoritmos_bandos = {"A": algoritmo_a, "B": algoritmo_b}
    return control


def test_la_partida_inicia_en_control_manual_y_alterna_a_algoritmos() -> None:
    control = ControlGrafico.crear(RUTA, (RUTA,))

    assert (control.modo, control.control_partida) == ("partida", "manual")
    control.cambiar_control_partida(1)
    assert control.control_partida == "algoritmos"
    assert set(control.algoritmos_bandos) == {"A", "B"}
    control.cambiar_control_partida(1)
    assert control.control_partida == "manual"


def test_cambiar_el_algoritmo_de_un_bando_recorre_todos_sin_tocar_el_otro() -> None:
    control = _control()
    vistos = []

    for _ in ALGORITMOS_AGENTE:
        control.cambiar_algoritmo_bando("A", 1)
        vistos.append(control.algoritmos_bandos["A"])

    assert sorted(vistos) == sorted(ALGORITMOS_AGENTE)
    assert control.algoritmos_bandos["B"] == "ucs"


def test_siguiente_turno_aplica_una_sola_jugada_del_bando_en_turno() -> None:
    control = _control()
    previo = control.estado

    control.siguiente_turno()

    decision = control.ultima_decision
    assert decision is not None and decision.bando == "A" and decision.algoritmo == "astar"
    assert es_accion_valida(control.escenario, previo, decision.accion)
    assert len(control.historial_partida) == 1
    assert control.historial_partida[0].accion == decision.accion
    assert control.historial_partida[0].estado_previo == previo
    assert control.estado.turno_actual == "B"
    assert not control.error


def test_cada_pulsacion_avanza_una_jugada_y_la_partida_se_verifica() -> None:
    control = _control()

    for numero in range(1, 5):
        control.siguiente_turno()
        assert len(control.historial_partida) == numero

    assert [turno.bando for turno in control.historial_partida] == ["A", "B", "A", "B"]
    control.verificar()
    assert control.verificacion is not None and control.verificacion.es_valido


def test_la_busqueda_publica_su_camino_y_minimax_sus_metricas() -> None:
    control = _control(algoritmo_a="ucs", algoritmo_b="alfa_beta")
    control.profundidad_adversarial = 1

    control.siguiente_turno()
    plan = control.resultado
    assert plan is not None and plan is control.ultima_decision.busqueda
    assert plan.camino[0] == control.ultima_decision.accion.origen

    control.siguiente_turno()
    assert control.resultado is None
    assert control.ultima_decision.adversarial is not None
    assert control.ultima_decision.adversarial.profundidad_maxima == 1


def test_siguiente_turno_requiere_modo_partida_y_control_por_algoritmos() -> None:
    control = ControlGrafico.crear(RUTA, (RUTA,))
    previo = control.estado

    control.siguiente_turno()
    assert control.estado == previo and control.historial_partida == () and control.error

    control.cambiar_control_partida(1)
    control.cambiar_modo()
    control.siguiente_turno()
    assert control.estado == previo and control.historial_partida == ()


def test_con_control_por_algoritmos_los_clics_del_tablero_no_mueven_unidades() -> None:
    control = _control()
    previo = control.estado

    control.clic_partida(Posicion(0, 1))
    control.clic_partida(Posicion(0, 2))

    assert control.estado == previo and control.historial_partida == ()
    assert control.unidad_partida is None


def test_al_terminar_la_partida_el_boton_deja_de_avanzar() -> None:
    control = _control()

    for _ in range(60):
        if es_terminal(control.escenario, control.estado):
            break
        control.siguiente_turno()
    jugadas = len(control.historial_partida)
    control.siguiente_turno()

    assert es_terminal(control.escenario, control.estado)
    assert len(control.historial_partida) == jugadas
    assert "terminada" in control.mensaje.lower() or "victoria" in control.mensaje.lower()
    control.verificar()
    assert control.verificacion.es_valido


def test_reiniciar_cambiar_modo_y_cargar_limpian_la_ultima_jugada() -> None:
    control = _control()
    control.siguiente_turno()

    control.reiniciar_partida()
    assert control.ultima_decision is None and control.resultado is None and control.historial_partida == ()

    control.siguiente_turno()
    control.cambiar_modo()
    assert control.ultima_decision is None

    control.cargar_ruta(OTRA_RUTA)
    assert control.ultima_decision is None


def test_partida_entre_algoritmos_se_exporta_y_reproduce(tmp_path) -> None:
    from tacticalgrid.modos.reproduccion import reproducir_registro_partida

    control = _control()
    for _ in range(3):
        control.siguiente_turno()
    destino = tmp_path / "partida_algoritmos.tg.json"

    assert control.exportar_experimento(destino)
    registro = json.loads(destino.read_text(encoding="utf-8"))
    reproducido = reproducir_registro_partida(control.escenario, registro)

    assert reproducido.estado_final == control.estado
    assert reproducido.reporte_partida.es_valido
