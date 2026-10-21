# Casos mínimos 6 a 10: estado compuesto, decisión adversarial, poda, orden y profundidad

## Alcance

Estos casos usan Minimax (E8.3), alfa-beta (E8.4), la comparación de métricas (E8.5), la utilidad de suma cero
(E8.2) y las acciones tácticas (E8.1) tal como están implementadas. La única pieza de código que agrega E8.6 es el
**orden de acciones configurable** (`algoritmos/orden_acciones.py`), que exige el caso 9.

Para cada caso se declara el escenario y el estado inicial, se escribe el resultado **esperado** (razonado antes de
ejecutar) y se compara con el **obtenido**. Todas las cifras de este documento, salvo los tiempos, están fijadas en
`tests/algoritmos/test_casos_minimos_adversariales.py`: si cambian los algoritmos, las reglas, la utilidad o los
escenarios, las pruebas fallan y el análisis debe revisarse.

| Caso | Qué debe demostrarse (enunciado) | Escenario didáctico | Variante académica 20 × 20 |
|---|---|---|---|
| 6. Estado compuesto | La misma posición física representa estados diferentes por información adicional del juego. | `estado_compuesto_libre.json` y `estado_compuesto_portador.json` | `caso_06_estado_compuesto_libre_20x20.json` y `caso_06_estado_compuesto_portador_20x20.json` |
| 7. Decisión adversarial | La mejor decisión según Minimax no coincide necesariamente con avanzar directamente al recurso. | `decision_adversarial.json` | `caso_07_decision_adversarial_20x20.json` |
| 8. Minimax vs. alfa-beta | Seleccionan la misma acción y alfa-beta evita evaluar parte del árbol. | `recurso_en_transporte.json` | `caso_08_minimax_alfa_beta_20x20.json` |
| 9. Orden de acciones | Cambiar el orden de sucesores modifica la cantidad de poda. | `recurso_en_transporte.json` y `campo_20x20.json` | `campo_20x20.json` ya cumple 20 × 20 |
| 10. Profundidad | El mismo estado se evalúa con distintas profundidades y se analizan los efectos. | `recurso_en_transporte.json` | `caso_10_profundidad_20x20.json` |

Los escenarios didácticos pequeños se conservan y se complementan con variantes académicas que respetan las reglas:
tres unidades por bando,
`juego.profundidad_maxima_minimax = 4` y `prueba.modo = "adversarial"`. Los comandos de este documento indican
`--algoritmo` para fijar el algoritmo de cada caso, aunque el escenario ya declare su modo de prueba.

Convenciones de los mapas: `.` camino (costo 1), `p` pasto (2), `b` bosque (4), `~` pantano (7), `#` muro,
`[A]`/`[B]` base de cada bando y `R` recurso libre. MAX es el bando en turno (A en todos los casos).

---

## Caso 6: estado compuesto

### Objetivo y configuración

Mostrar que la posición de las unidades no basta para describir una situación del juego: con las seis unidades en
las mismas casillas, que A1 transporte o no el recurso cambia el estado, su valor y la decisión.

Los dos escenarios son idénticos salvo en el recurso:

| | `estado_compuesto_libre.json` | `estado_compuesto_portador.json` |
|---|---|---|
| Unidades | A1 (2,2), A2 (0,1), A3 (1,0), B1 (4,1), B2 (4,2), B3 (3,0) | las mismas |
| `juego.portador_recurso` | `null` | `"A1"` |
| Recurso | libre en (2,4) | lo transporta A1 en (2,2) |

```text
estado_compuesto_libre.json            estado_compuesto_portador.json
    0   1   2   3   4                      0   1   2   3   4
0  [A]  A2  .   .   .                  0  [A]  A2  .   .   .
1   A3  .   .   .   .                  1   A3  .   .   .   .
2   .   .   A1  .   R                  2   .   .   A1* .   .        (* lleva el recurso)
3   B3  .   .   .   .                  3   B3  .   .   .   .
4   .   B1  B2  .  [B]                 4   .   B1  B2  .  [B]
```

