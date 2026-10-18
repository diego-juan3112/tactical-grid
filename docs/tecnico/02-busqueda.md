# Algoritmos de búsqueda

Historias E4.1 a E7.1: la instrumentación común y los cinco algoritmos de búsqueda. Los experimentos están en [casos mínimos 1, 2 y 5](../casos-minimos/casos-1-2-5-busqueda.md) y [casos mínimos 3 y 4](../casos-minimos/casos-3-4-obstaculo-y-heuristicas.md); la segunda heurística, en [heurística HTO](03-heuristica-hto.md).

## Instrumentación común — E4.1

E4.1 agrega la instrumentación común de búsqueda en `algoritmos/instrumentacion.py`, para que BFS, DFS, UCS, A* y Beam Search reporten resultados comparables sin duplicar código. `Nodo` guarda estado, padre, acción, costo acumulado y profundidad; `expandir` genera los hijos en el orden de las acciones, con el costo leído del escenario, y cuenta la expansión; `MedidorBusqueda` lleva estados generados (incorporados a la frontera, incluido el inicial), estados expandidos, máximo de frontera y tiempo, y construye el `ResultadoBusqueda`. `ResultadoBusqueda.a_diccionario()` devuelve la estructura del enunciado (`algoritmo`, `exito`, `camino`, `costo`, `estados_generados`, `estados_expandidos`, `maximo_frontera`) más `longitud` y `tiempo_segundos`; el resultado también conserva las acciones para el verificador de soluciones.

## BFS — E4.2

BFS es una búsqueda no informada: usa una frontera FIFO y explora los estados por niveles. Con cada acción equivalente a un movimiento, encuentra una solución con la menor cantidad de movimientos. El costo del terreno no afecta el orden ni desempata rutas; `ResultadoBusqueda.costo` aún informa la suma real de costos del camino y `longitud` informa sus movimientos.

La implementación consume `Problema`, marca el `EstadoJuego` completo como descubierto al encolarlo y descarta estados repetidos. Esto evita ciclos y conserva diferencias de estado relevantes, como el portador del recurso. Mantiene el orden de acciones del problema para resultados deterministas. Cada `Nodo` conserva padre y acción; `MedidorBusqueda.finalizar()` reconstruye camino y acciones. Si la frontera se agota, el resultado indica fracaso, con camino y acciones vacíos y costo `None`; los contadores y el tiempo reflejan la exploración realizada. BFS reutiliza las métricas E4.1 y no depende de dimensiones, coordenadas ni escenarios particulares.

## DFS — E4.3

DFS es la otra búsqueda no informada del proyecto: usa una frontera LIFO (una pila) y sigue cada rama hasta el fondo antes de retroceder. No garantiza el camino con menos movimientos ni el más barato: devuelve el primero que encuentra. `ResultadoBusqueda.costo` y `longitud` informan el costo real y los movimientos de ese camino.

DFS comparte con BFS todo salvo la frontera, para que la comparación de E4.4 aísle esa única diferencia:

- Consume el contrato `Problema` y las métricas de E4.1 (`Nodo`, `expandir`, `MedidorBusqueda`), con la misma convención de conteo.
- Marca el `EstadoJuego` completo como descubierto al apilarlo y descarta estados repetidos. Así evita ciclos (una unidad puede ir y volver) y termina siempre en espacios finitos, y conserva diferencias de estado como el portador del recurso.
- Comprueba el objetivo al extraer de la pila, igual que BFS.
- Apila los hijos en orden inverso para explorar primero el primer movimiento de `DESPLAZAMIENTOS` (arriba, abajo, izquierda, derecha). Por eso el resultado es determinista, y cambiar ese orden cambia el camino de DFS.
- Usa una pila explícita, sin recursión, para no depender del límite de recursión de Python en mapas grandes.

Ejemplo verificado en `tests/algoritmos/test_busqueda_profundidad.py`, en un mapa abierto de 3x3 con la unidad en (0, 0) y el objetivo en (0, 2): BFS llega en 2 movimientos, mientras DFS baja primero por la columna 0 y da la vuelta al mapa en 6 movimientos, con 9 estados generados, 6 expandidos y un máximo de frontera de 3. Si el objetivo es inalcanzable, DFS agota la pila tras visitar exactamente los mismos estados alcanzables que BFS.

