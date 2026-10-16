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

## Recoger y transportar el recurso — E3.2

Las reglas del recurso viven en `juego/recurso.py`, que solo consulta y transforma `EstadoJuego` (no lee JSON, no conoce Pygame ni los algoritmos). Antes estaban mezcladas dentro de `reglas.py`; E3.2 las extrae a un módulo propio sin cambiar el comportamiento y `reglas.py` las reutiliza.

- **Recoger:** una unidad recoge el recurso automáticamente al entrar en la celda donde está libre (`recoger_recurso`). Entonces `portador_recurso` pasa a ser su identificador y `posicion_recurso` queda en `null`. Pasar junto al recurso sin entrar en su celda no lo recoge.
- **Transportar:** mientras tiene portador, el recurso viaja con él. `posicion_del_recurso(estado)` responde dónde está el recurso, libre o transportado, y `obtener_portador(estado)` devuelve la unidad que lo lleva.
- **Ganar:** un bando gana cuando su portador está en la base de ese mismo bando (`bando_que_entrego_recurso`). Llevarlo a la base adversaria no da la victoria. Si el recurso estaba en la propia base y la unidad lo recoge allí, gana de inmediato.
- **Simetría:** A y B usan exactamente las mismas reglas.

`tests/juego/test_recurso.py` verifica cada criterio, incluida una partida completa sobre `escenarios/ejemplo_enunciado.json` en la que A1 recoge el recurso, lo transporta y gana en su base.

E2.2 completa el validador de escenarios. Antes de construir el `Escenario` se comprueban todas las reglas del enunciado: dimensiones consistentes con la matriz, terrenos declarados, costos positivos, posiciones dentro del mapa, unidades sobre celdas transitables, ids unicos, bandos y turno validos, y portador existente. Cualquier incumplimiento lanza `ErrorValidacionEscenario` con un mensaje que nombra el campo, el elemento y el valor recibido. Como la validacion ocurre completa antes de aplicar nada, una carga fallida no reemplaza ni altera el escenario vigente.

E2.3 agrega un set propio de escenarios en `escenarios/` para desarrollar y depurar algoritmos antes de recibir los del profesor: un mapa de 20 x 20 con todos los tipos de terreno y variantes pequenas. En `campo_20x20.json` y `ruta_corta_vs_economica.json` la ruta con menos movimientos es mas costosa que una mas larga, por lo que BFS y UCS producen caminos distintos. Las pruebas de `tests/escenario/test_escenarios_propios.py` comprueban estas propiedades sobre el modelo de E1.2, con los costos leidos del JSON.

E4.1 agrega la instrumentacion comun de busqueda en `algoritmos/instrumentacion.py`, para que BFS, DFS, UCS, A* y Beam Search reporten resultados comparables sin duplicar codigo. `Nodo` guarda estado, padre, accion, costo acumulado y profundidad; `expandir` genera los hijos en el orden de las acciones, con el costo leido del escenario, y cuenta la expansion; `MedidorBusqueda` lleva estados generados (incorporados a la frontera, incluido el inicial), estados expandidos, maximo de frontera y tiempo, y construye el `ResultadoBusqueda`. `ResultadoBusqueda.a_diccionario()` devuelve la estructura del enunciado (`algoritmo`, `exito`, `camino`, `costo`, `estados_generados`, `estados_expandidos`, `maximo_frontera`) mas `longitud` y `tiempo_segundos`; el resultado tambien conserva las acciones para el verificador de soluciones.

## BFS — E4.2

BFS es una busqueda no informada: usa una frontera FIFO y explora los estados por niveles. Con cada accion equivalente a un movimiento, encuentra una solucion con la menor cantidad de movimientos. El costo del terreno no afecta el orden ni desempata rutas; `ResultadoBusqueda.costo` aun informa la suma real de costos del camino y `longitud` informa sus movimientos.

La implementacion consume `Problema`, marca el `EstadoJuego` completo como descubierto al encolarlo y descarta estados repetidos. Esto evita ciclos y conserva diferencias de estado relevantes, como el portador del recurso. Mantiene el orden de acciones del problema para resultados deterministas. Cada `Nodo` conserva padre y accion; `MedidorBusqueda.finalizar()` reconstruye camino y acciones. Si la frontera se agota, el resultado indica fracaso, con camino y acciones vacios y costo `None`; los contadores y el tiempo reflejan la exploracion realizada. BFS reutiliza las metricas E4.1 y no depende de dimensiones, coordenadas ni escenarios particulares.

## DFS — E4.3

DFS es la otra busqueda no informada del proyecto: usa una frontera LIFO (una pila) y sigue cada rama hasta el fondo antes de retroceder. No garantiza el camino con menos movimientos ni el mas barato: devuelve el primero que encuentra. `ResultadoBusqueda.costo` y `longitud` informan el costo real y los movimientos de ese camino.

DFS comparte con BFS todo salvo la frontera, para que la comparacion de E4.4 aisle esa unica diferencia:

- Consume el contrato `Problema` y las metricas de E4.1 (`Nodo`, `expandir`, `MedidorBusqueda`), con la misma convencion de conteo.
- Marca el `EstadoJuego` completo como descubierto al apilarlo y descarta estados repetidos. Asi evita ciclos (una unidad puede ir y volver) y termina siempre en espacios finitos, y conserva diferencias de estado como el portador del recurso.
- Comprueba el objetivo al extraer de la pila, igual que BFS.
- Apila los hijos en orden inverso para explorar primero el primer movimiento de `DESPLAZAMIENTOS` (arriba, abajo, izquierda, derecha). Por eso el resultado es determinista, y cambiar ese orden cambia el camino de DFS.
- Usa una pila explicita, sin recursion, para no depender del limite de recursion de Python en mapas grandes.

Ejemplo verificado en `tests/algoritmos/test_busqueda_profundidad.py`, en un mapa abierto de 3x3 con la unidad en (0, 0) y el objetivo en (0, 2): BFS llega en 2 movimientos, mientras DFS baja primero por la columna 0 y da la vuelta al mapa en 6 movimientos, con 9 estados generados, 6 expandidos y un maximo de frontera de 3. Si el objetivo es inalcanzable, DFS agota la pila tras visitar exactamente los mismos estados alcanzables que BFS.

En el escenario predeterminado `campo_20x20.json` (de (1, 2) a (9, 10)), DFS expande menos estados que BFS (102 frente a 186), pero devuelve un camino mucho peor (98 movimientos y costo 283, frente a 16 movimientos y costo 45). Ademas, su frontera maxima es mayor (104 frente a 20). La ventaja de memoria que suele atribuirse a DFS, una pila de tamaño O(b * m), vale para la busqueda en arbol, que solo guarda la rama actual. En esta busqueda en grafo, cada expansion deja en la pila hermanos pendientes que se acumulan mientras se profundiza.

## E4.4 — Caso mínimo 1: BFS vs. DFS

### Propósito del experimento

Este caso demuestra que BFS (E4.2) y DFS (E4.3) encuentran solución sobre el mismo problema, pero recorren el
espacio de búsqueda de forma distinta. Ambos usan el mismo `ProblemaNavegacion`, la misma detección de estados
repetidos, la misma prueba de objetivo y las métricas de E4.1; la única diferencia es la frontera: cola (FIFO) en
BFS y pila (LIFO) en DFS. Las afirmaciones de esta sección están fijadas como pruebas en
`tests/algoritmos/test_caso_minimo_1.py`.

### Configuración reproducible

Escenario principal (cumple el mínimo de 20×20):

- Escenario: `escenarios/campo_20x20.json`. Unidad `A1` en `(1, 2)`; objetivo `(9, 10)`, la isla del recurso.
- Movimientos ortogonales generados en el orden arriba, abajo, izquierda, derecha.

Complemento verificado a mano:

- Escenario: `escenarios/ejemplo_enunciado.json` (4×4). Unidad `A1` en `(0, 1)`; objetivo `(3, 2)`, el mismo de
  `prueba.objetivo`.

```bash
python3 -B main.py escenarios/campo_20x20.json --algoritmo bfs_dfs
python3 -B main.py escenarios/ejemplo_enunciado.json --algoritmo bfs_dfs
```

La opción `bfs_dfs` ejecuta ambos algoritmos sobre el mismo problema e imprime una tabla comparativa.

### Resultados esperados y observados — escenario 4×4

Los valores esperados se obtuvieron con una traza manual de cada frontera. Para BFS, una cola de la que se extrae
por el frente; para DFS, una pila en la que los hijos se apilan en orden inverso, de modo que se extrae primero el
de la acción "arriba". En ambos casos el estado se marca al incorporarlo a la frontera.

```text
      0 1 2 3
F0    C A P P        A = inicio (0, 1), G = objetivo (3, 2)
F1    C # B P        C camino 1, P pasto 2, B bosque 4, S pantano 7, # muro
F2    C C S P        El recurso está en (2, 2)
F3    P P G C
```

| Métrica | BFS esperado | BFS observado | DFS esperado | DFS observado |
|---|---:|---:|---:|---:|
| Encuentra solución | Sí | Sí | Sí | Sí |
| Movimientos | 4 | 4 | 6 | 6 |
| Costo | 14 | 14 | 8 | 8 |
| Estados generados | 19 | 19 | 9 | 9 |
| Estados expandidos | 12 | 12 | 6 | 6 |
| Máximo de frontera | 7 | 7 | 3 | 3 |

Orden de expansión:

- **BFS:** `(0,1)`, `(0,0)`, `(0,2)`, `(1,0)`, `(1,2)`, `(0,3)`, `(2,0)`, `(2,2)*`, `(1,3)`, `(3,0)`, `(2,1)`, `(1,2)*`.
  Primero el inicio, luego sus vecinos, luego las celdas a dos pasos, y así sucesivamente. Las marcadas con `*` son
  estados en los que `A1` ya porta el recurso: al entrar en `(2, 2)` lo recoge, y por eso `(1, 2)` aparece dos veces
  como estados distintos (caso 6, estado compuesto). Camino: `(0,1) → (0,2) → (1,2) → (2,2) → (3,2)`, costo
  `2 + 4 + 7 + 1 = 14`.
