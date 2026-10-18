# Decisión adversarial

Historias E8.1 a E8.6: acciones tácticas, función de utilidad, Minimax, poda alfa-beta, métricas comparables y orden de acciones. Los experimentos están en [casos mínimos 6 a 10](../casos-minimos/casos-6-10-adversariales.md).

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
python main.py --consola escenarios/recurso_en_transporte.json --algoritmo minimax
python main.py --consola escenarios/recurso_en_transporte.json --algoritmo minimax --profundidad 2
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

## Poda alfa-beta — E8.4

`algoritmos/alfa_beta.py` implementa Minimax con poda alfa-beta. Devuelve la **misma decisión y el mismo valor** que
Minimax para la misma profundidad, la misma utilidad y el mismo orden de acciones, pero deja de explorar las ramas
que ya no pueden cambiar esa decisión.

```python
resultado = alfa_beta(escenario, estado, profundidad_maxima=4)   # mismo ResultadoMinimax que minimax()
resultado.nodos_podados                                         # ramas evitadas por la poda
```

### Funcionamiento

- Recorre el mismo árbol que Minimax: mismas `acciones_tacticas` en el mismo orden, mismo `preparar_turno`, mismo
  criterio de hoja y mismo evaluador. Ambos construyen el evaluador con `preparar_evaluador`, para garantizar que
  usan la misma función de utilidad.
- `alfa` es el mejor valor que MAX ya tiene asegurado en el camino actual y `beta` el mejor que tiene MIN. En un nodo
  MIN, si un hijo baja hasta `alfa`, MAX nunca elegiría llegar a ese nodo y se podan los hijos restantes; en un nodo
  MAX se poda cuando un hijo sube hasta `beta`.
- **Por qué la decisión es la misma:** la raíz conserva, como Minimax, la primera acción con valor estrictamente
  mayor. Se usa la variante *fail-soft*: una rama podada devuelve una cota superior que no supera el mejor valor ya
  encontrado, así que nunca reemplaza a la acción elegida, y ante un empate gana la primera.
- **Complejidad:** en el peor orden de acciones, `O(b^d)` como Minimax; con el mejor orden, `O(b^(d/2))`. Por eso el
  orden de generación de acciones influye en cuánto se poda (se analiza en E8.6).

### Métricas

Se cuentan igual que en Minimax (E8.3), más los nodos podados:

| Métrica | Significado en la implementación |
|---|---|
| Nodos generados | La raíz y cada sucesor creado. Una rama podada no se genera. |
| Nodos evaluados | Hojas en las que se calculó la utilidad. |
| Nodos podados | Ramas evitadas: en cada corte, las acciones hermanas que ya no se exploran. |
| Profundidad alcanzada | Mayor profundidad visitada; puede ser menor que en Minimax si la rama más profunda se podó. |

En la consola, el valor de una acción de la raíz cuya rama se podó se muestra como `<= v`: es una cota superior de su
valor real, que ya no puede superar a la acción elegida.

### Ejemplo verificado a mano

En un pasillo 1×8 (`. recurso . A1 . . B1 .`) con A en turno, profundidad 2 y solo el criterio `carrera_recurso`
activo (peso 1 desde `juego.pesos_utilidad`), cada hoja vale "distancia de B1 al recurso − distancia de A1 al recurso":

| Jugada de A1 | Respuesta B1 → (0, 5) | Respuesta B1 → (0, 7) | Valor |
|---|---:|---:|---:|
| a1: A1 → (0, 2) | 4 − 1 = 3 | 6 − 1 = 5 | **3** (MIN), alfa = 3 |
| a2: A1 → (0, 4) | 4 − 3 = 1 ≤ alfa | *podada* | ≤ 1 |

Tras valorar a1, MAX ya tiene asegurado 3. En a2 la primera respuesta de B ya vale 1: MIN puede dejar a2 en 1 o menos,
así que a2 nunca superará a a1 y no hace falta valorar la segunda respuesta. Ambos algoritmos eligen a1 con valor 3,
pero Minimax genera 7 nodos y evalúa 4 hojas, mientras alfa-beta genera 6, evalúa 3 y poda 1 rama.

### Resultados en los escenarios del repositorio

Minimax / alfa-beta sobre el estado inicial. En todos los casos la acción y el valor son idénticos:

