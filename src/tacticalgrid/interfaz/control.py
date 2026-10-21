"""Estado transitorio y operaciones de los controles de la aplicacion grafica."""

from collections.abc import Sequence
import base64
from dataclasses import asdict, dataclass, replace
from hashlib import sha256
from pathlib import Path

from tacticalgrid.algoritmos import (
    ORDENES,
    ResultadoBusqueda,
    ResultadoMinimax,
    ComparacionAdversarial,
    alfa_beta,
    comparar_minimax_alfa_beta,
    minimax,
    orden_desde_configuracion,
    validar_ancho_haz,
)
from tacticalgrid.algoritmos.minimax import profundidad_desde_configuracion, validar_profundidad
from tacticalgrid.algoritmos.utilidad import pesos_desde_configuracion
from tacticalgrid.algoritmos.verificador import (
    ReporteVerificacion,
    verificar_busqueda,
    verificar_decision,
    verificar_partida,
)
from tacticalgrid.escenario import Posicion, cargar_escenario
from tacticalgrid.escenario.escenario import Escenario
from tacticalgrid.juego import (
    Accion,
    EstadoJuego,
    ProblemaNavegacion,
    acciones_para_unidad,
    aplicar_accion,
    crear_estado_inicial,
    preparar_turno,
    unidades_seleccionables,
)
from tacticalgrid.juego.reglas import costo_accion, es_terminal, es_accion_valida
from tacticalgrid.juego.partida_manual import ResultadoPartidaManual, TurnoManual, huella_estado
from tacticalgrid.modos.prueba import MODO_ADVERSARIAL, MODO_BUSQUEDA, MODO_PARTIDA, MODOS, leer_configuracion_prueba
from tacticalgrid.modos.registro import RegistroExperimento, serializar
from tacticalgrid.modos.registro_partida import crear_registro_partida

from .busquedas import ALGORITMOS, preparar_busqueda, resolver_objetivo
from .dialogo import DialogoNoDisponible


def _modo_desde_escenario(escenario: Escenario) -> str:
    configuracion = leer_configuracion_prueba(escenario)
    return configuracion.modo if configuracion is not None else MODO_BUSQUEDA


@dataclass(frozen=True)
class AyudaAlgoritmo:
    """Explicacion breve y verificable del criterio de un algoritmo disponible."""

    descripcion: tuple[str, ...]
    criterio: str
    detalle: str | None = None


AYUDAS_ALGORITMOS = {
    "bfs": AyudaAlgoritmo(
        ("Busca rutas con menos movimientos.", "Puede ignorar terrenos costosos."),
        "menor cantidad de movimientos",
    ),
    "dfs": AyudaAlgoritmo(
        ("Profundiza una alternativa y retrocede.", "No garantiza ruta corta ni economica."),
        "profundizar una alternativa",
    ),
    "ucs": AyudaAlgoritmo(
        ("Minimiza el costo acumulado.", "Puede preferir una ruta mas larga."),
        "menor costo del recorrido",
    ),
    "astar": AyudaAlgoritmo(
        ("Combina costo recorrido y estimacion.", "La estimacion orienta hacia el objetivo."),
        "costo acumulado mas heuristica",
        "Manhattan: pasos horizontales y verticales.",
    ),
    "beam": AyudaAlgoritmo(
        ("Conserva solo k opciones por nivel.", "Puede descartar rutas utiles."),
        "exploracion limitada mediante k",
        "k indica cuantas alternativas conserva.",
    ),
}


def _reporte_a_diccionario(reporte: ReporteVerificacion) -> dict[str, object]:
    """Convierte un reporte de dominio a datos serializables para el panel.

    Proposito: presentar cada comprobacion sin exponer objetos internos de la GUI.
    Precondiciones: ``reporte`` es un ReporteVerificacion.
    Postcondiciones: devuelve sujeto, validez y comprobaciones como tipos JSON.
    Complejidad: O(C) temporal y espacial, con C comprobaciones.
    Uso de IA: Si.
    Intervencion de IA: Codex documentó la serialización de reportes en esta continuación.
    Validacion del estudiante: no puedo confirmar revisión del equipo; tests/interfaz/test_control.py valida los reportes.
    """
    return {
        "sujeto": reporte.sujeto,
        "valido": reporte.es_valido,
        "comprobaciones": [
            {"nombre": item.nombre, "correcta": item.correcta, "detalle": item.detalle}
            for item in reporte.comprobaciones
        ],
    }