- **DFS:** `(0,1)`, `(0,0)`, `(1,0)`, `(2,0)`, `(3,0)`, `(3,1)`. Desde el inicio, "arriba" sale del mapa y "abajo" es
  muro, así que sigue "izquierda" y desde ahí baja por la columna 0 sin volver atrás. Camino:
  `(0,1) → (0,0) → (1,0) → (2,0) → (3,0) → (3,1) → (3,2)`, costo `1 + 1 + 1 + 2 + 2 + 1 = 8`.

Los valores esperados y observados coinciden. En este mapa DFS resulta más barato que BFS, pero por azar del orden
de las acciones: ninguno de los dos usa el costo para decidir.

### Resultados esperados y observados — escenario 20×20

En el mapa grande no es práctico trazar a mano las 186 expansiones de BFS, así que los valores esperados son
propiedades derivadas de cada algoritmo y los observados son los valores medidos:

| Propiedad | Esperado | Observado |
|---|---|---|
| Ambos encuentran solución | Sí, el objetivo es alcanzable | BFS sí, DFS sí |
| Movimientos de BFS | El mínimo posible: la distancia Manhattan, `8 + 8 = 16` | 16 |
| Orden de expansión de BFS | Profundidad mínima no decreciente (por ondas) | Se cumple para los 186 estados expandidos |
| Movimientos de DFS | Mayor que 16: sigue la primera rama sin medir longitud | 98 |
| Orden de expansión de DFS | No respeta niveles | Se cumple |

| Métrica observada | BFS | DFS |
|---|---:|---:|
| Movimientos | 16 | 98 |
| Costo | 45 | 283 |
| Estados generados | 205 | 206 |
| Estados expandidos | 186 | 102 |
| Máximo de frontera | 20 | 104 |

### Cómo recorre el mapa cada algoritmo

`*` es el camino devuelto, `o` una celda expandida fuera del camino, `.` una celda no expandida y `#` un muro.

```text
BFS (186 expandidos)                         DFS (102 expandidos)
      01234567890123456789                         01234567890123456789
F0    oooooooooooooooooo..                   F0    ***.***.***.........
F1    ooAooooooooooooooo..                   F1    *.A.*.*.*.*.........
F2    oo*oooooooooooooo...                   F2    *..**.*.*.*.........
F3    oo*ooooooooooooo....                   F3    *.**..*.*.*.........
F4    oo*ooooooooo#####...                   F4    *.*...*.*.*.#####...
F5    oo*ooooooooooo......                   F5    *.*...*.*.*.........
F6    oo*oooooooooo.......                   F6    *.*...*.*.*.........
F7    oo*ooooooooo........                   F7    *.*...*.*.*.........
F8    oo*oooooooo.........                   F8    *.*...*.*.*.........
F9    oo********G.........                   F9    *.*...*.*.G.........
F10   oooooooooo..........                   F10   *.*...*.*...........
F11   ooooooooo...........                   F11   *.*...*.*...........
F12   oooo#ooo............                   F12   *.*.#.*.*...........
F13   oooo#oo.............                   F13   *.*.#.*.*...........
F14   oooo#o..............                   F14   *.*.#.*.*...........
F15   oooo#...............                   F15   *.*.#.*.*...........
F16   .ooo#...............                   F16   *.*.#.*.*...........
F17   ..o.................                   F17   *.*.o.*.*...........
F18   ....................                   F18   *.*.o.*.*...........
F19   ....................                   F19   ***.oo***...........
```

- **BFS** avanza como una onda desde `(1, 2)`: expande todas las celdas a distancia 1, luego a distancia 2, etc. La
  región explorada es aproximadamente un rombo alrededor del inicio, recortado por los bordes y los muros. Cuando
  extrae el objetivo ya expandió todo lo que está a 15 movimientos o menos y parte de lo que está a 16, por eso su
  camino es el más corto posible.
- **DFS** se mete en una sola rama y la sigue hasta el fondo. Desde `(1, 2)` toma "arriba", luego "izquierda" hasta
  `(0, 0)` y baja por toda la columna 0. Como marca los estados al apilarlos, las celdas vecinas que deja pendientes
  (por ejemplo, toda la columna 1) quedan descubiertas y no vuelven a entrar a la pila. Por eso el camino avanza en
  columnas alternas, formando una serpiente (columnas 0, 2, 6, 8 y 10), hasta que la columna 10 lo lleva al
  objetivo. De los 102 estados que expande, 98 son posiciones de su propio camino; solo `(17,4)`, `(18,4)`, `(19,4)`
  y `(19,5)` quedan fuera.
- **Frontera:** BFS nunca guarda más de 20 estados porque la onda es angosta en este mapa. DFS llega a 104, porque
  cada celda de la serpiente deja hermanos pendientes en la pila que no se retiran mientras siga profundizando.

