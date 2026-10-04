# TacticalGrid

Juego tactico 2D por turnos para Sistemas Inteligentes I. El juego permite observar y experimentar estrategias de busqueda y decision sobre escenarios externos.

## Stack tecnico

- **Python 3.12 o compatible:** facilita implementar con claridad los algoritmos de busqueda y decision, mantiene el codigo legible y modificable, e integra Pygame y pytest en el mismo proyecto.
- **Pygame:** TacticalGrid es un entorno tactico 2D en cuadricula; permite visualizar tablero, terrenos, unidades, caminos y resultados, con una interfaz suficiente para observar el sistema inteligente y no para producir un videojuego comercial.
- **pytest:** permite probar escenario, juego y algoritmos independientemente de Pygame, con pruebas automatizadas y reproducibles.
- **Uvicorn:** ejecuta un punto ASGI tecnico y aislado; no convierte el proyecto en una aplicacion web.
- **JSON:** contrato externo para escenarios.
- **Git:** control de versiones.
- **.venv:** entorno virtual local recomendado para aislar dependencias.

## Arquitectura

- `escenario`: lee, valida y representa JSON; provee dimensiones, terrenos, costos y transitabilidad.
- `juego`: representa `EstadoJuego` y `Unidad`; aqui viviran reglas, acciones y sucesores.
- `algoritmos`: contiene contratos de resultados y alojara estrategias de busqueda y decision.
- `interfaz`: inicializa Pygame y consumira estado y resultados.
- `servidor`: expone el punto ASGI tecnico para Uvicorn; no accede a las cuatro capas.

```text
JSON -> Escenario -> Juego -> Algoritmos -> Resultado
                         ^                 ^
                         |                 |
                    Interfaz Pygame consume estado y resultados

Uvicorn -> servidor ASGI aislado
pytest -> prueba escenario, juego, algoritmos y servidor sin Pygame
```

`Escenario` conserva la informacion estatica: dimensiones, terrenos, bases, posicion inicial del recurso, configuracion y unidades iniciales. `EstadoJuego` conserva la informacion dinamica: unidades, turno actual, posicion del recurso cuando no tiene portador, identificador del portador y estado general de la partida. `Unidad` representa identificador, bando, tipo y posicion actual.

E1.1 define `EstadoJuego` y `Unidad` como objetos inmutables y hashables. Las unidades se almacenan en una tupla canonica ordenada por identificador, por lo que su orden de entrada no modifica la identidad logica del estado. Las posiciones determinan acciones y transiciones disponibles; el turno determina que bando puede actuar; y el portador distingue situaciones visualmente iguales que requieren decisiones distintas. Cuando no hay portador, la posicion del recurso tambien forma parte del estado. El modelo no contiene dimensiones ni posiciones fijas: esas propiedades pertenecen al escenario cargado.

E1.2 define acciones, sucesores, condicion objetivo y costo. Cada accion mueve una unidad del bando en turno una celda ortogonal a una celda dentro del mapa, transitable y libre; al entrar en la celda del recurso libre la unidad lo recoge, y el recurso viaja con ella. Un bando gana cuando su portador llega a su propia base. El costo de una accion es el costo del terreno destino declarado en `tipos_terreno`, por lo que cambiar un costo en el JSON cambia el comportamiento sin tocar codigo. Los algoritmos de busqueda consumen el contrato `Problema`; `ProblemaNavegacion` lleva una unidad a una celda objetivo ignorando al adversario.

## Reglas deterministas de borde — E1.3

Una unidad sin movimientos legales no genera acciones; las demas unidades del mismo bando pueden actuar normalmente. El bloqueo individual no cambia el turno. Si ninguna unidad del bando activo puede actuar, `resolver_bloqueo_turno()` pasa el turno una vez al adversario cuando este tiene acciones. Si ambos bandos carecen de acciones, `estado_partida` pasa a `empate_bloqueo`, que es terminal y evita pases repetidos.

