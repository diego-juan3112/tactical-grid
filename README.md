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

`Escenario` conserva informacion estatica: dimensiones, terrenos, bases, recurso, configuracion y unidades iniciales. `EstadoJuego` conserva informacion dinamica: unidades, turno actual, posicion o portador del recurso y estado general de la partida. `Unidad` representa identificador, bando, tipo y posicion. E0.3 define esta separacion solo a alto nivel; E1.1 concretara el modelo interno, incluida la igualdad, hashing, inmutabilidad, copia, representacion canonica y representacion de estados visitados. E0.3 no bloquea esas decisiones. No se define el estado global solo como una coordenada.

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

`escenarios/arquitectura_basica.json` es un escenario valido de 20 x 20. Los escenarios comparativos de BFS/UCS se incorporaran con esas implementaciones, sin anticipar resultados que aun no existen.
