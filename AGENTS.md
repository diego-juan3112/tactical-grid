# AGENTS.md — TacticalGrid

Guía de contexto para cualquier asistente de IA (o persona nueva) que colabore en este proyecto. Resume las
decisiones estables aprobadas hasta la historia **E0.3**.

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

- **Python 3.12 o compatible:** permite expresar con claridad los algoritmos de busqueda y decision, mantener codigo legible y modificable, e integrar Pygame y pytest.
- **Pygame:** TacticalGrid es un entorno tactico 2D en cuadricula; permite visualizar tablero, terrenos, unidades, caminos y resultados. Es suficiente para observar el sistema inteligente, no para un videojuego comercial, y se aisla exclusivamente en `src/tacticalgrid/interfaz/`.
- **pytest:** permite pruebas automatizadas y reproducibles de escenario, juego y algoritmos sin abrir Pygame.
- **JSON:** contrato externo para escenarios intercambiables.
- **Uvicorn:** servidor ASGI para el punto tecnico aislado en `src/tacticalgrid/servidor/`; no sustituye `.venv` ni introduce un framework web.
- **.venv:** entorno virtual local obligatorio para instalar y ejecutar dependencias.
- **Git:** control de versiones.

La estructura real es:

```text
src/tacticalgrid/
├── escenario/    # carga, validacion y representacion estatica desde JSON
├── juego/        # estado dinamico y futuras reglas del dominio
├── algoritmos/   # resultados y futuras estrategias de busqueda/decision
├── interfaz/     # visualizacion Pygame
└── servidor/      # punto ASGI aislado para Uvicorn
tests/
├── escenario/
├── juego/
├── algoritmos/
└── servidor/
escenarios/
```

`escenario` carga, valida y provee datos estaticos, costos y transitabilidad. `juego` representa el estado
dinamico, reglas, acciones y sucesores. `algoritmos` consume contratos del dominio: no lee JSON, no conoce
Pygame ni contiene mapas, costos o posiciones codificados. `interfaz` consume estado y resultados para
visualizarlos; no contiene reglas ni algoritmos. No se permiten dependencias circulares.

E1.1 define el modelo del estado: `Escenario` contiene datos estaticos y `EstadoJuego` contiene unidades, turno,
posicion del recurso cuando no tiene portador, identificador del portador y estado general de la partida. Una
`Unidad` tiene identificador, bando, tipo y posicion actual. `EstadoJuego` y `Unidad` son inmutables y hashables;
las unidades se normalizan por identificador, de modo que su orden de almacenamiento no altera la identidad logica.
Las posiciones afectan acciones y transiciones, el turno determina que bando actua y el portador distingue estados
visualmente iguales que pueden exigir decisiones distintas. El estado no codifica dimensiones ni posiciones fijas:
esa informacion pertenece al escenario cargado. Las reglas detalladas de transicion se definen en historias posteriores.

Todo codigo propio, archivos, clases, funciones, variables, comentarios y documentacion se escribe en
espanol. Las claves del JSON son una excepcion: son un contrato externo y se conservan literalmente.

## Escenarios JSON

### Dónde viven

Los escenarios JSON de desarrollo y prueba viven en `escenarios/` (carpeta en la raíz del repo). Deben
incluir, como mínimo, un escenario ≥ 20×20. Los escenarios comparativos de ruta corta/costo y BFS/UCS
se agregan junto con la implementacion de esos algoritmos, para no declarar resultados inexistentes.

### Cómo ejecutarlos

Crear y activar un entorno virtual, e instalar las dependencias de desarrollo:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[desarrollo]'
```

Ejecutar pruebas: `python -m pytest`.

El punto de entrada funcional de la interfaz minima es `tacticalgrid`; requiere un entorno grafico y se
cierra mediante el control de cierre de la ventana. El servidor ASGI se ejecuta con `python -m uvicorn tacticalgrid.servidor.asgi:aplicacion --reload`. La instalacion, pytest y este comando ASGI se verificaron en Linux dentro de un entorno virtual temporal.

### Campos obligatorios (referencia rápida)

| Campo | Descripción |
|---|---|
| `version` | Versión del formato de escenario. |
| `mapa.filas` / `mapa.columnas` | Dimensiones de la cuadrícula. |
| `tipos_terreno` | Catálogo de terrenos, costos y transitabilidad. |
| `terreno` | Matriz que describe cada celda del mapa. |
| `bases.A` / `bases.B` | Posiciones de las bases. |
| `recurso` | Posición del recurso cuando no está siendo transportado. |
| `unidades` | Listado de unidades, bando, tipo y posición. |
| `turno` | Bando que debe actuar. |
| `juego.portador_recurso` | ID de la unidad que transporta el recurso, o `null`. |
| `prueba` | Configuración opcional para ejecutar `busqueda`, `partida` o `adversarial`. |

Se pueden agregar campos propios siempre que no alteren el significado de los obligatorios. Los nombres de
campo definidos por la especificación deben respetarse literalmente.

### Validación obligatoria antes de aplicar un escenario

Filas/columnas positivas y consistentes · todos los terrenos usados existen en `tipos_terreno` · terrenos
transitables tienen costo positivo · bases/recurso/unidades dentro del mapa · ninguna unidad sobre celda no
transitable · IDs de unidad únicos · cada unidad pertenece a `A` o `B` · `turno` es `A` o `B` ·
`portador_recurso` (si no es `null`) identifica una unidad existente.

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

Toda metrica debe exponer informacion equivalente: algoritmo, exito, camino, longitud, costo cuando
corresponda, estados generados, estados expandidos, maximo de frontera y tiempo. Para Minimax/alfa-beta:
nodos generados, nodos evaluados, nodos podados, profundidad alcanzada, tiempo, accion seleccionada y valor obtenido.

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

- Si cambia la estructura de carpetas, el formato de escenarios, o se agregan convenciones nuevas del
  equipo.
- Este archivo describe reglas y contexto estables; no es el lugar para el detalle de cada historia

## Referencias

- Especificación completa del proyecto: [`Primer proyecto.pdf`](./docs/Primer%20proyecto.pdf).
- Backlog de historias de usuario: Tablero de Proyectos en GitHub.
