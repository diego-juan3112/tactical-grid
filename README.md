# TacticalGrid

Juego tactico 2D por turnos para Sistemas Inteligentes I. El juego permite observar y experimentar estrategias de busqueda y decision sobre escenarios externos.

## Stack tecnico

- **Python 3.12 o 3.13 (no 3.14, que Pygame aun no soporta):** facilita implementar con claridad los algoritmos de busqueda y decision, mantiene el codigo legible y modificable, e integra Pygame y pytest en el mismo proyecto.
- **Pygame:** TacticalGrid es un entorno tactico 2D en cuadricula; permite visualizar tablero, terrenos, unidades, caminos y resultados, con una interfaz suficiente para observar el sistema inteligente y no para producir un videojuego comercial.
- **pytest:** permite probar escenario, juego y algoritmos independientemente de Pygame, con pruebas automatizadas y reproducibles.
- **Uvicorn:** ejecuta un punto ASGI tecnico y aislado; no convierte el proyecto en una aplicacion web.
- **JSON:** contrato externo para escenarios.
- **Git:** control de versiones.
- **.venv:** entorno virtual local recomendado para aislar dependencias.

## Arquitectura

- `escenario`: lee, valida y representa JSON; provee dimensiones, terrenos, costos y transitabilidad.
- `juego`: representa `EstadoJuego` y `Unidad`; aqui viviran reglas, acciones y sucesores.
- `algoritmos`: contiene contratos de resultados y alojara estrategias de busqueda y decision.
- `interfaz`: inicializa Pygame y consumira estado y resultados.
- `servidor`: expone el punto ASGI tecnico para Uvicorn; no accede a las cuatro capas.

```text
JSON -> Escenario -> Juego -> Algoritmos -> Resultado
                         ^                 ^
                         |                 |
                    Interfaz Pygame consume estado y resultados

Uvicorn -> servidor ASGI aislado
pytest -> prueba escenario, juego, algoritmos y servidor sin Pygame
```

`Escenario` conserva la informacion estatica: dimensiones, terrenos, bases, posicion inicial del recurso, configuracion y unidades iniciales. `EstadoJuego` conserva la informacion dinamica: unidades, turno actual, posicion del recurso cuando no tiene portador, identificador del portador y estado general de la partida. `Unidad` representa identificador, bando, tipo y posicion actual.

E1.1 define `EstadoJuego` y `Unidad` como objetos inmutables y hashables. Las unidades se almacenan en una tupla canonica ordenada por identificador, por lo que su orden de entrada no modifica la identidad logica del estado. Las posiciones determinan acciones y transiciones disponibles; el turno determina que bando puede actuar; y el portador distingue situaciones visualmente iguales que requieren decisiones distintas. Cuando no hay portador, la posicion del recurso tambien forma parte del estado. El modelo no contiene dimensiones ni posiciones fijas: esas propiedades pertenecen al escenario cargado.

E1.2 define acciones, sucesores, condicion objetivo y costo. Cada accion mueve una unidad del bando en turno una celda ortogonal a una celda dentro del mapa, transitable y libre; al entrar en la celda del recurso libre la unidad lo recoge, y el recurso viaja con ella. Un bando gana cuando su portador llega a su propia base. El costo de una accion es el costo del terreno destino declarado en `tipos_terreno`, por lo que cambiar un costo en el JSON cambia el comportamiento sin tocar codigo. Los algoritmos de busqueda consumen el contrato `Problema`; `ProblemaNavegacion` lleva una unidad a una celda objetivo ignorando al adversario.

## Reglas deterministas de borde — E1.3

Una unidad sin movimientos legales no genera acciones; las demas unidades del mismo bando pueden actuar normalmente. El bloqueo individual no cambia el turno. Si ninguna unidad del bando activo puede actuar, `resolver_bloqueo_turno()` pasa el turno una vez al adversario cuando este tiene acciones. Si ambos bandos carecen de acciones, `estado_partida` pasa a `empate_bloqueo`, que es terminal y evita pases repetidos.

La ausencia de ruta se determina en las historias de busqueda. Cuando una busqueda no encuentra solucion, `ResultadoBusqueda` representa fracaso (`exito = false`) con `camino` y `acciones` vacios, y `costo = None`. Ese resultado no modifica `EstadoJuego`: unidades, turno, recurso y `estado_partida` permanecen iguales. El contrato no agrega un algoritmo de busqueda a la capa de juego.

