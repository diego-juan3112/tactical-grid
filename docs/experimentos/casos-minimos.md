# Informe de ejecución de los diez casos mínimos

Fecha de ejecución: 2026-10-20. Se ejecutó `scripts/ejecutar_casos_minimos.py` con Python 3.12.3. El registro crudo
[`resultados-casos-minimos.json`](resultados-casos-minimos.json) conserva hashes SHA-256 de cada JSON, parámetros,
caminos/acciones, métricas y comprobaciones de `verificar_busqueda` o `verificar_decision`, incluidos los agregados
20 × 20. El registro anterior a estas variantes se preserva en
[`resultados-casos-minimos-antes-variantes-20x20.json`](resultados-casos-minimos-antes-variantes-20x20.json).
Las tablas resumen cifras deterministas y muestras de tiempos.

## Resultados

| Caso | JSON y parámetros | Resultado observado | Verificación |
|---|---|---|---|
| 1. BFS vs. DFS | `campo_20x20.json`; unidad/objetivo de `prueba` | BFS: 16 pasos, costo 45, 205 generados, 186 expandidos, frontera 20. DFS: 98 pasos, costo 283, 206 generados, 102 expandidos, frontera 104. | Ambos válidos |
| 2. Corto vs. económico | `ruta_corta_vs_economica.json`; parámetros de `prueba` | BFS: 8 pasos, costo 50. UCS: 12 pasos, costo 12. | Ambos válidos |
| 3. Obstáculo | `obstaculo_rodeo.json`; A* Manhattan y UCS | La ruta rodea la barrera: 15 pasos, costo 16 en ambos. | Ambos válidos; costo coincide |
| 4. Heurísticas | Mismo JSON y problema; A* Manhattan, A* HTO, UCS | Manhattan: 40 generados/33 expandidos/frontera 7. HTO: 38/26/frontera 12. UCS: 41/39/frontera 7. Las tres rutas cuestan 16 y miden 15 pasos. | Las tres válidas; UCS confirma costo óptimo |
| 5. Beam Search | `campo_20x20.json`; k=1,2,4,8 | k=1: sin solución, 74 expandidos. k=2: sin solución, 137. k=4: 34 pasos, costo 40, 133 expandidos. k=8: 36 pasos, costo 46, 276 expandidos. | Los cuatro reportes válidos, incluso las salidas sin solución |
| 6. Estado compuesto | `estado_compuesto_libre.json` y `estado_compuesto_portador.json`; alfa-beta profundidad 4 | Las seis posiciones unitarias son iguales, pero el estado y su huella difieren. Utilidad inicial: 4 vs. 92. Decisiones: A1→(2,3), valor 78; frente a A1→(1,2), valor 96. | Ambas decisiones válidas |
| 7. Decisión adversarial | `decision_adversarial.json`; Minimax, profundidades 1–4 | Prof. 1: A1→(0,2), recoge el recurso, valor 37. Prof. 2–4: A3→(2,2); valores −37, 37, −39. | Las cuatro decisiones válidas |
| 8. Minimax vs. alfa-beta | `recurso_en_transporte.json`; profundidad 4, orden `generacion` | Ambos eligen A1→(0,3), valor 72. Minimax 5900 generados/5238 evaluados. Alfa-beta 787/600, 907 ramas podadas. | Ambos reportes válidos; la equivalencia se confirmó |
| 9. Orden de acciones | Profundidad 4; los tres órdenes en dos escenarios | En `recurso_en_transporte`: evaluados 600/721/428 (generación/inverso/táctico), podados 907/1115/843; valor 72. En `campo_20x20`: evaluados 569/1570/465, podados 1358/1825/1150; valor −36. | Seis decisiones válidas; valor conservado por escenario |
| 10. Profundidad | `recurso_en_transporte.json`; Minimax y alfa-beta, prof. 1–4 | Ambos coinciden por profundidad. Valores: 74, 72, 76, 72. Minimax evalúa 8, 71, 582, 5238 hojas; alfa-beta 8, 31, 191, 600. La acción cambia entre profundidades. | Ocho decisiones válidas |

## Variantes académicas 20 × 20

Los cinco archivos `caso_06...20x20.json` a `caso_10...20x20.json` conservan la región transitable original y cierran
la extensión con muros. `tests/algoritmos/test_casos_adversariales_20x20.py` compara las ejecuciones pequeñas y grandes
por estado, acciones, valores y contadores. Las verificaciones del registro son válidas en todas las decisiones.

| Caso | Evidencia de ejecución 20 × 20 | Verificación |
|---|---|---|
| 6. Estado compuesto | Posiciones unitarias iguales; utilidad 4 frente a 92; decisiones a profundidad 4: A1→(2,3), valor 78 (377 evaluados), y A1→(1,2), valor 96 (136 evaluados). | Dos decisiones válidas; huellas/estados distintos. |
| 7. Decisión adversarial | Profundidad 1: A1 recoge en (0,2), valor 37. Profundidades 2–4: A3→(2,2), valores −37/37/−39; evaluados 6/16/44. | Cuatro decisiones válidas. |
| 8. Minimax vs. alfa-beta | Profundidad 4: misma acción A1→(0,3), valor 72. Minimax evalúa 5,238 nodos; alfa-beta 600 y poda 907 ramas. Tiempos de muestra: 0.569 s y 0.066 s. | Ambos reportes válidos; la comparación confirma acción/valor iguales. |
| 10. Profundidad | Valores 74/72/76/72 en profundidades 1–4; Minimax evalúa 8/71/582/5,238; alfa-beta 8/31/191/600. Cambia la acción entre niveles. | Ocho reportes válidos. |

