"""Heurística de distancia topológica con obstáculos (HTO), preparada para un problema de navegación."""

from collections import deque
from types import MappingProxyType
from typing import Mapping

from tacticalgrid.escenario.escenario import Posicion
from tacticalgrid.juego.accion import DESPLAZAMIENTOS
from tacticalgrid.juego.estado import EstadoJuego
from tacticalgrid.juego.problema import ProblemaNavegacion

from .instrumentacion import es_valor_finito


class HeuristicaObstaculos:
    """Precalcular distancias topológicas y estimar por recurrencia sin modificar el estado.

    Proposito: representar HTO como un componente preparado y ligado a un único problema de navegación.
    Precondiciones: el problema usa la topología estática, los movimientos ortogonales y los costos positivos del
    contrato actual de ``ProblemaNavegacion``.
    Postcondiciones: cada consulta proyecta un ``EstadoJuego`` solo para obtener su estimación; las distancias y
    estimaciones preparadas no sustituyen la identidad completa del estado.
    Complejidad: O(R + E) temporal y O(R) espacial al construir; O(U + delta K) temporal por consulta, con delta K los
    valores recurrentes nuevos, y O(R + K) espacial tras solicitar hasta H(K). Para N consultas exitosas el trabajo
    acumulado es O(K + N*U).
    Uso de IA: Si.
    Intervencion de IA: Codex: diseño e implementación de HTO, correcciones de contexto y de recurrencia incremental, e
    integración opcional con el motor A* existente (E6.2).
    Validacion del estudiante: pruebas de tests/algoritmos/test_heuristica_obstaculos.py y comparación de HTO con
    Manhattan sobre el mismo escenario en tests/algoritmos/test_casos_minimos_heuristicas.py (caso mínimo 4).
    """

    def __init__(self, problema: ProblemaNavegacion) -> None:
        """Preparar HTO para la topología, el objetivo y la escala de un problema concreto.

        Proposito: ejecutar una sola vez el BFS inverso e inicializar el prefijo numérico que luego extienden las
        consultas bajo demanda.
        Precondiciones: ``problema`` cumple el contrato de ``ProblemaNavegacion`` y su costo mínimo es positivo y
        finito.
        Postcondiciones: se conserva una tabla inmutable con las R posiciones alcanzables y una secuencia que contiene
        solo H(0); si el objetivo no es transitable, la tabla vacía representa la política de heurística cero.
        Complejidad: O(R + E) temporal y O(R) espacial para el BFS; la captura del contexto y H(0) son O(1).
        Uso de IA: Si.
        Intervencion de IA: Codex: BFS inverso e inicialización exclusiva de H(0) en lugar de la preparación numérica
        completa, como corrección del hallazgo E62-M01.
        Validacion del estudiante: pruebas de tests/algoritmos/test_heuristica_obstaculos.py: distancias en cuadrícula
        abierta y corredor, objetivo no transitable y preparación solo hasta H(1) con costo extremo adyacente.
        """
        self.problema = problema
        self._problema_preparado = problema
        self._escenario_preparado = problema.escenario
        self._objetivo_preparado = problema.objetivo
        self._identificador_unidad_preparado = problema.identificador_unidad
        self._costo_minimo_preparado = problema.costo_minimo_paso
        distancias = self._calcular_distancias()
        self._distancias: Mapping[Posicion, int] = MappingProxyType(distancias)
        self._estimaciones: list[int | float] = [0]

    @property
    def distancias(self) -> Mapping[Posicion, int]:
        """Vista inmutable de las distancias topológicas preparadas."""
        return self._distancias

    @property
    def estimaciones(self) -> tuple[int | float, ...]:
        """Copia inmutable del prefijo finito preparado, en O(K) temporal y espacial."""
        return tuple(self._estimaciones)

    def evaluar(self, estado: EstadoJuego) -> int | float:
        """Consultar HTO para el estado completo sin alterar su identidad.

        Proposito: proyectar el estado a la posición de la unidad navegante y devolver el valor H de su distancia.
        Precondiciones: ``estado`` contiene la unidad identificada por el problema usado durante la preparación.
        Postcondiciones: se devuelve cero en el objetivo o si la posición no tiene distancia preparada; en otro caso se
        extiende el prefijo y se devuelve el valor recurrente finito asociado. Si el contexto cambió, se lanza
        ``ValueError`` antes de usar las tablas o extender el prefijo. El estado, el problema y las distancias no
        cambian.
        Complejidad: O(U + delta K) temporal, con U unidades y delta K valores nuevos; O(delta K) espacial persistente.
        Una consulta ya preparada cuesta O(U); N consultas exitosas cuestan O(K + N*U).
        Uso de IA: Si.
        Intervencion de IA: Codex: consulta posicional, validación del contexto, extensión numérica bajo demanda y
        política de cero para posiciones externas, no transitables o desconectadas.
        Validacion del estudiante: pruebas de tests/algoritmos/test_heuristica_obstaculos.py: valor cero en el objetivo
        y en componentes desconectadas, estimación compartida por estados compuestos con igual posición, rechazo de
        valores no finitos y propiedades exhaustivas en mapas de 3x3.
        """
        self._validar_contexto()
        posicion = self.problema.posicion(estado)
        if posicion == self._objetivo_preparado:
            return 0
        distancia = self._distancias.get(posicion)
        if distancia is None:
            return 0
        return self._obtener_estimacion(distancia)

    def _validar_contexto(self) -> None:
        """Impedir consultas sobre tablas preparadas con un contexto de navegación incompatible.

        Proposito: detectar antes de evaluar las reasignaciones que invalidan la topología, el objetivo, la unidad
        proyectada o la escala numérica de HTO.
        Precondiciones: el componente se construyó con una instancia válida de ``ProblemaNavegacion``; el ``Escenario``
        del contrato actual es internamente inmutable.
        Postcondiciones: ningún objeto cambia; la función retorna si el contexto conserva las referencias y valores
        preparados, o lanza ``ValueError`` con los campos modificados.
        Complejidad: O(1) temporal respecto de celdas, terrenos y unidades, y O(1) espacial.
        Uso de IA: Si.
        Intervencion de IA: Codex: guarda de contexto como corrección del hallazgo E62-A01, sin recorrer la topología en
        cada consulta ni reconstruir el preprocesamiento de forma silenciosa.
        Validacion del estudiante: pruebas de tests/algoritmos/test_heuristica_obstaculos.py que rechazan el cambio de
        objetivo, de escenario, de unidad navegante, de costo mínimo y el reemplazo del problema.
        """
        cambios = []
        if self.problema is not self._problema_preparado:
            cambios.append("problema")
        else:
            if self.problema.escenario is not self._escenario_preparado:
                cambios.append("escenario")
            if self.problema.objetivo != self._objetivo_preparado:
                cambios.append("objetivo")
            if self.problema.identificador_unidad != self._identificador_unidad_preparado:
                cambios.append("identificador_unidad")
            if self.problema.costo_minimo_paso != self._costo_minimo_preparado:
                cambios.append("costo_minimo_paso")
        if cambios:
            campos = ", ".join(cambios)
            raise ValueError(
                "El contexto de ProblemaNavegacion cambio despues de preparar HTO "
                f"({campos}); construya una nueva HeuristicaObstaculos."
            )

    def _calcular_distancias(self) -> dict[Posicion, int]:
        """Calcular por BFS inverso la distancia en pasos hasta el objetivo.

        Proposito: construir la relajación topológica no ponderada que usa HTO, sin materializar una lista de aristas.
        Precondiciones: el objetivo está dentro de los límites del escenario y la transitabilidad es estática.
        Postcondiciones: se devuelve la distancia mínima entera de cada posición del componente transitable del
        objetivo, o un diccionario vacío si el objetivo no es transitable. No se consultan ni modifican estados de
        juego.
        Complejidad: O(R + E) temporal y O(R) espacial, con R las posiciones alcanzables desde el objetivo.
        Uso de IA: Si.
        Intervencion de IA: Codex: recorrido desde el objetivo con vecinos ortogonales calculados sobre la cuadrícula
        del escenario.
        Validacion del estudiante: pruebas de tests/algoritmos/test_heuristica_obstaculos.py: distancias conocidas en
        cuadrícula abierta, rodeo de una barrera y tablas distintas para objetivos y topologías distintos.
        """
        escenario = self.problema.escenario
        objetivo = self.problema.objetivo
        if not escenario.contiene_posicion(objetivo) or not escenario.es_transitable(objetivo):
            return {}

        distancias = {objetivo: 0}
        frontera = deque([objetivo])
        while frontera:
            actual = frontera.popleft()
            siguiente_distancia = distancias[actual] + 1
            for delta_fila, delta_columna in DESPLAZAMIENTOS:
                vecina = Posicion(actual.fila + delta_fila, actual.columna + delta_columna)
                if (
                    vecina not in distancias
                    and escenario.contiene_posicion(vecina)
                    and escenario.es_transitable(vecina)
                ):
                    distancias[vecina] = siguiente_distancia
                    frontera.append(vecina)
        return distancias

    def _obtener_estimacion(self, distancia_solicitada: int) -> int | float:
        """Extender bajo demanda el prefijo H(k) mediante sumas secuenciales.

        Proposito: obtener H(k) sin multiplicación directa y sin recalcular valores recurrentes ya preparados.
        Precondiciones: ``distancia_solicitada`` es una distancia no negativa de la tabla topológica y el contexto está
        validado; ``costo_minimo_paso`` es positivo y finito.
        Postcondiciones: se devuelve H(distancia_solicitada) finito y se conserva el prefijo ampliado; si falla H(j), se
        lanza ``ValueError`` con la distancia solicitada y j, sin almacenar el valor inválido y conservando
        H(0)..H(j-1).
        Complejidad: O(delta K) temporal y espacial persistente, con delta K la cantidad de valores nuevos; O(1) si
        H(distancia_solicitada) ya estaba preparado. Una secuencia arbitraria de fallos puede repetir el intento no
        representable y no queda cubierta por la amortización de consultas exitosas.
        Uso de IA: Si.
        Intervencion de IA: Codex: extensión incremental en lugar de la recurrencia anticipada, con conservación del
        prefijo finito ante fallos numéricos, como corrección del hallazgo E62-M01.
        Validacion del estudiante: pruebas de tests/algoritmos/test_heuristica_obstaculos.py: recurrencia con costos
        enteros y decimales, conservación del prefijo ante desbordamiento, independencia del orden de las consultas y
        consultas repetidas sin recálculo.
        """
        for distancia in range(len(self._estimaciones), distancia_solicitada + 1):
            try:
                estimacion = self._estimaciones[-1] + self._costo_minimo_preparado
            except OverflowError as error:
                raise ValueError(
                    "La recurrencia HTO excede el rango numerico finito soportado "
                    f"al solicitar H({distancia_solicitada}); fallo al calcular H({distancia}) "
                    f"con costo_minimo_paso={self._costo_minimo_preparado!r}."
                ) from error
            if not es_valor_finito(estimacion):
                raise ValueError(
                    "La recurrencia HTO excede el rango numerico finito soportado "
                    f"al solicitar H({distancia_solicitada}); fallo al calcular H({distancia}) "
                    f"con costo_minimo_paso={self._costo_minimo_preparado!r}."
                )
            self._estimaciones.append(estimacion)
        estimacion = self._estimaciones[distancia_solicitada]
        if not es_valor_finito(estimacion):
            raise ValueError(
                f"La consulta HTO produjo un valor no finito para la distancia topologica {distancia_solicitada}."
            )
        return estimacion