E1.3 no elimina unidades. Una intercepcion ya establecida transfiere atomicamente `portador_recurso` a la unidad adversaria y mantiene `posicion_recurso = null`; conserva las unidades y el turno. Si el nuevo portador ya esta en la base de su bando, esa misma transicion registra inmediatamente su victoria. La accion futura que origine la intercepcion sera responsable de alternar el turno mediante el flujo normal. Estas reglas son deterministas porque el mismo estado y escenario producen el mismo pase, empate o transferencia sin azar ni estado externo, y cada resultado se representa en un nuevo `EstadoJuego` inmutable.

## Bucle de turnos — E3.1

El dominio ofrece un flujo sincrono y paso a paso en `juego/partida.py`; el consumidor (jugador, interfaz, prueba o IA futura) decide cuándo repetirlo y qué opción elegir. No hay un bucle de partida interno ni concurrencia o lógica de tiempo real.

1. `preparar_turno(escenario, estado)` devuelve sin cambios un estado terminal; de lo contrario reutiliza `resolver_bloqueo_turno()` para mantener el turno, pasarlo una vez o declarar empate por bloqueo total.
2. `unidades_seleccionables()` expone solo unidades del bando activo con al menos una acción legal. Una unidad bloqueada no es seleccionable; `acciones_para_unidad()` para esa unidad activa devuelve una tupla vacía.
3. El consumidor elige una unidad y una de las acciones de `acciones_para_unidad()`. Esta consulta filtra `acciones_validas()` y no duplica reglas de movimiento. Una unidad adversaria o inexistente produce `ValueError`.
4. `aplicar_accion()` valida y ejecuta la acción según E1.2, crea un nuevo estado y alterna el turno exactamente una vez. E3.1 no vuelve a cambiarlo.

La selección es transitoria y no integra `EstadoJuego`, por lo que no altera su identidad lógica ni su hash. El pase automático pertenece a E1.3; si ambos bandos están bloqueados, la partida termina en `empate_bloqueo`. `resolver_intercepcion()` conserva el turno por sí sola. A y B utilizan las mismas reglas. MAX y MIN son roles adversariales futuros: no conceden más o menos acciones, profundidad o inteligencia. La integración de E2.1 comienza con un `Escenario` cargado; `crear_estado_inicial(escenario)` construye el estado sin que el módulo de partida lea JSON.

E2.2 completa el validador de escenarios. Antes de construir el `Escenario` se comprueban todas las reglas del enunciado: dimensiones consistentes con la matriz, terrenos declarados, costos positivos, posiciones dentro del mapa, unidades sobre celdas transitables, ids unicos, bandos y turno validos, y portador existente. Cualquier incumplimiento lanza `ErrorValidacionEscenario` con un mensaje que nombra el campo, el elemento y el valor recibido. Como la validacion ocurre completa antes de aplicar nada, una carga fallida no reemplaza ni altera el escenario vigente.

E2.3 agrega un set propio de escenarios en `escenarios/` para desarrollar y depurar algoritmos antes de recibir los del profesor: un mapa de 20 x 20 con todos los tipos de terreno y variantes pequenas. En `campo_20x20.json` y `ruta_corta_vs_economica.json` la ruta con menos movimientos es mas costosa que una mas larga, por lo que BFS y UCS producen caminos distintos. Las pruebas de `tests/escenario/test_escenarios_propios.py` comprueban estas propiedades sobre el modelo de E1.2, con los costos leidos del JSON.

E4.1 agrega la instrumentacion comun de busqueda en `algoritmos/instrumentacion.py`, para que BFS, DFS, UCS, A* y Beam Search reporten resultados comparables sin duplicar codigo. `Nodo` guarda estado, padre, accion, costo acumulado y profundidad; `expandir` genera los hijos en el orden de las acciones, con el costo leido del escenario, y cuenta la expansion; `MedidorBusqueda` lleva estados generados (incorporados a la frontera, incluido el inicial), estados expandidos, maximo de frontera y tiempo, y construye el `ResultadoBusqueda`. `ResultadoBusqueda.a_diccionario()` devuelve la estructura del enunciado (`algoritmo`, `exito`, `camino`, `costo`, `estados_generados`, `estados_expandidos`, `maximo_frontera`) mas `longitud` y `tiempo_segundos`; el resultado tambien conserva las acciones para el verificador de soluciones.

