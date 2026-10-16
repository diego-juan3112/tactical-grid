"""Heuristica de distancia topologica con obstaculos preparada para un problema de navegacion."""

from collections import deque
from types import MappingProxyType
from typing import Mapping

from tacticalgrid.escenario.escenario import Posicion
from tacticalgrid.juego.accion import DESPLAZAMIENTOS
from tacticalgrid.juego.estado import EstadoJuego
from tacticalgrid.juego.problema import ProblemaNavegacion

from .instrumentacion import es_valor_finito


class HeuristicaObstaculos:
    """Precalcula distancias topologicas y estima por recurrencia sin modificar el estado.

    Purpose: representar HTO como un componente preparado y ligado a un unico problema de navegacion.
    Preconditions: el problema usa la topologia estatica, los movimientos ortogonales y los costos positivos del
    contrato actual de ``ProblemaNavegacion``.
    Postconditions: cada consulta proyecta un ``EstadoJuego`` solo para obtener su estimacion; las distancias y
    estimaciones preparadas no sustituyen la identidad completa del estado.
    Complexity: O(R + E) temporal y O(R) espacial al construir; O(U + delta K) temporal por consulta, donde
    delta K son los valores recurrentes nuevos, y O(R + K) espacial tras solicitar hasta H(K). Para N consultas
    exitosas el trabajo acumulado es O(K + N*U).
    AI usage: Yes.
    AI intervention: Codex diseno e implemento HTO, sus correcciones de contexto y recurrencia incremental, y su
    integracion opcional con el motor A* existente conforme a E6.2.
    Student validation: pendiente de revision humana del equipo.
    """

    def __init__(self, problema: ProblemaNavegacion) -> None:
        """Prepara HTO para la topologia, el objetivo y la escala de un problema concreto.

        Purpose: ejecutar una sola vez el BFS inverso e inicializar el prefijo numerico que luego extenderan las
        consultas bajo demanda.
        Preconditions: problema cumple el contrato de ProblemaNavegacion y su costo minimo es positivo y finito.
        Postconditions: conserva una tabla inmutable con las R posiciones alcanzables y una secuencia que contiene
        solo H(0); si el objetivo no es transitable, la tabla vacia representa la politica de heuristica cero.
        Complexity: O(R + E) temporal y O(R) espacial para el BFS; la captura del contexto y H(0) son O(1).
        AI usage: Yes.
        AI intervention: Codex implemento el BFS inverso y cambio la preparacion numerica completa por la
        inicializacion exclusiva de H(0) para corregir E62-M01.
        Student validation: pendiente de revision humana del equipo.
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
        """Expone una vista inmutable de las distancias topologicas preparadas."""
        return self._distancias

    @property
    def estimaciones(self) -> tuple[int | float, ...]:
        """Expone una copia inmutable del prefijo finito preparado, en O(K) temporal y espacial."""
        return tuple(self._estimaciones)

    def evaluar(self, estado: EstadoJuego) -> int | float:
        """Consulta HTO para el estado completo sin alterar su identidad.

        Purpose: proyectar el estado a la posicion de la unidad navegante y devolver el valor H de su distancia.
        Preconditions: estado contiene la unidad identificada por el problema usado durante la preparacion.
        Postconditions: devuelve cero en el objetivo o si la posicion no tiene distancia preparada; en otro caso
        extiende el prefijo y devuelve el valor recurrente finito asociado. Si el contexto cambio, lanza
        ``ValueError`` antes de usar las tablas o extender el prefijo. No modifica estado, problema ni distancias.
        Complexity: O(U + delta K) temporal, donde U son las unidades y delta K los valores nuevos; O(delta K)
        espacial persistente. Una consulta ya preparada cuesta O(U); N consultas exitosas cuestan O(K + N*U).
        AI usage: Yes.
        AI intervention: Codex implemento la consulta posicional, la validacion del contexto, la extension numerica
        bajo demanda y la politica de cero para posiciones externas, no transitables o desconectadas.
        Student validation: pendiente de revision humana del equipo.
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
        """Impide consultar tablas preparadas con un contexto de navegacion incompatible.

        Purpose: detectar antes de evaluar las reasignaciones que invalidan la topologia, el objetivo, la unidad
        proyectada o la escala numerica de HTO.
        Preconditions: el componente fue construido con una instancia de ``ProblemaNavegacion`` valida; el
        ``Escenario`` del contrato actual es internamente inmutable.
        Postconditions: no modifica ningun objeto; retorna si el contexto conserva las referencias y valores
        preparados, o lanza ``ValueError`` identificando los campos modificados.
        Complexity: O(1) temporal respecto de celdas, terrenos y unidades, y O(1) espacial.
        AI usage: Yes.
        AI intervention: Codex incorporo la guarda de contexto para corregir E62-A01 sin recorrer la topologia en
        cada consulta ni reconstruir silenciosamente el preprocesamiento.
        Student validation: pendiente de revision humana del equipo; cubierta por pruebas de regresion de las
        reasignaciones permitidas por ``ProblemaNavegacion``.
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
        """Calcula por BFS inverso la distancia en pasos hasta el objetivo.

        Purpose: construir la relajacion topologica no ponderada usada por HTO sin materializar una lista de aristas.
        Preconditions: el objetivo pertenece a los limites del escenario y la transitabilidad es estatica.
        Postconditions: devuelve la distancia minima entera para cada posicion del componente transitable del
        objetivo, o un diccionario vacio si el objetivo no es transitable. No consulta ni modifica estados de juego.
        Complexity: O(R + E) temporal y O(R) espacial, donde R son las posiciones alcanzables desde el objetivo.
        AI usage: Yes.
        AI intervention: Codex implemento el recorrido desde el objetivo con vecinos ortogonales calculados sobre la
        cuadricula del escenario.
        Student validation: pendiente de revision humana del equipo.
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
        """Extiende bajo demanda el prefijo H(k) mediante sumas secuenciales.

        Purpose: obtener H(k) sin multiplicacion directa ni recalcular valores recurrentes ya preparados.
        Preconditions: distancia_solicitada es una distancia no negativa de la tabla topologica y el contexto fue
        validado; costo_minimo_paso es positivo y finito.
        Postconditions: devuelve H(distancia_solicitada) finito y conserva el prefijo ampliado; si falla H(j), lanza
        ValueError con la distancia solicitada y j, no almacena el valor invalido y conserva H(0)..H(j-1).
        Complexity: O(delta K) temporal y espacial persistente, donde delta K es la cantidad de valores nuevos;
        O(1) si H(distancia_solicitada) ya estaba preparado. Una secuencia arbitraria de fallos puede repetir el
        intento no representable y no queda cubierta por la amortizacion de consultas exitosas.
        AI usage: Yes.
        AI intervention: Codex cambio la recurrencia anticipada por extension incremental, preservando el prefijo
        finito ante fallos numericos para corregir E62-M01.
        Student validation: pendiente de revision humana del equipo.
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