| Escenario | Prof. | Acción elegida | Valor | Generados | Evaluados | Podados | Ahorro en evaluados | Tiempo (s) |
|---|---:|---|---:|---:|---:|---:|---:|---:|
| `recurso_en_transporte.json` | 2 | A1 (0, 2)→(0, 3) | 72 | 80 / 40 | 71 / 31 | 40 | 56 % | 0.009 / 0.005 |
| `recurso_en_transporte.json` | 3 | A2 (3, 3)→(4, 3) | 76 | 662 / 238 | 582 / 191 | 148 | 67 % | 0.069 / 0.029 |
| `recurso_en_transporte.json` | 4 | A1 (0, 2)→(0, 3) | 72 | 5900 / 787 | 5238 / 600 | 907 | 89 % | 0.738 / 0.077 |
| `campo_20x20.json` | 2 | A1 (1, 2)→(1, 3) | −36 | 133 / 51 | 121 / 39 | 82 | 68 % | 0.021 / 0.011 |
| `campo_20x20.json` | 3 | A1 (1, 2)→(1, 3) | −34 | 1222 / 230 | 1089 / 179 | 256 | 84 % | 0.142 / 0.029 |
| `campo_20x20.json` | 4 | A1 (1, 2)→(1, 3) | −36 | 11023 / 799 | 9801 / 569 | 1358 | 94 % | 1.224 / 0.114 |

El ahorro crece con la profundidad porque cada corte evita un subárbol completo, y los subárboles son mayores cuanto
más lejos está la hoja. Los tiempos dependen del equipo; los conteos de nodos son deterministas.

```bash
python main.py --consola escenarios/recurso_en_transporte.json --algoritmo alfa_beta
python main.py --consola escenarios/recurso_en_transporte.json --algoritmo alfa_beta --profundidad 3
```

Las pruebas de `tests/algoritmos/test_alfa_beta.py` fijan el árbol calculado a mano, la igualdad de decisión y valor
con Minimax en los escenarios del repositorio (profundidades 1 a 3), que los valores de la raíz son exactos o cotas
correctas, que la poda reduce el trabajo, que MIN no está en desventaja, los casos borde y la consola.

## Métricas comparables de Minimax y alfa-beta — E8.5

`algoritmos/comparacion_adversarial.py` ejecuta Minimax y alfa-beta sobre **el mismo estado, la misma profundidad y la
misma utilidad**, y reúne las siete métricas del enunciado de ambos en un solo objeto, para presentarlas lado a lado y
analizarlas en el informe técnico:

```python
comparacion = comparar_minimax_alfa_beta(escenario, estado, profundidad_maxima=3)
comparacion.minimax, comparacion.alfa_beta          # un ResultadoMinimax de cada algoritmo
comparacion.misma_accion, comparacion.mismo_valor   # verificacion del criterio de E8.4
comparacion.reduccion_porcentual("nodos_evaluados") # ahorro de la poda, en %
comparacion.a_diccionario()                         # estructura serializable a JSON
```

La lógica vive en la capa de algoritmos y no en la consola, para que la interfaz gráfica o el modo de prueba
`adversarial` (E10.1) puedan reutilizarla.

### Las siete métricas

| Métrica | Campo | Significado |
|---|---|---|
| Nodos generados | `nodos_generados` | La raíz y cada sucesor creado. |
| Nodos evaluados | `nodos_evaluados` | Hojas en las que se calculó la utilidad. |
| Nodos podados | `nodos_podados` | Ramas evitadas por alfa-beta; siempre 0 en Minimax. |
| Profundidad alcanzada | `profundidad_alcanzada` | Mayor profundidad visitada (la raíz es 0). |
| Tiempo | `tiempo_segundos` | Segundos hasta la decisión. |
| Acción seleccionada | `accion_seleccionada` | Acción legal elegida en la raíz, con su tipo táctico. |
| Valor obtenido | `valor` | Valor Minimax de la raíz desde la perspectiva de MAX. |

La **reducción porcentual** se calcula como `100 × (1 − alfa-beta / Minimax)` solo para las métricas de trabajo:
nodos generados, nodos evaluados y tiempo. En las demás no tiene sentido: los nodos podados son 0 en Minimax, y la
acción y el valor deben coincidir.

### Decisiones para que la comparación sea justa