### Conclusión académica

BFS y DFS son búsquedas no informadas sobre el mismo modelo, y la única diferencia entre ellos es el orden en que
extraen de la frontera. Ese solo cambio produce exploraciones opuestas: BFS recorre el espacio por niveles y
garantiza el menor número de movimientos, a costa de expandir casi todo lo cercano al inicio; DFS sigue una rama
hasta el fondo, expande menos estados, pero devuelve el primer camino que encuentra, que puede ser mucho más largo
(98 frente a 16 movimientos) y, en esta implementación en grafo, puede necesitar más frontera que BFS. Ninguno usa
los costos del terreno; para eso están UCS y A*.


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

### Casos mínimos 3 y 4: obstáculo y comparación de heurísticas

[Casos mínimos 3 y 4](docs/casos-minimos-obstaculo-y-heuristicas.md) documenta la ruta obligada por el muro de
`obstaculo_rodeo.json` y compara A* con Manhattan, A* con HTO y UCS sobre la misma configuración. Las pruebas de
`tests/algoritmos/test_casos_minimos_heuristicas.py` verifican el rodeo, la legalidad del camino, el costo y las
métricas discretas. La comparación se reproduce con:

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python \
  scripts/comparar_heuristicas_e62.py --repeticiones 1 --calentamiento 0
```

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

El parametro opcional `observador` de `busqueda_haz` recibe un `NivelHaz` por cada nivel (candidatos conservados y
descartados con su `f`) sin alterar el resultado; se usa en el analisis de E7.2 y sirve para visualizar la exploracion.

`k` se configura sin modificar codigo: desde la consola con `--k` (admite varios valores) o desde el JSON con el
campo propio `prueba.k`. La consola tiene prioridad sobre el JSON; un `k` que no sea un entero mayor o igual que 1 se
rechaza con un mensaje claro.

```bash
python3 -B main.py escenarios/campo_20x20.json --algoritmo beam --k 1 2 4 8
```

## E7.2 — Caso mínimo 5: efecto de k en Beam Search

### Propósito del experimento

Este caso analiza cómo cambia Beam Search (E7.1) al variar el ancho del haz `k` sobre el mismo escenario, estado
inicial, unidad y objetivo. Se busca observar qué ocurre con la exploración y con la solución cuando se restringe
la cantidad de alternativas conservadas y, en particular, identificar el momento exacto en que el haz descarta un
camino que después habría sido conveniente. Las afirmaciones de esta sección están fijadas como pruebas en
`tests/algoritmos/test_caso_minimo_5.py`.

### Configuración reproducible

- Escenario: `escenarios/campo_20x20.json` (20 filas por 20 columnas), creado en E2.3.
- Unidad: `A1`, con posición inicial `(1, 2)`. Objetivo posicional: `(9, 10)`, la isla del recurso.
- Anchos evaluados: `k = 1, 2, 4, 8`.
- Orden de los candidatos: `f(n) = g(n) + h(n)` con Manhattan escalada de E6.1; empates por orden de generación
  (las acciones se generan arriba, abajo, izquierda, derecha).
- Referencias sobre el mismo problema: UCS (costo óptimo) y BFS (mínimo número de movimientos).

```bash
python3 -B main.py escenarios/campo_20x20.json --algoritmo beam --k 1 2 4 8
```

La consola imprime cada resultado y, al final, una tabla comparativa por `k`.

### Representación del mapa

```text
      0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9
F0    P C C C C C C C C C C C C C C C C C C C
F1    P C A C C C C C C C C C C C C C C C C P
F2    P C P P P P P P P P P P P P P P P P C P
F3    P C P B B B P P P P P P P P P P P P C P
F4    P C P B B B B B B B B B # # # # # P C P
F5    P C P B B B B B B B B B B B P P P P C P
F6    P C P P P P S S S S S S S S P P P P C P
F7    P C P P P P S S S S S S S S P P P P C P
F8    P C P P P P S S S S S S S S P P P P C P
F9    P C P P P P S S S C G S S S P P P P C P
F10   P C P P P P S S S C C C C C C C C C C P
F11   P C P P P P S S S S S S S S P C P P C P
F12   P C P P # P S S S S S S S S P C P P C P
F13   P C P P # P S S S S S S S S P C C C C P
F14   P C P P # P P P P P P P P P P P P P C P
F15   P C P P # P P P P P P P P P B B B P C P
F16   P C P P # P P P P P P P P P B B B P C P
F17   P C P P P P P P P P P P P P B B B P C P
F18   P C C C C C C C C C C C C C C C C C C P
F19   C C C C C C C C C C C C C C C C C C C P
```

`A` es el inicio y `G` el objetivo. `C` es camino (costo 1), `P` pasto (2), `B` bosque (4), `S` pantano (7) y `#`
muro. La ruta óptima (UCS, costo 34) recorre la carretera de la fila 1 hasta la columna 18, baja por la columna 18
hasta la fila 10 y entra a la isla por la carretera de la fila 10.

### Resultados observados