La ausencia de ruta se determina en las historias de busqueda. Cuando una busqueda no encuentra solucion, `ResultadoBusqueda` representa fracaso (`exito = false`) con `camino` y `acciones` vacios, y `costo = None`. Ese resultado no modifica `EstadoJuego`: unidades, turno, recurso y `estado_partida` permanecen iguales. El contrato no agrega un algoritmo de busqueda a la capa de juego.

E1.3 no elimina unidades. Una intercepcion ya establecida transfiere atomicamente `portador_recurso` a la unidad adversaria y mantiene `posicion_recurso = null`; conserva las unidades y el turno. Si el nuevo portador ya esta en la base de su bando, esa misma transicion registra inmediatamente su victoria. La accion futura que origine la intercepcion sera responsable de alternar el turno mediante el flujo normal. Estas reglas son deterministas porque el mismo estado y escenario producen el mismo pase, empate o transferencia sin azar ni estado externo, y cada resultado se representa en un nuevo `EstadoJuego` inmutable.

## Bucle de turnos — E3.1

El dominio ofrece un flujo sincrono y paso a paso en `juego/partida.py`; el consumidor (jugador, interfaz, prueba o IA futura) decide cuándo repetirlo y qué opción elegir. No hay un bucle de partida interno ni concurrencia o lógica de tiempo real.

1. `preparar_turno(escenario, estado)` devuelve sin cambios un estado terminal; de lo contrario reutiliza `resolver_bloqueo_turno()` para mantener el turno, pasarlo una vez o declarar empate por bloqueo total.
2. `unidades_seleccionables()` expone solo unidades del bando activo con al menos una acción legal. Una unidad bloqueada no es seleccionable; `acciones_para_unidad()` para esa unidad activa devuelve una tupla vacía.
3. El consumidor elige una unidad y una de las acciones de `acciones_para_unidad()`. Esta consulta filtra `acciones_validas()` y no duplica reglas de movimiento. Una unidad adversaria o inexistente produce `ValueError`.
4. `aplicar_accion()` valida y ejecuta la acción según E1.2, crea un nuevo estado y alterna el turno exactamente una vez. E3.1 no vuelve a cambiarlo.

La selección es transitoria y no integra `EstadoJuego`, por lo que no altera su identidad lógica ni su hash. El pase automático pertenece a E1.3; si ambos bandos están bloqueados, la partida termina en `empate_bloqueo`. `resolver_intercepcion()` conserva el turno por sí sola. A y B utilizan las mismas reglas. MAX y MIN son roles adversariales futuros: no conceden más o menos acciones, profundidad o inteligencia. La integración de E2.1 comienza con un `Escenario` cargado; `crear_estado_inicial(escenario)` construye el estado sin que el módulo de partida lea JSON.

E2.2 completa el validador de escenarios. Antes de construir el `Escenario` se comprueban todas las reglas del enunciado: dimensiones consistentes con la matriz, terrenos declarados, costos positivos, posiciones dentro del mapa, unidades sobre celdas transitables, ids unicos, bandos y turno validos, y portador existente. Cualquier incumplimiento lanza `ErrorValidacionEscenario` con un mensaje que nombra el campo, el elemento y el valor recibido. Como la validacion ocurre completa antes de aplicar nada, una carga fallida no reemplaza ni altera el escenario vigente.

E2.3 agrega un set propio de escenarios en `escenarios/` para desarrollar y depurar algoritmos antes de recibir los del profesor: un mapa de 20 x 20 con todos los tipos de terreno y variantes pequenas. En `campo_20x20.json` y `ruta_corta_vs_economica.json` la ruta con menos movimientos es mas costosa que una mas larga, por lo que BFS y UCS deben producir caminos distintos (caso reutilizable en E5.2). Las pruebas de `tests/escenario/test_escenarios_propios.py` comprueban estas propiedades sobre el modelo de E1.2, con los costos leidos del JSON.

