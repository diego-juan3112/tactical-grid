# Interfaz gráfica

Historias E9.1 a E9.3: tablero, camino y exploración en Pygame. El uso paso a paso, con capturas, está en el manual de usuario (`docs/entregables/manual-de-usuario.docx`).

## Abrir la interfaz

Desde la raíz del repositorio, la ejecución sin argumentos abre Pygame con `campo_20x20.json`, sin iniciar una
búsqueda. Es también el flujo esperado al usar **Run Python File** sobre `main.py` en VS Code:

```bash
python main.py
python main.py --gui
```

El panel permite cambiar entre los escenarios JSON incluidos, seleccionar BFS, DFS, UCS, A* o Beam Search, elegir
una unidad real con las flechas y ajustar `k`. El objetivo se elige haciendo clic sobre una celda transitable.
`Enter` y el botón `Enter — Ejecutar busqueda` llaman a la misma acción y calculan una sola vez el camino y la
traza. Cambiar cualquier selector limpia el resultado anterior para que no se confunda con la nueva configuración.
La tecla o botón `E — Mostrar exploracion` alterna la capa sin recalcular.

La ayuda de la ventana cambia con el algoritmo seleccionado:

| Algoritmo | Criterio mostrado | Consecuencia práctica |
|---|---|---|
| BFS | Menor cantidad de movimientos | Puede atravesar terrenos costosos. |
| DFS | Profundizar una alternativa | No garantiza una ruta corta ni económica. |
| UCS | Menor costo acumulado | Puede elegir más movimientos para reducir el costo. |
| A* | Costo acumulado más heurística Manhattan | Manhattan estima movimientos horizontales y verticales. |
| Beam Search | Exploración limitada por `k` | Conserva `k` alternativas por nivel y puede descartar rutas útiles. |

El resultado distingue movimientos, costo y estados expandidos. La línea cian es el camino final. La capa violeta
de exploración muestra posiciones analizadas antes del resultado; una posición resaltada no implica que pertenezca
al camino. Los estados expandidos pueden superar las posiciones únicas porque estados distintos pueden proyectarse
sobre la misma celda. La leyenda indica el costo de cada terreno transitable; UCS y A* usan esos costos al decidir.

## Abrir un escenario JSON desde la ventana — E9.4

El botón **O — Abrir JSON**, a la derecha del título del panel, y la tecla `O` abren el selector de archivos del
sistema (`interfaz/dialogo.py`, con `tkinter`). El selector empieza en la carpeta del escenario actual y filtra los
archivos `.json`. Soltar un archivo sobre la ventana (evento `DROPFILE` de Pygame) hace lo mismo sin selector.

- **Carga atómica:** ambos caminos usan `ControlGrafico.abrir_escenario`, que reutiliza `cargar_ruta`. Si el archivo
  es inválido, el panel muestra el error y el escenario, las selecciones y el resultado anteriores no cambian.
- **Selectores:** un escenario abierto con éxito se agrega una sola vez a la lista de `<` y `>`, así que se puede volver a
  él después de cambiar de mapa.
- **Selecciones iniciales:** si el escenario declara una prueba de búsqueda, la unidad y el objetivo se toman de ella.
- **Sin selector:** si `tkinter` no está instalado o no hay pantalla, como pasa a menudo en Linux, el panel sugiere
  arrastrar el archivo. En Ubuntu, `tkinter` se instala con `sudo apt install python3-tk`.
- **Cancelar:** cerrar el selector sin elegir deja todo igual.

Las pruebas de `tests/interfaz/test_dialogo.py`, `tests/interfaz/test_control.py`, `tests/interfaz/test_renderizador.py`
y `tests/interfaz/test_aplicacion.py` cubren el selector, la carga externa, la ruta repetida, el archivo inválido, el
botón, la tecla `O` y soltar un archivo.

## Visualización del tablero, caminos y exploración — E9.1/E9.2/E9.3

La interfaz gráfica acepta el escenario como argumento posicional; sin argumento usa `campo_20x20.json`. Si no se
indica `--algoritmo`, conserva la vista estática de E9.1 y no ejecuta una búsqueda:

```bash
python main.py
python main.py --gui escenarios/ruta_corta_vs_economica.json
python main.py --gui escenarios/recurso_en_transporte.json
```

E9.2 ejecuta una búsqueda una sola vez antes del ciclo gráfico y dibuja su `ResultadoBusqueda.camino` sobre el
tablero. Los nombres admitidos son `bfs`, `dfs`, `ucs`, `astar` y `beam`:

```bash
python main.py --gui escenarios/ruta_corta_vs_economica.json --algoritmo bfs
python main.py --gui escenarios/ruta_corta_vs_economica.json --algoritmo dfs
python main.py --gui escenarios/ruta_corta_vs_economica.json --algoritmo ucs
python main.py --gui escenarios/ruta_corta_vs_economica.json --algoritmo astar
python main.py --gui escenarios/ruta_corta_vs_economica.json --algoritmo beam --k 4
```

La unidad y el objetivo indicados por consola tienen prioridad. Si se omiten, se leen de
`prueba.unidad_inicio` y `prueba.objetivo` del escenario, siempre que `prueba.modo` sea `busqueda`. No se inventan
valores cuando faltan ambos orígenes:

```bash
python main.py --gui escenarios/campo_20x20.json --algoritmo astar --unidad A1 --objetivo 10 15
python main.py --gui escenarios/campo_20x20.json --algoritmo beam --unidad A1 --objetivo 9 10 --k 4
```

Beam Search requiere un entero `k >= 1`: `--k` tiene prioridad y, si se omite, se usa `prueba.k`. A* usa Manhattan
por defecto. La línea cian conserva el orden exacto del camino; el anillo verde identifica el origen y el coral el
destino. Las bases, el recurso, las unidades y la cuadrícula se dibujan encima para mantener su identidad. El panel
muestra el algoritmo y `exito` o `sin solucion`; en el segundo caso no se dibuja ninguna ruta.

E9.3 captura, durante esa misma ejecución, cada `EstadoJuego` entregado realmente a la expansión común. La capa
permanece oculta al iniciar: `E` la muestra y una segunda pulsación la oculta sin recalcular ni perder el camino.
El violeta semitransparente representa posiciones asociadas con estados expandidos; no representa estados generados
ni la frontera. Si la búsqueda falla, la exploración registrada sigue disponible.

El panel distingue `Estados expandidos` de `Posiciones resaltadas`: estados compuestos diferentes pueden proyectarse
sobre una misma celda. BFS, DFS, UCS, A* y Beam Search usan esta traza real mediante `expandir()`. Se almacenan hasta
10 000 eventos por búsqueda; si se supera el límite, el total de la métrica permanece exacto, el panel marca `Traza
parcial` y solo se resaltan las posiciones presentes en el segmento almacenado. Sin busqueda, `E` no cambia la vista.
El panel mantiene visible `E — Mostrar exploracion`, explica que resalta posiciones exploradas y, mientras no exista
un resultado, indica que primero debe ejecutarse una búsqueda. Al activar la capa cambia a `E — Ocultar exploracion`.

Reproducción académica con BFS y UCS:

```bash
python main.py --gui escenarios/ruta_corta_vs_economica.json --algoritmo bfs
python main.py --gui escenarios/ruta_corta_vs_economica.json --algoritmo ucs
```

Los estados explorados fuera del camino corresponden a alternativas cuyos sucesores se analizaron antes de alcanzar
el objetivo. Por eso la exploración suele cubrir más celdas que la ruta final y puede colorear menos posiciones que
el total de expansiones.

### Presentación gráfica del tablero

El rediseño visual usa pixel art cenital: senderos de tierra, pasto, copas de árboles, pantano,
rocas, fortalezas, unidades por bando y un cristal estratégico. Los identificadores, el turno, la leyenda y la ruta
de E9.2 permanecen visibles. Las orientaciones de los tiles varían de forma determinista según terreno y posición;
no usan el generador aleatorio ni alteran el estado. Un terreno externo conserva un color y patrón estables, informa
su nombre en la leyenda y representa su transitabilidad sin asignarle una semántica nueva.

Los PNG se resuelven desde `tacticalgrid/interfaz/recursos`, se cargan una vez y las superficies transformadas se
cachean por sprite, tamaño y variante. Si falta un atlas, la interfaz sigue operativa con un fallback y lo informa en
el panel. Los recursos se incluyen como datos del paquete, por lo que la ejecución no depende del directorio actual
ni realiza descargas. Su procedencia se documenta en
`src/tacticalgrid/interfaz/recursos/ORIGEN.md`. No se incorporaron assets externos; el repositorio aún no define una
licencia general de redistribución.

Las capturas reproducibles bajo SDL dummy están en `docs/imagenes/redisenio-visual/`: incluyen el antes/después de
`campo_20x20.json`, `recurso_en_transporte.json` y las rutas diferentes de BFS y UCS en
`ruta_corta_vs_economica.json`. Esa evidencia no sustituye la revisión manual de una ventana real.
