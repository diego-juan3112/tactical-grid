# Guion de sustentación de TacticalGrid

## Demostraciones reproducibles

Ejecuta los comandos desde la raíz con el entorno instalado. La evidencia de referencia por caso está en
`casos-minimos.md` y `resultados-casos-minimos.json`; los conteos no deben presentarse como universales.

| Demostración | Escenario / preparación | Comando o secuencia real |
|---|---|---|
| JSON externo | Copia entregada por el docente; conserva su hash original. | `.venv/bin/python main.py --gui /ruta/al/escenario.json`; también `.venv/bin/python main.py --consola /ruta/al/escenario.json --verificar`. |
| BFS frente a DFS | `campo_20x20.json`, unidad/objetivo declarados en `prueba`. | `.venv/bin/python main.py --consola escenarios/campo_20x20.json --algoritmo bfs_dfs --verificar`. |
| BFS frente a UCS | `ruta_corta_vs_economica.json`. | `.venv/bin/python main.py --consola escenarios/ruta_corta_vs_economica.json --algoritmo ambos --verificar`. |
| A* Manhattan/HTO | Mismo escenario, unidad y objetivo. | `.venv/bin/python main.py --consola escenarios/obstaculo_rodeo.json --algoritmo a_estrella --heuristica manhattan --verificar`; repite el mismo comando con `--heuristica hto`. |
| Beam k | `campo_20x20.json`. | `.venv/bin/python main.py --consola escenarios/campo_20x20.json --algoritmo beam --k 1 2 4 8 --verificar`. |
| Partida manual | `prueba_gui_partida.json`, modo `partida`. | `.venv/bin/python main.py --gui escenarios/prueba_gui_partida.json`; realiza la secuencia de las secciones V10 y V11 de `guia-validacion-manual.md`. |
| Recurso y victoria | Mismo fixture; recoge en (0,2), transporta a base A. | Interacción Pygame manual. No existe un flag de consola para enviar acciones humanas paso a paso. |
| Minimax y alfa-beta | `caso_08_minimax_alfa_beta_20x20.json`, profundidad y orden iguales. | `.venv/bin/python main.py --consola escenarios/caso_08_minimax_alfa_beta_20x20.json --modo adversarial --algoritmo minimax_alfa_beta --profundidad 4 --orden generacion --verificar`. |
| Profundidad / orden | `caso_10_profundidad_20x20.json`; variar un parámetro por vez. | Repite con `--profundidad 1`, `2`, `3`, `4`, o con `--orden generacion`, `inverso`, `tactico`. |
| Verificación | Selecciona búsqueda, decisión o historial de partida. | Añade `--verificar` en consola; en GUI pulsa `V`. Para historial: `V — Verificar partida`. |
| Exportación y replay | Búsqueda/decisión inicial por consola o partida GUI. | Búsqueda: añade `--exportar resultado.json`. Sesión manual: pulsa `J` y después `.venv/bin/python main.py --consola --reproducir-registro resultado.tg.json`. |
| Diez casos y variantes académicas | Casos pequeños preservados y variantes adversariales 20 × 20 del registro. | `.venv/bin/python scripts/ejecutar_casos_minimos.py`. |

Para GUI, además de los comandos, mostrar: `M` cambia de modo; `O` abre JSON; `Enter` ejecuta búsqueda o evaluación;
`E` muestra exploración o compara adversarial; `Q` evalúa; `C` compara; `V` verifica; `A` solicita y confirma la
acción; `R` reinicia partida; `N` avanza un turno en la partida controlada por algoritmos; `J` exporta. Los botones del panel
describen los mismos controles.

## Preguntas para defensa técnica

El equipo debe responder con el código, los casos y su comprensión; este guion no atribuye respuestas ni dominio a
integrantes.

1. ¿Qué campos forman `EstadoJuego` y por qué dos tableros con iguales posiciones pueden ser estados distintos?
2. ¿Qué cambia entre la representación estática `Escenario` y el estado dinámico?
3. ¿Cómo se obtiene el costo de una acción y qué sucede si se modifica el costo de un terreno en JSON?
4. ¿Qué garantiza BFS? ¿Por qué DFS puede devolver una ruta larga aunque expanda menos nodos?
5. ¿Qué minimiza UCS y bajo qué supuestos corresponde la complejidad reportada?
6. ¿Qué valores usa Manhattan? ¿Qué cota estima HTO y por qué respeta obstáculos?
7. ¿Qué significa admisibilidad? ¿Qué evidencia del caso 4 es experimental y qué argumento debe sostenerse para una garantía general?
8. ¿Qué limita Beam Search? ¿Puede ampliar k empeorar una solución observada o impedir encontrar una ruta?
9. ¿Cómo se define la utilidad de suma cero? ¿Qué representan los pesos configurables?
10. ¿Quién es MAX en la raíz y qué implica alternar MAX/MIN sin crear capacidades distintas para A y B?
11. ¿Cómo decide alfa-beta qué rama cortar? ¿Por qué el orden de sucesores afecta la cantidad de poda?
12. ¿Qué significa la profundidad y cómo puede el horizonte cambiar la recomendación?
13. ¿Qué mide cada contador de búsqueda y decisión? ¿Por qué nodos podados no equivalen a nodos ahorrados?
14. ¿Cómo verifica el sistema una ruta, una decisión y una partida sin confiar en el resultado del algoritmo?
15. ¿Qué información conserva `tacticalgrid.partida/1` y qué comprueba al reproducir?
16. ¿Por qué evaluación adversarial y aplicación de recomendación son operaciones distintas?
17. ¿Qué responsabilidades pertenecen a escenario, juego, algoritmos, modos e interfaz?
18. ¿Qué herramientas de IA intervinieron y cómo queda registrada esa participación? ¿Qué tareas de revisión y validación siguen siendo responsabilidad del equipo?

## Evidencia a llevar

- JSON exacto usado, hash SHA-256 y modo/algoritmo declarados.
- Registro JSON generado y salida del verificador.
- Capturas de las búsquedas, controles y turnos ejecutados en escritorio.
- Hoja V01–V19 completada; no reemplazar campos observados con resultados esperados.
- Respuestas explicadas por el equipo. La validación académica no se deduce de pruebas automatizadas.
