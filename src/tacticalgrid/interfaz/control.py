"""Estado transitorio y operaciones de los controles de la aplicación gráfica."""

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
    """Explicación breve y verificable del criterio de un algoritmo disponible."""

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
    """Convertir un reporte del dominio en datos serializables para el panel.

    Proposito: presentar cada comprobación sin exponer objetos internos de la interfaz.
    Precondiciones: ``reporte`` es un ``ReporteVerificacion``.
    Postcondiciones: se devuelven el sujeto, la validez y las comprobaciones como tipos JSON.
    Complejidad: O(C) temporal y espacial, con C comprobaciones.
    Uso de IA: Si.
    Intervencion de IA: Codex: serialización de reportes y su documentación.
    Validacion del estudiante: pruebas de verificación de tests/interfaz/test_control.py, que leen los reportes
    serializados.
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
    """Selección y resultado vigentes de una sesión Pygame, fuera del dominio inmutable."""

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
        """Cargar el escenario inicial y derivar selecciones válidas sin ejecutar búsquedas.

        Proposito: construir el estado transitorio de la interfaz a partir de datos reales del escenario.
        Precondiciones: ``ruta`` identifica un JSON válido; las rutas disponibles no necesitan estar cargadas.
        Postcondiciones: se devuelven controles con una unidad existente y el modo tomado de ``prueba.modo`` (búsqueda
        por defecto); en modo partida, el turno se prepara antes de presentar la sesión.
        Complejidad: O(U log U + R log R) por crear el estado y ordenar R rutas disponibles.
        Uso de IA: Si.
        Intervencion de IA: Codex: diseño del controlador de sesión para la integración gráfica final (E9.3).
        Validacion del estudiante: pruebas ``test_crea_controles_desde_datos_reales_sin_ejecutar_busqueda`` y
        ``test_modo_partida_del_json_inicia_turno_y_selecciona_unidad_activa`` de tests/interfaz/test_control.py.
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
        """Derivar controles conservadores desde ``prueba`` y las unidades reales.

        Proposito: reutilizar la configuración válida sin depender de que todos los escenarios definan el modo búsqueda.
        Precondiciones: el escenario y el estado se corresponden.
        Postcondiciones: se devuelven un algoritmo admitido, una unidad existente o ``None``, un objetivo válido o
        ``None`` y un k positivo.
        Complejidad: O(U) temporal y espacial por enumerar U unidades.
        Uso de IA: Si.
        Intervencion de IA: Codex: inicialización segura de controles durante la integración gráfica.
        Validacion del estudiante: pruebas de tests/interfaz/test_control.py con escenarios de distintos modos, incluido
        un escenario externo con dimensiones, identificadores, turno y obstáculos variables.
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
        """Posición real de la unidad seleccionada, o ``None`` si no existe."""
        return next(
            (unidad.posicion for unidad in self.estado.unidades if unidad.identificador == self.unidad),
            None,
        )

    @property
    def ayuda_algoritmo(self) -> AyudaAlgoritmo:
        """Explicación correspondiente exactamente al algoritmo seleccionado."""
        return AYUDAS_ALGORITMOS[self.algoritmo]

    @property
    def unidades_partida(self):
        """Unidades que pueden actuar legalmente en el turno actual, derivadas del dominio."""
        return unidades_seleccionables(self.escenario, self.estado)

    @property
    def unidad_partida_actual(self):
        """Unidad seleccionada para la partida, si aún pertenece al turno."""
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
        """Alternar las heurísticas de A* implementadas y eliminar el resultado vigente."""
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
        """Cambiar entre búsqueda, partida y modo adversarial sin descartar el estado actual.

        Proposito: exponer el modo declarado en el escenario y permitir seleccionar una modalidad desde la interfaz.
        Precondiciones: el controlador tiene un escenario cargado y ``paso`` es un desplazamiento entero.
        Postcondiciones: se selecciona un modo reconocido, se limpian los resultados incompatibles y, al entrar en
        partida, se prepara el turno con las reglas del dominio. El estado solo cambia por el pase automático por
        bloqueo.
        Complejidad: O(U^2 + M) temporal y O(A) espacial en modo partida, con U unidades, A acciones y M modos.
        Uso de IA: Si.
        Intervencion de IA: Codex: selector de modos e inicialización de la partida.
        Validacion del estudiante: pruebas ``test_cambiar_modo_inicia_partida_y_cargar_otro_escenario_limpia_seleccion``
        y ``test_cambiar_modo_o_escenario_invalida_decision_y_verificacion`` de tests/interfaz/test_control.py.
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
        """Reiniciar la sesión manual desde el estado inicial conservado al cargar el escenario.

        Proposito: ofrecer un reinicio explícito que descarte solo el historial de la partida actual.
        Precondiciones: hay un escenario cargado y ``estado_inicial_partida`` pertenece a su sesión.
        Postcondiciones: se restaura el estado inicial preparado, se eliminan el historial y los reportes derivados y se
        activa el modo partida.
        Complejidad: O(U + A) temporal y espacial para preparar el turno y regenerar las acciones.
        Uso de IA: Si.
        Intervencion de IA: Codex: reinicio e historial manual verificable (R26).
        Validacion del estudiante: prueba ``test_reinicio_y_cambio_de_escenario_separan_historiales`` de
        tests/interfaz/test_control.py.
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
        """Seleccionar una unidad activa y consultar sus acciones legales al dominio.

        Proposito: mantener la selección gráfica alineada con el turno y las reglas del juego.
        Precondiciones: el modo actual es partida y el estado pertenece al escenario cargado.
        Postcondiciones: una unidad seleccionable queda elegida y sus acciones se conservan para visualizarlas y
        ejecutarlas; las unidades rivales o bloqueadas y los estados terminales se rechazan sin cambiar el turno.
        Complejidad: O(U + A) temporal y O(A) espacial por la consulta de unidades seleccionables y acciones del
        dominio.
        Uso de IA: Si.
        Intervencion de IA: Codex: conexión de la selección gráfica con ``unidades_seleccionables`` y
        ``acciones_para_unidad``.
        Validacion del estudiante: pruebas de tests/interfaz/test_control.py: selección de la unidad activa del turno,
        rechazo de una unidad rival y bloqueo de acciones tras una victoria.
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
        """Alternar el algoritmo adversarial y descartar los reportes calculados con otra configuración."""
        algoritmos = ("MINIMAX", "ALFA_BETA")
        self.algoritmo_adversarial = algoritmos[(algoritmos.index(self.algoritmo_adversarial) + paso) % len(algoritmos)]
        self._invalidar_decision("Algoritmo actualizado; ejecute la evaluacion adversarial.")

    def cambiar_profundidad_adversarial(self, paso: int) -> None:
        """Ajustar la profundidad adversarial con el mismo validador que usan los algoritmos."""
        self.profundidad_adversarial = validar_profundidad(max(1, self.profundidad_adversarial + paso))
        self._invalidar_decision("Profundidad actualizada; ejecute la evaluacion adversarial.")

    def cambiar_orden_adversarial(self, paso: int) -> None:
        """Recorrer los órdenes admitidos y conservar la configuración en la sesión actual."""
        self.orden_adversarial = ORDENES[(ORDENES.index(self.orden_adversarial) + paso) % len(ORDENES)]
        self._invalidar_decision("Orden actualizado; ejecute la evaluacion adversarial.")

    def _invalidar_decision(self, mensaje: str) -> None:
        """Eliminar los resultados adversariales cuando cambia su estado o su configuración de origen."""
        self.resultado_adversarial = None
        self.comparacion_adversarial = None
        self.estado_evaluado = None
        self.verificacion = None
        self.aplicar_confirmacion_pendiente = False
        self.mensaje = mensaje
        self.estado_busqueda = "configuracion adversarial lista"
        self.error = False

    def evaluar_decision(self, comparar: bool = False) -> None:
        """Evaluar el estado vigente con los algoritmos del dominio sin aplicar la acción recomendada.

        Proposito: recomendar acciones de Minimax o alfa-beta desde el estado vigente y producir sus métricas o su
        comparación.
        Precondiciones: el escenario y el estado están cargados; la profundidad y el orden pertenecen a sus dominios.
        Postcondiciones: se guarda el resultado del estado inmutable de entrada sin modificarlo; la comparación, cuando
        se solicita, ejecuta ambas variantes con igual profundidad, utilidad y orden. Las recomendaciones no se aplican.
        Complejidad: O(b^d) en una evaluación; la comparación suma O(b^d) de Minimax y de alfa-beta.
        Uso de IA: Si.
        Intervencion de IA: Codex: conexión de la interfaz con los algoritmos adversariales y su comparador.
        Validacion del estudiante: pruebas ``test_evaluacion_adversarial_usa_configuracion_json_y_no_muta_estado`` y
        ``test_comparacion_verifica_misma_decision_y_muestra_metricas`` de tests/interfaz/test_control.py.
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
        """Validar de forma independiente la recomendación adversarial del estado vigente.

        Proposito: mostrar si la decisión, el árbol y sus métricas son coherentes para el estado actual.
        Precondiciones: existe un resultado adversarial asociado al estado inmutable vigente.
        Postcondiciones: se guarda el reporte de ``verificar_decision``; la partida y la recomendación no cambian.
        Complejidad: O(b^d) por regenerar de forma independiente el árbol completo.
        Uso de IA: Si.
        Intervencion de IA: Codex: conexión de la verificación adversarial del dominio con la interfaz.
        Validacion del estudiante: pruebas de tests/interfaz/test_control.py: comparación verificada con la misma
        decisión e invalidación de la verificación al cambiar el modo o el escenario.
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
        """Exportar un experimento de E10.3 o el registro reproducible de una partida manual.

        Proposito: guardar las búsquedas y decisiones iniciales con el formato de E10.3, y las partidas o decisiones
        posteriores con el formato propio de partidas.
        Precondiciones: existe un resultado vigente de búsqueda o decisión, o una sesión de partida registrable.
        Postcondiciones: se escribe el formato correspondiente; si falta el resultado o hay un error, se informa la
        causa.
        Complejidad: O(N + R) temporal y espacial, con N bytes del escenario y R datos del registro.
        Uso de IA: Si.
        Intervencion de IA: Codex: conexión de la interfaz con el registro reproducible de E10.3 y heurística de A* como
        parámetro reproducible de consola.
        Validacion del estudiante: pruebas ``test_exporta_registro_gui_con_heuristica_y_comando_reproducible`` y
        ``test_exportacion_rechaza_archivo_de_escenario_modificado`` de tests/interfaz/test_control.py.
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
        """Exportar la sesión y, si existe, la evaluación calculada sobre su estado reconstruido.

        Proposito: serializar una copia íntegra del escenario, los eventos legales y el resultado para reproducirlos
        después.
        Precondiciones: se conserva el estado inicial de la sesión y los bytes del escenario no cambiaron.
        Postcondiciones: se escribe el formato ``tacticalgrid.partida/1`` solo si el verificador acepta las acciones
        registradas.
        Complejidad: O(N + T*U) temporal y espacial para N bytes, T acciones y U unidades.
        Uso de IA: Si.
        Intervencion de IA: Codex: conexión del historial manual con la exportación reproducible, incluida la decisión
        posterior a las jugadas.
        Validacion del estudiante: pruebas ``test_exporta_y_reproduce_partida_manual_desde_escenario_embebido`` y
        ``test_reproduce_evaluacion_adversarial_sobre_partida_previamente_jugada`` de tests/interfaz/test_control.py.
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
        """Pedir confirmación en dos interacciones y aplicar una recomendación vigente y legal.

        Proposito: separar explícitamente la evaluación automática de la ejecución efectiva de la jugada.
        Precondiciones: la recomendación pertenece al estado vigente y su acción sigue siendo legal.
        Postcondiciones: sin confirmación solo se prepara la confirmación; al confirmar, la acción se aplica una vez con
        las reglas del dominio, se cambia a partida y se eliminan el resultado, la comparación y el reporte obsoletos.
        Si el estado cambió o la acción es ilegal, se rechaza sin alterar la partida.
        Complejidad: O(U + A) para revalidar la acción y preparar el turno.
        Uso de IA: Si.
        Intervencion de IA: Codex: confirmación y aplicación explícita de la recomendación.
        Validacion del estudiante: pruebas ``test_recomendacion_requiere_confirmacion_y_se_aplica_una_vez`` y
        ``test_recomendacion_se_invalida_si_cambia_estado_o_configuracion`` de tests/interfaz/test_control.py.
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
        """Seleccionar una unidad del turno o ejecutar su acción al pulsar un destino legal.

        Proposito: traducir los clics del tablero en selecciones y acciones validadas por el dominio.
        Precondiciones: la posición proviene de una celda del tablero y el modo actual es partida.
        Postcondiciones: una acción válida crea un estado nuevo, prepara el turno siguiente e invalida los resultados
        anteriores; los clics inválidos conservan el estado y el turno. Las unidades no se mueven por coordenadas
        arbitrarias.
        Complejidad: O(U + A) temporal y espacial por buscar la unidad y la acción y actualizar las opciones del turno.
        Uso de IA: Si.
        Intervencion de IA: Codex: interacción por clic sobre las acciones legales existentes.
        Validacion del estudiante: pruebas de tests/interfaz/test_control.py: movimiento legal con cambio de turno,
        rechazo de unidad rival, destino no legal y obstáculo, recogida del recurso y victoria al entregarlo.
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
        """Agregar al historial una acción ya aceptada y aplicada por las reglas del dominio.

        Proposito: conservar evidencia ordenada de cada transición humana y de cada recomendación ejecutada
        explícitamente.
        Precondiciones: ``estado_previo`` y ``self.estado`` son consecutivos y ``accion`` es legal en el primero.
        Postcondiciones: se agregan al historial el bando, la unidad y la acción, el costo, el pase automático y las
        huellas de ambos estados.
        Complejidad: O(U log U) por las dos huellas canónicas para U unidades.
        Uso de IA: Si.
        Intervencion de IA: Codex: historial verificable y su captura en las acciones de la interfaz (R26).
        Validacion del estudiante: prueba
        ``test_partida_manual_completa_se_reconstruye_y_verifica_recogida_transporte_y_victoria`` de
        tests/interfaz/test_control.py.
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
        """Reemplazar el escenario de forma atómica, solo después de cargarlo por completo.

        Proposito: permitir cambiar de JSON sin dejar desincronizados el escenario, el estado, las selecciones y el
        resultado.
        Precondiciones: ``ruta`` puede apuntar a un archivo válido o inválido.
        Postcondiciones: si la carga tiene éxito, se reinician el estado, el modo, los controles, el camino, la traza y
        los reportes; en modo partida se prepara el turno. Si falla, todo se conserva y se informa el error.
        Complejidad: el costo de carga y validación más O(U log U) para el estado inicial.
        Uso de IA: Si.
        Intervencion de IA: Codex: carga atómica desde los controles para la integración gráfica final e invalidación
        del reporte de verificación.
        Validacion del estudiante: pruebas ``test_carga_invalida_conserva_sesion_completa`` y
        ``test_carga_valida_sustituye_estado_camino_traza_y_selecciones`` de tests/interfaz/test_control.py.
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
        """Cargar un escenario JSON elegido por el usuario y agregarlo a los selectores de escenario.

        Proposito: abrir mapas externos desde la ventana, con el selector de archivos o arrastrando el JSON sobre ella.
        Precondiciones: ``ruta`` puede apuntar a cualquier archivo, válido o no.
        Postcondiciones: si la carga atómica de ``cargar_ruta`` tiene éxito, el escenario queda vigente y su ruta figura
        una sola vez en ``rutas_escenarios``, ordenada con las demás; si falla, la sesión y los selectores no cambian y
        el mensaje explica el error. Se devuelve si se cargó.
        Complejidad: la de ``cargar_ruta`` más O(R log R) por reordenar las R rutas disponibles.
        Uso de IA: Si.
        Intervencion de IA: Claude (Opus 5.5): implementación y documentación (E9.4).
        Validacion del estudiante: pruebas de tests/interfaz/test_control.py: carga de un escenario externo, ruta ya
        listada sin duplicar y archivo inválido que conserva la sesión.
        """
        if not self.cargar_ruta(ruta):
            return False
        if self.ruta_escenario not in self.rutas_escenarios:
            self.rutas_escenarios = tuple(sorted((*self.rutas_escenarios, self.ruta_escenario)))
        return True

    def abrir_con_dialogo(self, seleccionar) -> bool:
        """Pedir un escenario con el selector de archivos y abrirlo.

        Proposito: conectar el botón y la tecla de apertura con la carga atómica sin acoplar el controlador a tkinter.
        Precondiciones: ``seleccionar`` recibe la carpeta inicial y devuelve una ruta, ``None`` si el usuario cancela, o
        lanza ``DialogoNoDisponible``.
        Postcondiciones: con una ruta, el comportamiento es el de ``abrir_escenario``; si el usuario cancela, nada
        cambia y el mensaje lo indica; si no hay selector, nada cambia y el mensaje sugiere arrastrar el archivo a la
        ventana. Se devuelve si se cargó un escenario.
        Complejidad: la de ``abrir_escenario``, más el tiempo que el usuario tarde en elegir.
        Uso de IA: Si.
        Intervencion de IA: Claude (Opus 5.5): implementación y documentación (E9.4).
        Validacion del estudiante: pruebas de tests/interfaz/test_control.py: archivo elegido, selección cancelada y
        selector no disponible.
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
        """Ejecutar una única búsqueda con las selecciones vigentes.

        Proposito: producir a la vez el camino de E9.2 y la traza de E9.3 desde los controles gráficos.
        Precondiciones: el escenario, el estado, el algoritmo y la unidad proceden del controlador; el objetivo puede
        faltar.
        Postcondiciones: con parámetros válidos, se sustituye el resultado anterior y se invalida el reporte previo sin
        modificar el estado; ante un error, se limpia el resultado y se informa la causa. Cada llamada ejecuta como
        máximo una búsqueda.
        Complejidad: la del algoritmo seleccionado y su traza acotada.
        Uso de IA: Si.
        Intervencion de IA: Codex: conexión de los controles con la API común de búsqueda, sin comandos ni subprocesos,
        e invalidación del reporte previo.
        Validacion del estudiante: pruebas de tests/interfaz/test_control.py: cinco algoritmos sin modificar el estado,
        configuración inválida que no ejecuta y elimina el resultado anterior, y bloqueo de ejecuciones simultáneas.
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
        """Verificar la búsqueda, la decisión o el historial de partida vigente.

        Proposito: reproducir las reglas del dominio para verificar búsquedas, recomendaciones o acciones registradas.
        Precondiciones: hay un resultado vigente del modo, o un estado inicial y un historial de partida.
        Postcondiciones: se guarda y se muestra el reporte; el estado de juego y el historial no cambian.
        Complejidad: depende del modo: se reproduce el camino, el árbol adversarial o las T transiciones registradas.
        Uso de IA: Si.
        Intervencion de IA: Codex: integración de E10.2 con los controles gráficos.
        Validacion del estudiante: pruebas de tests/interfaz/test_control.py: verificación independiente de la búsqueda,
        costo alterado rechazado, evento o transición alterados en la partida y limpieza del reporte al cambiar la
        selección.
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
        """Alternar la bandera que comparten la tecla y el botón, sin ejecutar búsquedas."""
        if self.resultado is None or self.resultado.traza_expansiones is None:
            self.mensaje = "La exploracion requiere ejecutar primero una busqueda."
            self.error = True
            return
        self.exploracion_visible = not self.exploracion_visible
        self.mensaje = "Exploracion visible." if self.exploracion_visible else "Exploracion oculta."
        self.error = False
