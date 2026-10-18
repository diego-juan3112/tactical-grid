# Arquitectura, modelo del estado y reglas del juego

Historias E0.3, E1.1 a E1.3, E2.2, E2.3, E3.1 y E3.2: cómo se separan las capas, qué información define un estado, qué acciones existen y qué reglas resuelven los casos de borde.

## Capas y dependencias

| Capa | Paquete | Responsabilidad |
|---|---|---|
| Escenario | `escenario/` | Lee, valida y representa el JSON: dimensiones, terrenos, costos, bases y unidades iniciales. |
| Juego | `juego/` | Estado dinámico, acciones, sucesores, costos, turnos, recurso, tácticas y el contrato `Problema`. |
| Algoritmos | `algoritmos/` | Búsquedas, heurísticas, utilidad, Minimax, alfa-beta, métricas y verificador. |
| Modos | `modos/` | Interpreta el campo `prueba`, ejecuta los modos `busqueda`, `partida` y `adversarial`, y arma el registro reproducible. |
| Interfaz | `interfaz/` | Dibuja tablero, camino y exploración con Pygame, y recibe la interacción del usuario. |
| Servidor | `servidor/` | Punto ASGI técnico y aislado para Uvicorn. |

```text
JSON -> Escenario -> Juego -> Algoritmos -> Resultado
                         ^                 ^
                         |                 |
                    Interfaz Pygame consume estado y resultados

Uvicorn -> servidor ASGI aislado
pytest -> prueba escenario, juego, algoritmos y servidor sin Pygame
```

Dependencias prohibidas: juego no importa Pygame ni JSON; algoritmos no importan Pygame, no abren JSON ni codifican mapas, posiciones o costos; interfaz no decide reglas; escenario no depende de algoritmos. Los costos se consultan desde el escenario cargado.

El contrato JSON usa literalmente `version`, `mapa.filas`, `mapa.columnas`, `tipos_terreno`, `terreno`, `bases.A`, `bases.B`, `recurso`, `unidades`, `turno`, `juego.portador_recurso` y `prueba`.

## Modelo del estado — E1.1

`Escenario` conserva la información estática: dimensiones, terrenos, bases, posición inicial del recurso, configuración y unidades iniciales. `EstadoJuego` conserva la información dinámica: unidades, turno actual, posición del recurso cuando no tiene portador, identificador del portador y estado general de la partida. `Unidad` representa identificador, bando, tipo y posición actual.

E1.1 define `EstadoJuego` y `Unidad` como objetos inmutables y hashables. Las unidades se almacenan en una tupla canónica ordenada por identificador, por lo que su orden de entrada no modifica la identidad lógica del estado. Las posiciones determinan acciones y transiciones disponibles; el turno determina qué bando puede actuar; y el portador distingue situaciones visualmente iguales que requieren decisiones distintas. Cuando no hay portador, la posición del recurso también forma parte del estado. El modelo no contiene dimensiones ni posiciones fijas: esas propiedades pertenecen al escenario cargado.

## Acciones, sucesores, objetivo y costo — E1.2

E1.2 define acciones, sucesores, condición objetivo y costo. Cada acción mueve una unidad del bando en turno una celda ortogonal a una celda dentro del mapa, transitable y libre; al entrar en la celda del recurso libre la unidad lo recoge, y el recurso viaja con ella. Un bando gana cuando su portador llega a su propia base. El costo de una acción es el costo del terreno destino declarado en `tipos_terreno`, por lo que cambiar un costo en el JSON cambia el comportamiento sin tocar código. Los algoritmos de búsqueda consumen el contrato `Problema`; `ProblemaNavegacion` lleva una unidad a una celda objetivo ignorando al adversario.

## Reglas deterministas de borde — E1.3

Una unidad sin movimientos legales no genera acciones; las demás unidades del mismo bando pueden actuar normalmente. El bloqueo individual no cambia el turno. Si ninguna unidad del bando activo puede actuar, `resolver_bloqueo_turno()` pasa el turno una vez al adversario cuando este tiene acciones. Si ambos bandos carecen de acciones, `estado_partida` pasa a `empate_bloqueo`, que es terminal y evita pases repetidos.

La ausencia de ruta se determina en las historias de búsqueda. Cuando una búsqueda no encuentra solución, `ResultadoBusqueda` representa fracaso (`exito = false`) con `camino` y `acciones` vacíos, y `costo = None`. Ese resultado no modifica `EstadoJuego`: unidades, turno, recurso y `estado_partida` permanecen iguales. El contrato no agrega un algoritmo de búsqueda a la capa de juego.