## BFS — E4.2

BFS es una busqueda no informada: usa una frontera FIFO y explora los estados por niveles. Con cada accion equivalente a un movimiento, encuentra una solucion con la menor cantidad de movimientos. El costo del terreno no afecta el orden ni desempata rutas; `ResultadoBusqueda.costo` aun informa la suma real de costos del camino y `longitud` informa sus movimientos.

La implementacion consume `Problema`, marca el `EstadoJuego` completo como descubierto al encolarlo y descarta estados repetidos. Esto evita ciclos y conserva diferencias de estado relevantes, como el portador del recurso. Mantiene el orden de acciones del problema para resultados deterministas. Cada `Nodo` conserva padre y accion; `MedidorBusqueda.finalizar()` reconstruye camino y acciones. Si la frontera se agota, el resultado indica fracaso, con camino y acciones vacios y costo `None`; los contadores y el tiempo reflejan la exploracion realizada. BFS reutiliza las metricas E4.1 y no depende de dimensiones, coordenadas ni escenarios particulares.

## UCS — E5.1

UCS usa una cola de prioridad minima ordenada exclusivamente por el costo acumulado `g(n)`. Los costos provienen de `Problema.costo()` y, en `ProblemaNavegacion`, de la celda destino declarada en `tipos_terreno` del JSON. Por eso puede elegir mas movimientos que BFS cuando el costo total resulta menor.

La implementacion conserva el mejor costo conocido por `EstadoJuego`, reinserta un estado ante una mejora estricta y descarta al extraer las entradas obsoletas. Un contador monotono resuelve empates sin comparar nodos ni estados y mantiene el orden de insercion. El inicial y cada insercion o reinsercion aceptada cuentan como generados; solo `expandir()` cuenta estados cuyos sucesores se analizan. `maximo_frontera` mide la cantidad de entradas presentes en la cola, incluidas las obsoletas aun no extraidas. `ResultadoBusqueda` incluye exito, camino, acciones, longitud, costo, generados, expandidos, maximo de frontera y tiempo.

Con cola binaria y reinserciones, las operaciones propias de UCS cuestan `O((V + E) log E)`, pero el modelo agrega el procesamiento de cada `EstadoJuego`. Si `U` es la cantidad de unidades y `d` la profundidad de la solucion, la cota completa es `O(E * U log U + (V + E) log E + d * U)` temporal y `O((V + E) * U + d)` espacial. Cada transicion reconstruye y ordena la tupla de unidades, el hash de un estado procesa sus unidades y la reconstruccion final consulta la posicion sobre cada estado del camino. La frontera puede incluir reinserciones y entradas obsoletas pendientes.

Ejemplo reproducible sobre el escenario de comparacion:

```python
from tacticalgrid.algoritmos import busqueda_anchura, busqueda_costo_uniforme
from tacticalgrid.escenario import Posicion, cargar_escenario
from tacticalgrid.juego import ProblemaNavegacion

escenario = cargar_escenario("escenarios/ruta_corta_vs_economica.json")
problema = ProblemaNavegacion(escenario, "A1", Posicion(2, 8))

print(busqueda_anchura(problema).a_diccionario())
print(busqueda_costo_uniforme(problema).a_diccionario())
```

BFS devuelve 8 movimientos y costo 50; UCS devuelve 12 movimientos y costo 12. Para ejecutar la cobertura automatizada: `python3 -m pytest tests/algoritmos/test_busqueda_costo_uniforme.py`.

## E5.2 — Caso mínimo 2: ruta corta vs. ruta económica

### Propósito del experimento

Este caso compara BFS y UCS sobre el mismo escenario, estado inicial, unidad y objetivo para demostrar que
minimizar la cantidad de movimientos no equivale necesariamente a minimizar el costo acumulado. Se reutiliza
`ruta_corta_vs_economica.json`, creado en E2.3; BFS proviene de E4.2, UCS de E5.1 y ambos reportan las métricas
comunes definidas en E4.1. Las características generales de los algoritmos se describen en las secciones
anteriores; aquí se documenta el experimento concreto y reproducible.

### Configuración reproducible

- Escenario: `escenarios/ruta_corta_vs_economica.json` (5 filas por 9 columnas).
- Unidad: `A1`, con posición inicial `(2, 0)`.
- Objetivo posicional: `(2, 8)`.
- Movimientos: una celda ortogonal por acción, dentro del mapa y sobre terreno transitable.
- Costo de cada acción: costo del terreno de la celda destino; la posición inicial no se cobra.

