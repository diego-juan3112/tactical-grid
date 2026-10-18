# Casos mínimos 3 y 4: obstáculo y comparación de heurísticas

## Alcance

Estos casos usan A*, Manhattan, HTO y UCS tal como están implementados en E6.1 y E6.2. La evidencia proviene de
`escenarios/obstaculo_rodeo.json`, las APIs del proyecto y el script `scripts/comparar_heuristicas_e62.py`. No se
agregaron algoritmos, reglas ni escenarios.

## Caso 3: obstáculo y rodeo

### Objetivo y configuración

El caso comprueba que una estimación geométrica puede considerar cercano un objetivo cuya ruta directa está
bloqueada.

| Propiedad | Valor leído del escenario |
|---|---|
| Archivo | `escenarios/obstaculo_rodeo.json` |
| Dimensiones | 8 filas × 7 columnas |
| Unidad | A1 |
| Inicio | `(4, 3)` |
| Objetivo | `(1, 3)` |
| Terreno de destino | `pasto`, costo 2 |
| Movimiento | Ortogonal |

La distancia Manhattan inicial es:

```text
|4 - 1| + |3 - 3| = 3
```

La ruta vertical directa pasaría por `(3, 3)`, `(2, 3)` y `(1, 3)`. La celda `(2, 3)` es un muro. La barrera
forma una U cerrada por arriba y por los costados; A1 debe salir por la abertura de `(6, 3)` y rodear uno de los
laterales.

### Representación obtenida del JSON

```text
    0 1 2 3 4 5 6
0   . . . . . . .
1   * * * G . . .
2   * # # # # # .
3   * # . . . # .
4   * # . S . # .
5   * # . * . # .
6   * # # * # # .
7   * * * * . . .
```

Leyenda: `S` inicio, `G` objetivo, `#` muro, `*` camino obtenido y `.` celda transitable fuera del recorrido.
El algoritmo conserva el orden arriba, abajo, izquierda y derecha; ante los dos rodeos simétricos, ese orden lleva
la ejecución registrada por el lateral izquierdo.

```text
(4,3) → (5,3) → (6,3) → (7,3) → (7,2) → (7,1) → (7,0) → (6,0)
→ (5,0) → (4,0) → (3,0) → (2,0) → (1,0) → (1,1) → (1,2) → (1,3)
```

El recorrido tiene 15 movimientos. Los primeros 14 destinos cuestan 1 y el objetivo cuesta 2 según el JSON, por
lo que el costo acumulado es `14 × 1 + 2 = 16`.

### Esperado y obtenido

| Comprobación | Esperado | Obtenido |
|---|---:|---:|
| Distancia Manhattan inicial | 3 | 3 |
| Distancia mínima con obstáculos | 15 movimientos | 15 movimientos |
| Costo óptimo | 16 | 16 |
| Ruta evita muros | Sí | Sí |
| Estado final satisface el objetivo | Sí | Sí |

UCS confirma el costo óptimo. La tabla topológica de HTO asigna distancia 15 a la posición inicial. La prueba
automatizada reaplica cada acción, consulta su legalidad, verifica la transitabilidad del destino y recalcula el
costo.

### Escenario complementario de 20 × 20

`campo_20x20.json` cumple el tamaño mínimo solicitado para los mapas de desarrollo. A1 parte de `(1, 2)` y busca
`(9, 10)`: Manhattan vale 16, mientras la ruta óptima cuesta 34 y usa 34 movimientos. Ese mapa complementa el caso
didáctico de 8 × 7. No lo sustituye porque estudia también costos heterogéneos y una topología mayor.

## Caso 4: comparación entre Manhattan y HTO

### Configuración

Cada ejecución carga el mismo JSON y construye un `ProblemaNavegacion` con A1 y el objetivo `(1, 3)`. HTO recibe la
misma instancia de problema que A* usa en esa ejecución. Manhattan permanece como opción predeterminada y la CLI no
recibe parámetros nuevos.