- **Misma utilidad y mismo orden de acciones.** Ambos leen los pesos de `juego.pesos_utilidad` del escenario y
  exploran `acciones_tacticas` en el mismo orden, que son las condiciones del criterio de E8.4.
- **Evaluadores independientes.** Cada algoritmo construye su propio `EvaluadorUtilidad`. Si compartieran uno, el
  segundo heredaría las distancias hacia el recurso ya calculadas por el primero y su tiempo parecería menor de lo
  que es.
- **Los tiempos dependen del equipo;** los conteos de nodos, la acción y el valor son deterministas y se pueden
  reproducir exactamente.

### Salida en consola

```bash
python main.py --consola escenarios/recurso_en_transporte.json --algoritmo minimax_alfa_beta --profundidad 3
```

```text
Bando MAX: A | Profundidad máxima: 3
Métrica                                 Minimax                Alfa-beta    Reducción
Nodos generados                             662                      238       64.0 %
Nodos evaluados                             582                      191       67.2 %
Nodos podados                                 0                      148
Profundidad alcanzada                         3                        3
Tiempo (s)                             0.090913                 0.032589       64.2 %
Acción seleccionada         A2 (3, 3) -> (4, 3)      A2 (3, 3) -> (4, 3)
Valor obtenido                             76.0                     76.0
Misma acción: Sí
Mismo valor: Sí
```

Sin `--profundidad`, se usa `juego.profundidad_maxima_minimax` del escenario. Las pruebas de
`tests/algoritmos/test_comparacion_adversarial.py` comprueban las siete métricas con el árbol del pasillo calculado a
mano (E8.4), que cada métrica coincide con ejecutar cada algoritmo por separado en los escenarios del repositorio
(profundidades 1 a 3), la serialización a JSON, la raíz terminal y la consola.

## Casos mínimos 6 a 10 — E8.6

[Casos mínimos 6 a 10](../casos-minimos/casos-6-10-adversariales.md) documenta, para cada caso, el escenario, el estado
inicial y la comparación entre el resultado esperado y el obtenido:

| Caso | Resultado principal |
|---|---|
| 6. Estado compuesto | Con las seis unidades en las mismas casillas, sin portador A1 va hacia el recurso y con portador lo lleva a su base (`estado_compuesto_libre.json` / `estado_compuesto_portador.json`). |
| 7. Decisión adversarial | Con profundidad 1 Minimax toma el recurso (valor 37); con profundidad 2 o más ve que B1 lo intercepta desde su base y no lo toma (−10 000) (`decision_adversarial.json`). |
| 8. Minimax vs. alfa-beta | Misma acción y valor en profundidades 1 a 4; con profundidad 4, alfa-beta evalúa 600 hojas frente a 5238 (−89 %). |
| 9. Orden de acciones | El orden cambia la poda, no el valor; el orden `tactico` es el que menos evalúa. Los nodos podados no miden el ahorro. |
| 10. Profundidad | El trabajo crece unas 8,5 veces por nivel y la decisión alterna con la paridad de la profundidad. |

### Orden de acciones configurable

El caso 9 exige cambiar el orden de generación de acciones. `algoritmos/orden_acciones.py` ofrece tres órdenes, que
Minimax y alfa-beta aplican en todos los nodos:

- `generacion`: el orden de `acciones_tacticas`. Es el predeterminado, así que E8.3, E8.4 y E8.5 no cambian.
- `inverso`: el mismo orden al revés.
- `tactico`: primero interceptar al portador, luego avanzar con el recurso, aproximarse al recurso, bloquear,
  perseguir, proteger y reposicionar.

Se cambia sin tocar código, con `--orden` en la consola o con el campo propio `juego.orden_acciones` del escenario; la
consola tiene prioridad. El orden no cambia el valor Minimax, pero sí cuánto poda alfa-beta y, entre acciones
empatadas, cuál se elige. Con el mismo orden, Minimax y alfa-beta siguen eligiendo lo mismo.

```bash
python main.py --consola escenarios/recurso_en_transporte.json --algoritmo minimax_alfa_beta --profundidad 4 --orden tactico
```

Las pruebas de `tests/algoritmos/test_casos_minimos_adversariales.py` fijan todas las cifras de los cinco casos, y
las de `tests/algoritmos/test_orden_acciones.py` cubren los tres órdenes y su integración con Minimax, alfa-beta y la
comparación.
