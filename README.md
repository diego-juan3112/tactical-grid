# TacticalGrid

Juego táctico 2D por turnos para experimentar con búsqueda y toma de decisiones. Proyecto 1 de Sistemas
Inteligentes I, Ingeniería de Sistemas y Computación, Universidad de Caldas.

Dos bandos compiten en una cuadrícula por tomar un recurso y llevarlo a su propia base. El juego es el entorno de
experimentación: el proyecto es el sistema que decide dentro de él, desde encontrar una ruta y optimizar su costo
hasta elegir la mejor jugada frente a un adversario. Los mapas, costos y posiciones se cargan desde escenarios JSON;
ninguno está escrito en el código.

![Interfaz de TacticalGrid: camino de UCS sobre ruta_corta_vs_economica.json](docs/imagenes/interfaz.png)

## Integrantes

- Juan Diego Henao Quintero ([@diego-juan3112](https://github.com/diego-juan3112))
- Ana Isabella Suárez Cardona ([@Aisc07](https://github.com/Aisc07))
- Santiago Silva Guarnizo ([@SilvaG35083](https://github.com/SilvaG35083))

## Requisitos

- Python 3.12 o 3.13 (`pyproject.toml` declara `requires-python = ">=3.12,<3.14"`).
- Git.
- Dependencias, instaladas con `pip`: Pygame 2.6 o superior y Uvicorn 0.30 o superior; para las pruebas, pytest 8.0 o
  superior (extra `desarrollo`).
- Opcional: `tkinter`, que usa el selector de archivos de la interfaz. Sin él, los escenarios se abren arrastrando el
  archivo sobre la ventana.

## Instalación

### Windows (PowerShell)

```powershell
git clone https://github.com/diego-juan3112/tactical-grid.git
cd tactical-grid
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[desarrollo]"
```

Con Python 3.12, usa `py -3.12`. Si PowerShell no permite activar el entorno, ejecuta una vez
`Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.

### Linux

```bash
git clone https://github.com/diego-juan3112/tactical-grid.git
cd tactical-grid
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[desarrollo]'
```

En Ubuntu, `sudo apt install python3.12-venv` instala `venv` y `sudo apt install python3-tk` instala `tkinter`.

Activa el entorno virtual en cada terminal nueva antes de ejecutar la aplicación.

## Interfaz gráfica

```bash
python main.py
python main.py --gui escenarios/ruta_corta_vs_economica.json --algoritmo ucs --unidad A1 --objetivo 2 8
```

Sin argumentos se abre `escenarios/campo_20x20.json`. Con `--gui` se pueden indicar el escenario y una búsqueda
inicial: `--algoritmo` (`bfs`, `dfs`, `ucs`, `astar` o `beam`), `--unidad`, `--objetivo FILA COLUMNA` y `--k`.

El panel lateral tiene tres modos, que se recorren con `M`:

| Modo | Uso | Teclas |
|---|---|---|
| Búsqueda | Elegir escenario, algoritmo (BFS, DFS, UCS, A* con Manhattan o HTO, Beam Search), unidad y `k`; un clic en el tablero fija el objetivo. El panel muestra el camino y las métricas. | `Enter` ejecuta · `E` muestra la exploración · `V` verifica · `J` exporta |
| Partida | Juego por turnos. Con control manual, se selecciona una unidad del bando activo y se hace clic en un destino legal. Con control por algoritmos, cada bando decide con el algoritmo elegido para él. | `N` siguiente turno (por algoritmos) · `V` verifica la partida · `R` reinicia · `J` exporta |
| Adversarial | Recomendación del bando en turno con Minimax o alfa-beta, con profundidad y orden de acciones ajustables, sin mover unidades. | `Q` o `Enter` evalúa · `C` o `E` compara ambos · `V` verifica · `A` aplica la recomendación (pide confirmación) |

`O` o el botón **O — Abrir JSON** abre un escenario con el selector de archivos; también se puede arrastrar el archivo
`.json` sobre la ventana. El [manual de usuario](docs/entregables/manual-de-usuario.docx) describe cada control.
La [guía rápida de la interfaz](docs/entregables/guia-rapida-interfaz-tacticalgrid.pdf) resume los flujos principales;
las capturas automatizadas de Pygame y sus configuraciones están en
[`docs/entregables/capturas-ui/`](docs/entregables/capturas-ui/).

## Consola

```bash
python main.py --consola ESCENARIO [opciones]
```

Sin `--modo` ni `--algoritmo`, la consola ejecuta el modo y el algoritmo que declara el campo `prueba` del escenario.
Las opciones de la consola tienen prioridad sobre el JSON.

```bash
# Búsqueda
python main.py --consola escenarios/campo_20x20.json
python main.py --consola escenarios/ruta_corta_vs_economica.json --algoritmo ambos
python main.py --consola escenarios/campo_20x20.json --algoritmo beam --k 1 2 4 8
python main.py --consola escenarios/campo_20x20.json --algoritmo a_estrella --heuristica hto

# Adversarial
python main.py --consola escenarios/decision_adversarial.json
python main.py --consola escenarios/recurso_en_transporte.json --algoritmo minimax_alfa_beta --profundidad 3

# Partida: ambos bandos deciden con el mismo algoritmo
python main.py --consola escenarios/estado_compuesto_portador.json --modo partida
```

| Opción | Uso |
|---|---|
| `--modo` | `busqueda`, `partida` o `adversarial`. |
| `--algoritmo` | Búsqueda: `bfs`, `dfs`, `ucs`, `a_estrella`, `beam`, `ambos` (BFS y UCS) o `bfs_dfs`. Adversarial: `minimax`, `alfa_beta` o `minimax_alfa_beta` (compara ambos). Partida: `minimax` o `alfa_beta`. |
| `--unidad`, `--objetivo FILA COLUMNA` | Unidad y destino de una búsqueda. |
| `--heuristica` | Heurística de A*: `manhattan` (predeterminada) o `hto`. |
| `--k` | Ancho de Beam Search; admite varios valores. |
| `--profundidad`, `--orden` | Profundidad de Minimax y alfa-beta, y orden de las acciones: `generacion`, `inverso` o `tactico`. |
| `--turnos` | Límite de jugadas del modo partida (50 si no se indica ni en el JSON). |
| `--verificar` | Comprueba la respuesta con las reglas del juego; termina con código 1 si una comprobación falla. |
| `--json`, `--exportar ARCHIVO` | Muestra o guarda el resultado en JSON, con el comando que lo reproduce y la huella del escenario. |
| `--reproducir-registro ARCHIVO` | Valida y reproduce un historial de partida exportado desde la interfaz con `J`. |

`python main.py --consola --help` muestra la ayuda completa.

## Escenarios JSON

Los escenarios siguen el formato JSON común del enunciado: `version`, `mapa.filas`, `mapa.columnas`, `tipos_terreno`,
`terreno`, `bases.A`, `bases.B`, `recurso`, `unidades`, `turno`, `juego.portador_recurso` y, opcionalmente,
`prueba`. La profundidad de Minimax se lee de `juego.profundidad_maxima_minimax`, como en el ejemplo del enunciado. Cualquier archivo con ese formato se carga sin modificar el código, desde la interfaz o desde la consola:

```bash
python main.py --consola ruta/al/escenario.json --verificar
```

Antes de aplicarse, el escenario se valida por completo. Si tiene un error, se indica el campo, el elemento y el valor
que lo causan, y no se aplica ningún cambio; la consola termina con código 1.

El proyecto admite estos campos propios, todos opcionales: `descripcion` (informativo), `prueba.algoritmo`, `prueba.k`,
`prueba.max_turnos`, `juego.orden_acciones` y `juego.pesos_utilidad`. Las opciones de la consola los reemplazan. Si
faltan, se usan los valores predeterminados, salvo `k` de Beam Search y la profundidad de Minimax en la consola, que
deben indicarse con `--k` y `--profundidad` cuando el JSON no los declara.

| Escenario incluido | Tamaño | Uso |
|---|---|---|
| `campo_20x20.json` | 20 × 20 | Escenario principal: lago de pantano, bosques y muros; la ruta más corta no es la más barata. |
| `arquitectura_basica.json` | 20 × 20 | Mapa abierto, todo camino. No declara `prueba`: requiere `--unidad` y `--objetivo`. |
| `ejemplo_enunciado.json` | 4 × 4 | Ejemplo del enunciado. |
| `ruta_corta_vs_economica.json` | 5 × 9 | La ruta recta cruza pantano (8 movimientos, costo 50); rodear cuesta 12. |
| `obstaculo_rodeo.json` | 8 × 7 | Un muro en U obliga a rodear un objetivo cercano. |
| `recurso_en_transporte.json` | 6 × 8 | Partida con el recurso en manos de A2. |
| `estado_compuesto_libre.json` y `estado_compuesto_portador.json` | 5 × 5 | Mismas posiciones; en el segundo, A1 lleva el recurso. |
| `decision_adversarial.json` | 3 × 6 | Tomar el recurso parece bueno, pero el rival lo intercepta. |
| `caso_06_estado_compuesto_libre_20x20.json` y `caso_06_estado_compuesto_portador_20x20.json` | 20 × 20 | Caso 6 en 20 × 20. |
| `caso_07_decision_adversarial_20x20.json` | 20 × 20 | Caso 7 en 20 × 20. |
| `caso_08_minimax_alfa_beta_20x20.json` | 20 × 20 | Caso 8 en 20 × 20: equivalencia y poda de Minimax y alfa-beta. |
| `caso_10_profundidad_20x20.json` | 20 × 20 | Caso 10 en 20 × 20: efecto de la profundidad. |
| `prueba_gui_partida.json` | 5 × 5 | Validación manual del modo partida de la interfaz. |

Las variantes de 20 × 20 conservan la región de juego de los casos pequeños y la rodean de muros. La clasificación
completa está en el [catálogo de escenarios](docs/tecnico/catalogo-escenarios.md).

## Algoritmos

| Algoritmo | Criterio | Parámetros |
|---|---|---|
| BFS | Menor número de movimientos. | — |
| DFS | Profundiza una rama antes de retroceder. | — |
| UCS | Menor costo acumulado según el terreno. | — |
| A* | `f(n) = g(n) + h(n)`. | Heurística Manhattan escalada o HTO (distancia con obstáculos). |
| Beam Search | Conserva los `k` mejores candidatos por nivel. | `k` |
| Minimax | Mejor jugada suponiendo que el rival responde de forma óptima. | Profundidad, orden de acciones |
| Minimax con poda alfa-beta | La misma decisión que Minimax, evitando ramas que no la cambian. | Profundidad, orden de acciones |

Las búsquedas reportan algoritmo, éxito, camino, costo, estados generados y expandidos, máximo de frontera, longitud y
tiempo. Minimax y alfa-beta reportan nodos generados, evaluados y podados, profundidad alcanzada, tiempo, acción
seleccionada y valor. La función de utilidad y sus pesos se describen en
[decisión adversarial](docs/tecnico/04-decision-adversarial.md).

## Pruebas

```bash
python -m pytest
```

La suite cubre escenario, juego, algoritmos, modos, verificación, registro e interfaz; las pruebas de interfaz usan el
controlador de video *dummy* de SDL y no abren una ventana. Las cifras de los diez casos mínimos están fijadas en
pruebas automatizadas.

Scripts de experimentos:

- `scripts/ejecutar_casos_minimos.py` ejecuta los diez casos mínimos y reescribe
  `docs/experimentos/resultados-casos-minimos.json`.
- `scripts/comparar_heuristicas_e62.py` compara A* con Manhattan, A* con HTO y UCS (`--help` muestra sus opciones).

## Documentación

| Documento | Contenido |
|---|---|
| [Enunciado](docs/enunciado/primer-proyecto.pdf) | Especificación del proyecto. |
| [Documento técnico](docs/entregables/documento-tecnico.docx) | Modelado, estados, reglas, costos, heurísticas, utilidad, metodología, resultados, complejidad, limitaciones y uso de IA. |
| [Manual de usuario](docs/entregables/manual-de-usuario.docx) | Instalación, interfaz, consola, escenarios externos, verificación y exportación. La guía rápida y el manifiesto documentan las capturas de interfaz generadas con Pygame. |
| [Arquitectura y modelo](docs/tecnico/01-arquitectura-y-modelo.md) | Capas, estado, acciones, costo, reglas de borde, validación y escenarios. |
| [Búsqueda](docs/tecnico/02-busqueda.md) | Instrumentación de métricas, BFS, DFS, UCS, A* y Beam Search. |
| [Heurística HTO](docs/tecnico/03-heuristica-hto.md) | Segunda heurística: definición, admisibilidad, costo y experimentos. |
| [Decisión adversarial](docs/tecnico/04-decision-adversarial.md) | Acciones tácticas, utilidad, Minimax, alfa-beta, métricas y orden de acciones. |
| [Modos, verificación y registro](docs/tecnico/05-modos-verificacion-y-registro.md) | Modos de prueba, verificador de soluciones y registro reproducible. |
| [Interfaz](docs/tecnico/06-interfaz.md) | Tablero, exploración, partida, evaluación adversarial y apertura de escenarios. |
| [Guía de validación manual](docs/tecnico/guia-validacion-manual.md) | Pasos para revisar la interfaz en una ventana real. |
| Casos mínimos: [1, 2 y 5](docs/casos-minimos/casos-1-2-5-busqueda.md) · [3 y 4](docs/casos-minimos/casos-3-4-obstaculo-y-heuristicas.md) · [6 a 10](docs/casos-minimos/casos-6-10-adversariales.md) | Configuración, resultado esperado y resultado obtenido de cada caso. |
| [Experimentos de los casos mínimos](docs/experimentos/casos-minimos.md) | Procedimiento y resultados registrados. |
| [Guía de sustentación](docs/experimentos/guia-sustentacion.md) | Comandos y escenarios para la demostración. |
| [AGENTS.md](AGENTS.md) | Reglas del proyecto y convención de documentación de métodos. |

## Uso de IA

El equipo usó IA generativa (Codex y Claude) como apoyo y lo declara en la documentación de cada método y en la
sección 17 del documento técnico, como exige el enunciado. Cada integrante responde por todo el código entregado.