En el escenario predeterminado `campo_20x20.json` (de (1, 2) a (9, 10)), DFS expande menos estados que BFS (102 frente a 186), pero devuelve un camino mucho peor (98 movimientos y costo 283, frente a 16 movimientos y costo 45). Además, su frontera máxima es mayor (104 frente a 20). La ventaja de memoria que suele atribuirse a DFS, una pila de tamaño O(b * m), vale para la búsqueda en árbol, que solo guarda la rama actual. En esta búsqueda en grafo, cada expansión deja en la pila hermanos pendientes que se acumulan mientras se profundiza.

## UCS — E5.1

UCS usa una cola de prioridad mínima ordenada exclusivamente por el costo acumulado `g(n)`. Los costos provienen de `Problema.costo()` y, en `ProblemaNavegacion`, de la celda destino declarada en `tipos_terreno` del JSON. Por eso puede elegir más movimientos que BFS cuando el costo total resulta menor.

La implementación conserva el mejor costo conocido por `EstadoJuego`, reinserta un estado ante una mejora estricta y descarta al extraer las entradas obsoletas. Un contador monótono resuelve empates sin comparar nodos ni estados y mantiene el orden de inserción. El inicial y cada inserción o reinserción aceptada cuentan como generados; solo `expandir()` cuenta estados cuyos sucesores se analizan. `maximo_frontera` mide la cantidad de entradas presentes en la cola, incluidas las obsoletas aún no extraídas. `ResultadoBusqueda` incluye éxito, camino, acciones, longitud, costo, generados, expandidos, máximo de frontera y tiempo.

Con cola binaria y reinserciones, las operaciones propias de UCS cuestan `O((V + E) log E)`, pero el modelo agrega el procesamiento de cada `EstadoJuego`. Si `U` es la cantidad de unidades y `d` la profundidad de la solución, la cota completa es `O(E * U log U + (V + E) log E + d * U)` temporal y `O((V + E) * U + d)` espacial. Cada transición reconstruye y ordena la tupla de unidades, el hash de un estado procesa sus unidades y la reconstrucción final consulta la posición sobre cada estado del camino. La frontera puede incluir reinserciones y entradas obsoletas pendientes.

Ejemplo reproducible sobre el escenario de comparación:

```python
from tacticalgrid.algoritmos import busqueda_anchura, busqueda_costo_uniforme
from tacticalgrid.escenario import Posicion, cargar_escenario
from tacticalgrid.juego import ProblemaNavegacion

escenario = cargar_escenario("escenarios/ruta_corta_vs_economica.json")
problema = ProblemaNavegacion(escenario, "A1", Posicion(2, 8))

print(busqueda_anchura(problema).a_diccionario())
print(busqueda_costo_uniforme(problema).a_diccionario())
```

BFS devuelve 8 movimientos y costo 50; UCS devuelve 12 movimientos y costo 12. Para ejecutar la cobertura automatizada: `python -m pytest tests/algoritmos/test_busqueda_costo_uniforme.py`.

## A* con Manhattan — E6.1

A* usa una cola de prioridad mínima ordenada por `f(n) = g(n) + h(n)`. `g(n)` es el costo real acumulado que
`Nodo` y `expandir()` calculan desde `Problema.costo()`; `h(n)` es una cota del costo restante; `f(n)` decide qué
nodo vigente se extrae primero. El algoritmo conserva el mejor `g` conocido por `EstadoJuego` completo, reinserta
una mejora estricta y descarta las entradas obsoletas mediante su `g`, no mediante `f`. Un contador monótono
resuelve empates sin comparar nodos ni estados.

La heurística implementada es:

```text
h(n) = (|fila_n - fila_objetivo| + |columna_n - columna_objetivo|) * costo_minimo_paso
```

`ProblemaNavegacion` calcula una sola vez `costo_minimo_paso` como el menor costo de los terrenos transitables del
escenario validado. El escalamiento es necesario porque el contrato admite costos positivos menores que 1: usar la
distancia Manhattan sin escalar podría sobreestimar. Con las reglas actuales, cada acción de navegación mueve una
celda ortogonal y cuesta al menos esa cota. Por ello Manhattan escalada es admisible; también es consistente porque
un paso reduce la distancia a lo sumo en uno y su costo es al menos `costo_minimo_paso`.

La heurística consulta la posición de la unidad navegante, pero los diccionarios del algoritmo conservan la
identidad completa de `EstadoJuego`. Estados con igual posición y distinto portador, recurso, turno u otras unidades
no se fusionan. Obstáculos y terrenos caros no se incorporan a `h`: mantienen la corrección, aunque reducen su
capacidad de orientar la búsqueda. La demostración de admisibilidad debe revisarse si aparecen diagonales, saltos,
costos no positivos o reglas de costo por unidad inferiores a la cota utilizada.

