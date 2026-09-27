# AGENTS.md — TacticalGrid

Guía de contexto para cualquier asistente de IA (o persona nueva) que colabore en este proyecto. Resuelve la
historia **E0.1**. Este archivo es un resumen operativo.

## Propósito del proyecto

TacticalGrid es un juego táctico 2D por turnos: dos bandos (A y B) compiten en una cuadrícula por tomar un
recurso estratégico y transportarlo hasta su propia base. **El juego es el entorno de experimentación; el
proyecto es el sistema inteligente que decide dentro de él.** La calidad visual no es un criterio de
evaluación relevante — la interfaz existe para observar y experimentar con la inteligencia del sistema.

> **Pregunta central del proyecto:** ¿Cómo cambia la forma de decidir de un sistema inteligente cuando pasa
> de encontrar una ruta, a optimizar su costo, utilizar conocimiento heurístico y finalmente actuar frente a
> un adversario que también toma decisiones?

## Reglas no negociables (del enunciado)

Cualquier código o sugerencia de IA debe respetar esto sin excepción:

- **Los costos vienen siempre del escenario JSON cargado**, nunca de constantes dispersas en el código de los
  algoritmos. Un cambio de costo en el JSON debe reflejarse en el comportamiento sin tocar código.
- **Ningún algoritmo puede depender de un mapa particular ni de posiciones escritas directamente en el
  código.** Todo escenario válido debe cargarse sin modificar el código fuente.
- **Separación estricta de 4 capas:** lógica de juego, representación del escenario, algoritmos de
  búsqueda/decisión, e interfaz gráfica. No mezclar responsabilidades entre capas.
- **La carga de un escenario es atómica:** se valida completo antes de aplicarse; si algo falla, el sistema
  no queda en un estado parcialmente modificado y el error se explica con claridad.
- **MAX y MIN son roles dentro del árbol Minimax, no niveles de capacidad distintos.** Ambos bandos operan
  bajo las mismas reglas.
- **La profundidad máxima de Minimax debe ser configurable sin modificar el código.**

## Arquitectura y stack técnico

**[PENDIENTE DE APROBACIÓN]** — el stack técnico y la estructura concreta de carpetas se definen en la
historia **E0.3**. Hasta que esa historia se cierre:

- Respetar la separación de 4 capas descrita arriba al proponer cualquier estructura.
- Cuando E0.3 quede resuelta, **este archivo debe actualizarse** reemplazando esta sección con: lenguaje,
  librerías principales, estructura real de carpetas, y comandos de instalación/ejecución/test.

## Escenarios JSON

### Dónde viven

Los escenarios JSON de desarrollo y prueba viven en `scenarios/` (carpeta en la raíz del repo). Deben
incluir, como mínimo: un escenario ≥ 20×20, un escenario donde una ruta con menos movimientos sea más
costosa que una más larga, y un escenario donde BFS y UCS produzcan caminos distintos.

### Cómo ejecutarlos

**[PENDIENTE DE APROBACIÓN]** — depende del stack elegido en E0.3.

### Campos obligatorios (referencia rápida)

| Campo | Descripción |
|---|---|
| `version` | Versión del formato de escenario. |
| `map.rows` / `map.columns` | Dimensiones de la cuadrícula. |
| `land_types` | Catálogo de terrenos, costos y transitabilidad. |
| `land` | Matriz que describe cada celda del mapa. |
| `base.A` / `base.B` | Posiciones de las bases. |
| `resource` | Posición del recurso cuando no está siendo transportado. |
| `units` | Listado de unidades, bando, tipo y posición. |
| `turn` | Bando que debe actuar. |
| `game.resource_carrier` | ID de la unidad que transporta el recurso, o `null`. |
| `test` | Configuración opcional para ejecutar `search`, `match` o `adversarial`. |

Se pueden agregar campos propios siempre que no alteren el significado de los obligatorios. Los nombres de
campo definidos por la especificación (en ingles, tal como están) deben respetarse literalmente.

### Validación obligatoria antes de aplicar un escenario