| k | Solución | Movimientos | Costo | Estados generados | Estados expandidos | Máximo de frontera | Niveles |
|---:|:---:|---:|---:|---:|---:|---:|---:|
| 1 | No | — | — | 74 | 74 | 1 | 74 |
| 2 | No | — | — | 137 | 137 | 2 | 70 |
| 4 | Sí | 34 | 40 | 137 | 133 | 4 | 34 |
| 8 | Sí | 36 | 46 | 284 | 276 | 8 | 36 |
| UCS (referencia) | Sí | 34 | 34 | 374 | 333 | — | — |
| BFS (referencia) | Sí | 16 | 45 | — | — | — | — |

El tiempo se reporta en consola, pero no se fija en la tabla porque depende de la máquina.

### Dónde se descarta el camino conveniente

Para cada `k` se comparó, nivel por nivel, el contenido del haz con los estados de la ruta óptima de UCS (el estado
de profundidad `i` de esa ruta debería estar en el nivel `i` del haz). Ningún `k` entre 1 y 8 conserva la ruta de
costo 34:

| k | Nivel | Estado de la ruta óptima descartado | `f` del descartado | `f` del último conservado |
|---:|---:|:---:|---:|---:|
| 1 | 9 | `(1, 11)` | 18 | 17 |
| 2 | 9 | `(1, 11)` | 18 | 18 |
| 4 | 11 | `(1, 13)` | 22 | 22 |
| 8 | 12 | `(1, 14)` | 24 | 24 |

- **k = 1.** En el nivel 9 la unidad está en `(1, 10)`, sobre la carretera. Bajar a `(2, 10)` (pasto) da
  `f = g + h = 10 + 7 = 17`; seguir a `(1, 11)` da `9 + 9 = 18`. La heurística premia acercarse en vertical a la isla
  e ignora que debajo están el bosque y el pantano, así que el único lugar del haz se lo queda el desvío. A partir de
  ahí la unidad rodea el lago por el oeste y el sur, y en el nivel 74 queda en `(15, 5)` rodeada de celdas que ya
  pasaron por el haz: el haz se vacía y la búsqueda termina **sin solución**, aunque el objetivo es alcanzable.
- **k = 2.** El segundo lugar del nivel 9 lo ocupa `(0, 10)`, que empata con `(1, 11)` en `f = 18` y se generó antes
  (la acción "arriba" se genera antes que "derecha"). La ruta óptima se pierde por **empate** y el haz termina
  atrapado en la misma zona que con `k = 1`.
- **k = 4.** Conserva la carretera más tiempo, pero en el nivel 11 descarta `(1, 13)` (`f = 22`), otra vez por empate
  con el último conservado. Continúa por el pasto de la fila 2 y llega con **costo 40**: seis más que el óptimo.
- **k = 8.** En el nivel 12 la mitad del haz está ocupada por celdas del oeste (columnas 2 a 4, `f` entre 21 y 23),
  que Manhattan considera prometedoras porque se acercan a la isla, pero el lago les cierra el paso. Esos lugares
  desplazan a `(1, 14)` y la solución final cuesta **46**, peor que con `k = 4`.

### Efecto sobre la exploración

Restringir `k` limita la memoria: el máximo de frontera es exactamente `k` en los cuatro casos. Sin embargo, los
estados generados y expandidos no crecen de forma monótona: `k = 4` genera lo mismo que `k = 2` (137) porque
encuentra el objetivo en 34 niveles, mientras que `k = 2` explora 70 niveles hasta quedarse sin candidatos. `k = 8`
explora más que todos (284 generados), porque mantiene ramas que no llevan a ninguna parte. Todas las variantes
exploran menos que UCS (374 generados), que es la contrapartida de no garantizar la solución óptima.

### Caso complementario: aumentar k empeora el costo

En `ruta_corta_vs_economica.json` (caso mínimo 2), ocurre lo contrario: la poda ayuda.

| k | Movimientos | Costo |
|---:|---:|---:|
| 1 | 12 | 12 |
| 2 | 12 | 12 |
| 4 | 8 | 50 |
| 8 | 8 | 50 |

En el nivel 1, desde `(2, 0)`, los candidatos son camino `(1, 0)` con `f = 10`, pasto `(3, 0)` con `f = 11` y pantano
`(2, 1)` con `f = 14`. Con `k = 1` y `k = 2` el pantano se descarta y solo sobrevive el rodeo barato (costo 12, igual
que UCS). Con `k = 4` el pantano también entra al haz; como Beam Search avanza por niveles y se detiene en el primer
nivel que contiene el objetivo, el corredor de pantano llega en el nivel 8, antes que el rodeo (nivel 12), y la
solución cuesta 50, la misma que BFS.

### Conclusión académica

