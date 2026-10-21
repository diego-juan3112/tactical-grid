# Lista de comprobación de escritorio para TacticalGrid

Esta guía requiere una ventana Pygame interactiva y la participación de una persona del equipo. Las pruebas con SDL
dummy no sustituyen estos pasos. Registra el resultado observado sin marcarlo desde el resultado esperado.

## Registro de la sesión

| Campo | Dato que debe registrar quien ejecuta |
|---|---|
| Fecha, nombre de quien valida | |
| Sistema operativo y versión | |
| Resolución y escala de pantalla | |
| Python y Pygame | |
| Escenario fixture | `escenarios/prueba_gui_partida.json` |
| JSON externo oficial disponible | Sí/No; nombre y SHA-256 si existe |
| Registro exportado/reproducido | Ruta, SHA-256, código de salida |

## Preparación y comandos confirmados en el punto de entrada

Desde la raíz, Linux con el entorno instalado:

```bash
.venv/bin/python main.py
.venv/bin/python main.py --gui escenarios/prueba_gui_partida.json
.venv/bin/python main.py --consola --help
```

El primer comando abre la GUI predeterminada; el segundo entrega el fixture al parser gráfico (`main.py` despacha los
argumentos posteriores a `--gui`); el tercero lista opciones de consola. Para un JSON que proporcione el profesor:

```bash
.venv/bin/python main.py --gui /ruta/al/escenario.json
```

No reemplaces el archivo oficial. El fixture es un mapa del repositorio para la secuencia manual descrita abajo. Para
exportar, pulsa `J` en la GUI, elige el destino y utiliza exactamente el nombre resultante en:

```bash
.venv/bin/python main.py --consola --reproducir-registro /ruta/al/registro.tg.json
```

## Pruebas observables

Para cada caso registra **Resultado observado**, selecciona **Pendiente / Aprobado / Fallido** y conserva la evidencia
indicada. Si una preparación no se cumple, marca No ejecutado en el resultado observado y explica la causa.

### V01 — Inicio y legibilidad

- **Requisito:** R23, R35.
- **Preparación:** escritorio con entorno gráfico; iniciar el comando `main.py` sin argumentos.
- **Pasos:** observa la ventana, maximízala o cambia su tamaño; revisa tablero, panel, controles, fuentes y colores.
- **Esperado:** la ventana abre, no hay solapamientos ni texto/botones recortados y los controles se distinguen.
- **Observado:** ______ **Estado:** Pendiente / Aprobado / Fallido.
- **Evidencia:** captura completa con resolución y escala registradas.

### V02 — Carga externa y reemplazo de escenario

- **Requisito:** R04, R06, R23, R35.
- **Preparación:** fixture visible y copia sin modificar de un JSON externo válido; si el oficial no está disponible,
  anótalo y prueba adicionalmente un escenario del repositorio que no esté abierto.
- **Pasos:** pulsa `O`, cancela; abre de nuevo y carga el archivo. Repite arrastrando el JSON sobre la ventana.
- **Esperado:** cancelar conserva sesión; carga válida actualiza mapa, controles y nombre. No se confunde fixture con
  escenario oficial.
- **Observado:** ______ **Estado:** Pendiente / Aprobado / Fallido.
- **Evidencia:** nombre, hash, captura antes/después y archivo usado.

### V03 — Rechazo de JSON inválido

- **Requisito:** carga atómica del escenario, R23.
- **Preparación:** crea una copia temporal de un JSON y coloca una unidad sobre un terreno no transitable.
- **Pasos:** carga la copia desde `O`.
- **Esperado:** el panel explica el error; escenario, estado y sesión anterior se conservan.
- **Observado:** ______ **Estado:** Pendiente / Aprobado / Fallido.
- **Evidencia:** copia inválida, mensaje y capturas antes/después.

### V04 — Cambio de modo

- **Requisito:** R23, R33.
- **Preparación:** escenario fixture cargado.
- **Pasos:** pulsa `M` repetidamente y observa la etiqueta del botón `M — Modo` y los controles de cada vista.
- **Esperado:** recorre Búsqueda, Partida y Adversarial. Un JSON con `prueba.modo` inicia en ese modo; sin `prueba`,
  inicia en Búsqueda.
- **Observado:** ______ **Estado:** Pendiente / Aprobado / Fallido.
- **Evidencia:** capturas por modo y configuración de los JSON probados.

### V05 — Camino y capa de exploración

- **Requisito:** R23, R24.
- **Preparación:** `ruta_corta_vs_economica.json` en modo Búsqueda.
- **Pasos:** selecciona unidad y destino; ejecuta con `Enter`; pulsa `E` para mostrar/ocultar exploración; cambia
  destino y repite.