### Esperado

- El modelo de E1.1 distingue los dos estados: mismas unidades, pero distinto `portador_recurso` y
  `posicion_recurso`, así que los `EstadoJuego` no son iguales y un conjunto de estados visitados los cuenta dos veces.
- La utilidad los valora distinto: sin portador solo pesa la carrera hacia el recurso; con portador pesan la posesión
  (+100) y lo que falta para entregarlo.
- La decisión cambia de objetivo: sin portador, ir por el recurso; con portador, llevarlo a la base A.

### Obtenido

| | Sin portador | Con portador |
|---|---|---|
| `EstadoJuego` | `portador=None`, recurso en (2,4) | `portador="A1"`, `posicion_recurso=None` |
| ¿Iguales? | **No**: distinto hash; `len({libre, portador}) == 2` | |
| Utilidad del estado | **4** = `carrera_recurso` 2 × (4 − 2) | **92** = `posesion` 100 + `entrega` −8 |
| Decisión de alfa-beta, profundidades 1 a 4 | A1 (2,2) → (2,3), `aproximarse_al_recurso` | A1 (2,2) → (1,2), `avanzar` |

Coincide con lo esperado en las cuatro profundidades. La carrera vale 4 porque la unidad de B más cercana al recurso
(B2) está a costo 4 y la de A (A1) a costo 2. La entrega vale −8 porque A1 está a costo 4 de su base.

---

## Caso 7: la mejor decisión no es avanzar directo al recurso

### Objetivo y configuración

Mostrar que tomar el recurso, la jugada que elegiría un agente voraz, puede ser la peor cuando se considera la
respuesta del adversario.

```text
decision_adversarial.json
    0   1   2   3   4   5
0  [A]  A1  R  [B]  #   #        B1 espera sobre su propia base, en (0,3)
1   #   #   #   #   #   #
2   A2  A3  .   .   B2  B3
```

A1 está a un paso del recurso, pero B1 espera sobre su propia base, adyacente al recurso. La fila 1 es un muro: A2,
A3, B2 y B3 completan las tres unidades por bando y pueden moverse en la fila 2, pero no alcanzan el recurso. Desde el
estado inicial A tiene tres acciones: A1 → (0,2) (tomar el recurso), A1 → (0,0) (retroceder) y A3 → (2,2).

### Esperado

- **Profundidad 1:** Minimax solo ve el estado tras su jugada. Tomar el recurso suma posesión +100 y entrega −4, y
  resta amenaza −60 porque B1 queda adyacente. Con movilidad +1, vale **37** y es la mejor jugada.
- **Profundidad 2 o más:** Minimax ve la respuesta de B. B1 intercepta al portador desde su base y gana en el acto,
  así que tomar el recurso vale **−10 000** y Minimax lo evita.

### Obtenido

Valor de cada acción de la raíz (Minimax; alfa-beta elige la misma acción con el mismo valor):

| Profundidad | A1 → (0,2): tomar el recurso | A1 → (0,0): retroceder | A3 → (2,2) | Decisión |
|---:|---:|---:|---:|---|
| 1 | **37** | −2 | 1 | Tomar el recurso |
| 2 | −10 000 | −98 | **−37** | A3 → (2,2) |
| 3 | −10 000 | −38 | **37** | A3 → (2,2) |
| 4 | −10 000 | −10 000 | **−39** | A3 → (2,2) |

Coincide con lo esperado. A partir de profundidad 2, Minimax hace una jugada de espera con A3 y deja a A1 junto al
recurso, custodiándolo: quien tome primero el recurso queda adyacente al rival y lo pierde.

Además, el caso adelanta el efecto de la profundidad (caso 10): retroceder con A1 parece aceptable con profundidad 2
o 3 (−98 o −38), pero con profundidad 4 Minimax descubre que también pierde, porque B1 toma el recurso libre y lo
lleva a su base, que está al lado.