La comparación por profundidad en una sola ejecución registró, en segundos, Minimax/alfa-beta: d1 0.0012/0.0012,
d2 0.0075/0.0038, d3 0.0606/0.0225, d4 0.5696/0.0818. Son muestras de esta máquina, no estimaciones
estadísticas. Los conteos, acciones y valores coinciden con los mapas pequeños porque las celdas añadidas son muros;
los tamaños de mapa reportados sí son 20 × 20. Las variantes nuevas incluyen tres unidades por bando y carga validada.

El archivo de registro incluye SHA-256, configuración, métricas y comprobación de acciones/estados para cada corrida.
La ejecución repetida debe conservar esas propiedades y los conteos deterministas; los tiempos cambian.

## Interpretación técnica

1. BFS conserva la garantía de menor número de movimientos; DFS devuelve su primer camino conforme al orden de
   sucesores, que en este mapa tiene 98 pasos. Menos expansiones de DFS no significan una ruta mejor.
2. BFS optimiza longitud, mientras UCS optimiza suma de costos: el camino de UCS es cuatro movimientos más largo,
   pero cuesta 12 frente a 50.
3. La distancia Manhattan inicial del caso 3 es 3, pero un muro bloquea el descenso directo. La ruta real necesita
   15 transiciones; por tanto, proximidad geométrica no implica transitabilidad.
4. HTO usa distancias por terreno transitable y respeta muros. Aquí expande siete estados menos que Manhattan, pero
   su máximo de frontera aumenta de 7 a 12. Los resultados respaldan la admisibilidad para este problema y se apoyan
   en la definición/cota de la heurística documentada en `docs/tecnico/03-heuristica-hto.md`; un solo escenario no
   constituye demostración general.
5. Beam recorta alternativas: k=1 y k=2 descartan la ruta que permitiría resolver el caso. k=4 sí llega; elevar a
   k=8 no garantiza menor costo ni longitud: en esta corrida entrega 46/36 frente a 40/34 con k=4.
6. Las posiciones no bastan para identificar el estado: portador y posición del recurso cambian la igualdad, huella,
   utilidad y decisión.
7. Al mirar solo una jugada, Minimax recoge el recurso. Con más profundidad ve respuestas del adversario y cambia a
   la acción de A3. Los valores impares/paridad no son una tendencia monotónica de utilidad.
8. Alfa-beta preserva la acción y valor de Minimax con igual profundidad/orden/desempate. El ahorro observado fue de
   88.5 % de hojas evaluadas. Las 907 podas cuentan ramas, no nodos evitados.
9. Cambiar el orden conserva el valor óptimo, pero altera la búsqueda y, ante empate, la acción elegida. `tactico`
   evaluó menos hojas en ambos escenarios; no se generaliza esa ventaja a todos los mapas.
10. Aumentar profundidad amplía trabajo y puede cambiar la recomendación. El conteo crece de 8 a 5238 hojas en
    Minimax entre profundidad 1 y 4; alfa-beta reduce el último conteo a 600.

## Condiciones y límites de la medición

- Los conteos, caminos y decisiones se registraron desde objetos de resultados reales; las verificaciones reconstruyen
  transiciones con reglas de dominio. No se usaron cifras fabricadas ni resultados de pruebas como sustituto de la
  ejecución.
- Los tiempos son una única muestra por ejecución en este equipo y dependen de sistema, carga y versión de Python.
  No son estimaciones de rendimiento estadístico. El registro JSON conserva los tiempos capturados.
- La semilla no aplica: los algoritmos ejecutados son deterministas y no usan aleatoriedad.
- Caso 6: la utilidad inicial con portador es 92, como reporta la explicación del estado compuesto. El valor 96 es
  el resultado Minimax de la raíz a profundidad 4, una magnitud distinta de la utilidad del estado inicial.
- Caso 7 no demuestra que siempre sea malo recoger el recurso; demuestra la respuesta de este escenario concreto.

## Reproducción

Desde la raíz, instalar el entorno indicado por `AGENTS.md` y ejecutar:

```bash
.venv/bin/python scripts/ejecutar_casos_minimos.py
.venv/bin/python -m pytest tests/algoritmos/test_casos_minimos_adversariales.py tests/algoritmos/test_caso_minimo_1.py tests/algoritmos/test_caso_minimo_5.py tests/algoritmos/test_casos_minimos_heuristicas.py
```

El primer comando ejecuta cada estrategia, calcula hashes, invoca el verificador y reemplaza el archivo crudo. Para
repetir un registro de partida manual exportado desde la GUI:

```bash
.venv/bin/python main.py --consola --reproducir-registro ruta/al/registro.tg.json
```

**Uso de IA:** Sí. Codex creó el ejecutor `scripts/ejecutar_casos_minimos.py` y este informe. **Validación del
estudiante:** el registro contiene verificaciones automáticas reales; la revisión y aprobación del equipo no constan en
este documento.