Desde la raíz del repositorio, la comparación se ejecuta con:

```bash
python3 -B main.py escenarios/ruta_corta_vs_economica.json --algoritmo ambos
```

### Representación del mapa

```text
      0 1 2 3 4 5 6 7 8
F0    C C C C C C C C C
F1    C # # # # # # # C
F2    A S S S S S S S G
F3    P # # # # # # # P
F4    P P P P P P P P P
```

`A` identifica el inicio y `G` el objetivo de la búsqueda; no son tipos de terreno. `C` es camino de costo 1,
`S` es pantano de costo 7, `P` es pasto de costo 2 y `#` es muro no transitable. El catálogo también declara
bosque de costo 4, aunque ninguna celda de esta matriz lo utiliza.

### Resultados esperados y observados

Los resultados esperados son valores de referencia establecidos mediante el análisis del escenario, sus reglas
de movimiento y sus costos; no se presentan como una predicción histórica anterior a las primeras ejecuciones.
Los resultados observados provienen de ejecutar las implementaciones actuales sobre el mismo
`ProblemaNavegacion`.

| Resultado | BFS: movimientos | BFS: costo | UCS: movimientos | UCS: costo |
|---|---:|---:|---:|---:|
| Esperado de referencia | 8 | 50 | 12 | 12 |
| Observado | 8 | 50 | 12 | 12 |

Los valores esperados y observados coinciden.

### Resultado observado con BFS

La ejecución produce el siguiente camino:

```text
(2, 0) → (2, 1) → (2, 2) → (2, 3) → (2, 4)
       → (2, 5) → (2, 6) → (2, 7) → (2, 8)
```

El camino contiene 9 posiciones y 8 movimientos. Entrar en las siete celdas de pantano cuesta 49 y entrar en
la celda final de camino cuesta 1: `7 + 7 + 7 + 7 + 7 + 7 + 7 + 1 = 50`. La posición inicial no representa
una acción y no se suma. BFS elige este corredor directo porque explora por niveles y la primera solución tiene
la menor profundidad, medida en movimientos; el costo acumulado no ordena su frontera.

### Resultado observado con UCS

La misma ejecución produce este recorrido:

```text
(2, 0) → (1, 0) → (0, 0) → (0, 1) → (0, 2)
       → (0, 3) → (0, 4) → (0, 5) → (0, 6)
       → (0, 7) → (0, 8) → (1, 8) → (2, 8)
```

El camino contiene 13 posiciones y 12 movimientos. Todos los destinos son celdas de camino, por lo que su
costo es `12 × 1 = 12`. UCS prioriza el costo acumulado `g(n)` y prefiere el corredor superior: realiza cuatro
movimientos adicionales, pero evita el pantano. La cantidad de movimientos y el costo de los movimientos son
magnitudes distintas.

### Comparación verificada

| Métrica | BFS | UCS |
|---|---|---|
| Encuentra solución | Sí | Sí |
| Movimientos | 8 | 12 |
| Costo acumulado | 50 | 12 |
| Estrategia | Menor profundidad | Menor costo acumulado |
| Corredor | Directo | Superior |

En términos cuantitativos, UCS realiza `12 - 8 = 4` movimientos adicionales. Reduce el costo en
`50 - 12 = 38`, equivalente a `(38 / 50) × 100 = 76 %` respecto del costo obtenido por BFS en este caso. Estos
valores describen este escenario y no constituyen una proporción general entre los algoritmos.

### Explicación de la diferencia

En teoría, BFS usa una frontera FIFO y explora todos los estados de una profundidad antes de avanzar a la
siguiente. Por eso, cuando cada acción representa un movimiento, optimiza la cantidad de movimientos, pero no
usa el costo acumulado para decidir qué nodo expandir. UCS ordena su frontera por `g(n)`, la suma de los costos
de las acciones. Como el escenario exige costos positivos, extraer el objetivo vigente de la cola de prioridad
conserva la garantía de obtener una solución de costo mínimo para el modelo implementado.