Filas/columnas positivas y consistentes · todos los terrenos usados existen en `land_types` · terrenos
transitables tienen costo positivo · bases/recurso/unidades dentro del mapa · ninguna unidad sobre celda no
transitable · IDs de unidad únicos · cada unidad pertenece a `A` o `B` · `turno` es `A` o `B` ·
`resource_carrier` (si no es `null`) identifica una unidad existente.

## Algoritmos que cubre el proyecto (mapa completo)

En este orden de complejidad creciente:

1. **No informada:** BFS y DFS.
2. **Costo uniforme:** UCS (minimiza costo acumulado, no cantidad de movimientos).
3. **Informada:** A* con `f(n) = g(n) + h(n)`, heurística Manhattan + una segunda heurística propia **[PENDIENTE DE APROBACIÓN]**
   justificada (qué estima, qué información usa, costo computacional, admisibilidad, cuándo pierde
   discriminación).
4. **Memoria limitada:** Beam Search, experimentado con k = 1, 2, 4, 8.
5. **Adversarial:** Minimax y Minimax con poda alfa-beta, profundidad limitada configurable, función de
   utilidad propia desde la perspectiva de MAX.

### Métricas obligatorias

- **Búsqueda (BFS/DFS/UCS/A*/Beam Search):** solución encontrada, longitud, estados generados, estados
  expandidos, máximo de frontera, tiempo.
- **Minimax/alfa-beta:** nodos generados, nodos evaluados, nodos podados, profundidad alcanzada, tiempo,
  acción seleccionada, valor obtenido.

Toda métrica debe exponerse en una estructura equivalente a la de ejemplo del PDF (campo `algorithm`,
`success`, `road`, `cost`, `generated_states`, `expanded_states`, `maximum_limit(maxima_frontera)`), para que los experimentos sean reproducibles y comparables.

## Convención de documentación de métodos

Todo método con lógica relevante (algoritmos de búsqueda, heurísticas, generación de sucesores, cálculo de
costos, función de utilidad, Minimax, alfa-beta, validadores) debe documentarse con estos 7 elementos — no
basta un comentario que solo diga qué hace el método:

| Elemento | Contenido esperado |
|---|---|
| `Purpose` | Responsabilidad concreta del método dentro de la solución. |
| `Preconditions` | Condiciones que deben cumplirse antes de ejecutarlo. |
| `Postconditions` | Condiciones que deben cumplirse después de una ejecución correcta. |
| `Complexity` | Costo temporal y, cuando corresponda, espacial. |
| `AI usage` | `Yes` o `No`, explícito. |
| `AI intervention` | Si hubo IA, describir con precisión en qué parte intervino. |
| `Student validation` | Cómo se revisó, probó, modificó o validó lo generado con IA. |

La documentación debe corresponder **exactamente** a la versión real del método implementado — si describe
algo distinto de lo que hace el código, se considera documentación inconsistente (y así se evalúa). No se
exige este nivel de detalle para métodos triviales.

## Uso de IA generativa en este proyecto

- Usar IA generativa como apoyo está permitido y no baja la nota por sí mismo, pero **debe declararse**
  siempre (ver tabla anterior).
- Cada estudiante es responsable de todo el código entregado y debe poder explicarlo, modificarlo y
  defenderlo en la sustentación individual, aunque lo haya generado la IA.
- Omitir deliberadamente el uso real de IA se considera una inconsistencia de documentación, no un detalle
  menor.
- Por eso, cualquier asistente de IA que trabaje en este repo debe **dejar rastro claro** de su intervención
  en la documentación del método que toque, siguiendo la tabla de arriba.

## Cuándo actualizar este archivo

- Al cerrar **E0.3** (arquitectura/stack): reemplazar las secciones marcadas `[PENDIENTE DE APROBACIÓN]`.
- Si cambia la estructura de carpetas, el formato de escenarios, o se agregan convenciones nuevas del
  equipo.
- Este archivo describe reglas y contexto estables; no es el lugar para el detalle de cada historia

## Referencias

- Especificación completa del proyecto: [`Primer proyecto.pdf`](./docs/Primer%20proyecto.pdf).
- Backlog de historias de usuario: Tablero de Proyectos en GitHub.