- **Esperado:** camino final y exploración se distinguen; un cambio de configuración no deja una ruta obsoleta.
- **Observado:** ______ **Estado:** Pendiente / Aprobado / Fallido.
- **Evidencia:** capturas de camino y exploración, objetivo elegido.

### V06 — Métricas de búsqueda y verificación

- **Requisito:** R12, R23, R24, R26.
- **Preparación:** búsqueda vigente con resultado.
- **Pasos:** desplázate por el panel; pulsa `V` o `V — Verificar búsqueda`.
- **Esperado:** son legibles algoritmo, éxito, ruta, longitud, costo, generados, expandidos, máximo de frontera y
  tiempo. El reporte enumera comprobaciones y no altera el tablero.
- **Observado:** ______ **Estado:** Pendiente / Aprobado / Fallido.
- **Evidencia:** captura del panel y del reporte de verificación.

### V07 — A* Manhattan y HTO

- **Requisito:** R15, R23, R25.
- **Preparación:** `obstaculo_rodeo.json`.
- **Pasos:** selecciona A*; en `Heurística A*` alterna Manhattan/HTO con `<` y `>`; ejecuta y verifica cada
  configuración sin cambiar escenario, unidad u objetivo.
- **Esperado:** la etiqueta muestra la heurística elegida; cada camino y métrica corresponde a esa corrida.
- **Observado:** ______ **Estado:** Pendiente / Aprobado / Fallido.
- **Evidencia:** dos capturas y exportaciones `J` si están disponibles.

### V08 — Beam Search y valores k

- **Requisito:** R16, R23, R25.
- **Preparación:** `campo_20x20.json` y Beam Search.
- **Pasos:** ajusta `Beam k` con los botones `<`/`>` hasta k=1, 2, 4 y 8; ejecuta cada valor, incluido cualquier
  resultado sin solución.
- **Esperado:** el valor visible coincide con cada corrida; falla o éxito y métricas cambian según la búsqueda real.
- **Observado:** ______ **Estado:** Pendiente / Aprobado / Fallido.
- **Evidencia:** cuatro capturas o registros exportados y hashes del JSON.

### V09 — Selección de unidad activa

- **Requisito:** R07, R23.
- **Preparación:** fixture en modo Partida, bando inicial A.
- **Pasos:** selecciona `portadora` haciendo clic en su ficha o con la fila Unidad activa; intenta seleccionar una
  unidad del bando B y observa el panel.
- **Esperado:** se identifica ID/tipo de la unidad seleccionada; solo unidades activas con acciones disponibles pueden
  actuar.
- **Observado:** ______ **Estado:** Pendiente / Aprobado / Fallido.
- **Evidencia:** capturas de unidad seleccionada y mensaje ante selección rival.

### V10 — Movimiento legal, obstáculos y turno

- **Requisito:** R07, R23.
- **Preparación:** fixture en Partida; turno A.
- **Pasos:** con `portadora`, pulsa `(0,2)`. Selecciona `defensa B-1` y pulsa `(3,0)`. Intenta un obstáculo o una celda
  no resaltada antes de continuar.
- **Esperado:** la acción legal avanza un paso y cambia A→B→A. El destino ilegal no mueve unidades, no cambia turno y
  no agrega jugada.
- **Observado:** ______ **Estado:** Pendiente / Aprobado / Fallido.
- **Evidencia:** capturas antes/después y contador de jugadas.

### V11 — Recurso, transporte y victoria

- **Requisito:** R07, R23, R26.
- **Preparación:** continúa la sesión V10.
- **Pasos:** mueve `portadora` a `(0,1)`; `defensa B-1` a `(2,0)`; `portadora` a `(0,0)`.
- **Esperado:** al entrar en `(0,2)`, el recurso pasa a la unidad y deja de verse como objeto libre. Luego acompaña a
  la unidad; al llegar a base A se muestra `victoria_A` y no se permiten más jugadas.
- **Observado:** ______ **Estado:** Pendiente / Aprobado / Fallido.
- **Evidencia:** capturas de recurso libre, portador y victoria; hash de sesión.

### V12 — Historial y verificación de partida

- **Requisito:** R26, R32, R33.
- **Preparación:** partida V11 con cinco acciones aplicadas.
- **Pasos:** pulsa `V — Verificar partida`.
- **Esperado:** el panel muestra las propiedades comprobadas y acepta el historial reconstruido desde estado inicial,
  incluyendo turnos, costos y victoria.
- **Observado:** ______ **Estado:** Pendiente / Aprobado / Fallido.
- **Evidencia:** captura completa del reporte.

### V13 — Reinicio de sesión