`k` controla cuánta memoria usa Beam Search, pero no cuánto se acerca a la solución óptima. Un haz estrecho puede
descartar el camino conveniente en un único nivel —por una heurística que ignora obstáculos y terrenos caros, o por un
simple empate resuelto por el orden de las acciones— y quedar sin solución aunque exista. Un haz más ancho conserva
más alternativas, pero también más candidatos engañosos, y al detenerse en el primer nivel que contiene el objetivo
favorece los caminos cortos aunque sean caros. En el límite, sin poda, Beam Search se comporta como BFS. Por eso el
efecto de `k` depende del escenario y debe evaluarse experimentalmente, no suponerse monótono.

## Acciones tácticas adversariales — E8.1

E8.1 define el espacio de acciones que usarán Minimax y alfa-beta, sin convertir el juego en un sistema de combate:
no hay puntos de vida, ataques ni eliminación de unidades. El juego tiene solo dos mecánicas.

- **Mover** (`tipo = "mover"`, E1.2): la unidad avanza una celda ortogonal a una celda dentro del mapa, transitable
  y libre.
- **Interceptar** (`tipo = "interceptar"`, nueva): una unidad ortogonalmente adyacente al portador rival usa su
  turno para quitarle el recurso. Nadie se mueve; el recurso pasa al interceptor mediante `resolver_intercepcion`
  (E1.3) y `aplicar_accion` alterna el turno una sola vez. En la acción, `origen` es la celda del interceptor y
  `destino` la del portador; su costo es el del terreno de esa celda, leído del JSON. Si el interceptor está en su
  propia base, gana en ese momento. Sin esta acción, la intercepción de E1.3 no podía ocurrir, porque una unidad
  nunca puede entrar en la celda ocupada del portador.

`acciones_validas` agrega la intercepción después de los movimientos de cada unidad, así que cada unidad aporta a lo
sumo cinco acciones. Como ambos bandos usan las mismas reglas, si el antiguo portador sigue adyacente puede
recuperar el recurso en su turno.

Las tácticas del enunciado no son mecánicas nuevas, sino el significado de cada acción legal en la situación
actual. `juego/tacticas.py` las clasifica, en orden de prioridad (`d` es la distancia Manhattan):

| Tipo táctico | Situación | Condición |
|---|---|---|
| `interceptar_portador` | El rival porta el recurso | La acción es una intercepción. |
| `aproximarse_al_recurso` | Recurso libre | El movimiento reduce `d` hasta el recurso (incluye recogerlo). |
| `avanzar` | La unidad porta el recurso | El movimiento reduce `d` hasta su base. |
| `proteger_zona` | Un aliado porta el recurso | El movimiento reduce `d` hasta el portador aliado (lo escolta). |
| `bloquear_posicion` | El rival porta el recurso | El destino queda en el rectángulo entre el portador rival y su base, es decir, sobre alguna de sus rutas más cortas. |
| `perseguir_portador` | El rival porta el recurso | No bloquea, pero reduce `d` hasta el portador rival. |
| `reposicionar` | Cualquiera | Ninguna de las anteriores. |

`acciones_tacticas(escenario, estado)` devuelve las mismas acciones que `acciones_validas`, en el mismo orden, cada
una con su tipo táctico. La clasificación solo usa "propio" y "rival", nunca un bando concreto, por lo que A y B
tienen las mismas tácticas: MAX y MIN serán roles, no capacidades distintas. El tipo táctico sirve para explicar
una decisión de Minimax (por ejemplo, que bloquear sea mejor que acercarse al recurso) y para experimentar con el
orden de las acciones; no altera la legalidad.

Las pruebas de `tests/juego/test_tacticas.py` cubren cuándo se puede interceptar y cuándo no (en diagonal, a dos
celdas, sin portador, portador aliado), su efecto y su costo, la victoria al interceptar desde la propia base, cada
tipo táctico, la simetría entre bandos y la legalidad de todas las acciones en partidas de hasta cuatro jugadas
sobre `ejemplo_enunciado.json`, `recurso_en_transporte.json` y `campo_20x20.json`.

## Función de utilidad propia — E8.2

`algoritmos/utilidad.py` evalúa un estado desde la perspectiva de MAX: mayor es mejor para MAX y menor es mejor
para MIN. Es la función que Minimax y alfa-beta (E8.3, E8.4) usarán en las hojas del árbol.

```python
evaluador = EvaluadorUtilidad(escenario, bando_max="A")    # pesos por defecto
evaluador.evaluar(estado)                                   # un número
evaluador.desglosar(estado)                                 # aporte de cada criterio
valorar_acciones(evaluador, estado)                         # cada acción legal con la utilidad a la que lleva
```

### Diseño: suma cero

Cada criterio se calcula como "lo bueno para MAX menos lo bueno para MIN". Por eso, si se intercambia qué bando es
MAX, cada criterio cambia exactamente de signo. MIN no está en desventaja: minimizar esta utilidad es lo mismo que
maximizar la suya. Las pruebas lo comprueban sobre todos los estados alcanzables en tres jugadas de
`ejemplo_enunciado.json` y `recurso_en_transporte.json`.

### Criterios y justificación de los pesos