Con V estados alcanzables, E transiciones examinadas, U unidades por estado y una solución de profundidad d, la
cota implementada es `O(E * (U log U + U) + (V + E) log E + d * U)` temporal y
`O((V + E) * U + d)` espacial. Incluye la reconstrucción canónica de estados, hashing, evaluaciones heurísticas,
reinserciones y entradas obsoletas. El cálculo aritmético de Manhattan es O(1), pero localizar la unidad actual en
el estado cuesta O(U).

Ejecución y comparación de costos:

```bash
python main.py --consola escenarios/ruta_corta_vs_economica.json --algoritmo a_estrella
python main.py --consola escenarios/ruta_corta_vs_economica.json --algoritmo ucs
```

A* y UCS deben obtener el mismo costo óptimo bajo estas condiciones; no se exige que coincidan el camino, las
métricas ni el tiempo. La opción `ambos` conserva su significado anterior y ejecuta solamente BFS y UCS.

### Casos mínimos 3 y 4: obstáculo y comparación de heurísticas

[Casos mínimos 3 y 4](../casos-minimos/casos-3-4-obstaculo-y-heuristicas.md) documenta la ruta obligada por el muro de
`obstaculo_rodeo.json` y compara A* con Manhattan, A* con HTO y UCS sobre la misma configuración. Las pruebas de
`tests/algoritmos/test_casos_minimos_heuristicas.py` verifican el rodeo, la legalidad del camino, el costo y las
métricas discretas. La comparación se reproduce con:

```bash
python scripts/comparar_heuristicas_e62.py --repeticiones 1 --calentamiento 0
```

## Beam Search — E7.1

`algoritmos/busqueda_haz.py` implementa Beam Search por niveles con ancho `k`. En cada nivel se expanden todos los
nodos del haz, sus hijos se ordenan por `f(n) = g(n) + h(n)` (Manhattan escalada de E6.1 por defecto; la heurística
es un parámetro, de modo que la segunda heurística de E6.2 se puede usar sin cambiar el algoritmo) y solo los `k`
mejores pasan al siguiente nivel; el resto se olvida. Un estado que ya entró en un haz no vuelve a entrar. El objetivo
se comprueba al formar cada haz y los empates se resuelven por orden de generación, por lo que el resultado es
determinista. Reporta las métricas de E4.1 con el nombre `BEAM_SEARCH_K<k>`; un estado cuenta como generado cuando
entra al haz, por lo que el máximo de frontera nunca supera `k`.

Beam Search no es completo ni óptimo. Con `k = 1` actúa como una búsqueda voraz; con `k` mayor que cualquier nivel no
poda y se comporta como BFS (mínimo número de movimientos, eligiendo el objetivo de menor `f` en ese nivel). Por eso
aumentar `k` no siempre reduce el costo. Resultados reproducibles (`tests/algoritmos/test_busqueda_haz.py`):

| Escenario | k = 1 | k = 2 | k = 4 | k = 8 | UCS (óptimo) |
|---|---|---|---|---|---|
| `ejemplo_enunciado.json` | costo 12, 6 mov. | costo 7, 6 mov. | costo 14, 4 mov. | costo 14, 4 mov. | costo 7 |
| `ruta_corta_vs_economica.json` | costo 12, 12 mov. | costo 12, 12 mov. | costo 50, 8 mov. | costo 50, 8 mov. | costo 12 |
| `obstaculo_rodeo.json` | costo 20, 19 mov. | sin solución | costo 16, 15 mov. | costo 16, 15 mov. | costo 16 |
| `campo_20x20.json` | sin solución | sin solución | costo 40, 34 mov. | costo 46, 36 mov. | costo 34 |

El parámetro opcional `observador` de `busqueda_haz` recibe un `NivelHaz` por cada nivel (candidatos conservados y
descartados con su `f`) sin alterar el resultado; se usa en el análisis de E7.2 y sirve para visualizar la exploración.

`k` se configura sin modificar código: desde la consola con `--k` (admite varios valores) o desde el JSON con el
campo propio `prueba.k`. La consola tiene prioridad sobre el JSON; un `k` que no sea un entero mayor o igual que 1 se
rechaza con un mensaje claro.

```bash
python main.py --consola escenarios/campo_20x20.json --algoritmo beam --k 1 2 4 8
```