**Observación sobre E8.1:** la jugada de A3 aparece clasificada como `aproximarse_al_recurso`, aunque el muro le
impide llegar. La clasificación táctica usa la distancia Manhattan, que ignora los muros; no afecta a la decisión,
que depende solo de la utilidad, pero conviene tenerlo en cuenta al explicar los tipos tácticos.

---

## Caso 8: Minimax y alfa-beta eligen lo mismo con menos trabajo

### Objetivo y configuración

Mostrar que, con la misma profundidad, utilidad y orden de acciones, alfa-beta elige la misma acción con el mismo
valor que Minimax y evita evaluar parte del árbol.

Se usa `recurso_en_transporte.json`, un escenario de E2.3 con tres unidades por bando en el que A2 ya transporta el
recurso:

```text
recurso_en_transporte.json
    0   1   2   3   4   5   6   7
0  [A]  .   A1  .   B2  .   .   .
1   .   p   p   b   b   p   p   .
2   .   B1  #   .   .   #   p   .
3   .   p   #   A2* .   #   p   .        (* A2 lleva el recurso)
4   .   p   p   ~   ~   p   p   .
5   A3  .   .   .   .   .   B3 [B]
```

### Esperado

- La misma acción y el mismo valor en todas las profundidades (es la garantía de E8.4).
- Con profundidad 1 no hay nada que podar: la raíz nunca poda y sus hijos son hojas.
- El ahorro crece con la profundidad, porque cada corte evita un subárbol mayor.

### Obtenido

| Profundidad | Acción (ambos) | Valor | Minimax: generados / evaluados | Alfa-beta: generados / evaluados / podados | Menos evaluados |
|---:|---|---:|---:|---:|---:|
| 1 | A2 (3,3) → (2,3) | 74 | 9 / 8 | 9 / 8 / 0 | 0 % |
| 2 | A1 (0,2) → (0,3) | 72 | 80 / 71 | 40 / 31 / 40 | 56 % |
| 3 | A2 (3,3) → (4,3) | 76 | 662 / 582 | 238 / 191 / 148 | 67 % |
| 4 | A1 (0,2) → (0,3) | 72 | 5900 / 5238 | 787 / 600 / 907 | 89 % |

