# Modos de prueba, verificación y registro reproducible

Historias E10.1 a E10.3: cómo se ejecuta un escenario externo en cada modo, cómo se comprueban las respuestas y cómo se registra un experimento para repetirlo.

## Modos de prueba `busqueda`, `partida` y `adversarial` — E10.1

El profesor puede cargar un escenario externo con un campo `prueba` y la aplicación ejecuta el modo pedido **sin
cambios de código**. La lógica vive en `src/tacticalgrid/modos/`, una capa de orquestación que usa escenario, juego
y algoritmos sin abrir archivos ni conocer Pygame; la consola la consume y la interfaz podrá hacerlo.

```bash
python main.py --consola ruta/al/escenario_del_profesor.json
```

| Modo | Qué hace | Algoritmo por defecto |
|---|---|---|
| `busqueda` | Resuelve la navegación de `prueba.unidad_inicio` hasta `prueba.objetivo` con BFS, DFS, UCS, A* o Beam Search. | `ucs` |
| `partida` | Carga el escenario completo y **continúa el juego por turnos** desde ese estado: ambos bandos deciden con el mismo algoritmo, profundidad y orden, hasta una victoria, un empate por bloqueo o el límite de jugadas. | `alfa_beta` |
| `adversarial` | Evalúa el estado cargado con Minimax o alfa-beta y selecciona la acción del bando en turno. | `alfa_beta` |

### Cómo se decide qué ejecutar

- **Modo:** `--modo` en la consola. Si no se indica, se deduce de `--algoritmo`: un algoritmo explícito conserva su
  comportamiento anterior, aunque el JSON declare otro modo. Si tampoco se indica, se usa `prueba.modo`, y si el
  escenario no tiene `prueba`, `busqueda`.
- **Algoritmo:** `--algoritmo`; si no, el campo propio `prueba.algoritmo` (debe ser de la familia del modo); si no,
  el valor por defecto de la tabla.
- **Resto de parámetros:** unidad y objetivo (`--unidad`, `--objetivo` o `prueba`), ancho `k` (`--k` o `prueba.k`),
  profundidad (`--profundidad` o `juego.profundidad_maxima_minimax`), orden de acciones (`--orden` o
  `juego.orden_acciones`) y límite de la partida (`--turnos`, el campo propio `prueba.max_turnos` o 50). La consola
  siempre tiene prioridad sobre el JSON.

Un escenario externo que solo traiga los campos del enunciado (`modo`, `unidad_inicio`, `objetivo`) funciona con los
valores por defecto. Un `prueba` inválido (modo desconocido, objetivo sin `fila`/`columna`, algoritmo de otra familia,
`max_turnos` no positivo) se rechaza con un mensaje que nombra el campo. Una combinación incompatible en la consola,
como `--modo partida --algoritmo bfs`, también se rechaza.

### Modo `partida`

La partida continúa desde el estado del JSON (unidades, turno y portador), no se reinicia. Antes de cada jugada se
aplica `preparar_turno` (E1.3/E3.1): si el bando en turno está bloqueado, pasa el turno, y si ambos lo están, la
partida termina en empate. Cada bando decide como MAX con el mismo algoritmo, porque MAX y MIN son roles, no
capacidades distintas. El límite de jugadas existe porque dos bandos que se custodian mutuamente pueden no terminar
nunca; no se agregó una regla de empate por repetición, que no forma parte de las reglas del juego.

```text
$ python main.py --consola escenarios/estado_compuesto_portador.json --modo partida
Algoritmo de ambos bandos: alfa_beta | Profundidad: 4 | Orden de acciones: generacion
Límite: 50 jugadas

Turno 1 | A | A1 (2, 2) -> (1, 2) [avanzar] | valor 96.0 | evaluados 136
Turno 2 | B | B1 (4, 1) -> (3, 1) [perseguir_portador] | valor -96.0 | evaluados 217
...
Turno 6 | B | B1 (2, 1) -> (3, 1) [reposicionar] | valor -10000 | evaluados 255
Turno 7 | A | A1 (0, 2) -> (0, 1) [avanzar] | valor 10000 | evaluados 127
Turno 8 | B | B1 (3, 1) -> (2, 1) [perseguir_portador] | valor -10000 | evaluados 35
Turno 9 | A | A1 (0, 1) -> (0, 0) [avanzar] | valor 10000 | evaluados 28

Resultado: victoria de A en 9 jugadas
```

El valor de cada jugada está expresado desde la perspectiva del bando que juega. Desde la jugada 6, B ve −10 000:
dentro de su horizonte, A gana haga lo que haga. `jugar_partida` devuelve un `ResultadoPartida` con cada jugada (estado
previo, decisión con sus métricas y estado resultante) y `a_diccionario()` para exportarlo a JSON.

| Escenario (profundidad 4) | Resultado de la partida |
|---|---|
| `ejemplo_enunciado.json` | Victoria de B en 6 jugadas |
| `estado_compuesto_portador.json` | Victoria de A en 9 jugadas |
| `recurso_en_transporte.json`, `decision_adversarial.json` | Sin ganador al llegar al límite: ambos bandos se custodian |

### Comandos

