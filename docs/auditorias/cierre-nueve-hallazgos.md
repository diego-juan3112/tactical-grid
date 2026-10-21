# Cierre de correcciones de los nueve hallazgos

Fecha: 2026-10-20. Se preservaron los cambios locales que existían antes de esta tarea. La auditoría de origen permanece como registro histórico; este documento refleja el estado tras las correcciones y validaciones descritas aquí.

## Matriz de cierre

| ID | Estado anterior | Cambio realizado | Evidencia | Estado actual |
|---|---|---|---|---|
| 1 | Métricas presentes en el código, legibilidad real sin comprobar | Se añadieron pruebas de renderizado que comparan con resultados reales los campos de BFS, DFS, UCS, A* y Beam; se inspeccionaron capturas de GUI existentes | `test_renderizador.py`; capturas `busqueda-metricas.png` y `adversarial-minimax-alfa-beta.png` | CORREGIDO Y VERIFICADO en superficies y capturas de 1400×900; no se reescribió el renderizador |
| 2 | `arquitectura_basica.json` ya corregido | Sin cambios | JSON 20×20, seis IDs únicos, A=3/B=3; prueba de escenarios | RESUELTO Y VERIFICADO; el historial identifica `509f07b`, sin atribuirlo a una persona |
| 3 | Casos 6/7/8/10 solo con mapas pequeños | Se agregaron cinco variantes 20×20, conservando los originales pequeños; se compararon sus resultados y se archivó el registro previo | `test_casos_adversariales_20x20.py`, ejecutor y JSON con hashes/verificaciones | CORREGIDO Y PROBADO bajo el mínimo dimensional del PDF; falta confirmación del profesor sobre si la interpretación anterior permitía fixtures pequeños |
| 4 | Issue #34 abierta; PR #71 fusionado | Verificación GitHub de issue, criterios, PR y merge; no se modificó GitHub | Issue #34 abierta; PR #71 fusionado a `main` el 2026-10-16 19:00 UTC; código y pruebas satisfacen el criterio visible | Implementación completa; cierre administrativo manual recomendado |
| 5 | E11.4 no comprobada | Se consultó issue #38 y se organizó checklist de práctica individual en este cierre | Issue #38 abierta, asignada a `SilvaG35083`, `aisc7` y `diego-juan3112`; guion, diez casos, manual y checklist V01–V19 disponibles | EN CURSO; solo el equipo puede demostrar y registrar las competencias individuales |
| 6 | Documentación incompleta en cuatro métodos | Se documentaron entradas/salidas, errores, complejidad, IA e intervención en los cuatro métodos; se declara que la revisión estudiantil no está acreditada | `test_documentacion_metodos.py` y suite completa | CORREGIDO Y PROBADO; la validación académica del equipo sigue sin acreditarse |
| 7 | README y Word abreviaban dos nombres | README y portadas/texto de documento técnico y manual actualizados con los nombres completos suministrados | Extracción OOXML verifica las dos grafías en los tres entregables; no se alteró autoría Git | IMPLEMENTADO; falta render visual de los DOCX |
| 8 | GUI adversarial presente solo en cambios locales; se reportó retirada | No se cambió funcionalidad; se fortalecieron aserciones de métricas y se inspeccionó captura real de comparación | Pruebas de control/renderizador; `adversarial-minimax-alfa-beta.png`; diff local de GUI | IMPLEMENTADO EN EL WORKSPACE; está sin confirmar en Git. La visualización interna del árbol sigue opcional y no se añadió |
| 9 | Sin diagramas formales | No se alteró el DOCX para agregar diagramas | El PDF no los exige; no se alteró la arquitectura | MEJORA OPCIONAL, NO IMPLEMENTADA |

## Escenarios 20 × 20

Se crearon:

- `caso_06_estado_compuesto_libre_20x20.json`
- `caso_06_estado_compuesto_portador_20x20.json`
- `caso_07_decision_adversarial_20x20.json`
- `caso_08_minimax_alfa_beta_20x20.json`
- `caso_10_profundidad_20x20.json`

Cada uno tiene 20 filas, 20 columnas y tres unidades por bando. Los originales tenían seis unidades (tres por bando) y se conservaron sin cambios. En cada variante se mantuvo la región original transitable y se usaron muros no transitables en la extensión; las pruebas cargan los JSON y comparan acciones, valores, generación/evaluación de nodos y podas frente a los mapas pequeños.

