"""Prueba de aislamiento de las capas centrales respecto de Pygame."""

import os
import subprocess
import sys
from pathlib import Path


def test_capas_centrales_no_importan_pygame() -> None:
    raiz = Path(__file__).resolve().parents[2]
    entorno = os.environ | {"PYTHONPATH": str(raiz / "src")}
    resultado = subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys; import tacticalgrid.escenario, tacticalgrid.juego, tacticalgrid.algoritmos; "
            "assert 'pygame' not in sys.modules",
        ],
        cwd=raiz,
        env=entorno,
        capture_output=True,
        text=True,
        check=False,
    )

    assert resultado.returncode == 0, resultado.stderr