En el experimento, el corredor directo tiene menos movimientos, pero atraviesa terreno costoso. El corredor
superior es más largo y solo entra en celdas de costo 1. Por eso BFS selecciona el primero y UCS el segundo. La
ruta económica depende de los costos declarados en el JSON: si cambian, puede cambiar la prioridad de UCS sin
modificar el algoritmo. Ambos resultados se obtienen a partir del mismo `ProblemaNavegacion`, con idénticos
escenario, estado inicial, unidad, objetivo y reglas de movimiento y costo.

### Particularidad del recurso

El recurso está inicialmente en `(2, 4)`. La ruta directa de BFS entra en esa celda y la transición común lo
asigna a `A1`; la ruta superior de UCS no pasa por allí. La recogida modifica el estado dinámico, pero el objetivo
de este problema de navegación consiste únicamente en ubicar `A1` en `(2, 8)`, y las reglas de movimiento y costo
siguen siendo las mismas para ambos algoritmos. El caso compara rutas de navegación, no estrategias completas de
partida.

### Demostración complementaria en el escenario 20×20

El caso 5×9 facilita la revisión manual de cada transición y costo. Como complemento, `campo_20x20.json` demuestra
el mismo principio sobre un mapa que satisface el requisito dimensional general del proyecto. Ambos algoritmos
parten de `A1` en `(1, 2)` y buscan el objetivo `(9, 10)`:

```bash
python3 -B main.py escenarios/campo_20x20.json --algoritmo ambos
```

| Métrica observada | BFS | UCS |
|---|---:|---:|
| Movimientos | 16 | 34 |
| Costo acumulado | 45 | 34 |

Los recorridos observados son diferentes. El cálculo de referencia confirma que existe una ruta de 16 movimientos
con costo 42, pero no es la que devuelve BFS con el orden actual. BFS minimiza profundidad y conserva el orden de
descubrimiento de sus sucesores; no usa el costo para desempatar entre soluciones de 16 movimientos. Por eso su
resultado observado cuesta 45. UCS sí prioriza el costo acumulado y devuelve 34 movimientos con costo 34.

El escenario 5×9 se conserva como caso mínimo didáctico y el 20×20 como demostración complementaria. Esta
documentación no presupone una excepción académica para el tamaño 5×9; su aceptación como escenario principal de
evaluación requiere confirmación externa.

### Conclusión académica

BFS y UCS encuentran caminos diferentes sobre el mismo mapa porque optimizan criterios distintos. BFS reduce la
cantidad de movimientos y atraviesa el pantano; UCS reduce el costo acumulado y acepta un recorrido más largo por
camino. Ninguno de los dos criterios sustituye al otro: la elección depende de si el problema pide menor
profundidad o menor costo según los terrenos del escenario.

## A* con Manhattan — E6.1

A* usa una cola de prioridad minima ordenada por `f(n) = g(n) + h(n)`. `g(n)` es el costo real acumulado que
`Nodo` y `expandir()` calculan desde `Problema.costo()`; `h(n)` es una cota del costo restante; `f(n)` decide que
nodo vigente se extrae primero. El algoritmo conserva el mejor `g` conocido por `EstadoJuego` completo, reinserta
una mejora estricta y descarta las entradas obsoletas mediante su `g`, no mediante `f`. Un contador monotono
resuelve empates sin comparar nodos ni estados.

La heuristica implementada es:

```text
h(n) = (|fila_n - fila_objetivo| + |columna_n - columna_objetivo|) * costo_minimo_paso
```

`ProblemaNavegacion` calcula una sola vez `costo_minimo_paso` como el menor costo de los terrenos transitables del
escenario validado. El escalamiento es necesario porque el contrato admite costos positivos menores que 1: usar la
distancia Manhattan sin escalar podria sobreestimar. Con las reglas actuales, cada accion de navegacion mueve una
celda ortogonal y cuesta al menos esa cota. Por ello Manhattan escalada es admisible; tambien es consistente porque
un paso reduce la distancia a lo sumo en uno y su costo es al menos `costo_minimo_paso`.

La heuristica consulta la posicion de la unidad navegante, pero los diccionarios del algoritmo conservan la
identidad completa de `EstadoJuego`. Estados con igual posicion y distinto portador, recurso, turno u otras unidades
no se fusionan. Obstaculos y terrenos caros no se incorporan a `h`: mantienen la correccion, aunque reducen su
capacidad de orientar la busqueda. La demostracion de admisibilidad debe revisarse si aparecen diagonales, saltos,
costos no positivos o reglas de costo por unidad inferiores a la cota utilizada.