- **Requisito:** R07, R26.
- **Preparación:** historial con acciones o estado terminal.
- **Pasos:** pulsa `R` o `R — Reiniciar partida`.
- **Esperado:** regresa al estado inicial preparado y se limpia el historial/reporte de la sesión nueva.
- **Observado:** ______ **Estado:** Pendiente / Aprobado / Fallido.
- **Evidencia:** capturas antes/después y contador de jugadas.

### V14 — Recomendación Minimax y alfa-beta

- **Requisito:** R23, R25, R33.
- **Preparación:** fixture o `decision_adversarial.json`, modo Adversarial.
- **Pasos:** recorre algoritmo con `<`/`>` para Minimax y alfa-beta; establece profundidad y orden; ejecuta con `Q` o
  `Enter`; compara con `C` o `E`.
- **Esperado:** se muestran recomendación y métricas verdaderas; misma profundidad/orden/utilidad produce mismo valor y
  acción bajo el desempate documentado. La evaluación no mueve unidades.
- **Observado:** ______ **Estado:** Pendiente / Aprobado / Fallido.
- **Evidencia:** capturas de ambas ejecuciones y parámetros visibles.

### V15 — Orden y profundidad

- **Requisito:** R23, R25.
- **Preparación:** `recurso_en_transporte.json`, modo Adversarial.
- **Pasos:** compara orden generación, inverso y táctico a profundidad fija; luego cambia profundidad manteniendo orden.
- **Esperado:** el panel refleja cada parámetro, valor y conteo. La poda puede variar por orden; la recomendación puede
  cambiar con profundidad. No se exige una mejora en todos los escenarios.
- **Observado:** ______ **Estado:** Pendiente / Aprobado / Fallido.
- **Evidencia:** captura/registro por combinación.

### V16 — Verificación y aplicación explícita

- **Requisito:** R26, R33.
- **Preparación:** recomendación vigente en modo Adversarial.
- **Pasos:** pulsa `V — Verificar decisión`; luego `A — Aplicar recomendación` dos veces, siguiendo la confirmación del
  panel.
- **Esperado:** primer `A` solicita confirmación; segundo revalida y aplica una sola vez. La verificación reporta
  legalidad; tras aplicar, la recomendación antigua se invalida y el estado cambia a Partida.
- **Observado:** ______ **Estado:** Pendiente / Aprobado / Fallido.
- **Evidencia:** capturas antes/después y contador/historial.

### V17 — Exportación y reproducción

- **Requisito:** R32, R33.
- **Preparación:** partida manual con al menos una acción; repetir como una decisión evaluada después de movimientos.
- **Pasos:** pulsa `J`, guarda el registro y ejecuta el comando de reproducción de la sección de preparación. Registra
  salida/código. Repite una copia alterada solo si se puede conservar el archivo original.
- **Esperado:** replay reproduce estado final, acciones y decisión; una alteración de integridad se rechaza.
- **Observado:** ______ **Estado:** Pendiente / Aprobado / Fallido.
- **Evidencia:** archivo original, SHA-256, salida de consola y captura.

### V18 — Comparación de búsqueda y escenarios

- **Requisito:** R23, R24, R25, R35.
- **Preparación:** `ruta_corta_vs_economica.json`.
- **Pasos:** ejecuta BFS y UCS con mismo inicio/objetivo; ejecuta luego A* con ambas heurísticas en `obstaculo_rodeo.json`.
- **Esperado:** rutas y métricas coinciden con el algoritmo/escenario; BFS puede preferir menos movimientos y UCS
  menor costo. No se mezclan resultados de distintos hashes.
- **Observado:** ______ **Estado:** Pendiente / Aprobado / Fallido.
- **Evidencia:** capturas de rutas, métricas y archivo/hash de escenario.

### V19 — Manejo de selector y errores

- **Requisito:** R23, R35.
- **Preparación:** GUI abierta.
- **Pasos:** abre `O`, cancela; después carga JSON inválido; luego arrastra JSON válido.
- **Esperado:** cancelar no modifica sesión; inválido muestra mensaje y conserva mapa; válido carga sin reiniciar la
  aplicación.
- **Observado:** ______ **Estado:** Pendiente / Aprobado / Fallido.
- **Evidencia:** capturas, archivos y errores exactos.

## Incidencias y firma

| ID | Pasos para repetir | Resultado obtenido | Evidencia / archivo | Responsable |
|---|---|---|---|---|
| | | | | |

Fecha de cierre: ____________________  Revisión por integrante: ____________________

**R35 permanece NO VERIFICABLE hasta que el equipo complete y firme esta lista en escritorio real.** El JSON oficial
del profesor debe anotarse por separado; el fixture del repositorio no lo sustituye.