Las distancias se miden con el **costo del terreno del JSON y respetando muros**: para cada base y para la
posición del recurso se calcula una sola vez, con Dijkstra invertido, el costo mínimo desde cada celda. Esos costos
coinciden con el costo óptimo de UCS. Si una celda no puede llegar al destino, se le asigna un costo mayor que
cualquier ruta del mapa.

| Criterio | Qué mide | Fórmula (MAX = +, MIN = −) | Peso | Por qué ese peso |
|---|---|---|---:|---|
| `terminal` | Fin de la partida | `±victoria`; empate por bloqueo = 0 | 10 000 | Muy superior a cualquier suma de los demás criterios: ganar siempre vale más que cualquier ventaja posicional. |
| `posesion` | Quién tiene el recurso | `±posesion` | 100 | Tener el recurso es la condición necesaria para ganar; equivale a 50 unidades de costo de camino, más que cualquier distancia de los mapas de desarrollo. |
| `entrega` | Cuánto le falta al portador | `∓entrega × costo(portador → su base)` | 2 | Cada unidad de costo ahorrada acerca la victoria. Es pequeño frente a `posesion` para que entregar no compense perder el recurso. |
| `carrera_recurso` | Quién llega antes al recurso libre | `carrera × (costo_MIN − costo_MAX)` | 2 | Misma escala que `entrega`: con el recurso libre, la ventaja es llegar primero. |
| `amenaza` | Rivales que pueden interceptar ya | `∓amenaza × rivales adyacentes al portador` | 60 | Un rival adyacente puede quitar el recurso en su turno (E8.1), lo que haría perder los 100 de posesión. Vale más que 30 unidades de costo, así que el portador acepta un rodeo moderado para no quedar expuesto. |
| `bloqueo` | Rivales sobre la ruta corta del portador | `∓bloqueo × rivales en el rectángulo portador–base` | 10 | Un rival en la ruta obliga a rodear o a arriesgarse a la intercepción; es una amenaza futura, por eso pesa menos que `amenaza`. |
| `movilidad` | Unidades disponibles | `movilidad × (unidades de MAX con movimientos − las de MIN)` | 1 | Las unidades no se eliminan, pero una unidad bloqueada no aporta. Es un desempate. |

### Por qué una acción vale más que otra

`valorar_acciones` aplica cada acción legal y evalúa el estado resultante. Comparando los desgloses se ve qué
criterio decide. En `recurso_en_transporte.json`, con MAX = A, el estado inicial vale **72**
(`posesion 100`, `entrega −18`, `bloqueo −10`):

| Acción de A | Tipo táctico | Criterio que cambia | Utilidad |
|---|---|---|---:|
| A2 `(3,3) → (2,3)` | `avanzar` | `entrega` de −18 a −16 | **74** (la mejor) |
| A1, A3 o A2 hacia `(4,3)` | varios | ninguno | 72 |
| A2 `(3,3) → (3,4)` | `reposicionar` | `entrega` −20 y `bloqueo` −20 (un rival más en su ruta) | 60 (la peor) |

Cuando el rival del portador puede interceptar, la intercepción es la acción mejor valorada para él con cualquiera
de los dos bandos como MAX: cambia `posesion` de un signo al otro (una diferencia de 200).

### Cómo cambia el comportamiento al variar los pesos

Los pesos se cambian sin tocar código, con el campo propio opcional `juego.pesos_utilidad` del escenario. Solo se
indican los que cambian; un criterio desconocido o un valor no numérico se rechaza con un mensaje claro:

```json
"juego": {"portador_recurso": null, "pesos_utilidad": {"amenaza": 0}}
```

Ejemplo en un mapa abierto de 5×5 (todo camino, base A en `(0, 0)`): A1 porta el recurso en `(2, 2)` y el rival B1
está en `(1, 1)`, vigilando la ruta corta.

| Acción de A1 | `entrega` | `amenaza` | `bloqueo` | Utilidad (por defecto) | Utilidad (`amenaza = 0`) |
|---|---:|---:|---:|---:|---:|
| Acercarse a `(1, 2)` | −6 | −60 | −10 | 24 | **84** |
| Retroceder a `(3, 2)` | −10 | 0 | −10 | **80** | 80 |

Con los pesos por defecto, el portador **retrocede**: se aleja de su base, pero evita quedar junto a B1. Con
`amenaza = 0` ignora el riesgo y **avanza** por la ruta corta. En general: subir `amenaza` o `bloqueo` vuelve al
portador más prudente; subir `entrega` lo vuelve más directo; subir `carrera_recurso` hace que las unidades corran
antes hacia el recurso libre; y bajar `posesion` por debajo de `amenaza` haría que interceptar o evitar la
intercepción pierda importancia relativa.

Las pruebas de `tests/algoritmos/test_utilidad.py` fijan cada criterio por separado, los valores terminales, la
suma cero, los ejemplos de esta sección y la validación de los pesos.

## Minimax con profundidad limitada — E8.3

`algoritmos/minimax.py` elige la mejor acción para el bando en turno explorando el árbol de juego hasta una
profundidad máxima. MAX es el bando en turno en la raíz y MIN el otro: son roles, no capacidades distintas, porque
ambos usan las mismas acciones legales (`acciones_tacticas`, E8.1) y la misma utilidad de suma cero (E8.2).

