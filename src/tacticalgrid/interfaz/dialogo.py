"""Selector de archivos del sistema para abrir un escenario JSON desde la interfaz gráfica."""

from pathlib import Path


class DialogoNoDisponible(RuntimeError):
    """El sistema no ofrece un selector de archivos: falta tkinter o no hay pantalla para mostrarlo."""


def pedir_ruta_escenario(directorio_inicial: Path) -> Path | None:
    """Mostrar el selector de archivos nativo y devolver el escenario JSON elegido.

    Proposito: permitir cargar un mapa propio desde la ventana, sin escribir rutas en la terminal.
    Precondiciones: la llamada se hace desde el hilo de la interfaz; ``directorio_inicial`` es la carpeta en la que se
    abre el selector.
    Postcondiciones: se devuelve la ruta elegida, o ``None`` si el usuario cancela; el archivo no se lee ni se valida
    aquí, porque de eso se encarga la carga atómica del controlador. Se lanza ``DialogoNoDisponible`` si tkinter no
    está instalado o no hay pantalla. La ventana auxiliar de tkinter siempre se destruye.
    Complejidad: O(1) propia; el tiempo lo determina el usuario mientras el selector está abierto.
    Uso de IA: Si.
    Intervencion de IA: Claude (Opus 5.5): selector y documentación (E9.4).
    Validacion del estudiante: pruebas de tests/interfaz/test_dialogo.py: ruta elegida con cierre de la raíz,
    cancelación, falta de tkinter, falta de pantalla e importación del módulo sin cargar tkinter.
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


def pedir_ruta_registro(directorio_inicial: Path) -> Path | None:
    """Mostrar el selector nativo para guardar un registro JSON de experimento.

    Proposito: obtener una ruta de salida elegida por el usuario sin acoplar la aplicación a una ubicación fija.
    Precondiciones: la llamada se hace desde el hilo de Pygame y ``directorio_inicial`` existe o es una ruta utilizable.
    Postcondiciones: se devuelve la ruta elegida, o ``None`` al cancelar; no se escriben archivos y la raíz de tkinter
    siempre se destruye. Se lanza ``DialogoNoDisponible`` si falta tkinter o una pantalla.
    Complejidad: O(1) propia; el tiempo de selección depende del usuario.
    Uso de IA: Si.
    Intervencion de IA: Codex: conexión del selector de guardado con el registro exportable de experimentos.
    Validacion del estudiante: prueba ``test_pide_ruta_de_guardado_json_y_cierra_la_raiz`` de
    tests/interfaz/test_dialogo.py y prueba ``test_tecla_j_abre_destino_y_exporta_registro_de_busqueda`` de
    tests/interfaz/test_aplicacion.py.
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
        elegido = filedialog.asksaveasfilename(
            parent=raiz,
            title="Guardar registro reproducible",
            initialdir=str(directorio_inicial),
            initialfile="experimento-tacticalgrid.json",
            defaultextension=".json",
            filetypes=[("Resultados JSON", "*.json"), ("Todos los archivos", "*.*")],
        )
    finally:
        raiz.destroy()
    return Path(elegido) if elegido else None
