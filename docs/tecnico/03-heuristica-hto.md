# E6.2: Segunda heurística propia

## 1. Estado de la propuesta y la implementación

Este documento define, justifica y registra la implementación de una segunda heurística para
`ProblemaNavegacion`. `HeuristicaObstaculos` (HTO) está integrada programáticamente con A* mediante una estrategia
preparada opcional; Manhattan continúa siendo el comportamiento predeterminado. La integración, sus pruebas y la
campaña experimental definitiva están implementadas y auditadas. La aprobación estudiantil y docente permanece
pendiente; por eso E6.2 no se considera terminada.

**Implementado:**

- componente HTO, con BFS inverso y tabla de distancias topológicas enteras;
- consulta desde `EstadoJuego` mediante proyección a la posición de la unidad navegante;
- recurrencia numérica incremental bajo demanda;
- validación del contexto preparado para corregir E62-A01;
- manejo de desbordamientos y conservación del prefijo finito para corregir E62-M01;
- selección opcional de una heurística preparada en `busqueda_a_estrella`, sin duplicar el motor;
- Manhattan como estrategia predeterminada y rechazo controlado de estrategias ligadas a otro problema;
- pruebas funcionales, de regresión, integración, casos límite y propiedades con oráculos independientes;
- script comparativo y campaña experimental definitiva con evidencia persistente verificable.

**Limitación de interfaz:**

- la interfaz/CLI no invoca A* ni ofrece selección de heurística; la API conserva Manhattan como comportamiento
  predeterminado. Esta limitación no afecta la integración programática ni el script experimental.

**Pendiente:** validación real del equipo estudiantil, evaluación docente, revisión final de la entrega,
incorporación manual de los archivos al control de versiones y Pull Request correspondiente.

La propuesta adapta técnicas conocidas: distancias mínimas en grafos sin pesos y BFS inverso. No presenta esos
conceptos como una invención. El aporte propuesto por el equipo consiste en definir la relajación apropiada para
TacticalGrid, demostrar su relación con el estado compuesto, integrar los costos configurables, separar
preprocesamiento y consulta, tratar posiciones sin conexión e integrarla con el motor A* existente. La aceptación
final de esta adaptación como heurística "propia" corresponde al docente y permanece pendiente.

## 2. Problema que intenta resolver

La heurística Manhattan de E6.1 usa la diferencia de filas y columnas entre la unidad y el objetivo. Esa estimación
ignora los obstáculos. En `obstaculo_rodeo.json`, la unidad A1 empieza a distancia Manhattan 3 del objetivo, pero los
muros obligan a recorrer 15 movimientos.

La segunda heurística estima la cantidad mínima de movimientos ortogonales que necesita la unidad cuando respeta
los obstáculos estáticos del escenario. Después convierte esa distancia en una cota de costo mediante el menor costo
de terreno transitable declarado en el JSON.

## 3. Información utilizada

La heurística usa estos datos:

- la posición de la unidad navegante en `EstadoJuego`;
- la posición objetivo de `ProblemaNavegacion`;
- las dimensiones y la transitabilidad del escenario cargado;
- `costo_minimo_paso`, calculado a partir de los terrenos transitables del escenario.

La heurística no usa el turno, el portador del recurso, la posición del recurso, las posiciones de las demás unidades
ni `estado_partida`. `ProblemaNavegacion` tampoco usa esos campos para habilitar movimientos o calcular costos. Las
demás unidades no bloquean y el turno se conserva durante la navegación.

La propuesta se apoya en estas partes del repositorio:

- `src/tacticalgrid/juego/accion.py`: define los cuatro desplazamientos ortogonales;
- `src/tacticalgrid/juego/reglas.py`: genera movimientos transitables y obtiene el costo del terreno destino;
- `src/tacticalgrid/juego/problema.py`: fija la unidad, el objetivo y `costo_minimo_paso`;
- `src/tacticalgrid/algoritmos/busqueda_a_estrella.py`: conserva el estado completo y usa `g + h` como prioridad;
- `src/tacticalgrid/algoritmos/heuristica_obstaculos.py`: implementa BFS, contexto y recurrencia bajo demanda;
- `tests/escenario/test_escenarios_propios.py`: verifica las longitudes y costos usados en los casos experimentales;
- `tests/algoritmos/test_busqueda_a_estrella.py`: compara el costo obtenido por A* con el de UCS;
- `tests/algoritmos/test_heuristica_obstaculos.py`: verifica HTO con casos concretos y propiedades.

## 4. Modelo formal

Se distinguen los siguientes conjuntos:

- \(S\): estados completos que puede recibir o producir `ProblemaNavegacion`;
- \(Q\): posiciones representables por `Posicion`, es decir, pares de coordenadas enteras, incluso fuera del mapa;
- \(P\subset Q\): posiciones dentro de los límites del escenario;
- \(V_P\subseteq P\): posiciones cuyo terreno es transitable;
- \(\pi:S\rightarrow Q\): posición de la unidad navegante dentro del estado completo.

El escenario validado coloca sus unidades iniciales en \(V_P\), pero `ProblemaNavegacion` también acepta un
`estado_inicial` externo y solo comprueba que contenga la unidad indicada. Por eso no se presupone que todo estado
aceptado cumple \(\pi(s)\in V_P\).