```bash
python main.py --consola escenarios/campo_20x20.json                       # prueba.modo = busqueda -> UCS
python main.py --consola escenarios/decision_adversarial.json              # prueba.modo = adversarial -> alfa-beta
python main.py --consola escenarios/recurso_en_transporte.json --turnos 10 # prueba.modo = partida
python main.py --consola escenarios/campo_20x20.json --modo adversarial --profundidad 3
python main.py --consola escenarios/ejemplo_enunciado.json --modo partida --algoritmo minimax --profundidad 3
```

Las pruebas de `tests/modos/` cubren la lectura y validación de `prueba`, la precedencia entre consola y JSON, una
partida calculada a mano con pases por bloqueo, partidas con ganador, empate y límite, la igualdad de las partidas
jugadas con Minimax y con alfa-beta, y la consola en los tres modos.

## Verificador de soluciones — E10.2

`algoritmos/verificador.py` comprueba propiedades básicas de cada respuesta, para no confiar ciegamente en que el
algoritmo terminó sin error. No reutiliza los cálculos internos de los algoritmos: **reproduce cada respuesta con
las reglas del juego** (E1.2, E1.3, E8.1) y compara. Cada verificación devuelve un `ReporteVerificacion` con una
comprobación por propiedad (correcta o fallida, con su detalle) y no se detiene en la primera falla.

### Uso desde consola

La opción `--verificar` funciona en los tres modos de prueba. Imprime el reporte y, si alguna comprobación falla,
la consola termina con código 1.

```bash
python main.py --consola escenarios/ruta_corta_vs_economica.json --algoritmo ambos --verificar
python main.py --consola escenarios/campo_20x20.json --algoritmo beam --k 1 2 4 8 --verificar
python main.py --consola escenarios/recurso_en_transporte.json --modo adversarial --algoritmo minimax_alfa_beta --profundidad 3 --verificar
python main.py --consola escenarios/recurso_en_transporte.json --modo partida --profundidad 2 --turnos 10 --verificar
```

Ejemplo de salida para UCS:

```text
VERIFICACIÓN: UCS (busqueda)
------------------------------------------------------------
  ✓ movimientos_validos: 12 movimientos legales
  ✓ sin_obstaculos: ninguna celda del camino es un obstaculo
  ✓ camino_coherente: el camino coincide con las acciones aplicadas
  ✓ costo_coincide: costo 12 igual a la suma de las transiciones
  ✓ estado_final_objetivo: el estado final cumple la condicion objetivo
  ✓ estados_validos: 13 estados validos
  ✓ metricas_coherentes: contadores y longitud consistentes
Resultado de la verificación: VÁLIDO
```

### Qué se comprueba

| Criterio del enunciado | Búsquedas (`verificar_busqueda`) | Minimax y alfa-beta (`verificar_decision`) | Partida (`verificar_partida`) |
|---|---|---|---|
| Movimientos válidos | `movimientos_validos`: cada acción es ortogonal, parte de la posición actual y es legal en el estado alcanzado; `camino_coherente`: el camino coincide con las acciones | `accion_seleccionada_legal` | `jugadas_legales` |
| Ninguna unidad atraviesa obstáculos | `sin_obstaculos`: ninguna celda del camino es un muro ni está fuera del mapa | Incluido en `estados_validos` | Incluido en `estados_validos` |
| El costo coincide con las transiciones | `costo_coincide`: se suma el costo del JSON de cada transición reproducida | — | — |
| El estado final satisface el objetivo | `estado_final_objetivo` | — | `resultado_coherente`: el resultado declarado (victoria, empate o límite) corresponde al estado final |
| No se generan estados inválidos | `estados_validos`: cada estado del camino | `estados_validos`: cada estado del árbol | `estados_validos` y `estados_encadenados` |
| Acciones de Minimax legales | — | `acciones_consideradas_legales`: **todas** las acciones de **todos** los nodos del árbol, no solo la raíz; `valores_raiz_legales`; `tacticas_coherentes` | `decisiones_verificadas`: aplica `verificar_decision` a cada jugada |
| (adicional) | `metricas_coherentes` | `valor_correcto`, `decision_optima` y `metricas_coherentes` | — |

Un estado es inválido si tiene ids repetidos, un bando o turno desconocido, una unidad fuera del mapa o sobre un
obstáculo, dos unidades en la misma celda (salvo en navegación, donde E1.2 decidió que no se bloquean), un recurso
sin portador ni posición o con ambos, un portador inexistente, o una victoria registrada sin que el portador esté en
su base.

### Cómo se verifica una decisión adversarial

`verificar_decision` **regenera el árbol** que Minimax debió explorar, con la misma profundidad, orden de acciones,
pase de turno y utilidad, y en cada nodo comprueba con `es_accion_valida` cada acción considerada. Con ese árbol
calcula el valor Minimax exacto: el valor reportado debe coincidir (`valor_correcto`) y la acción elegida debe ser la
primera con el mejor valor (`decision_optima`), también para alfa-beta, cuya decisión debe ser la misma. Para Minimax,
los nodos generados, evaluados y la profundidad alcanzada deben coincidir exactamente con el árbol; para alfa-beta
no pueden superarlos. Por eso verificar una decisión cuesta lo mismo que ejecutar Minimax completo.

