# Auditoría de nueve hallazgos — TacticalGrid

Fecha: 2026-10-20. Alcance: nueve hallazgos indicados por el equipo; sin cambios funcionales. El estado evaluado incluye el árbol de trabajo local, no solo HEAD.

## Línea base y matriz

- **Recuento:** 3 hallazgos abiertos en el workspace (#1 parcial, #3 confirmado, #6 parcial); 1 resuelto (#2); 1 reporte desactualizado (#8); 2 mejoras opcionales (#7, #9); 2 no verificables (#4, #5). El #3 además requiere aclaración del profesor sobre el alcance de “mapas de desarrollo”; mientras no exista respuesta, se mantiene incumplimiento bajo la lectura literal.
- Rama `main`, HEAD `0097097fcaf83e3ebf10182d7e4d6f4a0e4788dd` (PR #78 integrado). `git status --short` mostró cambios locales amplios, entre ellos GUI, pruebas, documentos Word y README. Los cambios locales son evidencia del estado del workspace, pero no están confirmados ni publicados.
- Suite: **974 passed in 38.26s**, Python 3.12.3. Ejecutor de casos: **10 experimentos registrados** en `docs/experimentos/resultados-casos-minimos.json`.
- No existía `docs/auditorias/`. El PDF consultado es `docs/enunciado/primer-proyecto.pdf`, páginas 2–10.
- GitHub no fue consultable: `gh auth status` informa que el token de `aisc7` es inválido y la conexión a `api.github.com` falla.

| ID | Hallazgo | Clasificación | Evidencia | Fuente PDF/GitHub | Riesgo | Acción |
|---|---|---|---|---|---|---|
| 1 | Métricas GUI | INCUMPLIMIENTO PARCIAL | Código y pruebas en árbol local; falta comprobación en ventana real | PDF pp. 3, 7 | Medio: legibilidad y versión entregada | Completar revisión manual de escritorio y conservar captura |
| 2 | `arquitectura_basica.json` | RESUELTO Y VERIFICADO | 20×20, A=3/B=3, carga y validación automatizada | PDF pp. 2–3; commit `509f07b` | Bajo | Ninguna en el archivo actual |
| 3 | Casos adversariales pequeños | INCUMPLIMIENTO CONFIRMADO | Casos 6/7/8/10 usan 5×5/3×6/6×8/6×8 | PDF p. 2 | Alto: lectura literal del requisito de desarrollo | Consultar al profesor; preparar escenarios 20×20 si no autoriza excepción |
| 4 | Issue E10.3 #34 / PR #71 | NO VERIFICABLE | Merge del PR consta en Git; estado y aceptación de issue no accesibles | Git local; GitHub sin acceso | Medio: gestión del backlog | Consultar issue y cerrar manualmente solo tras cotejar criterios |
| 5 | Historia E11.4 | NO VERIFICABLE | Hay guion y checklist local; issue, asignaciones y backlog no accesibles | GitHub sin acceso | Alto para preparación individual | Verificar tablero y asignar demostraciones por integrante |
| 6 | Documentación de cuatro métodos | INCUMPLIMIENTO PARCIAL | `_costo`, `_leer_objetivo`, `_leer_algoritmo` carecen de docstring ingenieril; `comando` tiene docstring breve | PDF pp. 8–9 | Alto: requisito obligatorio en lógica relevante | Documentar los tres métodos relevantes y evaluar si `comando` requiere los siete elementos |
| 7 | Nombres completos en README | MEJORA OPCIONAL | README identifica tres personas; dos nombres no están en forma completa suministrada | PDF p. 10 solo exige nombres | Bajo | Actualizar precisión solo con validación de identidad; no inventar tercer nombre |
| 8 | Minimax en GUI | INFORMACIÓN DESACTUALIZADA | Implementación local y pruebas existen; ausente en HEAD; visualización de árbol no aparece | PDF pp. 4–7 | Medio: riesgo de presentar versión sin cambios locales | Integrar/confirmar cambios y hacer prueba manual; no se exige dibujar árbol |
| 9 | Diagramas DOCX | MEJORA OPCIONAL | DOCX carece de imágenes, formas y gráficos incrustados; no se identificó requisito explícito de diagrama | PDF pp. 9–10 | Bajo | Añadir diagramas solo como mejora y cotejarlos con la arquitectura real |

## Hallazgo 1 — Métricas de búsqueda en la GUI

### Evidencia del código

En el workspace actual, `src/tacticalgrid/interfaz/renderizador.py:786-841` presenta algoritmo, éxito, longitud, costo, estados generados/expandidos, máximo de frontera, tiempo y leyenda del camino. El camino se dibuja en la cuadrícula en `renderizador.py:374-375`. `control.py` mantiene resultados y los invalida al cambiar selección/configuración o cargar escenario; `tests/interfaz/test_control.py` cubre invalidación y carga. Los cinco algoritmos BFS, DFS, UCS, A* y Beam usan el camino de renderizado compartido.

### Evidencia de ejecución

`tests/interfaz/test_renderizador.py::test_panel_muestra_metricas_completas_de_busqueda_y_comparacion` observa los textos de las métricas sobre una superficie Pygame. Pruebas parametrizadas inspeccionan camino para BFS, DFS, UCS, A* y Beam. La prueba completa pasa. Las métricas vienen de `ResultadoBusqueda` almacenado. El registro de casos ejecutado también obtuvo, por ejemplo, BFS en `campo_20x20.json`: 205 generados, 186 expandidos, frontera 20, longitud 16, costo 45.

Minimax/alfa-beta muestra acción, valor, profundidad configurada/alcanzada, nodos generados/evaluados/podados y tiempo mediante `_lineas_decision` en `renderizador.py:97-174`; las pruebas adversariales de control/renderizador cubren proyección y comparación.

### Interpretación del PDF

P. 3 enumera para búsqueda las métricas exigidas. P. 5 enumera métricas de Minimax/alfa-beta. P. 7 requiere visualizar el camino encontrado y establece como mínimo entidades/turno. Observar estados explorados/fronteras/decisiones se valora como extra.

### Conclusión

El reporte de que faltan esos campos está desactualizado para el árbol de trabajo actual. No puedo confirmar legibilidad en la ventana real: `docs/tecnico/guia-validacion-manual.md` deja V01 y V06 pendientes y explica que SDL dummy no sustituye esa revisión. Tampoco queda verificado que el nuevo GUI esté en el commit que se entregará: `control.py`, `renderizador.py` y sus pruebas tienen cambios locales.

### Acción recomendada / criterio de aceptación

Completar V01/V06 con captura de escritorio y revisar todos los renglones a la resolución usada. Aceptar cuando las métricas estén legibles, se correspondan con el resultado ejecutado y el camino se vea para los cinco algoritmos; cambiar de algoritmo/escenario debe retirar resultados anteriores.

## Hallazgo 2 — `arquitectura_basica.json`

### Evidencia del código

`escenarios/arquitectura_basica.json` define mapa 20×20 y seis unidades; recuento JSON: A=3, B=3. IDs son únicos en el archivo. Las posiciones están dentro de 0–19; el mapa es todo terreno `camino` transitable. El escenario carga durante `tests/escenario/test_escenarios_propios.py`.

### Evidencia de ejecución / Git

`python` no está instalado en el shell, pero `.venv/bin/python scripts/ejecutar_casos_minimos.py` completó los casos y la suite pasó. `git log -- escenarios/arquitectura_basica.json` identifica el cambio `509f07b` («completa tres unidades por bando»); el commit está en el historial. Esto no prueba autoría personal de Juan Diego. La carga/selectabilidad general de unidades se prueba en GUI, pero no encontré una prueba dedicada de seleccionar las seis unidades de este JSON en ventana real.

Escenarios principales catalogados: `campo_20x20.json` y `arquitectura_basica.json` son 20×20 y ambos tienen tres unidades por bando. Los mapas pequeños enumerados en la sección de escenarios son casos experimentales/fixtures. `ejemplo_enunciado.json` es 4×4 y solo ilustra el formato del PDF.

### Interpretación del PDF

P. 2 pide mínimo 20×20 en mapas utilizados durante el desarrollo; p. 3 pide al menos tres unidades por bando. La aplicación debe aceptar dimensiones válidas externas.

### Conclusión

El estado actual de `arquitectura_basica.json` cumple y es consistente con el historial visible. No se infiere autoría individual del commit.

### Acción recomendada / criterio de aceptación

Sin cambio necesario. Aceptación ya demostrada por estructura, carga y pruebas de escenarios.

## Hallazgo 3 — Casos adversariales en mapas pequeños

### Evidencia del código y ejecución

`docs/casos-minimos/casos-6-10-adversariales.md` y sus JSON asignan: caso 6 `estado_compuesto_{libre,portador}.json` (5×5), caso 7 `decision_adversarial.json` (3×6), caso 8 `recurso_en_transporte.json` (6×8), caso 9 `recurso_en_transporte.json` y `campo_20x20.json`, caso 10 `recurso_en_transporte.json` (6×8). Los cinco demostraron los objetivos declarados según los registros y verificadores actuales. `scripts/ejecutar_casos_minimos.py` se ejecutó y escribió diez resultados; la suite completa pasó. El script verifica decisiones/rutas legales y métricas, no sustituye la interpretación del requisito de tamaño.

Casos 6–10 actuales: caso 6 distingue el estado por portador y cambia utilidad/decisión; caso 7 a profundidad 1 recoge, y a 2–4 evita la respuesta de interceptación; caso 8 ambos algoritmos escogen el mismo movimiento/valor y alfa-beta evalúa menos hojas; caso 9 el orden cambia las podas; caso 10 cambiar profundidad altera conteos/decisión. Resultados exactos y hashes están en `docs/experimentos/resultados-casos-minimos.json` y resumen en `docs/experimentos/casos-minimos.md`.

### Interpretación del PDF

P. 2 dice literalmente que «los mapas utilizados durante el desarrollo» deben tener al menos 20×20 y que la aplicación admitirá otras dimensiones válidas suministradas externamente. No dispone una excepción explícita para experimentos didácticos. El ejemplo JSON 4×4 del mismo PDF y la aceptación de escenarios externos prueban que el formato no está restringido a 20×20; no dicen expresamente que los mapas pequeños internos de los casos mínimos estén exentos.

### Conclusión y alternativas

La lectura literal incluye escenarios experimentales, por lo que su uso actual es un incumplimiento. La intención de la norma respecto de fixtures didácticos requiere aclaración del profesor; no se presume autorización.

- **A, conservar casos pequeños:** facilita inspección manual y hace visibles las decisiones/ramas; conserva los resultados reproducibles actuales. Mantiene riesgo académico mientras no exista respuesta del profesor.
- **B, equivalentes 20×20:** es viable en principio colocando la configuración táctica en una región y aislando el resto con obstáculos, pero no se puede garantizar equivalencia sin construir y volver a ejecutar los mapas. Mayor espacio puede aumentar branching/nodos exponencialmente según profundidad; los valores de utilidad pueden variar por rutas/costos alcanzables y las métricas seguramente cambiarían. Requeriría actualizar JSON, hashes, registros, tests y documentos de resultados. No se implementó.

### Pregunta sugerida al profesor

«El enunciado pide mapas de desarrollo de al menos 20×20 y también incluye un ejemplo JSON de 4×4 y exige admitir dimensiones externas. ¿Los mapas pequeños usados únicamente para demostrar casos mínimos didácticos (6, 7, 8 y 10) están permitidos como fixtures, o esos casos también deben ejecutarse en escenarios de al menos 20×20?»

### Acción recomendada / criterio de aceptación

Obtener respuesta documentada. Si no hay excepción, construir equivalentes 20×20 y repetir mediciones. Aceptar con evidencia de dimensiones, objetivo del caso, propiedad reproducida y verificación para cada experimento.

## Hallazgo 4 — E10.3 #34 / PR #71

### Evidencia del código/GitHub

Git identifica `e3f3155` como merge de `#71` («E10.3 — Resultados y métricas reproducibles») a `main`, fechado 2026-10-16. El commit incluye implementación de registro, parámetros, resultados, verificación, pruebas y cambios de `AGENTS.md`/README. El código de `RegistroExperimento.comando` y exportación está presente; pruebas `tests/modos/test_registro.py` pasan.

No se pudo consultar título, estado actual, cuerpo/criterios de #34, detalle real del PR en GitHub, rama/base/fecha de merge desde la API, enlace de cierre automático, comentarios ni tareas pendientes fuera del merge. El título del branch/merge no reemplaza esos datos.

### Interpretación y conclusión

La implementación de registro de experimentos que corresponde a E10.3 está integrada en Git. El estado administrativo de issue #34 es **NO VERIFICABLE**; un merge no prueba por sí solo que todos sus criterios estén completos ni que la issue siga abierta/cerrada.

### Acción recomendada / criterio de aceptación

Al recuperar acceso, cotejar criterios de #34 con PR #71 y probar cada criterio; cerrar solo si están satisfechos. Comentario sugerido si se confirma: «E10.3 quedó implementada e integrada por PR #71 (merge a main). Se verificaron los criterios mediante [pruebas/artefactos concretos]. Cierro la issue; no quedan tareas de alcance pendientes.» No usarlo antes del cotejo.

## Hallazgo 5 — E11.4 / sustentación

### Evidencia disponible

Sí existen `docs/experimentos/guia-sustentacion.md`, `docs/experimentos/casos-minimos.md`, `docs/experimentos/resultados-casos-minimos.json` y `docs/tecnico/guia-validacion-manual.md`. README enlaza al guion y a los diez casos. La guía de escritorio deja pruebas V01–V19 para completar por una persona; recomienda capturas, JSON externo del profesor, resolución y hashes. El informe indica que la revisión/validación estudiantil no puede confirmarse.

### Datos no verificables

No se pudo consultar si existe E11.4, su descripción literal, asignaciones, criterios, si es la única historia abierta, tareas por integrante ni entregables de backlog pendientes. La evidencia local no sustituye el estado del tablero. No hay sustento para declarar que los tres integrantes tienen asignaciones actuales o que dominan el código.

### Checklist verificable

- [ ] Consultar E11.4 y backlog; registrar criterios, asignaciones y otras historias abiertas.
- [ ] Completar V01–V19 en una GUI de escritorio; guardar capturas y resultados observados.
- [ ] Ejecutar casos mínimos y conservar registro/hash del estado que se sustentará.
- [ ] Ejecutar escenario externo del profesor si fue entregado; conservar hash y comando.
- [ ] Cada integrante explica estado, costos/heurística, Minimax/utilidad, métricas y uso de IA; registrar quién demuestra cada punto.
- [ ] Practicar una modificación pequeña por integrante y explicar su efecto; las pruebas aprobadas no demuestran dominio individual.
- [ ] Confirmar que código y documentos pertenecen al mismo commit de entrega.

### Acción recomendada / criterio de aceptación

Recuperar el issue tracker y asignar responsables concretos. Aceptar E11.4 solo con criterios del issue completados y evidencia individual/manual registrada.

## Hallazgo 6 — Documentación de métodos

### Evidencia del código

| Método | Estado documental / relevancia | Elementos pendientes y recomendación |
|---|---|---|
| `EvaluadorUtilidad._costo` — `src/tacticalgrid/algoritmos/utilidad.py:183` | Sin docstring. Relevante: cálculo de distancias con costos y tratamiento de inalcanzable. | Los siete elementos. Complejidad debe distinguir cache hit O(1), miss en `_costos_hacia` (cálculo de distancias sobre el mapa) y fallback `max(mapa.values())` O(V). Precisar el sentinel `max + 1`, escenario y precondiciones. Prioridad alta. |
| `_leer_objetivo` — `src/tacticalgrid/modos/prueba.py:142` | Sin docstring. Parser/validador de configuración de objetivo, no valida límites del mapa; lógica relevante por contrato JSON. | Siete elementos; devolver `None` o `Posicion` de enteros y `ValueError` para estructura/tipos inválidos. Complejidad O(1) por dos campos. Señalar que los bool se rechazan como int. Prioridad media-alta. |
| `_leer_algoritmo` — `src/tacticalgrid/modos/prueba.py:155` | Sin docstring. Valida algoritmo permitido según modo. | Siete elementos; reconocer `None`, permitir miembro de `_ALGORITMOS_JSON[modo]`, si no lanzar `ValueError`. O(1) por tuplas acotadas. Prioridad media-alta. |
| `RegistroExperimento.comando` — `src/tacticalgrid/modos/registro.py:87` | Docstring de una frase, sin siete elementos. Relevante para reproducibilidad, aunque compone argumentos de forma directa. | Documentar salida reproducible y quoting con `shlex.join`; complejidad O(P + longitud serializada), P parámetros/opciones. Considerar `self.archivo` y parámetros como precondición. Prioridad media. |

En `a_diccionario` y `desglosar` hay documentación más amplia, pero no implica que estos cuatro métodos hereden esa cobertura. No se afirma validación estudiantil adicional; las pruebas automatizadas ejercitan contratos generales, no avalan revisión personal. `tests/test_documentacion_metodos.py` pasa, pero no obliga a que todos estos métodos tengan documentación semánticamente completa.

### Interpretación del PDF / conclusión

P. 8 exige siete elementos en español equivalentes a Purpose, Preconditions, Postconditions, Complexity, AI usage, AI intervention y Student validation para métodos de lógica relevante; enumera expresamente costos y validadores. El repo fija las etiquetas españolas en `AGENTS.md`. `_costo` y ambos lectores son relevantes. `comando` es más discutible por ser serialización de argumentos, pero su responsabilidad afecta la reproducción y merece documentación completa o una justificación explícita de trivialidad; no es trivial por debajo del umbral declarado (<8 líneas totales).

### Acción recomendada / criterio de aceptación

Actualizar docstrings junto con los métodos si se modifican. Declarar IA con veracidad y no declarar validación estudiantil no ocurrida. Aceptar con revisión semántica de complejidad/pre y postcondiciones, y prueba que respalde cualquier validación afirmada.

## Hallazgo 7 — Nombres del equipo

### Evidencia

README lista Juan Diego Henao Quintero, Ana Suárez y Santiago Silva. Los dos documentos Word contienen los mismos nombres abreviados para Ana y Santiago; ambos incluyen Juan Diego Henao Quintero. Los nombres completos proporcionados por el equipo —Ana Isabella Suárez Cardona y Santiago Silva Guarnizo— no aparecen en README ni en los DOCX. No aparece guion con lista de integrantes. No se infiere el nombre completo de Juan Diego más allá de lo ya publicado.

### Interpretación del PDF / conclusión

P. 10 exige que README incluya como mínimo los nombres de integrantes, no dice literalmente que deban aparecer nombres legales completos. El README sí identifica tres integrantes, por lo que no es incumplimiento explícito; es una mejora de precisión y coherencia documental frente a los datos suministrados. No puedo autenticar los nombres suministrados con evidencia independiente.

### Acción recomendada / criterio de aceptación

Con validación del equipo, sincronizar los nombres elegidos en README, portadas de ambos DOCX y cualquier guion que los incluya. No tocar créditos de commits ni atribución histórica. Aceptar cuando las grafías coincidan y el tercer nombre esté confirmado por el equipo.

## Hallazgo 8 — Minimax en GUI

### Evidencia del código y pruebas

El HEAD `0097097` no incluye las adiciones locales actuales a GUI. En el árbol de trabajo, `ControlGrafico` reconoce modo adversarial, selecciona Minimax/alfa-beta, ajusta profundidad/orden, evalúa y compara, verifica y permite aplicar con confirmación; véase `src/tacticalgrid/interfaz/control.py:452-550,709+`. `aplicacion.py:151-167,245-259` conecta teclado/botones. `renderizador.py:1016-1026,1083-1094` ofrece evaluar, comparar, verificar, aplicar y presentar recomendación/métricas. Pruebas `test_control.py` cubren evaluación, no mutación, comparación y aplicación explícita; `test_renderizador.py` verifica textos de métricas.

La GUI no dibuja ramas/alternativas/estados evaluados del árbol. Existe una cadena residual inalcanzable en `renderizador.py:1027-1028` que afirma que el modo se integrará en la fase siguiente; los modos válidos tienen rama adversarial previa, pero es evidencia de texto obsoleto. No se encontró en GUI visualización de “acciones consideradas” aparte de recomendación y métricas.

### Interpretación del PDF / conclusión

Pp. 4–5 exigen Minimax y alfa-beta, profundidad configurable y métricas. P. 7 valora visualizar decisiones consideradas; no exige dibujar árbol, ramas o frontera adversarial. Así, la integración funcional está presente en el workspace, pero está sin confirmar y no se verificó en ventana. El informe de que desapareció por completo está desactualizado para este workspace; con respecto a HEAD, aún no forma parte de la versión registrada. Se retiró/ausentó la visualización adicional de árbol, que no es requisito mínimo.

### Acción recomendada / criterio de aceptación

No restaurar árbol durante esta auditoría. Antes de entregar, revisar el diff y decidir su integración; ejecutar ambos algoritmos en ventana, cambiar profundidad, comparar, verificar y aplicar explícitamente. Priorizar legibilidad del panel; documentar visualización del árbol como opcional. Retirar la indicación de fase siguiente si se confirma como residuo en la corrección posterior.

## Hallazgo 9 — Diagramas en documento técnico

### Evidencia del DOCX

Inspección de `word/document.xml` y ZIP de `docs/entregables/documento-tecnico.docx`: cero elementos multimedia, cero imágenes en línea/ancladas, cero formas y cero objetos gráficos. El texto sí contiene una figura/diagrama ASCII o textual (las figuras referidas no prueban un diagrama arquitectónico formal); no hay imágenes incrustadas. No se modificó el DOCX.

### Interpretación del PDF / conclusión

Pp. 9–10 enumera contenido obligatorio del documento técnico (modelo, estados, reglas, costos, heurísticas, utilidad, experimentos, complejidad, limitaciones e IA), sin exigir diagramas. La ausencia de diagramas no es incumplimiento explícito.

### Propuestas y ubicación

| Diagrama | Beneficio / prioridad | Ubicación sugerida |
|---|---|---|
| Arquitectura JSON→validación→Escenario/EstadoJuego→algoritmos→resultado→GUI | Explica capas e interfaces reales; P2. | Después del capítulo de arquitectura/modelado. |
| Ciclo de partida selección→validación→acción→transición→turno/victoria | Resume autoridad de reglas; P2. | Después de reglas del juego. |
| Flujo de búsqueda frontera→expansión→objetivo→camino/verificación | Apoya instrumentación y resultados; P2. | Antes del capítulo de algoritmos de búsqueda. |
| Árbol Minimax MAX/MIN con corte alfa-beta | Aclara poda y profundidad; P2 para explicación. | Capítulo de decisión adversarial. No es visualización interactiva exigida. |

### Acción recomendada / criterio de aceptación

Opcional; si se incorporan, validar cada flecha contra dependencias reales del repo (en particular, algoritmos no deben leer JSON ni depender de GUI) y sincronizar Word sin alterar arquitectura.

## Verificación cruzada y prioridades

- GUI adversarial, casos 6–10 y documentación/informes nuevos aparecen en el estado local pero no necesariamente en HEAD. El workspace incluye cambios no confirmados en `README.md`, ambos DOCX, GUI, pruebas y documentación; el informe no certifica esos archivos como versión final.
- La salida reciente de `scripts/ejecutar_casos_minimos.py` informa diez registros verificados; los casos adversariales mantienen mapas pequeños. El PDF permite dimensiones externas, pero no enuncia una excepción interna.
- Las pruebas SDL dummy verifican contenido/dibujo sobre superficie, no legibilidad, recortes, interacción o escalado de ventana real. La guía manual deja estos controles pendientes.
- No se comprobó un escenario externo oficial del profesor ni respuestas individuales de sustentación.

### P0 — Incumplimientos académicos confirmados

1. Casos 6, 7, 8 y 10 no alcanzan 20×20 bajo la lectura literal del requisito de desarrollo (alto; pendiente de aclaración formal).
2. Documentación de `_costo`, `_leer_objetivo` y `_leer_algoritmo` incumple la convención obligatoria; completar `comando` por su rol de reproducibilidad.

### P1 — Gestión o sustentación

1. Verificar issue #34/PR #71 y E11.4 cuando GitHub sea accesible; no actuar sobre estados desconocidos.
2. Completar guía de escritorio V01–V19, comprobar GUI de la versión que se entregará y distribuir preparación por integrante.
3. Obtener respuesta del profesor sobre mapas didácticos; si no hay excepción, adaptar los casos.

### P2 — Mejoras técnicas recomendadas

1. Sincronizar grafías completas del equipo después de validación.
2. Hacer que cambios locales de GUI y documentación pertenezcan a una única versión de entrega revisable.
3. Considerar los diagramas propuestos como apoyo explicativo, asegurando correspondencia con módulos actuales.

### P3 — Mejoras opcionales

1. Visualizar ramas/estados considerados por Minimax. El PDF solo valora esta capacidad y las métricas requeridas ya se muestran en la implementación local.
2. Mejoras visuales adicionales; la calidad artística no es criterio central.

## Limitaciones

- NO VERIFICABLE: estado/cuerpo/criterios de issue #34, estado y metadatos completos de PR #71 en GitHub, E11.4, asignaciones e inventario de issues abiertas, debido a credenciales GitHub inválidas y conexión API fallida.
- NO VERIFICABLE: legibilidad de escritorio y GUI en entorno gráfico real; pruebas automáticas emplean SDL dummy y la guía marca la actividad pendiente.
- NO VERIFICABLE: autorización del profesor para fixtures pequeños; hace falta respuesta explícita.
- NO VERIFICABLE: validación académica individual, nombres completos de terceros y que cada integrante pueda defender el sistema; requiere confirmación/evidencia del equipo.
- La ejecución del script de casos actualizó el registro JSON experimental, que ya estaba dentro del conjunto no confirmado del workspace. No se modificó código, GUI, escenarios, README ni DOCX durante la auditoría; no se cerraron issues ni se crearon commits/pushes.