E1.3 no elimina unidades. Una intercepción ya establecida transfiere atómicamente `portador_recurso` a la unidad adversaria y mantiene `posicion_recurso = null`; conserva las unidades y el turno. Si el nuevo portador ya está en la base de su bando, esa misma transición registra inmediatamente su victoria. La acción futura que origine la intercepción será responsable de alternar el turno mediante el flujo normal. Estas reglas son deterministas porque el mismo estado y escenario producen el mismo pase, empate o transferencia sin azar ni estado externo, y cada resultado se representa en un nuevo `EstadoJuego` inmutable.

## Validación de escenarios — E2.2

E2.2 completa el validador de escenarios. Antes de construir el `Escenario` se comprueban todas las reglas del enunciado: dimensiones consistentes con la matriz, terrenos declarados, costos positivos, posiciones dentro del mapa, unidades sobre celdas transitables, ids únicos, bandos y turno válidos, y portador existente. Cualquier incumplimiento lanza `ErrorValidacionEscenario` con un mensaje que nombra el campo, el elemento y el valor recibido. Como la validación ocurre completa antes de aplicar nada, una carga fallida no reemplaza ni altera el escenario vigente.

## Escenarios propios — E2.3

E2.3 agrega un set propio de escenarios en `escenarios/` para desarrollar y depurar algoritmos antes de recibir los del profesor: un mapa de 20 x 20 con todos los tipos de terreno y variantes pequeñas. En `campo_20x20.json` y `ruta_corta_vs_economica.json` la ruta con menos movimientos es más costosa que una más larga, por lo que BFS y UCS producen caminos distintos. Las pruebas de `tests/escenario/test_escenarios_propios.py` comprueban estas propiedades sobre el modelo de E1.2, con los costos leídos del JSON.

## Bucle de turnos — E3.1

El dominio ofrece un flujo síncrono y paso a paso en `juego/partida.py`; el consumidor (jugador, interfaz, prueba o IA futura) decide cuándo repetirlo y qué opción elegir. No hay un bucle de partida interno ni concurrencia o lógica de tiempo real.

1. `preparar_turno(escenario, estado)` devuelve sin cambios un estado terminal; de lo contrario reutiliza `resolver_bloqueo_turno()` para mantener el turno, pasarlo una vez o declarar empate por bloqueo total.
2. `unidades_seleccionables()` expone solo unidades del bando activo con al menos una acción legal. Una unidad bloqueada no es seleccionable; `acciones_para_unidad()` para esa unidad activa devuelve una tupla vacía.
3. El consumidor elige una unidad y una de las acciones de `acciones_para_unidad()`. Esta consulta filtra `acciones_validas()` y no duplica reglas de movimiento. Una unidad adversaria o inexistente produce `ValueError`.
4. `aplicar_accion()` valida y ejecuta la acción según E1.2, crea un nuevo estado y alterna el turno exactamente una vez. E3.1 no vuelve a cambiarlo.

La selección es transitoria y no integra `EstadoJuego`, por lo que no altera su identidad lógica ni su hash. El pase automático pertenece a E1.3; si ambos bandos están bloqueados, la partida termina en `empate_bloqueo`. `resolver_intercepcion()` conserva el turno por sí sola. A y B utilizan las mismas reglas. MAX y MIN son roles adversariales futuros: no conceden más o menos acciones, profundidad o inteligencia. La integración de E2.1 comienza con un `Escenario` cargado; `crear_estado_inicial(escenario)` construye el estado sin que el módulo de partida lea JSON.

## Recoger y transportar el recurso — E3.2

Las reglas del recurso viven en `juego/recurso.py`, que solo consulta y transforma `EstadoJuego` (no lee JSON, no conoce Pygame ni los algoritmos). Antes estaban mezcladas dentro de `reglas.py`; E3.2 las extrae a un módulo propio sin cambiar el comportamiento y `reglas.py` las reutiliza.

- **Recoger:** una unidad recoge el recurso automáticamente al entrar en la celda donde está libre (`recoger_recurso`). Entonces `portador_recurso` pasa a ser su identificador y `posicion_recurso` queda en `null`. Pasar junto al recurso sin entrar en su celda no lo recoge.
- **Transportar:** mientras tiene portador, el recurso viaja con él. `posicion_del_recurso(estado)` responde dónde está el recurso, libre o transportado, y `obtener_portador(estado)` devuelve la unidad que lo lleva.
- **Ganar:** un bando gana cuando su portador está en la base de ese mismo bando (`bando_que_entrego_recurso`). Llevarlo a la base adversaria no da la victoria. Si el recurso estaba en la propia base y la unidad lo recoge allí, gana de inmediato.
- **Simetría:** A y B usan exactamente las mismas reglas.

`tests/juego/test_recurso.py` verifica cada criterio, incluida una partida completa sobre `escenarios/ejemplo_enunciado.json` en la que A1 recoge el recurso, lo transporta y gana en su base.