Resultados deterministas de la última ejecución:

| Caso | Resultado 20 × 20 | Verificación |
|---|---|---|
| 6 | Mismas posiciones, estado distinto por portador. Utilidad 4/92. A profundidad 4: A1→(2,3), valor 78, frente a A1→(1,2), valor 96. | Ambas decisiones válidas; equivalencia con casos pequeños en profundidades 1–4 |
| 7 | Prof. 1 toma recurso (A1→(0,2), valor 37); prof. 2–4 elige A3→(2,2), valores −37/37/−39. | Las cuatro decisiones válidas; conteos y selección iguales al mapa pequeño |
| 8 | Prof. 4: ambos eligen A1→(0,3), valor 72. Minimax evalúa 5,238 hojas; alfa-beta 600 y registra 907 ramas podadas. | Ambos reportes válidos; mismo resultado y poda efectiva |
| 10 | Prof. 1–4: valores 74/72/76/72; Minimax evalúa 8/71/582/5,238; alfa-beta 8/31/191/600; cambia la acción entre profundidades. | Ocho decisiones válidas; mismas métricas/decisiones que el mapa pequeño |

Los tiempos de la corrida están en `docs/experimentos/resultados-casos-minimos.json`; son muestras dependientes de la máquina. La corrida registrada antes de agregar las variantes se preservó en `resultados-casos-minimos-antes-variantes-20x20.json`. Los documentos de escenarios, catálogo y casos mínimos describen ambos formatos.

## Interfaz gráfica

La GUI muestra para búsqueda el algoritmo, éxito, longitud, costo, estados generados/expandidos, máximo de frontera y tiempo, y dibuja el camino sobre el tablero. Las pruebas nuevas inspeccionan el valor mostrado contra el objeto de resultado para los cinco algoritmos. Para Minimax/alfa-beta se muestran profundidad, acción, valor, nodos generados/evaluados/podados y tiempo. Las capturas existentes muestran el panel completo y legible a 1400×900; no se hicieron cambios cosméticos.

La GUI adversarial y sus pruebas siguen en modificaciones locales no confirmadas. No se crearon commits ni se modificó el branch. Revisar el conjunto local y elegir la versión de entrega sigue siendo responsabilidad del equipo.

## Git y cambios que ya existían

La rama sigue siendo `main`, HEAD `0097097fcaf83e3ebf10182d7e4d6f4a0e4788dd`. Antes de esta tarea ya existían cambios locales extensos: GUI, modo de partida manual y replay, registro, verificador, README, DOCX, guías, capturas y eliminación de `DESIGN.md` y cinco imágenes de rediseño. No se restauró `DESIGN.md`, no se descartó ni sobrescribió ninguno de esos cambios. Las cinco imágenes didácticas se conservan como eliminaciones locales preexistentes.

En esta tarea se añadieron/editaron código de documentación, cinco escenarios, pruebas, el ejecutor y evidencias/documentación. `git status --short` al final debe revisarse antes de preparar commit, para no mezclar correcciones con cambios anteriores. No se hicieron commit, push, merge ni actualización/cierre de issue.

## GitHub

- **Issue #34, E10.3:** abierta; criterio: resultados accesibles de forma equivalente a la estructura JSON de ejemplo mediante UI, log o exportación, sin exigir archivo. Se comprobó implementación `--json`/`--exportar`, registro de resultados y tests de reproducibilidad. No hay comentarios en issue/PR ni requerimientos pendientes visibles en el texto. **Recomendación:** cerrarla manualmente con comentario cuando el equipo confirme la evidencia.
- **PR #71:** cerrado y fusionado el 16 de octubre de 2026 a las 19:00 UTC en `main`; rama `E10.3-—-Resultados-y-métricas-reproducibles`; merge commit `e3f3155d73be90f54b12592d003b0584d5604f03`. El PR no tiene descripción ni comentarios. Merge del PR no cerró #34.
- **Issue #38, E11.4:** abierta, asignada a los tres integrantes. Criterios son habilidades demostradas individualmente, no documentos ni pruebas automatizadas. No se cerró.

Comentario manual sugerido para #34 tras aprobación del equipo: «E10.3 satisface los criterios mediante salida `--json`, exportación `--exportar` y reproducción de parámetros/resultados; `tests/modos/test_registro.py` verifica la estructura y reproducción en búsqueda, Beam, alfa-beta y partida. La implementación quedó integrada por PR #71 en `main`. Cierro la issue.»