Coincide con lo esperado en las tres afirmaciones. El mecanismo se puede seguir a mano en el árbol del pasillo de
E8.4 ([poda alfa-beta](../tecnico/04-decision-adversarial.md#poda-alfa-beta--e84)): Minimax genera 7 nodos y evalúa 4; alfa-beta genera 6, evalúa 3 y
poda 1 rama, y ambos eligen la misma jugada con valor 3.

---

## Caso 9: el orden de las acciones cambia la poda

### Objetivo y configuración

Mostrar que cambiar el orden en que se generan los sucesores modifica cuánto poda alfa-beta. Se comparan los tres
órdenes de `algoritmos/orden_acciones.py`, con profundidad 4:

- `generacion`: el orden de `acciones_tacticas` (unidades por identificador; movimientos arriba, abajo, izquierda,
  derecha). Es el predeterminado y el de E8.3 y E8.4.
- `inverso`: ese mismo orden al revés.
- `tactico`: primero las jugadas de mayor impacto según su tipo táctico (interceptar al portador, avanzar con el
  recurso, aproximarse al recurso, bloquear, perseguir, proteger, reposicionar). Entre jugadas del mismo tipo se
  conserva el orden de generación.

El orden se cambia sin tocar código, con `--orden` en la consola o con el campo propio `juego.orden_acciones`.

### Esperado

- El **valor** Minimax no depende del orden: el máximo o el mínimo de un conjunto no cambia por el orden en que se
  recorre. Por lo mismo, **Minimax** hace el mismo trabajo con cualquier orden.
- Alfa-beta poda más cuanto antes encuentra las mejores jugadas, porque alfa y beta se ajustan antes. Se espera que
  `tactico` sea el que menos trabajo hace.
- Con otro orden puede cambiar la **acción** elegida, pero solo entre acciones con el mismo valor, porque ambos
  algoritmos conservan la primera de las empatadas.

### Obtenido

Alfa-beta con profundidad 4 (el valor es 72 en `recurso_en_transporte.json` y −36 en `campo_20x20.json` con los tres
órdenes):

| Escenario | Orden | Generados | Evaluados | Podados | Acción elegida |
|---|---|---:|---:|---:|---|
| `recurso_en_transporte.json` | `generacion` | 787 | 600 | 907 | A1 (0,2) → (0,3) |
| | `inverso` | 962 | 721 | 1115 | A2 (3,3) → (4,3) |
| | `tactico` | **587** | **428** | 843 | A1 (0,2) → (0,3) |
| `campo_20x20.json` | `generacion` | 799 | 569 | 1358 | A1 (1,2) → (1,3) |
| | `inverso` | 1965 | 1570 | 1825 | A1 (1,2) → (1,3) |
| | `tactico` | **657** | **465** | 1150 | A1 (1,2) → (1,3) |

Coincide con lo esperado:

- El valor no cambia con el orden, y Minimax genera los mismos nodos con los tres (662 generados y 582 evaluados con
  profundidad 3 en `recurso_en_transporte.json`).
- `tactico` es el que menos evalúa en ambos escenarios y profundidades (3 y 4); `inverso` es el que más.
- Con `inverso`, en `recurso_en_transporte.json` se elige A2 → (4,3) en lugar de A1 → (0,3): ambas valen 72 en la
  raíz, y cada orden se queda con la primera de las empatadas. Alfa-beta y Minimax siguen eligiendo lo mismo entre
  sí con cada orden.

**Hallazgo: los nodos podados no miden el ahorro.** En `recurso_en_transporte.json`, `tactico` evalúa menos hojas que
`generacion` (428 frente a 600), pero cuenta **menos** ramas podadas (843 frente a 907). La métrica cuenta ramas
evitadas, no nodos: un corte cerca de la raíz cuenta como una sola rama pero evita un subárbol completo, mientras que
muchos cortes cerca de las hojas suman muchas ramas pequeñas. Para comparar el ahorro hay que mirar los nodos
evaluados y generados.

---

## Caso 10: efecto de la profundidad

### Objetivo y configuración

Evaluar el mismo estado (`recurso_en_transporte.json`) con profundidades 1 a 4 y analizar cómo cambian el trabajo,
el tiempo y la decisión.

### Esperado

- El trabajo crece de forma exponencial, aproximadamente `b^d`, con `b` cercano a las 8 acciones de la raíz.
- Más profundidad permite ver respuestas del adversario que antes quedaban fuera del horizonte, así que la decisión
  puede cambiar.

### Obtenido

| Profundidad | Acción elegida | Valor | Minimax: generados / evaluados | Alfa-beta: generados / evaluados / podados | Tiempo Minimax / alfa-beta (s) |
|---:|---|---:|---:|---:|---:|
| 1 | A2 (3,3) → (2,3), `avanzar` | 74 | 9 / 8 | 9 / 8 / 0 | 0.001 / 0.001 |
| 2 | A1 (0,2) → (0,3), `proteger_zona` | 72 | 80 / 71 | 40 / 31 / 40 | 0.008 / 0.004 |
| 3 | A2 (3,3) → (4,3), `reposicionar` | 76 | 662 / 582 | 238 / 191 / 148 | 0.074 / 0.026 |
| 4 | A1 (0,2) → (0,3), `proteger_zona` | 72 | 5900 / 5238 | 787 / 600 / 907 | 0.655 / 0.085 |

Los tiempos dependen del equipo; los conteos, las acciones y los valores son deterministas.

- **Crecimiento exponencial:** los nodos generados por Minimax se multiplican por 8,9, 8,3 y 8,9 en cada nivel, como
  se esperaba. Alfa-beta crece mucho más despacio, y su ventaja aumenta con la profundidad (caso 8).
- **La decisión cambia con la profundidad, y alterna.** Con profundidad 1, el portador A2 avanza (74). Con 2, Minimax
  ve que B puede responder y prefiere que A1 proteja la zona (72). Con 3 vuelve a una jugada de A2 (76), y con 4, a la
  de A1 (72).
- **Efecto de la paridad.** Con profundidad impar, la última jugada que se mira es de MAX, que elige su mejor
  continuación sin respuesta de MIN, y la estimación sale optimista (74 y 76). Con profundidad par, la última jugada es
  de MIN y la estimación sale más prudente (72 y 72). Por eso, al comparar decisiones conviene usar profundidades de
  la misma paridad, o una profundidad par si se quiere considerar siempre la respuesta del adversario.

El caso 7 muestra el otro efecto clásico de la profundidad: una jugada que parece aceptable dentro del horizonte
(retroceder con A1 con profundidad 2 o 3) resulta perdedora cuando el horizonte se amplía (profundidad 4).

---

## Reproducibilidad

Las variantes 20 × 20 conservan la región transitable original y agregan muros no transitables en la extensión. Las
pruebas `tests/algoritmos/test_casos_adversariales_20x20.py` comparan estado, decisión, valor y contadores con los
escenarios pequeños. Los hashes, verificaciones y métricas se guardan por separado en
`docs/experimentos/resultados-casos-minimos.json`; la corrida anterior se preservó en
`docs/experimentos/resultados-casos-minimos-antes-variantes-20x20.json`.

Desde la raíz del repositorio, con el entorno virtual activo:

```bash
# Caso 6: misma posición, decisión distinta
python main.py --consola escenarios/estado_compuesto_libre.json --algoritmo alfa_beta
python main.py --consola escenarios/estado_compuesto_portador.json --algoritmo alfa_beta

# Caso 7: con profundidad 1 toma el recurso; con 2 o más, no
python main.py --consola escenarios/decision_adversarial.json --algoritmo minimax --profundidad 1
python main.py --consola escenarios/decision_adversarial.json --algoritmo minimax --profundidad 2

# Caso 8: tabla comparativa Minimax vs. alfa-beta
python main.py --consola escenarios/recurso_en_transporte.json --algoritmo minimax_alfa_beta --profundidad 4

# Caso 9: el mismo estado con los tres órdenes
python main.py --consola escenarios/recurso_en_transporte.json --algoritmo minimax_alfa_beta --profundidad 4 --orden generacion
python main.py --consola escenarios/recurso_en_transporte.json --algoritmo minimax_alfa_beta --profundidad 4 --orden inverso
python main.py --consola escenarios/recurso_en_transporte.json --algoritmo minimax_alfa_beta --profundidad 4 --orden tactico

# Caso 10: el mismo estado con profundidades 1 a 4
python main.py --consola escenarios/recurso_en_transporte.json --algoritmo minimax_alfa_beta --profundidad 1
python main.py --consola escenarios/recurso_en_transporte.json --algoritmo minimax_alfa_beta --profundidad 4

# Todas las afirmaciones de este documento
python -m pytest tests/algoritmos/test_casos_minimos_adversariales.py
```

## Uso de IA y validación

- **Uso de IA:** sí. Claude (Opus 5.5) propuso los escenarios nuevos (`estado_compuesto_libre.json`,
  `estado_compuesto_portador.json` y `decision_adversarial.json`), el orden de acciones configurable y sus tres
  órdenes, las pruebas de `tests/algoritmos/test_casos_minimos_adversariales.py` y `test_orden_acciones.py`, y la
  redacción de este documento.
- **Cómo se obtuvieron los datos:** los resultados esperados se razonaron antes de ejecutar; los valores del caso 7
  con profundidad 1 se verificaron a mano criterio por criterio. Los resultados obtenidos se tomaron de la ejecución
  de los algoritmos del proyecto y quedaron fijados en las pruebas.
- **Validación del estudiante:** el equipo revisó los escenarios, los resultados esperados y las cifras obtenidas;
  todas quedan fijadas en `tests/algoritmos/test_casos_minimos_adversariales.py`.