```python
resultado = minimax(escenario, estado, profundidad_maxima=4)
resultado.accion_seleccionada   # AccionTactica elegida (acción legal + tipo táctico)
resultado.valores_raiz          # valor Minimax de cada acción de la raíz, para explicar la decisión
```

### Funcionamiento

- Antes de expandir un nodo se aplica `preparar_turno` (E3.1/E1.3): si el bando en turno está bloqueado, el turno
  pasa al adversario sin consumir profundidad; si ambos lo están, la partida termina en empate.
- Un nodo es hoja si es terminal, si no tiene acciones o si alcanzó la profundidad máxima. En las hojas se calcula la
  utilidad con `EvaluadorUtilidad`, con los pesos de `juego.pesos_utilidad` si el escenario los define.
- Los nodos MAX toman el máximo de sus hijos y los nodos MIN el mínimo. Las acciones se exploran en el orden de
  `acciones_tacticas`; ante un empate de valor se conserva la **primera** acción, para que alfa-beta (E8.4) pueda
  reproducir exactamente la misma decisión con el mismo orden.
- Complejidad: `O(b^d)` nodos, con `b` acciones por nodo (a lo sumo 5 por unidad del bando en turno) y `d` la
  profundidad máxima. Con profundidad 4, `campo_20x20.json` genera 11 023 nodos y tarda menos de 2 segundos.

### Profundidad configurable sin tocar código

La profundidad se lee de `juego.profundidad_maxima_minimax` del escenario (todos los escenarios del repositorio
declaran 4) o de `--profundidad` en la consola, que tiene prioridad. Un valor que no sea un entero mayor o igual que 1
se rechaza con un mensaje claro.

```bash
python3 -B main.py escenarios/recurso_en_transporte.json --algoritmo minimax
python3 -B main.py escenarios/recurso_en_transporte.json --algoritmo minimax --profundidad 2
```

### Métricas

| Métrica | Significado en la implementación |
|---|---|
| Nodos generados | La raíz y cada sucesor creado al aplicar una acción. |
| Nodos evaluados | Hojas en las que se calculó la utilidad. |
| Nodos podados | Siempre 0 en Minimax; existe para compararlo con alfa-beta (E8.4). |
| Profundidad alcanzada | Mayor profundidad de un nodo visitado (la raíz es 0). Es menor que la máxima si todas las ramas terminan antes. |
| Tiempo | Segundos desde el inicio hasta la decisión. |
| Acción seleccionada | Acción legal de la raíz con mayor valor, con su tipo táctico. |
| Valor obtenido | Valor Minimax de la raíz desde la perspectiva de MAX. |

`ResultadoMinimax.a_diccionario()` exporta estas métricas en una estructura serializable a JSON.

### Ejemplo verificado a mano: mirar más lejos cambia la decisión

En un corredor 1×4 (`base A | A1 | recurso | B1 sobre la base B`), con A en turno:

| Acción de A1 | Valor con profundidad 1 | Valor con profundidad 2 | Valor con profundidad 3 |
|---|---:|---:|---:|
| Recoger el recurso en `(0, 2)` | **37** | −10 000 | −10 000 |
| Retroceder a `(0, 0)` | −2 | **−98** | **−38** |

Con profundidad 1, recoger el recurso parece lo mejor (posesión +100, aunque B1 quede adyacente: amenaza −60). Con
profundidad 2, Minimax ve la respuesta de MIN: B1 intercepta desde su propia base y gana. Por eso retrocede y
prefiere dejar que B recoja el recurso (−98) antes que perder la partida. Los nodos se pueden contar a mano: con
profundidad 2 se generan 5 (la raíz, 2 jugadas de A y 1 respuesta de B a cada una) y se evalúan 2 hojas.

En `recurso_en_transporte.json` ocurre algo similar: con profundidad 1 lo mejor es que el portador A2 avance
(utilidad 74), pero con profundidad 2 Minimax elige `A1 (0, 2) → (0, 3)`, una jugada de `proteger_zona` que se cruza
en el camino de B2, porque deja a A en mejor posición tras la mejor respuesta de B (valor 72 frente a 64).

Las pruebas de `tests/algoritmos/test_minimax.py` fijan este árbol calculado a mano, la legalidad de la acción
elegida, la coherencia de las métricas, que MIN no está en desventaja (reflejar el tablero e intercambiar los bandos
da el mismo valor para quien mueve), la lectura de la profundidad desde el JSON y la consola.

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
python3 main.py --algoritmo dfs
python3 main.py --algoritmo ucs
python3 main.py --algoritmo a_estrella
python3 main.py --algoritmo beam --k 4
python3 main.py --algoritmo ambos
python3 main.py --algoritmo bfs_dfs
python3 main.py escenarios/recurso_en_transporte.json --algoritmo minimax --profundidad 2
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

| Archivo | Tamaño | Proposito |
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
