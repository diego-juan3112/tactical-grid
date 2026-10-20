"""Selector de archivos del sistema para abrir un escenario JSON desde la interfaz grafica."""

from pathlib import Path


class DialogoNoDisponible(RuntimeError):
    """El sistema no ofrece un selector de archivos: falta tkinter o no hay pantalla para mostrarlo."""


def pedir_ruta_escenario(directorio_inicial: Path) -> Path | None:
    """Muestra el selector de archivos nativo y devuelve el escenario JSON elegido.

    Proposito: permitir que el usuario cargue un mapa propio desde la ventana, sin escribir rutas en la terminal.
    Precondiciones: se llama desde el hilo de la interfaz; ``directorio_inicial`` es la carpeta donde se abre el
    selector.
    Postcondiciones: devuelve la ruta elegida, o ``None`` si el usuario cancela; no lee ni valida el archivo, eso lo
    hace la carga atomica del controlador. Lanza ``DialogoNoDisponible`` si tkinter no esta instalado o no hay pantalla.
    La ventana auxiliar de tkinter siempre se destruye.
    Complejidad: O(1) propia; el tiempo lo determina el usuario mientras el selector esta abierto.
    Uso de IA: Si.
    Intervencion de IA: Claude (Opus 5.5) propuso este selector y su documentacion en E9.4.
    Validacion del estudiante: el equipo lo reviso y probo en la ventana; tests/interfaz/test_dialogo.py cubre la
    ruta elegida, la cancelacion, la falta de tkinter y la falta de pantalla.
    """
    try:
        import tkinter
        from tkinter import filedialog
    except ImportError as error:
        raise DialogoNoDisponible("tkinter no esta instalado") from error
    try:
        raiz = tkinter.Tk()
    except tkinter.TclError as error:
        raise DialogoNoDisponible("no hay pantalla para el selector de archivos") from error
    try:
        raiz.withdraw()
        raiz.attributes("-topmost", True)
        elegido = filedialog.askopenfilename(
            parent=raiz,
            title="Abrir escenario JSON",
            initialdir=str(directorio_inicial),
            filetypes=[("Escenario JSON", "*.json"), ("Todos los archivos", "*.*")],
        )
    finally:
        raiz.destroy()
    return Path(elegido) if elegido else None