UCS actúa como referencia independiente del costo. La ejecución del 15 de octubre de 2026, con una
muestra y sin calentamiento, produjo:

| Métrica | A* Manhattan | A* HTO | UCS |
|---|---:|---:|---:|
| Éxito | Sí | Sí | Sí |
| Costo | 16 | 16 | 16 |
| Longitud | 15 | 15 | 15 |
| Estados generados | 40 | 38 | 41 |
| Estados expandidos | 33 | 26 | 39 |
| Máximo de frontera | 7 | 12 | 7 |
| Preparación de heurística | 0 ms | 0.222029 ms | No aplica |
| Búsqueda | 2.007766 ms | 1.981645 ms | Referencia funcional |
| Preparación + búsqueda A* | 2.007766 ms | 2.203674 ms | No aplica |

Los contadores, el costo y la longitud son deterministas con el orden actual de acciones y desempate. Los tiempos
corresponden a una muestra del entorno indicado en Reproducibilidad; otras ejecuciones pueden producir duraciones
distintas.

### Interpretación

Manhattan estima 3 porque ignora el muro y solo mide diferencias de fila y columna. HTO ejecuta un BFS inverso sobre
las celdas transitables y obtiene 15 pasos desde el inicio. Ambas estimaciones son admisibles bajo las reglas de
`ProblemaNavegacion`; A* encuentra en ambos casos el costo óptimo 16 que confirma UCS.

HTO genera dos estados menos y expande siete menos. La frontera máxima sube de 7 a 12 porque ese contador mide el
pico de nodos pendientes, no el trabajo acumulado. HTO puede concentrar expansiones en rutas prometedoras y dejar
más alternativas pendientes durante un tramo de la búsqueda.

El constructor de HTO recorre el componente transitable y almacena las distancias. Ese preprocesamiento añadió
0.222029 ms en la muestra. En este caso HTO redujo expansiones, pero la suma de preparación y búsqueda superó el
tiempo de Manhattan. En mapas abiertos o en topologías donde la distancia con obstáculos coincide con Manhattan,
HTO puede obtener los mismos contadores y pagar el preprocesamiento sin una ventaja práctica. `campo_20x20.json`
muestra esa situación: ambas variantes generan 289 estados y expanden 199 con la implementación actual.

## Reproducibilidad

| Dato | Valor |
|---|---|
| SHA base | `d3d8601702fba992d07dad6cb945a11cd1dcd65f` |
| Python | 3.12.3 |
| pytest | 9.1.1 |
| Sistema de la medición | Linux 6.17.0-1032-oem, x86_64 |
| Repeticiones medidas | 1 por estrategia y escenario |
| Calentamientos | 0 |
| Semilla del script | 6022026 |
| Registros crudos | No se exportaron; el script mantuvo 9 registros en memoria |

Comandos:

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q -p no:cacheprovider \
  tests/algoritmos/test_casos_minimos_heuristicas.py

PYTHONDONTWRITEBYTECODE=1 .venv/bin/python \
  scripts/comparar_heuristicas_e62.py --repeticiones 1 --calentamiento 0

PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q -p no:cacheprovider
```

Los casos se consideran correctos si el escenario carga, la ruta directa contiene un muro, la distancia mínima es
15, las tres búsquedas obtienen costo 16, las rutas contienen acciones legales y A* conserva las métricas discretas
registradas para Manhattan y HTO.

## Uso de IA y validación

**AI usage:** Yes.

**AI intervention:** Codex inspeccionó el escenario y los contratos existentes, ejecutó Manhattan, HTO y UCS,
generó la representación textual desde el JSON, redactó este documento y agregó las pruebas de integración de los
casos 3 y 4. No modificó A*, HTO, UCS, reglas, escenarios, exportaciones ni CLI.

**Student validation:** pendiente. El equipo estudiantil debe revisar el mapa, ejecutar los comandos, contrastar las
métricas y aprobar la interpretación antes de presentar esta evidencia como validada por estudiantes.
