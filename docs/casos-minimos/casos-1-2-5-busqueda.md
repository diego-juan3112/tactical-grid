# Casos mínimos 1, 2 y 5: BFS frente a DFS, ruta corta frente a económica y Beam Search

Experimentos reproducibles de búsqueda. Los algoritmos se describen en [algoritmos de búsqueda](../tecnico/02-busqueda.md). Las cifras están fijadas en `tests/algoritmos/test_caso_minimo_1.py`, `tests/algoritmos/test_busqueda_costo_uniforme.py` y `tests/algoritmos/test_caso_minimo_5.py`.

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
python main.py --consola escenarios/campo_20x20.json --algoritmo bfs_dfs
python main.py --consola escenarios/ejemplo_enunciado.json --algoritmo bfs_dfs
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

## E5.2 — Caso mínimo 2: ruta corta vs. ruta económica

### Propósito del experimento

Este caso compara BFS y UCS sobre el mismo escenario, estado inicial, unidad y objetivo para demostrar que
minimizar la cantidad de movimientos no equivale necesariamente a minimizar el costo acumulado. Se reutiliza
`ruta_corta_vs_economica.json`, creado en E2.3; BFS proviene de E4.2, UCS de E5.1 y ambos reportan las métricas
comunes definidas en E4.1. Las características generales de los algoritmos se describen en
[algoritmos de búsqueda](../tecnico/02-busqueda.md); aquí se documenta el experimento concreto y reproducible.

### Configuración reproducible

- Escenario: `escenarios/ruta_corta_vs_economica.json` (5 filas por 9 columnas).
- Unidad: `A1`, con posición inicial `(2, 0)`.
- Objetivo posicional: `(2, 8)`.
- Movimientos: una celda ortogonal por acción, dentro del mapa y sobre terreno transitable.
- Costo de cada acción: costo del terreno de la celda destino; la posición inicial no se cobra.

Desde la raíz del repositorio, la comparación se ejecuta con:

```bash
python main.py --consola escenarios/ruta_corta_vs_economica.json --algoritmo ambos
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
python main.py --consola escenarios/campo_20x20.json --algoritmo ambos
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
python main.py --consola escenarios/campo_20x20.json --algoritmo beam --k 1 2 4 8
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
