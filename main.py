"""Punto de entrada de TacticalGrid: abrir la interfaz gráfica o la consola según los argumentos."""

import sys
from pathlib import Path


RAIZ = Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ / "src"))

from tacticalgrid.despachador import ejecutar


if __name__ == "__main__":
    sys.exit(ejecutar())