@dataclass
class ControlGrafico:
    """Seleccion y resultado vigentes de una sesion Pygame, fuera del dominio inmutable."""

    rutas_escenarios: tuple[Path, ...]
    ruta_escenario: Path
    escenario: Escenario
    estado: EstadoJuego
    algoritmo: str
    unidad: str | None
    objetivo: Posicion | None
    k: int
    modo: str = MODO_BUSQUEDA
    unidad_partida: str | None = None
    acciones_partida: tuple[Accion, ...] = ()
    algoritmo_adversarial: str = "MINIMAX"
    profundidad_adversarial: int = 1
    orden_adversarial: str = "generacion"
    resultado_adversarial: ResultadoMinimax | None = None
    comparacion_adversarial: ComparacionAdversarial | None = None
    estado_evaluado: EstadoJuego | None = None
    aplicar_confirmacion_pendiente: bool = False
    heuristica_astar: str = "manhattan"
    historial_busquedas: tuple[tuple[str, ResultadoBusqueda], ...] = ()
    contexto_historial_busquedas: tuple | None = None
    huella_escenario: str = ""
    estado_inicial_partida: EstadoJuego | None = None
    historial_partida: tuple[TurnoManual, ...] = ()
    resultado: ResultadoBusqueda | None = None
    verificacion: ReporteVerificacion | None = None
    exploracion_visible: bool = False
    mensaje: str = "Elija objetivo y ejecute con Enter."
    error: bool = False
    estado_busqueda: str = "sin ejecutar"
    ejecutando: bool = False

    @classmethod
    def crear(cls, ruta: str | Path, rutas_disponibles: Sequence[Path]) -> "ControlGrafico":
        """Carga el escenario inicial y deriva selecciones validas sin ejecutar busquedas.

        Proposito: construir el estado transitorio de la GUI a partir de datos reales del escenario.
        Precondiciones: ``ruta`` identifica un JSON valido; las rutas disponibles no necesitan estar cargadas.
        Postcondiciones: devuelve controles con unidad existente y modo tomado de ``prueba.modo`` (o busqueda por
        defecto); cuando el modo es partida prepara el turno antes de presentar la sesion.
        Complejidad: O(U log U + R log R) por crear el estado y normalizar R rutas disponibles.
        Uso de IA: Si.
        Intervencion de IA: Codex diseño el controlador de sesion para la integracion grafica final de E9.3.
        Validacion del estudiante: revisado y aprobado por el equipo; cubierta por pruebas de carga y selecciones
        iniciales.
        """
        ruta_resuelta = Path(ruta).resolve()
        contenido_escenario = ruta_resuelta.read_bytes()
        escenario = cargar_escenario(ruta_resuelta)
        if ruta_resuelta.read_bytes() != contenido_escenario:
            raise ValueError("El archivo del escenario cambio durante la carga; intentelo de nuevo.")
        huella_escenario = sha256(contenido_escenario).hexdigest()
        estado = crear_estado_inicial(escenario)
        estado_inicial_partida = estado
        modo = _modo_desde_escenario(escenario)
        configuracion_prueba = leer_configuracion_prueba(escenario)
        profundidad = profundidad_desde_configuracion(escenario.configuracion_juego) or 1
        orden = orden_desde_configuracion(escenario.configuracion_juego) or "generacion"
        if modo == MODO_PARTIDA:
            estado = preparar_turno(escenario, estado)
        rutas = tuple(sorted({Path(item).resolve() for item in rutas_disponibles} | {ruta_resuelta}))
        algoritmo, unidad, objetivo, k = cls._selecciones_iniciales(escenario, estado)
        control = cls(
            rutas,
            ruta_resuelta,
            escenario,
            estado,
            algoritmo,
            unidad,
            objetivo,
            k,
            modo,
            algoritmo_adversarial=(
                "MINIMAX"
                if configuracion_prueba is not None and configuracion_prueba.algoritmo == "minimax"
                else "ALFA_BETA"
                if configuracion_prueba is not None and configuracion_prueba.algoritmo == "alfa_beta"
                else "ALFA_BETA"
            ),
            profundidad_adversarial=profundidad,
            orden_adversarial=orden,
            huella_escenario=huella_escenario,
            estado_inicial_partida=estado_inicial_partida,
        )
        if modo == MODO_ADVERSARIAL:
            control.mensaje = "Modo adversarial reconocido; su panel se habilitara en la siguiente integracion."
            control.estado_busqueda = "modo adversarial"
        elif modo == MODO_PARTIDA:
            control.mensaje = "Partida cargada. Seleccione una unidad del bando activo."
            control.estado_busqueda = "partida en curso"
        return control

    @staticmethod
    def _selecciones_iniciales(
        escenario: Escenario,
        estado: EstadoJuego,
    ) -> tuple[str, str | None, Posicion | None, int]:
        """Deriva controles conservadores desde ``prueba`` y las unidades reales.

        Proposito: reutilizar configuracion valida sin depender de que todos los escenarios definan modo busqueda.
        Precondiciones: escenario y estado corresponden entre si.
        Postcondiciones: devuelve algoritmo admitido, unidad existente o ``None``, objetivo valido o ``None``
        y k positivo.
        Complejidad: O(U) temporal y espacial por enumerar U unidades.
        Uso de IA: Si.
        Intervencion de IA: Codex implemento la inicializacion segura de controles durante la integracion grafica.
        Validacion del estudiante: revisado y aprobado por el equipo; cubierta por pruebas con escenarios de
        distintos modos.
        """
        configuracion = escenario.configuracion_prueba or {}
        unidades = tuple(unidad.identificador for unidad in estado.unidades)
        unidad_json = configuracion.get("unidad_inicio")
        unidad = unidad_json if unidad_json in unidades else (unidades[0] if unidades else None)
        algoritmo_json = configuracion.get("algoritmo")
        equivalencias = {"a_estrella": "astar"}
        algoritmo = equivalencias.get(algoritmo_json, algoritmo_json)
        if algoritmo not in ALGORITMOS:
            algoritmo = "bfs"
        try:
            objetivo = resolver_objetivo(None, configuracion)
            if not escenario.contiene_posicion(objetivo):
                objetivo = None
        except ValueError:
            objetivo = None
        k_json = configuracion.get("k")
        try:
            k = validar_ancho_haz(k_json) if k_json is not None else 4
        except ValueError:
            k = 4
        return algoritmo, unidad, objetivo, k

    @property
    def unidades(self) -> tuple[str, ...]:
        """Identificadores reales de las unidades del estado vigente."""
        return tuple(unidad.identificador for unidad in self.estado.unidades)

    @property
    def origen(self) -> Posicion | None:
        """Posicion real de la unidad seleccionada, o ``None`` cuando no existe."""
        return next(
            (unidad.posicion for unidad in self.estado.unidades if unidad.identificador == self.unidad),
            None,
        )

    @property
    def ayuda_algoritmo(self) -> AyudaAlgoritmo:
        """Explicacion correspondiente exactamente al algoritmo seleccionado."""
        return AYUDAS_ALGORITMOS[self.algoritmo]

    @property
    def unidades_partida(self):
        """Unidades legales para actuar en el turno actual, derivadas del dominio."""
        return unidades_seleccionables(self.escenario, self.estado)

    @property
    def unidad_partida_actual(self):
        """Unidad actualmente seleccionada para la partida, si aun pertenece al turno."""
        return next(
            (unidad for unidad in self.unidades_partida if unidad.identificador == self.unidad_partida),
            None,
        )

    def _invalidar_resultado(self, mensaje: str) -> None:
        self.resultado = None
        self.verificacion = None
        self.resultado_adversarial = None
        self.comparacion_adversarial = None
        self.estado_evaluado = None
        self.aplicar_confirmacion_pendiente = False
        self.exploracion_visible = False
        self.mensaje = mensaje
        self.error = False
        self.estado_busqueda = "configuracion lista"

    def cambiar_algoritmo(self, paso: int) -> None:
        if self.modo != MODO_BUSQUEDA:
            return
        indice = (ALGORITMOS.index(self.algoritmo) + paso) % len(ALGORITMOS)
        self.algoritmo = ALGORITMOS[indice]
        self._invalidar_resultado("Algoritmo actualizado; ejecute una busqueda.")

    def cambiar_unidad(self, paso: int) -> None:
        if self.modo == MODO_PARTIDA:
            disponibles = tuple(unidad.identificador for unidad in self.unidades_partida)
            if not disponibles:
                self.unidad_partida = None
                self.acciones_partida = ()
                self.mensaje = "No hay unidades legales para el bando activo."
                self.error = False
                return
            indice = (
                disponibles.index(self.unidad_partida)
                if self.unidad_partida in disponibles
                else (-1 if paso > 0 else 0)
            )
            self.seleccionar_unidad_partida(disponibles[(indice + paso) % len(disponibles)])
            return
        unidades = self.unidades
        if not unidades:
            self.mensaje = "El escenario no contiene unidades seleccionables."
            self.error = True
            self.estado_busqueda = "error de configuracion"
            return
        if self.unidad is None:
            self.unidad = unidades[0]
            self.historial_busquedas = ()
            self.contexto_historial_busquedas = None
            self._invalidar_resultado("Unidad actualizada; ejecute una busqueda.")
            return
        indice = (unidades.index(self.unidad) + paso) % len(unidades)
        self.unidad = unidades[indice]
        self.historial_busquedas = ()
        self.contexto_historial_busquedas = None
        self._invalidar_resultado("Unidad actualizada; ejecute una busqueda.")

    def cambiar_k(self, paso: int) -> None:
        if self.algoritmo != "beam":
            return
        self.k = validar_ancho_haz(max(1, self.k + paso))
        self._invalidar_resultado("Ancho de Beam actualizado; ejecute una busqueda.")

    def cambiar_heuristica_astar(self, paso: int) -> None:
        """Alterna las heuristicas A* implementadas y elimina el resultado vigente."""
        if self.modo != MODO_BUSQUEDA or self.algoritmo != "astar":
            return
        opciones = ("manhattan", "hto")
        self.heuristica_astar = opciones[(opciones.index(self.heuristica_astar) + paso) % len(opciones)]
        self._invalidar_resultado("Heuristica de A* actualizada; ejecute la busqueda.")

    def seleccionar_objetivo(self, posicion: Posicion) -> None:
        if self.modo != MODO_BUSQUEDA:
            return
        if not self.escenario.contiene_posicion(posicion) or not self.escenario.es_transitable(posicion):
            self.mensaje = "El objetivo debe ser una celda transitable."
            self.error = True
            self.resultado = None
            self.verificacion = None
            self.exploracion_visible = False
            self.estado_busqueda = "error de configuracion"
            return
        self.objetivo = posicion
        self._invalidar_resultado("Objetivo actualizado; ejecute una busqueda.")

    def cambiar_modo(self, paso: int = 1) -> None:
        """Cambia entre busqueda, partida y modo adversarial sin descartar el estado actual.

        Proposito: exponer el modo declarado en el escenario y permitir seleccionar una modalidad desde la GUI.
        Precondiciones: el controlador tiene un escenario cargado y ``paso`` es un desplazamiento entero.
        Postcondiciones: selecciona un modo reconocido, limpia resultados incompatibles y, al entrar a partida,
        prepara el turno mediante las reglas del dominio. El estado solo cambia por el pase automatico por bloqueo.
        Complejidad: O(U^2 + M) temporal y O(A) espacial en modo partida, donde U son unidades, A acciones y M modos.
        Uso de IA: Si.
        Intervencion de IA: Codex integro el selector de modos y la inicializacion de partida en esta continuacion.
        Validacion del estudiante: No puedo confirmar revision manual del equipo; pruebas de interfaz cubren modos,
        preparacion del turno y conservacion del estado.
        """
        self.modo = MODOS[(MODOS.index(self.modo) + paso) % len(MODOS)]
        self.resultado = None
        self.verificacion = None
        self.historial_busquedas = ()
        self.contexto_historial_busquedas = None
        self.resultado_adversarial = None
        self.comparacion_adversarial = None
        self.estado_evaluado = None
        self.aplicar_confirmacion_pendiente = False
        self.exploracion_visible = False
        self.unidad_partida = None
        self.acciones_partida = ()
        if self.modo == MODO_PARTIDA:
            self.estado = preparar_turno(self.escenario, self.estado)
            self.estado_busqueda = self.estado.estado_partida
            self.mensaje = "Partida cargada. Seleccione una unidad del bando activo."
            self.error = False
        elif self.modo == MODO_BUSQUEDA:
            self.estado_busqueda = "configuracion lista"
            self.mensaje = "Modo busqueda. Seleccione un objetivo y ejecute un algoritmo."
            self.error = False
        else:
            self.estado_busqueda = "modo adversarial"
            self.mensaje = "El modo adversarial requiere ejecutar una evaluacion."
            self.error = False

    def reiniciar_partida(self) -> None:
        """Reinicia la sesión manual desde el estado inicial conservado al cargar el escenario.

        Proposito: ofrecer un reinicio explícito que descarte solo el historial de la partida actual.
        Precondiciones: hay un escenario cargado y ``estado_inicial_partida`` pertenece a su sesión.
        Postcondiciones: restaura el estado inicial preparado, elimina el historial y reportes derivados y activa modo partida.
        Complejidad: O(U + A) temporal y espacial para preparar el turno y regenerar acciones.
        Uso de IA: Si.
        Intervencion de IA: Codex agregó reinicio e historial verificable manual para R26.
        Validacion del estudiante: no puedo confirmar revisión del equipo; pruebas cubren reinicio y descarte de eventos.
        """
        if self.estado_inicial_partida is None:
            return
        self.estado = preparar_turno(self.escenario, self.estado_inicial_partida)
        self.historial_partida = ()
        self.modo = MODO_PARTIDA
        self.unidad_partida = None
        self.acciones_partida = ()
        self.resultado = None
        self.verificacion = None
        self.resultado_adversarial = None
        self.comparacion_adversarial = None
        self.estado_evaluado = None
        self.aplicar_confirmacion_pendiente = False
        self.exploracion_visible = False
        self.mensaje = "Partida reiniciada. Seleccione una unidad del bando activo."
        self.estado_busqueda = self.estado.estado_partida
        self.error = False

    def seleccionar_unidad_partida(self, identificador: str) -> bool:
        """Selecciona una unidad activa y consulta sus acciones legales al dominio.

        Proposito: mantener la seleccion grafica alineada con el turno y las reglas oficiales del juego.
        Precondiciones: el modo actual es partida y el estado pertenece al escenario cargado.
        Postcondiciones: una unidad seleccionable queda elegida y sus acciones se conservan para visualizacion y
        ejecucion; unidades rivales, bloqueadas o estados terminales se rechazan sin cambiar el turno.
        Complejidad: O(U + A) temporal y O(A) espacial, dada la consulta de seleccionables y acciones del dominio.
        Uso de IA: Si.
        Intervencion de IA: Codex conecto la seleccion grafica a unidades_seleccionables y acciones_para_unidad.
        Validacion del estudiante: No puedo confirmar revision manual del equipo; pruebas verifican bandos,
        acciones disponibles y rechazo de seleccion invalida.
        """
        if self.modo != MODO_PARTIDA:
            return False
        unidad = next((item for item in self.unidades_partida if item.identificador == identificador), None)
        if unidad is None:
            self.mensaje = f"La unidad {identificador!r} no puede actuar en este turno."
            self.error = True
            return False
        self.unidad_partida = identificador
        self.acciones_partida = acciones_para_unidad(self.escenario, self.estado, identificador)
        self.mensaje = f"{identificador} — tipo {unidad.tipo}: seleccione un destino resaltado."
        self.error = False
        return True

    def cambiar_algoritmo_adversarial(self, paso: int) -> None:
        """Alterna el algoritmo adversarial y descarta reportes calculados con otra configuracion."""
        algoritmos = ("MINIMAX", "ALFA_BETA")
        self.algoritmo_adversarial = algoritmos[(algoritmos.index(self.algoritmo_adversarial) + paso) % len(algoritmos)]
        self._invalidar_decision("Algoritmo actualizado; ejecute la evaluacion adversarial.")

    def cambiar_profundidad_adversarial(self, paso: int) -> None:
        """Ajusta la profundidad adversarial con el mismo validador utilizado por los algoritmos."""
        self.profundidad_adversarial = validar_profundidad(max(1, self.profundidad_adversarial + paso))
        self._invalidar_decision("Profundidad actualizada; ejecute la evaluacion adversarial.")

    def cambiar_orden_adversarial(self, paso: int) -> None:
        """Recorre los ordenes admitidos y conserva la configuracion en la sesion actual."""
        self.orden_adversarial = ORDENES[(ORDENES.index(self.orden_adversarial) + paso) % len(ORDENES)]
        self._invalidar_decision("Orden actualizado; ejecute la evaluacion adversarial.")

    def _invalidar_decision(self, mensaje: str) -> None:
        """Elimina resultados adversariales cuando cambia su estado o configuracion fuente."""
        self.resultado_adversarial = None
        self.comparacion_adversarial = None
        self.estado_evaluado = None
        self.verificacion = None
        self.aplicar_confirmacion_pendiente = False
        self.mensaje = mensaje
        self.estado_busqueda = "configuracion adversarial lista"
        self.error = False

    def evaluar_decision(self, comparar: bool = False) -> None:
        """Evalua el estado vigente con los algoritmos del dominio, sin aplicar la accion recomendada.

        Proposito: recomendar acciones de Minimax/alfa-beta desde el estado vigente y producir metricas o comparacion.
        Precondiciones: el escenario y estado estan cargados; la profundidad y el orden pertenecen a sus dominios.
        Postcondiciones: guarda resultado para el estado inmutable de entrada sin modificarlo; comparacion, cuando se
        solicita, ejecuta ambas variantes bajo igual profundidad, utilidad y orden. No aplica recomendaciones.
        Complejidad: O(b^d) en una evaluacion; la comparacion suma O(b^d) Minimax y alfa-beta.
        Uso de IA: Si.
        Intervencion de IA: Codex conecto la GUI con los algoritmos adversariales existentes y su comparador.
        Validacion del estudiante: No puedo confirmar revision manual; pruebas de interfaz cubren no mutacion,
        configuracion, metricas y recomendacion.
        """
        if self.modo != MODO_ADVERSARIAL:
            self.mensaje = "Cambie al modo adversarial para evaluar una decision."
            self.error = True
            return
        try:
            profundidad = validar_profundidad(self.profundidad_adversarial)
            if comparar:
                self.comparacion_adversarial = comparar_minimax_alfa_beta(
                    self.escenario, self.estado, profundidad, self.orden_adversarial
                )
                self.resultado_adversarial = (
                    self.comparacion_adversarial.minimax
                    if self.algoritmo_adversarial == "MINIMAX"
                    else self.comparacion_adversarial.alfa_beta
                )
            else:
                algoritmo = minimax if self.algoritmo_adversarial == "MINIMAX" else alfa_beta
                self.resultado_adversarial = algoritmo(
                    self.escenario, self.estado, profundidad, orden=self.orden_adversarial
                )
                self.comparacion_adversarial = None
        except ValueError as error:
            self._invalidar_decision(str(error))
            self.error = True
            self.estado_busqueda = "error de evaluacion adversarial"
            return
        self.estado_evaluado = self.estado
        self.verificacion = None
        self.aplicar_confirmacion_pendiente = False
        accion = self.resultado_adversarial.accion_seleccionada
        self.mensaje = (
            "Evaluacion completada; no se modifico la partida. No hay accion legal recomendada."
            if accion is None
            else f"Evaluacion completada; recomendacion para {self.resultado_adversarial.bando_max}. No se ejecuto."
        )
        self.estado_busqueda = "decision evaluada"
        self.error = False

    def verificar_decision_actual(self) -> None:
        """Valida independientemente la recomendacion adversarial correspondiente al estado vigente.

        Proposito: mostrar si la decision, el arbol y sus metricas son coherentes para el estado actual.
        Precondiciones: existe un resultado adversarial asociado al estado inmutable vigente.
        Postcondiciones: guarda el reporte de ``verificar_decision`` y no altera partida ni recomendacion.
        Complejidad: O(b^d) por regenerar independientemente el arbol completo.
        Uso de IA: Si.
        Intervencion de IA: Codex conecto la verificacion adversarial del dominio con la GUI.
        Validacion del estudiante: No puedo confirmar revision manual; las pruebas automatizadas verifican resultado
        valido, ausencia de decision y estado obsoleto.
        """
        if self.resultado_adversarial is None or self.estado_evaluado != self.estado:
            self.verificacion = None
            self.mensaje = "No verificable: evalúe una decision para el estado actual antes de verificarla."
            self.error = True
            return
        self.verificacion = verificar_decision(self.escenario, self.estado, self.resultado_adversarial)
        self.error = not self.verificacion.es_valido
        self.estado_busqueda = "verificacion valida" if self.verificacion.es_valido else "verificacion fallida"
        fallidas = self.verificacion.fallidas
        self.mensaje = (
            "Accion valida; arbol, decision y metricas verificados."
            if self.verificacion.es_valido
            else "Verificacion invalida: " + "; ".join(f"{item.nombre}: {item.detalle}" for item in fallidas)
        )

    def exportar_experimento(self, destino: str | Path) -> bool:
        """Exporta un experimento E10.3 o el registro reproducible de una partida manual.

        Proposito: conservar busquedas/decisiones iniciales en E10.3 y partidas o decisiones posteriores en formato propio.
        Precondiciones: existe un resultado vigente para busqueda/decision, o una sesion de partida registrable.
        Postcondiciones: escribe el formato correspondiente; ante falta de resultado o error informa la causa.
        Complejidad: O(N + R) temporal y espacial, con N bytes del escenario y R datos del registro.
        Uso de IA: Si.
        Intervencion de IA: Codex conecto la interfaz con el registro reproducible de E10.3 y agrego la heuristica A*
        como parametro reproducible de consola.
        Validacion del estudiante: No puedo confirmar revision manual; pruebas verifican huella, comando, contenido y
        rechazo de un escenario modificado.
        """
        destino = Path(destino).resolve()
        if self.modo == MODO_PARTIDA or (self.modo == MODO_ADVERSARIAL and self.historial_partida):
            return self._exportar_partida_manual(destino)
        if self.modo == MODO_BUSQUEDA:
            resultado = self.resultado
            if resultado is None:
                self.mensaje = "No verificable: ejecute una busqueda antes de exportar el experimento."
                self.error = True
                return False
            algoritmo = "a_estrella" if self.algoritmo == "astar" else self.algoritmo
            parametros = {
                "algoritmo": algoritmo,
                "unidad": self.unidad,
                "objetivo": [self.objetivo.fila, self.objetivo.columna],
                "k": self.k if self.algoritmo == "beam" else None,
                "heuristica": self.heuristica_astar if self.algoritmo == "astar" else None,
            }
            resultados = (resultado,)
        elif self.modo == MODO_ADVERSARIAL:
            if self.resultado_adversarial is None or self.estado_evaluado != self.estado:
                self.mensaje = "No verificable: evalúe una decision vigente antes de exportar."
                self.error = True
                return False
            inicial = crear_estado_inicial(self.escenario)
            if self.estado not in (inicial, preparar_turno(self.escenario, inicial)):
                self.mensaje = (
                    "No se puede reproducir desde el JSON original: la decision usa una partida ya modificada."
                )
                self.error = True
                return False
            algoritmo = "minimax_alfa_beta" if self.comparacion_adversarial else self.algoritmo_adversarial.lower()
            pesos = pesos_desde_configuracion(self.escenario.configuracion_juego)
            parametros = {
                "algoritmo": algoritmo,
                "profundidad": self.profundidad_adversarial,
                "orden_acciones": self.orden_adversarial,
                "bando_max": self.resultado_adversarial.bando_max,
                "pesos_utilidad": asdict(pesos),
            }
            resultados = (self.comparacion_adversarial or self.resultado_adversarial,)
        else:
            self.mensaje = "El modo partida manual no conserva un historial exportable de jugadas."
            self.error = True
            return False
        try:
            contenido = self.ruta_escenario.read_bytes()
            huella = sha256(contenido).hexdigest()
            if huella != self.huella_escenario:
                raise ValueError("El escenario cambio desde que se cargo; recarguelo antes de exportar.")
            raiz = Path(__file__).resolve().parents[3]
            try:
                archivo = self.ruta_escenario.relative_to(raiz).as_posix()
            except ValueError:
                archivo = str(self.ruta_escenario)
            registro = RegistroExperimento(
                archivo=archivo,
                huella_sha256=huella,
                escenario=self.escenario,
                verificar=self.verificacion is not None,
            )
            registro.definir(self.modo, **parametros)
            for item in resultados:
                registro.agregar_resultado(item)
            if self.verificacion is not None:
                registro.agregar_verificacion(self.verificacion)
            destino.write_text(serializar(registro.a_diccionario()) + "\n", encoding="utf-8")
        except (OSError, ValueError) as error:
            self.mensaje = f"No se pudo exportar: {error}"
            self.error = True
            return False
        self.mensaje = f"Experimento reproducible exportado: {destino.name}"
        self.error = False
        self.estado_busqueda = "registro exportado"
        return True

    def _exportar_partida_manual(self, destino: Path) -> bool:
        """Exporta la sesión y, si existe, la evaluación calculada sobre su estado reconstruido.

        Proposito: serializar una copia íntegra del escenario, eventos legales y resultado para reproducción posterior.
        Precondiciones: se conserva el estado inicial de la sesión y los bytes del escenario no cambiaron.
        Postcondiciones: escribe el formato tacticalgrid.partida/1 solo si el verificador acepta las acciones registradas.
        Complejidad: O(N + T*U) temporal y espacial para N bytes, T acciones y U unidades.
        Uso de IA: Si.
        Intervencion de IA: Codex conectó historial manual y exportación reproducible, incluida decisión posterior a jugadas.
        Validacion del estudiante: no puedo confirmar revisión del equipo; pruebas comprueban exportación y replay de registros.
        """
        if self.estado_inicial_partida is None:
            self.mensaje = "No se puede exportar: falta el estado inicial de la sesión."
            self.error = True
            return False
        try:
            bytes_escenario = self.ruta_escenario.read_bytes()
            huella = sha256(bytes_escenario).hexdigest()
            if huella != self.huella_escenario:
                raise ValueError("El escenario cambió desde que se cargó; recárguelo antes de exportar.")
            partida = ResultadoPartidaManual.desde_estado(
                self.escenario, self.estado_inicial_partida, self.historial_partida, self.estado
            )
            reporte_partida = verificar_partida(self.escenario, partida, verificar_arboles=False)
            if not reporte_partida.es_valido:
                raise ValueError("El historial no pasó verificar_partida.")
            evaluacion = None
            verificaciones: dict[str, object] = {"partida": _reporte_a_diccionario(reporte_partida)}
            if self.modo == MODO_ADVERSARIAL and self.resultado_adversarial is not None:
                if self.estado_evaluado != self.estado:
                    raise ValueError("La evaluación adversarial no corresponde al estado actual.")
                algoritmo = "minimax_alfa_beta" if self.comparacion_adversarial else self.algoritmo_adversarial.lower()
                resultado = self.comparacion_adversarial or self.resultado_adversarial
                evaluacion = {
                    "algoritmo": algoritmo,
                    "profundidad": self.profundidad_adversarial,
                    "orden_acciones": self.orden_adversarial,
                    "resultado": resultado.a_diccionario(),
                }
                reporte_decision = verificar_decision(self.escenario, self.estado, self.resultado_adversarial)
                if not reporte_decision.es_valido:
                    raise ValueError("La recomendación vigente no pasó verificar_decision.")
                verificaciones["decision"] = _reporte_a_diccionario(reporte_decision)
            registro = crear_registro_partida(
                base64.b64encode(bytes_escenario).decode("ascii"),
                huella,
                self.estado_inicial_partida,
                self.historial_partida,
                self.estado,
                partida.resultado,
                self.modo,
                evaluacion=evaluacion,
                verificaciones=verificaciones,
            )
            destino.write_text(serializar(registro) + "\n", encoding="utf-8")
        except (OSError, ValueError) as error:
            self.mensaje = f"No se pudo exportar: {error}"
            self.error = True
            return False
        self.mensaje = f"Partida reproducible exportada: {destino.name}"
        self.error = False
        self.estado_busqueda = "registro exportado"
        return True

    def aplicar_decision_recomendada(self, confirmar: bool = False) -> None:
        """Solicita confirmacion en dos interacciones y aplica una recomendacion aun vigente y legal.

        Proposito: separar explicitamente la evaluacion automatica de la ejecucion efectiva de la jugada.
        Precondiciones: la recomendacion pertenece al estado vigente y su accion sigue siendo legal.
        Postcondiciones: sin confirmar solo arma la confirmacion; al confirmar aplica una vez por reglas del dominio,
        cambia a partida y elimina resultado/comparacion/reporte ya obsoletos. Estados cambiados o acciones ilegales
        se rechazan sin alterar la partida.
        Complejidad: O(U + A) para revalidar la accion y preparar el turno.
        Uso de IA: Si.
        Intervencion de IA: Codex implemento confirmacion e interaccion de aplicacion explicita de la recomendacion.
        Validacion del estudiante: No puedo confirmar revision manual; pruebas comprueban confirmacion requerida,
        legalidad e invalidacion de reportes.
        """
        resultado = self.resultado_adversarial
        accion_tactica = resultado.accion_seleccionada if resultado is not None else None
        if resultado is None or accion_tactica is None or self.estado_evaluado != self.estado:
            self._invalidar_decision("La recomendacion no corresponde al estado actual; vuelva a evaluar.")
            self.error = True
            return
        if not es_accion_valida(self.escenario, self.estado, accion_tactica.accion):
            self._invalidar_decision("La recomendacion ya no es legal; vuelva a evaluar.")
            self.error = True
            return
        if self.verificacion is None or not self.verificacion.es_valido:
            self.mensaje = "No verificable: verifique la recomendacion valida antes de aplicarla."
            self.error = True
            self.aplicar_confirmacion_pendiente = False
            return
        if not confirmar:
            self.aplicar_confirmacion_pendiente = True
            self.mensaje = "Confirme con A — Aplicar para ejecutar la accion recomendada una sola vez."
            return
        estado_previo = self.estado
        self.estado = aplicar_accion(self.escenario, self.estado, accion_tactica.accion)
        self._registrar_turno_manual(accion_tactica.accion, estado_previo)
        self.estado = preparar_turno(self.escenario, self.estado)
        self.modo = MODO_PARTIDA
        self.unidad_partida = None
        self.acciones_partida = ()
        self.historial_busquedas = ()
        self.contexto_historial_busquedas = None
        self.resultado = None
        self.exploracion_visible = False
        self.resultado_adversarial = None
        self.comparacion_adversarial = None
        self.estado_evaluado = None
        self.aplicar_confirmacion_pendiente = False
        self.verificacion = None
        self.estado_busqueda = self.estado.estado_partida
        self.error = False
        self.mensaje = f"Recomendacion aplicada. Turno del bando {self.estado.turno_actual}."

    def clic_partida(self, posicion: Posicion) -> None:
        """Selecciona una unidad del turno o ejecuta su accion al pulsar un destino legal.

        Proposito: traducir clics del tablero en selecciones y acciones validadas por el dominio.
        Precondiciones: la posicion proviene de una celda del tablero y el modo actual es partida.
        Postcondiciones: una accion valida crea un estado nuevo, prepara el turno siguiente e invalida resultados
        anteriores; los clics invalidos conservan estado y turno. No mueve unidades por coordenadas arbitrarias.
        Complejidad: O(U + A) temporal y espacial por buscar unidad/accion y actualizar opciones del turno.
        Uso de IA: Si.
        Intervencion de IA: Codex implemento la interaccion por clic sobre acciones legales existentes.
        Validacion del estudiante: No puedo confirmar revision manual del equipo; pruebas de controlador y eventos
        cubren movimiento, rechazo, turnos, recurso y terminalidad.
        """
        if self.modo != MODO_PARTIDA:
            return
        unidad = next((item for item in self.estado.unidades if item.posicion == posicion), None)
        if unidad is not None and any(item.identificador == unidad.identificador for item in self.unidades_partida):
            self.seleccionar_unidad_partida(unidad.identificador)
            return
        accion = next(
            (item for item in self.acciones_partida if item.destino == posicion),
            None,
        )
        if accion is None:
            self.mensaje = "Seleccione una unidad activa y luego uno de sus destinos legales."
            self.error = True
            return
        try:
            estado_previo = self.estado
            self.estado = aplicar_accion(self.escenario, self.estado, accion)
        except ValueError as error:
            self.mensaje = f"Accion rechazada: {error}"
            self.error = True
            return
        self._registrar_turno_manual(accion, estado_previo)
        self.estado = preparar_turno(self.escenario, self.estado)
        self.resultado = None
        self.verificacion = None
        self.exploracion_visible = False
        self.unidad_partida = None
        self.acciones_partida = ()
        self.historial_busquedas = ()
        self.contexto_historial_busquedas = None
        ganador = self.estado.estado_partida.removeprefix("victoria_") if self.estado.estado_partida.startswith("victoria_") else None
        if ganador is not None:
            self.mensaje = f"Victoria del bando {ganador}: entrego el recurso en su base."
        elif es_terminal(self.escenario, self.estado):
            self.mensaje = "Partida terminada: empate por bloqueo."
        else:
            self.mensaje = f"Accion aplicada. Turno del bando {self.estado.turno_actual}."
        self.estado_busqueda = self.estado.estado_partida
        self.error = False

    def _registrar_turno_manual(self, accion: Accion, estado_previo: EstadoJuego) -> None:
        """Agrega una acción que ya fue aceptada y aplicada por las reglas del dominio.

        Proposito: conservar evidencia ordenada de cada transición humana y recomendación ejecutada explícitamente.
        Precondiciones: ``estado_previo`` y ``self.estado`` son consecutivos y ``accion`` es legal en el primero.
        Postcondiciones: agrega bando, unidad/acción, costo, pase automático y huellas de ambos estados al historial.
        Complejidad: O(U log U) por las dos huellas canónicas para U unidades.
        Uso de IA: Si.
        Intervencion de IA: Codex agregó historial verificable y su captura en acciones GUI para R26.
        Validacion del estudiante: no puedo confirmar revisión del equipo; pruebas verifican datos, orden e invariantes.
        """
        referencia = self.historial_partida[-1].estado_resultante if self.historial_partida else self.estado_inicial_partida
        preparado = preparar_turno(self.escenario, referencia) if referencia is not None else estado_previo
        turno = TurnoManual(
            numero=len(self.historial_partida) + 1,
            bando=estado_previo.turno_actual,
            hubo_pase=referencia is not None and preparado != referencia and preparado == estado_previo,
            estado_previo=estado_previo,
            accion=accion,
            costo=costo_accion(self.escenario, accion),
            estado_resultante=self.estado,
            huella_previa=huella_estado(estado_previo),
            huella_resultante=huella_estado(self.estado),
        )
        self.historial_partida = (*self.historial_partida, turno)

    def cargar_ruta(self, ruta: str | Path) -> bool:
        """Reemplaza atomicamente el escenario solo despues de cargarlo por completo.

        Proposito: permitir cambiar de JSON sin dejar escenario, estado, selecciones y resultado desincronizados.
        Precondiciones: ``ruta`` puede apuntar a un archivo valido o invalido.
        Postcondiciones: con exito reinicia estado, modo, controles, camino, traza y reportes; en modo partida prepara
        el turno. Ante error conserva todo y lo informa.
        Complejidad: costo de carga y validacion mas O(U log U) para el estado inicial.
        Uso de IA: Si.
        Intervencion de IA: Codex implemento la carga atomica desde controles para la integracion grafica final y
        agrego la invalidacion del reporte de verificacion en esta auditoria.
        Validacion del estudiante: No puedo confirmar una revision manual del equipo para la invalidacion del reporte
        agregada en esta auditoria; la suite automatizada cubre carga valida e invalida y el reporte de verificacion.
        """
        ruta_resuelta = Path(ruta).resolve()
        try:
            contenido_escenario = ruta_resuelta.read_bytes()
            escenario = cargar_escenario(ruta_resuelta)
            if ruta_resuelta.read_bytes() != contenido_escenario:
                raise ValueError("El archivo del escenario cambio durante la carga; intentelo de nuevo.")
            estado = crear_estado_inicial(escenario)
            estado_inicial_partida = estado
            modo = _modo_desde_escenario(escenario)
            configuracion_prueba = leer_configuracion_prueba(escenario)
            if modo == MODO_PARTIDA:
                estado = preparar_turno(escenario, estado)
            algoritmo, unidad, objetivo, k = self._selecciones_iniciales(escenario, estado)
            profundidad = profundidad_desde_configuracion(escenario.configuracion_juego) or 1
            orden = orden_desde_configuracion(escenario.configuracion_juego) or "generacion"
            huella_escenario = sha256(contenido_escenario).hexdigest()
        except (OSError, ValueError) as error:
            self.mensaje = f"No se pudo cargar: {error}"
            self.error = True
            self.estado_busqueda = "error de carga"
            return False
        self.ruta_escenario = ruta_resuelta
        self.escenario = escenario
        self.estado = estado
        self.estado_inicial_partida = estado_inicial_partida
        self.historial_partida = ()
        self.algoritmo = algoritmo
        self.unidad = unidad
        self.objetivo = objetivo
        self.k = k
        self.modo = modo
        self.algoritmo_adversarial = (
            "MINIMAX" if configuracion_prueba is not None and configuracion_prueba.algoritmo == "minimax" else "ALFA_BETA"
        )
        self.profundidad_adversarial = profundidad
        self.orden_adversarial = orden
        self.huella_escenario = huella_escenario
        self.unidad_partida = None
        self.acciones_partida = ()
        self.historial_busquedas = ()
        self.contexto_historial_busquedas = None
        self.resultado = None
        self.verificacion = None
        self.resultado_adversarial = None
        self.comparacion_adversarial = None
        self.estado_evaluado = None
        self.aplicar_confirmacion_pendiente = False
        self.exploracion_visible = False
        self.mensaje = (
            "Partida cargada. Seleccione una unidad del bando activo."
            if modo == MODO_PARTIDA
            else f"Escenario cargado: {ruta_resuelta.name}"
        )
        self.error = False
        self.estado_busqueda = "partida en curso" if modo == MODO_PARTIDA else "configuracion lista"
        return True

    def cambiar_escenario(self, paso: int) -> None:
        indice = (self.rutas_escenarios.index(self.ruta_escenario) + paso) % len(self.rutas_escenarios)
        self.cargar_ruta(self.rutas_escenarios[indice])

    def abrir_escenario(self, ruta: str | Path) -> bool:
        """Carga un escenario JSON elegido por el usuario y lo suma a los selectores de escenario.

        Proposito: abrir mapas externos, como los del profesor, desde la ventana: con el selector de archivos o
        arrastrando el JSON sobre ella.
        Precondiciones: ``ruta`` puede apuntar a cualquier archivo, valido o no.
        Postcondiciones: si la carga atomica de ``cargar_ruta`` tiene exito, el escenario queda vigente y su ruta
        figura una sola vez en ``rutas_escenarios``, ordenada con las demas; si falla, la sesion y los selectores
        no cambian y el mensaje explica el error. Devuelve si se cargo.
        Complejidad: la de ``cargar_ruta`` mas O(R log R) por reordenar las R rutas disponibles.
        Uso de IA: Si.
        Intervencion de IA: Claude (Opus 5.5) propuso este metodo y su documentacion en E9.4.
        Validacion del estudiante: el equipo lo reviso y probo en la ventana; tests/interfaz/test_control.py cubre
        la carga externa, la ruta repetida y el archivo invalido.
        """
        if not self.cargar_ruta(ruta):
            return False
        if self.ruta_escenario not in self.rutas_escenarios:
            self.rutas_escenarios = tuple(sorted((*self.rutas_escenarios, self.ruta_escenario)))
        return True

    def abrir_con_dialogo(self, seleccionar) -> bool:
        """Pide un escenario con el selector de archivos y lo abre.

        Proposito: conectar el boton y la tecla de apertura con la carga atomica, sin acoplar el controlador a tkinter.
        Precondiciones: ``seleccionar`` recibe la carpeta inicial y devuelve una ruta, ``None`` si el usuario cancela,
        o lanza ``DialogoNoDisponible``.
        Postcondiciones: con una ruta, se comporta como ``abrir_escenario``; si el usuario cancela, nada cambia y el
        mensaje lo indica; si no hay selector, nada cambia y el mensaje sugiere arrastrar el archivo a la ventana.
        Devuelve si se cargo un escenario.
        Complejidad: la de ``abrir_escenario``, mas el tiempo que el usuario tarde en elegir.
        Uso de IA: Si.
        Intervencion de IA: Claude (Opus 5.5) propuso este metodo y su documentacion en E9.4.
        Validacion del estudiante: el equipo lo reviso y probo en la ventana; tests/interfaz/test_control.py cubre
        la eleccion, la cancelacion y la falta de selector.
        """
        try:
            ruta = seleccionar(self.ruta_escenario.parent)
        except DialogoNoDisponible:
            self.mensaje = "No hay selector de archivos: arrastra el JSON a la ventana para abrirlo."
            self.error = True
            return False
        if ruta is None:
            self.mensaje = "Apertura cancelada; el escenario no cambio."
            self.error = False
            return False
        return self.abrir_escenario(ruta)

    def ejecutar(self) -> None:
        """Ejecuta una unica busqueda con las selecciones vigentes.

        Proposito: producir conjuntamente el camino E9.2 y la traza E9.3 desde los controles graficos.
        Precondiciones: escenario, estado, algoritmo y unidad proceden del controlador; el objetivo puede faltar.
        Postcondiciones: con parametros validos sustituye el resultado anterior e invalida el reporte previo sin
        mutar el estado; ante error limpia el resultado e informa la causa. Nunca ejecuta mas de una busqueda por llamada.
        Complejidad: la del algoritmo seleccionado y su traza acotada.
        Uso de IA: Si.
        Intervencion de IA: Codex conecto los controles a la API comun de busqueda sin comandos ni subprocesos y
        agrego la invalidacion del reporte previo en esta auditoria.
        Validacion del estudiante: No puedo confirmar una revision manual del equipo para la invalidacion del reporte
        agregada en esta auditoria; la suite automatizada cubre cinco algoritmos, no mutacion y verificacion.
        """
        if self.ejecutando:
            return
        if self.modo != MODO_BUSQUEDA:
            self.mensaje = "Cambie al modo busqueda para ejecutar navegacion."
            self.error = True
            return
        self.verificacion = None
        if self.unidad is None:
            self.resultado = None
            self.exploracion_visible = False
            self.mensaje = "El escenario no contiene unidades para navegar."
            self.error = True
            self.estado_busqueda = "error de configuracion"
            return
        if self.objetivo is None:
            self.resultado = None
            self.exploracion_visible = False
            self.mensaje = "Seleccione primero una celda objetivo."
            self.error = True
            self.estado_busqueda = "error de configuracion"
            return
        self.ejecutando = True
        self.estado_busqueda = "en curso"
        self.mensaje = "Ejecutando busqueda..."
        try:
            self.resultado = preparar_busqueda(
                self.escenario,
                self.estado,
                self.algoritmo,
                self.unidad,
                (self.objetivo.fila, self.objetivo.columna),
                self.k if self.algoritmo == "beam" else None,
                self.heuristica_astar if self.algoritmo == "astar" else "manhattan",
            )
        except ValueError as error:
            self.resultado = None
            self.exploracion_visible = False
            self.mensaje = str(error)
            self.error = True
            self.estado_busqueda = "error de configuracion"
            return
        finally:
            self.ejecutando = False
        self.exploracion_visible = False
        clave_contexto = (self.ruta_escenario, self.estado, self.unidad, self.objetivo)
        if self.contexto_historial_busquedas != clave_contexto:
            self.historial_busquedas = ()
            self.contexto_historial_busquedas = clave_contexto
        etiqueta = self.algoritmo.upper()
        if self.algoritmo == "beam":
            etiqueta += f" k={self.k}"
        elif self.algoritmo == "astar":
            etiqueta += f" ({self.heuristica_astar})"
        self.historial_busquedas = (
            *self.historial_busquedas[-1:],
            (etiqueta, replace(self.resultado, traza_expansiones=None)),
        )
        self.mensaje = "Busqueda finalizada." if self.resultado.exito else "Busqueda finalizada sin solucion."
        self.error = False
        self.estado_busqueda = "completada" if self.resultado.exito else "sin solucion"

    def verificar(self) -> None:
        """Verifica la búsqueda, decisión o historial de partida vigente.

        Proposito: reproducir reglas del dominio para verificar busquedas, recomendaciones o acciones registradas.
        Precondiciones: hay un resultado vigente del modo o estado inicial e historial de partida.
        Postcondiciones: guarda y muestra el reporte; no modifica el estado de juego ni el historial.
        Complejidad: depende del modo; reproduce camino, árbol adversarial o T transiciones registradas.
        Uso de IA: Si.
        Intervencion de IA: Codex integro E10.2 con los controles graficos durante esta auditoria.
        Validacion del estudiante: No puedo confirmar una revision manual del equipo posterior a esta auditoria;
        tests/interfaz/test_control.py cubre resultado valido, costo alterado e invalidacion del reporte.
        """
        if self.modo == MODO_PARTIDA:
            if self.estado_inicial_partida is None:
                self.verificacion = None
                self.mensaje = "No verificable: falta el estado inicial de esta sesión."
                self.error = True
                return
            partida = ResultadoPartidaManual.desde_estado(
                self.escenario, self.estado_inicial_partida, self.historial_partida, self.estado
            )
            self.verificacion = verificar_partida(self.escenario, partida, verificar_arboles=False)
            self.error = not self.verificacion.es_valido
            self.estado_busqueda = "verificacion valida" if self.verificacion.es_valido else "verificacion fallida"
            fallidas = [f"{item.nombre}: {item.detalle}" for item in self.verificacion.fallidas]
            self.mensaje = (
                f"Partida válida: {len(self.historial_partida)} acciones verificadas."
                if not fallidas
                else "Partida inválida: " + "; ".join(fallidas)
            )
            return
        if self.resultado is None or self.unidad is None or self.objetivo is None:
            self.verificacion = None
            self.mensaje = "Ejecute una busqueda antes de verificarla."
            self.error = True
            self.estado_busqueda = "sin resultado para verificar"
            return
        problema = ProblemaNavegacion(self.escenario, self.unidad, self.objetivo, self.estado)
        self.verificacion = verificar_busqueda(problema, self.resultado)
        self.error = not self.verificacion.es_valido
        self.estado_busqueda = "verificacion valida" if self.verificacion.es_valido else "verificacion fallida"
        fallidas = [item.nombre for item in self.verificacion.comprobaciones if not item.correcta]
        self.mensaje = (
            "Verificacion valida: todas las propiedades comprobadas."
            if not fallidas
            else "Verificacion invalida: " + ", ".join(fallidas)
        )

    def alternar_exploracion(self) -> None:
        """Alterna la misma bandera usada por teclado y boton, sin ejecutar busquedas."""
        if self.resultado is None or self.resultado.traza_expansiones is None:
            self.mensaje = "La exploracion requiere ejecutar primero una busqueda."
            self.error = True
            return
        self.exploracion_visible = not self.exploracion_visible
        self.mensaje = "Exploracion visible." if self.exploracion_visible else "Exploracion oculta."
        self.error = False