Una búsqueda que fracasa solo se verifica en su estructura (`fracaso_coherente`: sin camino, sin acciones y costo
nulo). No se afirma que no exista ruta, porque Beam Search puede fracasar aunque exista (E7.2).

Las pruebas de `tests/algoritmos/test_verificador.py` verifican las respuestas reales de BFS, DFS, UCS, A\* y Beam
Search (k = 1, 2, 4, 8) en cuatro escenarios, de Minimax y alfa-beta con los tres órdenes de acciones y de partidas
completas. También comprueban que el verificador **detecta** respuestas alteradas a propósito: un movimiento en
diagonal, un paso por un muro, un costo falso, un camino que no llega, métricas imposibles, una acción ilegal o una
intercepción inventada en la raíz, un valor falso, una acción que no es la óptima, nodos que no corresponden al árbol,
una jugada manipulada y un resultado de partida falso, además de cada tipo de estado inválido.

## Resultados y métricas reproducibles — E10.3

Cualquier prueba de la consola (modo `busqueda`, `adversarial` o `partida`) puede entregar sus resultados en una
estructura JSON equivalente a la del enunciado, junto con todo lo necesario para repetir el experimento. No es
obligatorio crear un archivo:

- `--json` imprime **solo** el registro en la salida estándar, en lugar del texto habitual. Sirve como log y se
  puede guardar o comparar (`... --json > resultado.json`).
- `--exportar ARCHIVO` guarda el mismo registro en un archivo y sigue mostrando el texto habitual.

```bash
python main.py --consola escenarios/ruta_corta_vs_economica.json --algoritmo ambos --json
python main.py --consola escenarios/campo_20x20.json --algoritmo beam --k 1 2 4 8 --exportar beam.json
python main.py --consola escenarios/recurso_en_transporte.json --modo adversarial --algoritmo minimax_alfa_beta --profundidad 3 --verificar --json
```

### Contenido del registro

```json
{
  "formato": "tacticalgrid.resultados/1",
  "escenario": {
    "archivo": "escenarios/ruta_corta_vs_economica.json",
    "version": "1.0",
    "filas": 5,
    "columnas": 9,
    "huella_sha256": "ee55444b12fae723a21e0ec5f97e6b87c2c1b494f1a90060e21e5c9da54389b4"
  },
  "modo": "busqueda",
  "parametros": {
    "algoritmo": "ucs",
    "unidad": "A1",
    "objetivo": [2, 8]
  },
  "comando": "python main.py escenarios/ruta_corta_vs_economica.json --modo busqueda --algoritmo ucs --unidad A1 --objetivo 2 8",
  "nota": "Todos los algoritmos son deterministas: ...",
  "resultados": [
    {
      "algoritmo": "UCS",
      "exito": true,
      "camino": [[2, 0], [1, 0], [0, 0], [0, 1], [0, 2], [0, 3], [0, 4], [0, 5], [0, 6], [0, 7], [0, 8], [1, 8], [2, 8]],
      "costo": 12,
      "estados_generados": 22,
      "estados_expandidos": 19,
      "maximo_frontera": 3,
      "longitud": 12,
      "tiempo_segundos": 0.0027
    }
  ]
}
```

| Campo | Para qué sirve |
|---|---|
| `escenario` | Archivo, versión, dimensiones y **huella SHA-256** del contenido del JSON. Si alguien cambia un costo o mueve un muro, la huella cambia: dos registros solo son comparables si su huella coincide. |
| `modo` y `parametros` | Los valores **realmente usados**, ya resueltos entre la consola y el campo `prueba` del JSON: algoritmo, unidad, objetivo, `k`, profundidad, orden de acciones, límite de turnos y pesos de la utilidad. |
| `comando` | La línea de consola que repite el experimento con esos mismos parámetros. |
| `resultados` | Un elemento por algoritmo ejecutado. En búsqueda, la estructura del enunciado (`algoritmo`, `exito`, `camino`, `costo`, `estados_generados`, `estados_expandidos`, `maximo_frontera`) más `longitud` y `tiempo_segundos`. En adversarial, las métricas de Minimax y alfa-beta (nodos generados, evaluados y podados, profundidad alcanzada, tiempo, acción seleccionada y valor) o la comparación de E8.5. En partida, cada jugada con su decisión. |
| `verificacion` | Solo con `--verificar`: el reporte de E10.2 de cada resultado y si todos son válidos. |

### Reproducibilidad

Todos los algoritmos son deterministas: con el mismo escenario (misma huella) y los mismos parámetros, los
resultados son idénticos salvo `tiempo_segundos`, que depende de la máquina. Las pruebas de
`tests/modos/test_registro.py` lo comprueban de la forma más directa: ejecutan el `comando` que trae el registro y
verifican que los resultados coinciden con los originales (sin contar el tiempo) en búsqueda, Beam Search,
alfa-beta y partida. También comprueban que la huella cambia al modificar el escenario, que el JSON se puede leer
completo con `--json` y que `--exportar` guarda el mismo contenido.
