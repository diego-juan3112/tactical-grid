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

E2.3 agrega un set propio de escenarios en `escenarios/` para desarrollar y depurar algoritmos antes de recibir los del profesor: un mapa de 20 x 20 con todos los tipos de terreno y variantes pequenas. En `campo_20x20.json` y `ruta_corta_vs_economica.json` la ruta con menos movimientos es mas costosa que una mas larga, por lo que BFS y UCS deben producir caminos distintos (caso reutilizable en E5.2). Las pruebas de `tests/escenario/test_escenarios_propios.py` comprueban estas propiedades sobre el modelo de E1.2, con los costos leidos del JSON.

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
