"""Estado transitorio y operaciones de los controles de la aplicacion grafica."""

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from tacticalgrid.algoritmos import ResultadoBusqueda, validar_ancho_haz
from tacticalgrid.escenario import Posicion, cargar_escenario
from tacticalgrid.escenario.escenario import Escenario
from tacticalgrid.juego import EstadoJuego, crear_estado_inicial

from .busquedas import ALGORITMOS, preparar_busqueda, resolver_objetivo
from .dialogo import DialogoNoDisponible


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
    resultado: ResultadoBusqueda | None = None
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
        Postcondiciones: devuelve controles con unidad existente, configuracion reutilizable y resultado vacio.
        Complejidad: O(U log U + R log R) por crear el estado y normalizar R rutas disponibles.
        Uso de IA: Si.
        Intervencion de IA: Codex diseño el controlador de sesion para la integracion grafica final de E9.3.
        Validacion del estudiante: revisado y aprobado por el equipo; cubierta por pruebas de carga y selecciones
        iniciales.
        """
        ruta_resuelta = Path(ruta).resolve()
        escenario = cargar_escenario(ruta_resuelta)
        estado = crear_estado_inicial(escenario)
        rutas = tuple(sorted({Path(item).resolve() for item in rutas_disponibles} | {ruta_resuelta}))
        algoritmo, unidad, objetivo, k = cls._selecciones_iniciales(escenario, estado)
        return cls(rutas, ruta_resuelta, escenario, estado, algoritmo, unidad, objetivo, k)

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

    def _invalidar_resultado(self, mensaje: str) -> None:
        self.resultado = None
        self.exploracion_visible = False
        self.mensaje = mensaje
        self.error = False
        self.estado_busqueda = "configuracion lista"

    def cambiar_algoritmo(self, paso: int) -> None:
        indice = (ALGORITMOS.index(self.algoritmo) + paso) % len(ALGORITMOS)
        self.algoritmo = ALGORITMOS[indice]
        self._invalidar_resultado("Algoritmo actualizado; ejecute una busqueda.")

    def cambiar_unidad(self, paso: int) -> None:
        unidades = self.unidades
        if not unidades:
            self.mensaje = "El escenario no contiene unidades seleccionables."
            self.error = True
            self.estado_busqueda = "error de configuracion"
            return
        if self.unidad is None:
            self.unidad = unidades[0]
            self._invalidar_resultado("Unidad actualizada; ejecute una busqueda.")
            return
        indice = (unidades.index(self.unidad) + paso) % len(unidades)
        self.unidad = unidades[indice]
        self._invalidar_resultado("Unidad actualizada; ejecute una busqueda.")

    def cambiar_k(self, paso: int) -> None:
        if self.algoritmo != "beam":
            return
        self.k = validar_ancho_haz(max(1, self.k + paso))
        self._invalidar_resultado("Ancho de Beam actualizado; ejecute una busqueda.")

    def seleccionar_objetivo(self, posicion: Posicion) -> None:
        if not self.escenario.contiene_posicion(posicion) or not self.escenario.es_transitable(posicion):
            self.mensaje = "El objetivo debe ser una celda transitable."
            self.error = True
            self.resultado = None
            self.exploracion_visible = False
            self.estado_busqueda = "error de configuracion"
            return
        self.objetivo = posicion
        self._invalidar_resultado("Objetivo actualizado; ejecute una busqueda.")

    def cargar_ruta(self, ruta: str | Path) -> bool:
        """Reemplaza atomicamente el escenario solo despues de cargarlo por completo.

        Proposito: permitir cambiar de JSON sin dejar escenario, estado, selecciones y resultado desincronizados.
        Precondiciones: ``ruta`` puede apuntar a un archivo valido o invalido.
        Postcondiciones: con exito reinicia estado, controles, camino y traza; ante error conserva todo y lo informa.
        Complejidad: costo de carga y validacion mas O(U log U) para el estado inicial.
        Uso de IA: Si.
        Intervencion de IA: Codex implemento la carga atomica desde controles para la integracion grafica final.
        Validacion del estudiante: revisado y aprobado por el equipo; cubierta por pruebas de carga valida e invalida.
        """
        ruta_resuelta = Path(ruta).resolve()
        try:
            escenario = cargar_escenario(ruta_resuelta)
            estado = crear_estado_inicial(escenario)
            algoritmo, unidad, objetivo, k = self._selecciones_iniciales(escenario, estado)
        except (OSError, ValueError) as error:
            self.mensaje = f"No se pudo cargar: {error}"
            self.error = True
            self.estado_busqueda = "error de carga"
            return False
        self.ruta_escenario = ruta_resuelta
        self.escenario = escenario
        self.estado = estado
        self.algoritmo = algoritmo
        self.unidad = unidad
        self.objetivo = objetivo
        self.k = k
        self.resultado = None
        self.exploracion_visible = False
        self.mensaje = f"Escenario cargado: {ruta_resuelta.name}"
        self.error = False
        self.estado_busqueda = "configuracion lista"
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
        Postcondiciones: con parametros validos sustituye el resultado anterior sin mutar el estado; ante error limpia
        el resultado e informa la causa. Nunca ejecuta mas de una busqueda por llamada.
        Complejidad: la del algoritmo seleccionado y su traza acotada.
        Uso de IA: Si.
        Intervencion de IA: Codex conecto los controles a la API comun de busqueda sin comandos ni subprocesos.
        Validacion del estudiante: revisado y aprobado por el equipo; cubierta por pruebas de cinco algoritmos y no
        mutacion.
        """
        if self.ejecutando:
            return
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
        self.mensaje = "Busqueda finalizada." if self.resultado.exito else "Busqueda finalizada sin solucion."
        self.error = False
        self.estado_busqueda = "completada" if self.resultado.exito else "sin solucion"

    def alternar_exploracion(self) -> None:
        """Alterna la misma bandera usada por teclado y boton, sin ejecutar busquedas."""
        if self.resultado is None or self.resultado.traza_expansiones is None:
            self.mensaje = "La exploracion requiere ejecutar primero una busqueda."
            self.error = True
            return
        self.exploracion_visible = not self.exploracion_visible
        self.mensaje = "Exploracion visible." if self.exploracion_visible else "Exploracion oculta."
        self.error = False