Sea el grafo de navegación estática:

\[
G_P=(V_P,E_P)
\]

Existe una arista no ponderada entre dos vértices de \(V_P\) cuando son ortogonalmente adyacentes. La topología de
este grafo es no dirigida porque la transitabilidad depende de la celda y cada desplazamiento ortogonal entre dos
celdas transitables puede recorrerse en ambos sentidos.

Sea:

- \(t\in P\): posición objetivo; el constructor exige que esté dentro del mapa, pero no que sea transitable;
- \(c_{\min}>0\): menor costo de un terreno transitable;
- \(d_{\text{obst}}(p,t)\): cantidad mínima de aristas entre `p` y `t` en \(G_P\).

La heurística propuesta es:

\[
h_{\text{obst}}(s)=
\begin{cases}
d_{\text{obst}}(\pi(s),t)\cdot c_{\min}, &
    \text{si }t\in V_P,\ \pi(s)\in V_P\text{ y ambas están conectadas}\\
0, & \text{en otro caso}
\end{cases}
\]

La segunda rama cubre objetivos no transitables, posiciones no transitables o externas y posiciones fuera del
componente conectado del objetivo. El valor cero evita introducir infinito en la prioridad de A* y mantiene una
cota inferior válida. Esta definición es matemática sobre números reales; la política para operaciones `float` se
analiza por separado en la sección 7.1.

## 5. Relación entre el estado real y el grafo de posiciones

El A* actual conserva `EstadoJuego` como identidad en sus diccionarios de costos. HTO recibe el estado completo y
consulta una proyección posicional; la integración no sustituye la identidad del estado por esa posición.

Para un estado cuya posición pertenece a \(V_P\), cada transición válida de `ProblemaNavegacion` cumple estas
propiedades:

1. mueve la unidad navegante una celda ortogonal;
2. llega a una celda transitable;
3. se proyecta sobre una arista de \(G_P\);
4. cuesta lo declarado para el terreno destino;
5. cuesta al menos \(c_{\min}\).

Los cambios en el recurso o en `estado_partida` no eliminan movimientos de navegación ni cambian su costo. Por eso,
toda ruta real que comienza en \(V_P\) produce una ruta válida en el grafo de posiciones. El grafo descarta
información del estado, pero no inventa atajos que atraviesen obstáculos.

Existe un caso de borde permitido por la implementación: un `estado_inicial` externo puede colocar la unidad fuera
de \(V_P\). `generar_movimientos` valida que el destino esté dentro del mapa y sea transitable, pero no comprueba la
transitabilidad del origen. Por tanto, desde una celda no transitable, e incluso desde una posición externa adyacente
al mapa, puede existir una primera transición hacia \(V_P\). Esa transición no es una arista de \(G_P\), porque su
origen no es un vértice. La heurística devuelve cero en el origen; después de esa primera transición, toda posición
sucesora pertenece a \(V_P\). No puede existir la transición inversa hacia el origen no transitable, porque este no
sería un destino válido.

Esta relación depende de las reglas actuales. La demostración debe revisarse si el proyecto agrega diagonales,
saltos, bloqueos dinámicos, costos por unidad o acciones cuyo efecto espacial no corresponda a una arista de
\(G_P\).

## 6. Demostración de admisibilidad

Sea `s` un estado con solución, \(\pi(s)\in V_P\) y conexión con el objetivo. Sea una ruta real óptima desde `s`
hasta un estado objetivo:

\[
s=s_0,s_1,\ldots,s_k
\]

La proyección de esa ruta contiene `k` movimientos válidos en \(G_P\). La definición de distancia mínima garantiza:

\[
d_{\text{obst}}(\pi(s),t)\leq k
\]

Cada movimiento real cuesta al menos \(c_{\min}\). Entonces:

\[
d_{\text{obst}}(\pi(s),t)c_{\min}
\leq kc_{\min}
\leq \sum_{i=0}^{k-1}c(s_i,s_{i+1})
=h^*(s)
\]

También se cumple \(h_{\text{obst}}(s)\geq0\). Por tanto:

\[
0\leq h_{\text{obst}}(s)\leq h^*(s)
\]

Si la posición no pertenece al componente del objetivo, no existe una ruta en el grafo estático. Si la posición
inicial está fuera de \(V_P\), puede existir una ruta real que primero ingrese al grafo. En ambos casos la política
propuesta devuelve cero. Como los costos son positivos, cero sigue siendo una cota inferior del costo de cualquier
solución finita.

Si el objetivo no es transitable, ninguna transición puede entrar en esa celda. La heurística devuelve cero. Un
estado inicial externo ya situado en el objetivo satisface la condición objetivo y también recibe cero. Esta decisión
conserva el comportamiento actual de `ProblemaNavegacion`, cuyo constructor valida los límites del objetivo pero no
exige su transitabilidad.

## 7. Demostración de consistencia

Considere primero una transición válida de `s` a `s'` con posiciones `p` y `p'` pertenecientes a \(V_P\) y
conectadas con el objetivo. Ambas son adyacentes en \(G_P\). La propiedad triangular de la distancia mínima no
ponderada establece:

\[
d_{\text{obst}}(p,t)\leq 1+d_{\text{obst}}(p',t)
\]

Como \(c(s,s')\geq c_{\min}\):

\[
\begin{aligned}
h_{\text{obst}}(s)
&=d_{\text{obst}}(p,t)c_{\min}\\
&\leq c_{\min}+d_{\text{obst}}(p',t)c_{\min}\\
&\leq c(s,s')+h_{\text{obst}}(s')
\end{aligned}
\]

Si \(t\in V_P\), en un estado objetivo \(d_{\text{obst}}(t,t)=0\). Si \(t\notin V_P\), se aplica la segunda rama de
la definición. En ambos casos \(h_{\text{obst}}=0\).

Dos posiciones de \(V_P\) unidas por una arista pertenecen al mismo componente. Si ese componente no contiene el
objetivo, ambas reciben cero y la desigualdad se mantiene. Si `p` está fuera de \(V_P\), la implementación puede
permitir `p -> p'` con `p'` transitable; entonces \(h(p)=0\leq c(s,s')+h(p')\). La transición desde \(V_P\) hacia
una posición no transitable o externa no existe. Estos casos cubren las transiciones admitidas por las reglas actuales.

La prueba anterior usa aritmética real. No demuestra por sí sola las mismas desigualdades para cada operación
binaria de punto flotante.

### 7.1. Política numérica implementada

El siguiente contraejemplo muestra la diferencia entre la multiplicación directa y la acumulación secuencial usada
para `g`:

```python
c = 0.1
h = 6 * c                       # 0.6000000000000001
g = 0.0
for _ in range(6):
    g += c                      # 0.6
assert h > g
```

En un corredor de seis pasos con costo `0.1`, la multiplicación directa sobreestima el costo `float` acumulado por
el algoritmo. También puede romper la consistencia local: para distancias 6 y 5,
`6 * 0.1 == 0.6000000000000001`, mientras que `0.1 + 5 * 0.1 == 0.6`.

Se comparan cuatro políticas:

| Política | Ventaja | Limitación o garantía |
|---|---|---|
| A. Multiplicación directa | O(1), coincide con la fórmula real y con Manhattan actual. | Las guardas de finitud no evitan sobreestimaciones finitas; no garantiza admisibilidad ni consistencia bit a bit. |
| B. Recurrencia `H(0)=0`, `H(k+1)=fl(H(k)+c_min)` | Replica el orden de acumulación de una sucesión de costos mínimos y es la política implementada por HTO. | Requiere supuestos explícitos sobre monotonía y finitud; no resuelve por sí sola la no asociatividad de `g+h`. |
| C. Redondeo conservador | Podría aproximar por debajo bajo una semántica y una cota de error demostradas. | No se ha definido una cota suficiente; una tolerancia arbitraria o un único `math.nextafter()` no cubren errores acumulados. |
| D. Cero global | Es admisible y consistente como heurística y evita toda sobreestimación. | Pierde toda orientación y convierte A* en comportamiento equivalente a UCS respecto de `h`. |

Bajo operaciones finitas no negativas cuya suma `fl` sea monótona, la recurrencia B permite demostrar una propiedad
local. Si \(d(p)\leq d(p')+1\), la monotonía de la sucesión \(H\) y que \(c(s,s')\geq c_{\min}\) dan:

\[
H(d(p))\leq H(d(p')+1)
=\operatorname{fl}(H(d(p'))+c_{\min})
\leq\operatorname{fl}(H(d(p'))+c(s,s')).
\]

También, para un camino de `k` pasos cuyo costo se acumula secuencialmente desde cero, la monotonía permite comparar
por inducción \(H(k)\) con esa acumulación, siempre que todas las operaciones permanezcan dentro del dominio finito
soportado. Como \(d_{\text{obst}}\leq k\), se obtiene una cota respecto de ese costo `float` secuencial.

Estas propiedades locales no demuestran automáticamente la optimalidad global bit a bit de A*: `g`, `h` y `g+h`
se agrupan de formas distintas, las sumas no son asociativas y A* realiza comparaciones estrictas. Tampoco prueban que
la recurrencia sea una cota inferior del costo matemático exacto; su referencia es la semántica secuencial `float`
especificada.

La implementación selecciona B, donde `fl` es el resultado de la suma ejecutada por Python para los operandos
numéricos del problema. Inicia la secuencia exclusivamente con `H(0)=0` y la extiende en orden ascendente cuando una
consulta necesita una distancia todavía no preparada. Cada valor parte del último valor finito disponible; no se usa
multiplicación directa ni se recalcula la secuencia desde cero. Consultar distancias en distinto orden produce el
mismo prefijo porque toda ampliación sigue la misma recurrencia ascendente.

Si una suma produce un valor no finito, HTO lanza `ValueError` antes de incorporarlo. El prefijo finito previo queda
disponible y un intento posterior de calcular el mismo valor no representable vuelve a fallar de forma controlada.
La recurrencia no ofrece exactitud matemática sobre números reales: puede redondear hacia arriba o hacia abajo. Su
garantía demostrada se refiere a acumulaciones secuenciales `float`, finitas y no negativas, bajo la monotonía de la
suma redondeada y la precondición de que cada costo de paso sea al menos `costo_minimo_paso`.

Estas propiedades aisladas no demuestran automáticamente la optimalidad global bit a bit de A*. La integración
conserva el rechazo de costos, estimaciones y prioridades no finitas de E6.1; no se usan infinito ni NaN como
prioridades.

### 7.2. E62-A01: validación del contexto preparado

La implementación inicial podía conservar una tabla calculada para un objetivo y reutilizarla después de reasignar
datos del `ProblemaNavegacion`. Eso permitía consultar distancias obsoletas y producir una estimación incompatible con
el problema vigente.

La corrección captura durante la construcción la identidad del problema, la identidad del escenario, el objetivo, el
identificador de la unidad y el costo mínimo. `evaluar()` valida ese contexto antes de localizar la unidad, consultar
distancias o extender la secuencia. Si detecta un cambio, lanza `ValueError`, identifica las dependencias modificadas
y exige construir una nueva HTO. La comparación por identidad de problema y escenario mantiene la validación en
tiempo constante respecto del tamaño del mapa; objetivo, identificador y costo se comparan por valor.

La garantía cubre las reasignaciones permitidas por los objetos del contrato actual. No pretende proteger contra
manipulación deliberada de atributos privados, uso de `object.__setattr__` para violar objetos congelados ni mutación
concurrente sin sincronización.

### 7.3. E62-M01: recurrencia incremental bajo demanda

La implementación inicial preparaba `H(0)` hasta `H(D)`, donde `D` era la máxima distancia topológica. Podía fallar
durante la construcción por un valor distante no representable, aunque ninguna consulta necesitara esa estimación.

La corrección mantiene separado el BFS de la escala numérica: el BFS se ejecuta una vez y precalcula todas las
distancias enteras alcanzables, mientras la secuencia numérica comienza solo con `H(0)` y crece al consultarse. En un
corredor de tres celdas con `costo_minimo_paso=1e308`, la construcción es válida, `H(0)=0` y `H(1)=1e308`; solicitar
`H(2)` produce un valor no finito y causa `ValueError`, sin eliminar `H(0)` ni `H(1)`.

E62-M01 evita desbordamientos anticipados causados por estimaciones nunca consultadas. No elimina los desbordamientos
de valores que sí se solicitan ni los que puedan aparecer posteriormente al calcular costos acumulados o `g+h`.

## 8. Comparación con Manhattan

La heurística Manhattan de E6.1 es:

\[
h_M(s)=\left(|f_s-f_t|+|c_s-c_t|\right)c_{\min}
\]

En aritmética real, para una posición conectada con el objetivo, cualquier camino ortogonal necesita al menos la
distancia Manhattan:

\[
d_{\text{obst}}(\pi(s),t)\geq d_M(\pi(s),t)
\]

Por tanto:

\[
h_{\text{obst}}(s)\geq h_M(s)
\]

La desigualdad puede ser estricta cuando un muro obliga a rodear. Ambas heurísticas matemáticas coinciden si existe
un camino transitable cuya longitud equivale a Manhattan. Para posiciones desconectadas, la política asigna cero a
la heurística propuesta; la relación de dominancia no aplica en ese caso sin solución. Una política `float` distinta
para HTO y la multiplicación directa de Manhattan tampoco hereda automáticamente esta dominancia bit a bit.

Las dos heurísticas ignoran la distribución de costos. Un camino corto con pantano puede ser más caro que un rodeo
por camino. La segunda heurística mejora la información sobre obstáculos, pero no estima qué combinación de terrenos
produce el menor costo.

Una heurística dominante no garantiza menor tiempo total. El preprocesamiento consume tiempo y los empates de `f`,
el orden de sucesores y el tamaño del escenario influyen en las métricas observadas.

## 9. Construcción y costo computacional

HTO ejecuta BFS desde el objetivo sobre \(G_P\) durante su construcción. El recorrido calcula una tabla inmutable de
distancias topológicas enteras: para cada posición alcanzable almacena exclusivamente la cantidad mínima de movimientos
hasta el objetivo. No almacena costos ponderados. La escala numérica se conserva en una secuencia separada y diferida.

Sean:

- `R`: cantidad de posiciones transitables alcanzables desde el objetivo;
- `E`: cantidad de adyacencias examinadas por el BFS;
- `U`: cantidad de unidades en el `EstadoJuego` consultado;
- `K`: máxima distancia consultada con éxito;
- `ΔK`: valores nuevos de la recurrencia calculados durante una consulta;
- `N`: cantidad de consultas exitosas.

Los costos de HTO son:

| Operación | Tiempo | Espacio persistente nuevo |
|---|---:|---:|
| Preparación topológica mediante BFS | O(R + E) | O(R) |
| Consulta que extiende la secuencia | O(U + ΔK) | O(ΔK) |
| Consulta cuyo valor ya está preparado | O(U) | O(1) |
| N consultas exitosas hasta H(K) | O(K + N·U) acumulado | O(K) adicional a la tabla |
| Estado persistente completo de HTO | — | O(R + K) |

En una cuadrícula cada celda tiene como máximo cuatro vecinas, por lo que `E=O(R)` para el componente recorrido.
El BFS no se repite durante las consultas. La validación del contexto cuesta O(1) respecto de R, E, U y K; localizar
la unidad mediante `ProblemaNavegacion.posicion()` cuesta O(U), la consulta del diccionario cuesta O(1) promedio y
cada ampliación cuesta O(ΔK).

La propiedad pública `estimaciones` materializa una tupla con el prefijo completo, por lo que inspeccionarla cuesta
O(K) temporal y espacial transitorio. Si una extensión falla, el valor no finito no se almacena; intentos posteriores
pueden repetir esa suma inválida. La amortización O(K + N·U) corresponde a consultas exitosas, no elimina el costo de
intentos fallidos.

El tiempo total se separa así:

\[
T_{\text{total}}=T_{\text{preprocesamiento}}+T_{A^*}
\]

El trabajo O(K + N·U) representa únicamente el costo acumulado de las consultas heurísticas exitosas; no es el tiempo
completo de A*, que también incluye generación de estados, hashing, comparaciones y operaciones de la cola de prioridad.

La preparación y consulta se separan así:

- **Preprocesamiento:** depende de dimensiones, transitabilidad y objetivo; ejecuta BFS, produce distancias enteras,
  captura el contexto y crea solo `H(0)`.
- **Consulta:** valida el contexto, extrae la posición desde el estado completo, consulta la distancia y amplía el
  prefijo numérico solo cuando es necesario.
- **Reutilización:** cambiar problema, escenario, objetivo, unidad o costo mínimo invalida la instancia preparada y
  exige construir una HTO nueva. Aunque cambiar solo costos no altera la topología, sí invalida la escala capturada.

La tabla debe pertenecer inicialmente a una búsqueda o instancia concreta de `ProblemaNavegacion`. Se descarta una
caché global porque añade invalidación y riesgo de mezclar escenarios. Esta decisión no impide reutilizar la tabla
dentro de la misma instancia.

## 10. Escenarios favorables y limitaciones

Las distancias y costos siguientes se distinguen de las métricas observadas en la campaña definitiva. Las primeras
son propiedades del mapa verificadas por pruebas; los contadores y tiempos son resultados experimentales de la
sección 11 y no propiedades matemáticas universales de las heurísticas.

### 10.1. `obstaculo_rodeo.json`

- Inicio: A1 en `(4, 3)`.
- Objetivo: `(1, 3)`.
- Manhattan inicial: 3.
- Distancia mínima respetando obstáculos: 15 movimientos, resultado derivado del mapa y verificado por prueba.
- Menor costo transitable: 1.

La heurística propuesta distingue el rodeo impuesto por el muro en U. Este escenario permite contrastarla con
Manhattan sin cambiar estado inicial, objetivo ni reglas. En la campaña definitiva HTO redujo los estados expandidos
de 33 a 26, mantuvo el costo óptimo 16 y aumentó la frontera máxima de 7 a 12. La reducción del tiempo de búsqueda
compensó el preprocesamiento en la mediana observada.

### 10.2. `ruta_corta_vs_economica.json`

- Inicio: A1 en `(2, 0)`.
- Objetivo: `(2, 8)`.
- Manhattan inicial: 8.
- Ruta más corta: 8 movimientos y costo 50, resultado verificado por prueba.
- Ruta de costo mínimo: 12 movimientos y costo 12, resultado verificado por prueba.

Las dos heurísticas producen la misma estimación inicial. Ninguna reconoce que la ruta recta atraviesa pantano y que
un camino de 12 movimientos cuesta menos. En la campaña ambas produjeron los mismos contadores discretos y costo
óptimo 12; HTO añadió preparación sin mejorar el tiempo total mediano. La igualdad de contadores no demuestra
igualdad de todos los valores heurísticos, sino que ambas indujeron el mismo comportamiento discreto observado.

### 10.3. `campo_20x20.json`

- Inicio: A1 en `(1, 2)`.
- Objetivo: `(9, 10)`.
- Manhattan inicial: 16.
- Ruta mínima en movimientos: 16, con costo 42; resultado verificado por prueba.
- Ruta de costo mínimo: 34 movimientos y costo 34; resultado verificado por prueba.

La estimación inicial coincide con Manhattan. El escenario sirve para medir el costo del preprocesamiento y mostrar
que conocer obstáculos no resuelve la diferencia entre distancia y costo del terreno. En la campaña ambas
heurísticas generaron 289 estados y expandieron 199; HTO incurrió en preparación y consulta adicionales y obtuvo un
tiempo total mediano mayor.

### 10.4. Casos donde pierde capacidad de discriminación

La heurística aporta poca información en mapas abiertos, corredores sin desvíos y escenarios donde todos los nodos
relevantes conservan la misma relación entre distancia con obstáculos y distancia Manhattan. También pierde fuerza
cuando el costo mínimo es muy inferior a los costos que aparecen en las rutas viables.

## 11. Evidencia automatizada y experimento definitivo

### 11.1. Pruebas automatizadas

La última verificación ejecutó 327 pruebas del proyecto: 34 corresponden al archivo específico de HTO y 36 al de A*;
estos subconjuntos forman parte del total y no se suman nuevamente. Todas aprobaron. La evidencia cubre:

- distancias topológicas, obstáculos, componentes desconectados y objetivo no transitable;
- estados completos distintos que proyectan la misma posición;
- costos enteros, decimales, heterogéneos, extremos y subnormales;
- conservación del prefijo y regresión E62-M01;
- cambios de problema, escenario, objetivo, unidad y costo mínimo para E62-A01;
- identidad problema--heurística, inyección opcional, reinserciones y desempate de A*;
- integración HTO--A*, reconstrucción de caminos y costo coincidente con UCS;
- oráculos de BFS y Dijkstra implementados en pruebas sin reutilizar HTO ni las transiciones del dominio.

La prueba de propiedades recorre las 256 configuraciones de bloqueo alrededor de un objetivo central en una
cuadrícula 3×3. Comprueba distancias, admisibilidad y consistencia sobre las aristas evaluadas. Es exhaustiva para
esas topologías concretas, no para todos los mapas, objetivos ni valores numéricos posibles. UCS es la referencia de
costo óptimo dentro del dominio compartido; no sustituye esos oráculos espaciales independientes.

Las pruebas automatizadas y auditorías técnicas no equivalen a validación estudiantil ni aprobación docente.

### 11.2. Contrato integrado de A*

La API vigente es:

```python
busqueda_a_estrella(problema, *, heuristica_preparada=None)
```

- omitir el parámetro o pasar `None` selecciona Manhattan;
- pasar una `HeuristicaObstaculos` construida para el mismo problema selecciona `evaluar(estado)`;
- una estrategia ligada a otra instancia de problema produce `ValueError` antes de crear la frontera;
- HTO se construye externamente, ejecuta el BFS una vez y A* reutiliza esa misma instancia durante la búsqueda.

La integración no duplica el motor: conserva `EstadoJuego` como identidad, la prioridad `f=g+h`, la cola, el
desempate por inserción, las reinserciones por mejoras estrictas y la reconstrucción. `ResultadoBusqueda.algoritmo`
continúa informando `A_ESTRELLA`; la etiqueta Manhattan/HTO pertenece a los registros experimentales externos. La
interfaz/CLI no invoca A* ni expone selección de heurística; esa capacidad existe en la API y el script experimental.

### 11.3. Metodología de la campaña definitiva

La campaña se ejecutó el 14 de octubre de 2026 con Python 3.12.3, el `.venv` del repositorio y
Linux 6.17.0-1032-oem x86_64. Comparó A*/Manhattan, A*/HTO y UCS/sin heurística en
`obstaculo_rodeo.json`, `ruta_corta_vs_economica.json` y `campo_20x20.json`.

Para cada escenario y estrategia se ejecutaron 10 rondas de calentamiento y 50 repeticiones medidas. La semilla
`6022026` hizo reproducible el orden aleatorio de las tres estrategias en cada ronda, no los tiempos. Cada ejecución
creó un problema nuevo y cada ejecución HTO creó una heurística nueva.

La preparación HTO se midió con `perf_counter_ns()` alrededor de su constructor e incluye el BFS inverso. El tiempo
de búsqueda procede del cronómetro de `ResultadoBusqueda`; incluye la recurrencia HTO diferida. El total de cada
muestra es la suma de ambos componentes, no una medición externa extremo a extremo. La carga JSON, la construcción
del problema, la validación funcional, las estadísticas y la escritura quedaron fuera de los intervalos.

Se informan medianas, mínimos, máximos y MAD no escalada. La comparación temporal principal empareja las dos
heurísticas por escenario y repetición. Las mediciones son descriptivas y dependen del entorno; no se aplicó una
prueba de significancia estadística.

### 11.4. Procedencia e integridad

La evidencia definitiva tiene identificador `e62-definitiva-20261014T224204-0500-ec59ea36` y permanece en:

```text
/media/isa/IsaPortable3/PROGLINUX/Inteligentes1/evidencia-e62/
e62-definitiva-20261014T224204-0500-ec59ea36/
```

Es almacenamiento local persistente externo al repositorio, no una dirección pública disponible para cualquier
evaluador. El SHA-256 de `muestras.jsonl` es
`24a014f130cfe89e32ea0322dc09c9fa26d4adbb1b57159d39d89c70f227ed37`.

El dataset contiene 450 registros: nueve grupos de 50, sin calentamientos, duplicados ni faltantes. La validación
independiente comprobó JSON, etiquetas, orden, tiempos finitos, suma de componentes, costos y métricas discretas.
El manifiesto conserva rama, HEAD, estado Git no confirmado, comando, entorno y hashes de 19 fuentes. Las copias
fueron idénticas antes y después de la campaña y `SHA256SUMS.txt` verificó todos los artefactos. Esta campaña reemplaza
la evidencia perdida de una ejecución anterior, pero no reconstruye su procedencia histórica.

### 11.5. Resultados funcionales

| Escenario | Estrategia | Costo | Longitud | Generados | Expandidos | Frontera |
|---|---|---:|---:|---:|---:|---:|
| `obstaculo_rodeo.json` | Manhattan | 16 | 15 | 40 | 33 | 7 |
| `obstaculo_rodeo.json` | HTO | 16 | 15 | 38 | 26 | 12 |
| `obstaculo_rodeo.json` | UCS | 16 | 15 | 41 | 39 | 7 |
| `ruta_corta_vs_economica.json` | Manhattan | 12 | 12 | 16 | 13 | 3 |
| `ruta_corta_vs_economica.json` | HTO | 12 | 12 | 16 | 13 | 3 |
| `ruta_corta_vs_economica.json` | UCS | 12 | 12 | 22 | 19 | 3 |
| `campo_20x20.json` | Manhattan | 34 | 34 | 289 | 199 | 53 |
| `campo_20x20.json` | HTO | 34 | 34 | 289 | 199 | 53 |
| `campo_20x20.json` | UCS | 34 | 34 | 374 | 333 | 44 |

Las tres estrategias alcanzaron el costo de UCS en cada ronda. No se exige igualdad de caminos: soluciones óptimas
alternativas pueden tener el mismo costo.

### 11.6. Resultados temporales

Medianas en milisegundos:

| Escenario | Estrategia | Preparación | Búsqueda | Total | MAD total |
|---|---|---:|---:|---:|---:|
| `obstaculo_rodeo.json` | Manhattan | 0 | 1.284690 | 1.284690 | 0.015435 |
| `obstaculo_rodeo.json` | HTO | 0.121108 | 1.068003 | 1.192079 | 0.015435 |
| `ruta_corta_vs_economica.json` | Manhattan | 0 | 0.438125 | 0.438125 | 0.008312 |
| `ruta_corta_vs_economica.json` | HTO | 0.094987 | 0.463652 | 0.556858 | 0.010686 |
| `campo_20x20.json` | Manhattan | 0 | 12.043084 | 12.043084 | 0.084894 |
| `campo_20x20.json` | HTO | 1.030009 | 12.335167 | 13.370519 | 0.109234 |

La mediana del total se calcula sobre los totales individuales y no tiene por qué ser la suma exacta de las medianas
de preparación y búsqueda. Para la comparación emparejada se define:

\[
\Delta_r=T_{\text{total,HTO},r}-T_{\text{total,Manhattan},r}
\]

| Escenario | Mediana de Δ (ms) | MAD de Δ (ms) | Mínimo--máximo (ms) | Favor HTO | Diferencia de medianas (ms) |
|---|---:|---:|---:|---:|---:|
| `obstaculo_rodeo.json` | -0.094986 | 0.015435 | -0.459496--0.301582 | 49/50 (98 %) | -0.092611 |
| `ruta_corta_vs_economica.json` | 0.121108 | 0.013060 | -0.206595--1.019916 | 2/50 (4 %) | 0.118733 |
| `campo_20x20.json` | 1.316155 | 0.073615 | -3.101305--2.632310 | 2/50 (4 %) | 1.327434 |

La mediana de diferencias emparejadas y la diferencia entre medianas son estimadores distintos y no se presupone
que coincidan. HTO no es universalmente superior: resultó favorable cuando el rodeo topológico redujo exploración,
pero el trabajo adicional no se compensó en los otros dos escenarios.

## 12. Riesgos y condiciones de validez

| Riesgo o cambio | Consecuencia |
|---|---|
| Movimiento diagonal o salto | La distancia del grafo actual puede sobreestimar. |
| Bloqueos dinámicos | La proyección seguiría siendo una relajación solo si elimina restricciones; requiere una nueva prueba. |
| Costo por unidad inferior a `costo_minimo_paso` | Rompe la cota de costo usada en admisibilidad y consistencia. |
| Acciones no espaciales con costo bajo | Pueden romper la correspondencia entre transición real y arista. |
| Cambio de problema, escenario, objetivo, unidad o costo mínimo | La guarda E62-A01 rechaza la consulta y exige una HTO nueva. |
| Suma recurrente no finita | E62-M01 conserva el prefijo finito y produce `ValueError` para el valor solicitado. |
| Multiplicación directa con `float` | Puede romper admisibilidad y consistencia respecto del costo secuencial. |
| Recurrencia numérica fuera de sus precondiciones | La propiedad local no basta para garantizar optimalidad global de A*. |
| Suma `g+h` no finita en la integración | Debe conservarse la guarda de prioridad existente en A*. |
| Posición inicial externa fuera de \(V_P\) | Recibe cero; su primera transición puede ingresar al grafo y debe analizarse aparte. |

## 13. Estado de las seis decisiones técnicas

Las seis decisiones originales se conservan con su historial. `Implementado`, `probado`, `auditado` o `medido` son
estados técnicos y no representan aprobación estudiantil ni docente.

1. **Adoptar `h_obst` como segunda heurística de E6.2.**
   - Propuesto e implementado: HTO usa distancias topológicas y la recurrencia B bajo demanda.
   - Verificación técnica: admisibilidad, consistencia y dominancia de la definición real están demostradas bajo los
     supuestos explícitos; la recurrencia tiene garantías condicionadas respecto de acumulación secuencial `float`.
   - Probado, auditado y medido: integración A* y tres escenarios de la campaña definitiva.
   - Aprobación estudiantil y docente: pendientes.

2. **Devolver cero para posiciones desconectadas y objetivos no transitables.**
   - Propuesto e implementado: devuelve cero para desconexión, objetivo no transitable y posiciones externas o no
     transitables; también devuelve cero en el objetivo.
   - Verificación técnica: existen pruebas de cada caso y de la primera transición desde fuera de \(V_P\).
   - Probado y auditado; aprobación estudiantil pendiente.

3. **Precalcular distancias una vez por problema mediante BFS desde el objetivo.**
   - Propuesto e implementado: BFS se ejecuta durante la construcción y almacena distancias enteras; solo `H(0)` se
     prepara inicialmente y los demás valores se calculan bajo demanda.
   - Verificación técnica: las pruebas comparan la tabla con un BFS independiente y comprueban que las consultas no
     repiten verificaciones de transitabilidad.
   - Probado, auditado y medido separadamente con `perf_counter_ns()`; aprobación estudiantil pendiente.

4. **Mantener `EstadoJuego` completo como identidad de A*.**
   - Propuesto e implementado: HTO recibe `EstadoJuego` y usa la posición solo como proyección de consulta.
   - Verificación técnica: estados distintos con igual posición comparten estimación sin convertirse en la misma
     identidad; A* continúa usando `EstadoJuego` en sus mejores costos.
   - Probado y auditado; aprobación estudiantil pendiente.

5. **Conservar Manhattan como comportamiento predeterminado.**
   - Implementado: omitir `heuristica_preparada` o pasar `None` usa Manhattan; HTO se selecciona explícitamente.
   - Probado, auditado y medido: compatibilidad de invocaciones, selección y etiquetado experimental externo.
   - Limitación: la interfaz/CLI no ofrece selección de HTO. Aprobación estudiantil pendiente.

6. **Inyectar la heurística en A* sin duplicar el algoritmo.**
   - Implementado: `heuristica_preparada` modifica únicamente la evaluación de `h`; se conservan motor, `g+h`, cola,
     desempate, reinserciones, guardas y reconstrucción.
   - Probado y auditado: identidad de problema, errores controlados, integración y nombre `A_ESTRELLA` del resultado.
   - Medido: preparación separada y etiqueta heurística en registros externos. Aprobación estudiantil pendiente.

## 14. Matriz de criterios de aceptación

| Criterio | Evidencia en código | Evidencia en pruebas o experimento | Limitaciones | Estado técnico |
|---|---|---|---|---|
| 1. Qué estima | `HeuristicaObstaculos.evaluar()` consulta distancia topológica y recurrencia escalada. | Oráculos BFS/Dijkstra y costos óptimos de la campaña. | La política devuelve cero fuera del componente o grafo válido. | Implementado, probado y auditado; validación estudiantil pendiente. |
| 2. Qué información utiliza | Objetivo, posición de la unidad, transitabilidad, dimensiones y `costo_minimo_paso`; A01 fija el contexto. | Pruebas de cambios de problema, escenario, objetivo, unidad y costo mínimo. | No modela costos heterogéneos completos ni bloqueos dinámicos. | Implementado y probado; validación estudiantil pendiente. |
| 3. Complejidad | BFS O(R + E); consulta O(U + ΔK), acumulado O(K + N·U), memoria O(R + K). | Pruebas comprueban un BFS por instancia; campaña separa preparación y búsqueda. | Los tiempos reales incluyen cola, estados, hashing y entorno de ejecución. | Analizado y medido; validación estudiantil pendiente. |
| 4. Admisibilidad | Definición real y recurrencia `H(0)=0`, `H(k+1)=fl(H(k)+c_min)`. | Propiedades en 256 topologías, extremos numéricos y costos coincidentes con UCS. | Garantías `float` condicionadas; no se afirma optimalidad global universal bit a bit. | Demostrado bajo supuestos, probado y auditado; aprobación docente pendiente. |
| 5. Discriminación | Distancia topológica domina condicionalmente a Manhattan en posiciones conectadas. | Menos expansiones y menor mediana total en `obstaculo_rodeo`; sin mejora discreta en los otros escenarios. | No distingue la distribución completa de costos y su preparación puede no compensarse. | Caracterizado experimentalmente; validación estudiantil pendiente. |

## 15. Uso de IA generativa y validación estudiantil

**AI usage:** Yes.

**AI intervention:** Codex auditó E6.1 y el modelo de navegación, comparó familias de heurísticas y participó en el
diseño y demostración de HTO, el análisis de complejidad y la investigación numérica. También intervino en la
implementación, las pruebas de propiedades y oráculos, la detección y corrección de E62-A01 y E62-M01, la integración
de A*, el script experimental, las auditorías independientes, la consolidación de evidencia y esta actualización
documental. La revisión incluyó el contraejemplo con `0.1`, valores extremos, estados externos y la distinción entre
UCS como referencia de costo dentro del dominio y los oráculos independientes de BFS/Dijkstra.

BFS inverso y las distancias mínimas en grafos sin pesos son técnicas conocidas. El aporte académico propuesto es su
adaptación al contrato de TacticalGrid, la justificación de la relajación y su tratamiento numérico y de ciclo de vida;
su aceptación corresponde al docente y al equipo.

**Student validation:** pendiente. Las auditorías asistidas por IA no sustituyen el conocimiento ni la
responsabilidad académica del equipo. Sus integrantes deben revisar cada supuesto contra `ProblemaNavegacion`,
reproducir distancias, contraejemplo, regresiones y campaña, explicar las demostraciones y aprobar o corregir las
decisiones de la sección 13 antes de presentar la historia como validada.