## Checklist E11.4

### Material ya disponible

- `docs/experimentos/guia-sustentacion.md`: demostraciones reproducibles, preguntas y evidencia que deben llevar.
- `docs/experimentos/casos-minimos.md` y `docs/casos-minimos/`: escenarios, resultados esperados/observados y explicación de los diez casos.
- `docs/experimentos/resultados-casos-minimos.json`: salidas, hashes y verificaciones actuales; variantes académicas 20×20 separadas.
- `docs/entregables/manual-de-usuario.docx`, `docs/entregables/documento-tecnico.docx` y PDF de guía rápida.
- `docs/tecnico/guia-validacion-manual.md`: V01–V19, con espacios para observación, estado y evidencia.

### Actividades personales todavía necesarias

- [ ] Cada integrante practica explicar `EstadoJuego`, la separación `Escenario`/estado dinámico y por qué importa portador/turno.
- [ ] Cada integrante ejecuta una búsqueda sobre un JSON externo del profesor y explica el resultado/costo.
- [ ] Cada integrante justifica una heurística y su admisibilidad (incluidos supuestos y límites de la evidencia experimental).
- [ ] Cada integrante explica una decisión Minimax, la utilidad, MAX/MIN bajo reglas iguales y la diferencia entre recomendación y aplicación.
- [ ] Cada integrante predice y luego mide el efecto de cambiar profundidad y orden de acciones.
- [ ] Cada integrante explica complejidad y método documentado, identifica IA declarada y distingue pruebas de validación personal.
- [ ] Cada integrante realiza una modificación pequeña en vivo o ensaya una modificación equivalente.
- [ ] El equipo completa V01–V19 en escritorio con capturas y resultados observados; no marcar aprobados por valores esperados.
- [ ] El equipo compara hash del commit/escenarios/documentos de la entrega y lleva los registros que reproducen esa misma versión.

Las pruebas aprobadas, las capturas y esta lista no demuestran por sí solas que un integrante domine el código; se requiere práctica y evidencia individual.

## Mejoras opcionales no implementadas

- **Árbol/ramas Minimax:** ayudaría a explicar alternativas y cortes, más allá de la recomendación y métricas actuales. Eleva riesgo de rendimiento, saturación del panel y complejidad de instrumentación; no hay una estimación fiable sin alcance visual definido. Aporte de sustentación moderado, sin requisito mínimo del PDF.
- **Diagramas Word:** podrían resumir arquitectura, ciclo de partida, búsqueda y árbol adversarial. Riesgo bajo en código, riesgo de mantenimiento/inconsistencia documental moderado. El tiempo depende de diseño y renderizado del documento y no se puede estimar con evidencia local; no son exigidos.

## Validación y límites

- Python 3.12.3. Base anterior: 974 pruebas aprobadas.
- Pruebas focales finales: `136 passed in 16.69s` (`tests/test_documentacion_metodos.py`, pruebas de renderizador/control y variantes adversariales 20×20).
- Regresión completa: `1011 passed in 37.98s`, sin fallos ni errores; el aumento respecto de la base de 974 corresponde a pruebas añadidas en el workspace.
- `scripts/ejecutar_casos_minimos.py` se ejecutó dos veces y terminó correctamente: diez casos pequeños preservados y cuatro grupos de variantes 20×20. Cada ejecución comprueba decisiones/resultados y genera verificaciones e identificadores SHA-256 en el JSON. Los tiempos son mediciones variables, no un criterio de igualdad reproducible.
- `git diff --check`: sin errores.
- `unzip -t` confirmó la integridad estructural de ambos DOCX.
- Las capturas existentes de búsqueda/adversarial fueron inspeccionadas. No se añadió screenshot en esta tarea.
- El render DOCX vía `render_docx.py` no pudo empezar: el `.venv` no tiene `pdf2image` (`ModuleNotFoundError`). OOXML de los dos DOCX fue comprobado y los nombres están; su revisión visual sigue pendiente.
- GitHub se verificó mediante el conector vinculado, sin writes. La API `gh` local continúa sin autenticación válida; no se expuso ni usó su token.
- No existe respuesta del profesor sobre los casos didácticos pequeños. Aunque ahora hay variantes 20×20 comprobadas, no se atribuye autorización retroactiva.