Con V estados alcanzables, E transiciones examinadas, U unidades por estado y una solucion de profundidad d, la
cota implementada es `O(E * (U log U + U) + (V + E) log E + d * U)` temporal y
`O((V + E) * U + d)` espacial. Incluye la reconstruccion canonica de estados, hashing, evaluaciones heuristicas,
reinserciones y entradas obsoletas. El calculo aritmetico de Manhattan es O(1), pero localizar la unidad actual en
el estado cuesta O(U).

Ejecucion y comparacion de costos:

```bash
python3 -B main.py escenarios/ruta_corta_vs_economica.json --algoritmo a_estrella
python3 -B main.py escenarios/ruta_corta_vs_economica.json --algoritmo ucs
```

A* y UCS deben obtener el mismo costo optimo bajo estas condiciones; no se exige que coincidan el camino, las
metricas ni el tiempo. La opcion `ambos` conserva su significado anterior y ejecuta solamente BFS y UCS.

## Beam Search — E7.1

`algoritmos/busqueda_haz.py` implementa Beam Search por niveles con ancho `k`. En cada nivel se expanden todos los
nodos del haz, sus hijos se ordenan por `f(n) = g(n) + h(n)` (Manhattan escalada de E6.1 por defecto; la heuristica
es un parametro, de modo que la segunda heuristica de E6.2 se puede usar sin cambiar el algoritmo) y solo los `k`
mejores pasan al siguiente nivel; el resto se olvida. Un estado que ya entro en un haz no vuelve a entrar. El objetivo
se comprueba al formar cada haz y los empates se resuelven por orden de generacion, por lo que el resultado es
determinista. Reporta las metricas de E4.1 con el nombre `BEAM_SEARCH_K<k>`; un estado cuenta como generado cuando
entra al haz, por lo que el maximo de frontera nunca supera `k`.

Beam Search no es completo ni optimo. Con `k = 1` actua como una busqueda voraz; con `k` mayor que cualquier nivel no
poda y se comporta como BFS (minimo numero de movimientos, eligiendo el objetivo de menor `f` en ese nivel). Por eso
aumentar `k` no siempre reduce el costo. Resultados reproducibles (`tests/algoritmos/test_busqueda_haz.py`):

| Escenario | k = 1 | k = 2 | k = 4 | k = 8 | UCS (optimo) |
|---|---|---|---|---|---|
| `ejemplo_enunciado.json` | costo 12, 6 mov. | costo 7, 6 mov. | costo 14, 4 mov. | costo 14, 4 mov. | costo 7 |
| `ruta_corta_vs_economica.json` | costo 12, 12 mov. | costo 12, 12 mov. | costo 50, 8 mov. | costo 50, 8 mov. | costo 12 |
| `obstaculo_rodeo.json` | costo 20, 19 mov. | sin solucion | costo 16, 15 mov. | costo 16, 15 mov. | costo 16 |
| `campo_20x20.json` | sin solucion | sin solucion | costo 40, 34 mov. | costo 46, 36 mov. | costo 34 |

`k` se configura sin modificar codigo: desde la consola con `--k` (admite varios valores) o desde el JSON con el
campo propio `prueba.k`. La consola tiene prioridad sobre el JSON; un `k` que no sea un entero mayor o igual que 1 se
rechaza con un mensaje claro.

```bash
python3 -B main.py escenarios/campo_20x20.json --algoritmo beam --k 1 2 4 8
```

## Ejecución desde consola

Desde la raíz del repositorio, la ejecución sin argumentos usa UCS y el escenario predeterminado
`escenarios/campo_20x20.json`:

```bash
python3 -B main.py
```

La demostración E5.2 selecciona explícitamente el escenario 5×9 y ambos algoritmos:

```bash
python3 -B main.py escenarios/ruta_corta_vs_economica.json --algoritmo ambos
```

Otras selecciones disponibles son:

```bash
python3 main.py --algoritmo bfs
python3 main.py --algoritmo ucs
python3 main.py --algoritmo a_estrella
python3 main.py --algoritmo beam --k 4
python3 main.py --algoritmo ambos
```

Si no se indican más argumentos, la unidad y el objetivo se leen de `prueba.unidad_inicio` y `prueba.objetivo`
del escenario. Para elegirlos explícitamente, use `--unidad ID` y `--objetivo FILA COLUMNA`; por ejemplo:

```bash
python3 main.py --algoritmo ucs --unidad A1 --objetivo 9 10
```

Dependencias prohibidas: juego no importa Pygame ni JSON; algoritmos no importan Pygame, no abren JSON ni codifican mapas, posiciones o costos; interfaz no decide reglas; escenario no depende de algoritmos. Los costos se consultan desde el escenario cargado.

## Estructura

```text
src/tacticalgrid/
├── escenario/
├── juego/
├── algoritmos/
├── interfaz/
└── servidor/
tests/
├── escenario/
├── juego/
├── algoritmos/
└── servidor/
escenarios/
```

El contrato JSON usa literalmente `version`, `mapa.filas`, `mapa.columnas`, `tipos_terreno`, `terreno`, `bases.A`, `bases.B`, `recurso`, `unidades`, `turno`, `juego.portador_recurso` y `prueba`.

## Windows (PowerShell)

Requiere Python 3.12 o 3.13 (no 3.14: Pygame aun no publica instalador para esa version). Con `py -0` se listan las versiones instaladas; si solo tienes 3.12, usa `py -3.12` en lugar de `py -3.13`.

```powershell
git clone https://github.com/diego-juan3112/tactical-grid.git
cd tactical-grid
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python --version
python -m pip install --upgrade pip
python -m pip install -e ".[desarrollo]"
python -m pytest
tacticalgrid
python -m uvicorn tacticalgrid.servidor.asgi:aplicacion --reload
```

`python --version` debe mostrar 3.12.x o 3.13.x antes de instalar. Si muestra 3.14, borra `.venv` y vuelve a crearlo con una version admitida.

## Linux

Requiere Python 3.12 o 3.13 (no 3.14). Si `python3 --version` muestra otra version, usa el ejecutable explicito, por ejemplo `python3.13` o `python3.12`.

```bash
git clone https://github.com/diego-juan3112/tactical-grid.git
cd tactical-grid
python3.13 -m venv .venv
source .venv/bin/activate
python --version
python -m pip install --upgrade pip
python -m pip install -e '.[desarrollo]'
python -m pytest
tacticalgrid
python -m uvicorn tacticalgrid.servidor.asgi:aplicacion --reload
```

En Linux se verificaron la instalacion en `.venv`, pytest y Uvicorn; el clon no se repitio porque este repositorio ya estaba presente. `uvicorn tacticalgrid.servidor.asgi:aplicacion --reload` inicia el servidor ASGI en desarrollo. `tacticalgrid` abre la interfaz minima de Pygame y se cierra mediante el control de la ventana.

Para salir del entorno virtual en Windows o Linux:

```bash
deactivate
```

## Escenarios

Todos los escenarios viven en `escenarios/` y usan el formato JSON comun. El campo propio `descripcion` explica el proposito de cada uno; `prueba` indica la navegacion a resolver (unidad y objetivo) o el modo de juego.

| Archivo | Tamano | Proposito |
|---|---|---|
| `ejemplo_enunciado.json` | 4 x 4 | Ejemplo literal del enunciado. |
| `arquitectura_basica.json` | 20 x 20 | Mapa abierto, todo camino; comprueba carga y exploracion en 20 x 20. |
| `campo_20x20.json` | 20 x 20 | Mapa principal de desarrollo: anillo de camino, lago de pantano con el recurso en una isla, bosques y muros. BFS observado: 16 movimientos y costo 45; el calculo de referencia encuentra como minimo 42 entre las rutas de 16 movimientos. UCS observado: 34 movimientos y costo 34. |
| `ruta_corta_vs_economica.json` | 5 x 9 | BFS vs. UCS: la ruta recta por pantano tiene 8 movimientos y cuesta 50; rodear por camino toma 12 movimientos y cuesta 12. Con el pantano a costo 1, ambas coinciden. |
| `obstaculo_rodeo.json` | 8 x 7 | El objetivo esta a distancia Manhattan 3, pero un muro en U obliga a un recorrido de 15 movimientos (caso 3: obstaculo y heuristica). |
| `recurso_en_transporte.json` | 6 x 8 | Partida con `portador_recurso` = `A2` (caso 6: estado compuesto). |

Las propiedades de los escenarios se verifican con un calculo de referencia y con las implementaciones de BFS y
UCS sobre el modelo del juego. Cuando el resultado observado depende del desempate del algoritmo, la tabla lo
distingue del optimo de referencia.