E4.1 agrega la instrumentacion comun de busqueda en `algoritmos/instrumentacion.py`, para que BFS, DFS, UCS, A* y Beam Search reporten resultados comparables sin duplicar codigo. `Nodo` guarda estado, padre, accion, costo acumulado y profundidad; `expandir` genera los hijos en el orden de las acciones, con el costo leido del escenario, y cuenta la expansion; `MedidorBusqueda` lleva estados generados (incorporados a la frontera, incluido el inicial), estados expandidos, maximo de frontera y tiempo, y construye el `ResultadoBusqueda`. `ResultadoBusqueda.a_diccionario()` devuelve la estructura del enunciado (`algoritmo`, `exito`, `camino`, `costo`, `estados_generados`, `estados_expandidos`, `maximo_frontera`) mas `longitud` y `tiempo_segundos`; el resultado tambien conserva las acciones para el verificador de soluciones.

Dependencias prohibidas: juego no importa Pygame ni JSON; algoritmos no importan Pygame, no abren JSON ni codifican mapas, posiciones o costos; interfaz no decide reglas; escenario no depende de algoritmos. Los costos se consultan desde el escenario cargado.

## Estructura

```text
src/tacticalgrid/
├── escenario/
├── juego/
├── algoritmos/
├── interfaz/
└── servidor/
tests/
├── escenario/
├── juego/
├── algoritmos/
└── servidor/
escenarios/
```

El contrato JSON usa literalmente `version`, `mapa.filas`, `mapa.columnas`, `tipos_terreno`, `terreno`, `bases.A`, `bases.B`, `recurso`, `unidades`, `turno`, `juego.portador_recurso` y `prueba`.

## Windows (PowerShell)

El remoto configurado del proyecto requiere el alias SSH `github.com-personal`:

```powershell
git clone git@github.com-personal:diego-juan3112/tactical-grid.git
cd tactical-grid
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[desarrollo]"
python -m pytest
tacticalgrid
python -m uvicorn tacticalgrid.servidor.asgi:aplicacion --reload
```

Estos comandos no se ejecutaron en este entorno Linux; deben validarse en Windows con el alias SSH configurado.

## Linux

```bash
git clone git@github.com-personal:diego-juan3112/tactical-grid.git
cd tactical-grid
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[desarrollo]'
python -m pytest
tacticalgrid
python -m uvicorn tacticalgrid.servidor.asgi:aplicacion --reload
```

En Linux se verificaron la instalacion en `.venv`, pytest y Uvicorn; el clon no se repitio porque este repositorio ya estaba presente. `uvicorn tacticalgrid.servidor.asgi:aplicacion --reload` inicia el servidor ASGI en desarrollo. `tacticalgrid` abre la interfaz minima de Pygame y se cierra mediante el control de la ventana.

Para salir del entorno virtual en Windows o Linux:

```bash
deactivate
```

## Escenarios

Todos los escenarios viven en `escenarios/` y usan el formato JSON comun. El campo propio `descripcion` explica el proposito de cada uno; `prueba` indica la navegacion a resolver (unidad y objetivo) o el modo de juego.

| Archivo | Tamano | Proposito |
|---|---|---|
| `ejemplo_enunciado.json` | 4 x 4 | Ejemplo literal del enunciado. |
| `arquitectura_basica.json` | 20 x 20 | Mapa abierto, todo camino; comprueba carga y exploracion en 20 x 20. |
| `campo_20x20.json` | 20 x 20 | Mapa principal de desarrollo: anillo de camino, lago de pantano con el recurso en una isla, bosques y muros. Ruta mas corta de A1 al recurso: 16 movimientos, costo 42; ruta mas economica: 34 movimientos, costo 34. |
| `ruta_corta_vs_economica.json` | 5 x 9 | BFS vs. UCS: la ruta recta por pantano tiene 8 movimientos y cuesta 50; rodear por camino toma 12 movimientos y cuesta 12. Con el pantano a costo 1, ambas coinciden. |
| `obstaculo_rodeo.json` | 8 x 7 | El objetivo esta a distancia Manhattan 3, pero un muro en U obliga a un recorrido de 15 movimientos (caso 3: obstaculo y heuristica). |
| `recurso_en_transporte.json` | 6 x 8 | Partida con `portador_recurso` = `A2` (caso 6: estado compuesto). |

Los numeros de la tabla son verificados por pytest con un calculo de referencia sobre el modelo del juego; no son resultados de BFS ni UCS, que se implementan en historias posteriores.
