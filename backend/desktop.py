"""
Textos Sagrados como aplicación de escritorio: una ventana propia, sin consola.

Arranca el servidor interno y lo muestra en una ventana nativa usando el «modo
app» de Edge o Chrome —una ventana limpia, sin barra de navegador—. Windows
siempre trae Edge, así que no hace falta ninguna dependencia extra frágil.

    python desktop.py             (desarrollo, con consola)
    pythonw desktop.py            (sin consola)
    empaquetado con PyInstaller   (ver CONSTRUIR-APP-Windows.bat)
"""

from __future__ import annotations

import io
import sys

if sys.stdout is None:
    sys.stdout = io.StringIO()
if sys.stderr is None:
    sys.stderr = io.StringIO()

import os
import shutil
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path


def _base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent


BASE = _base_dir()
os.environ.setdefault("TS_DB_PATH", str(BASE / "data" / "corpus.db"))
os.environ.setdefault("TS_LEXICON_PATH", str(BASE / "data" / "lexicon.json"))

# Registro de arranque: sin consola, es la única ventana al problema.
LOG = BASE / "registro-arranque.txt"

def _log(msg: str) -> None:
    linea = f"{__import__('time').strftime('%H:%M:%S')}  {msg}"
    try:
        print(linea, flush=True)          # visible en modo prueba (con consola)
    except Exception:  # noqa: BLE001
        pass
    try:
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(linea + "\n")
    except Exception:  # noqa: BLE001
        pass


def _puerto_libre() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


def _esperar(url: str, timeout: float = 40) -> bool:
    import urllib.request
    fin = time.time() + timeout
    while time.time() < fin:
        try:
            urllib.request.urlopen(url + "/health", timeout=2)
            return True
        except Exception:  # noqa: BLE001
            time.sleep(0.3)
    return False


def _desde_registro(exe: str) -> str | None:
    """Ruta del navegador según el registro de Windows (App Paths)."""
    try:
        import winreg
    except ImportError:
        return None
    ruta = rf"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\{exe}"
    for raiz in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
        try:
            with winreg.OpenKey(raiz, ruta) as k:
                val, _ = winreg.QueryValueEx(k, None)
                if val and Path(val).exists():
                    return val
        except OSError:
            pass
    return None


def _navegador() -> str | None:
    """Localiza Edge o Chrome, que permiten abrir una ventana en modo app."""
    # 1. El registro de Windows: lo más fiable.
    for exe in ("msedge.exe", "chrome.exe"):
        r = _desde_registro(exe)
        if r:
            return r
    # 2. Rutas conocidas, usando las variables de entorno directamente.
    pf = os.environ.get("ProgramFiles", r"C:\Program Files")
    pf86 = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")
    for base in (pf86, pf):
        for sub in (r"Microsoft\Edge\Application\msedge.exe",
                    r"Google\Chrome\Application\chrome.exe"):
            c = os.path.join(base, sub)
            if Path(c).exists():
                return c
    # 3. En el PATH.
    for nombre in ("msedge", "chrome"):
        w = shutil.which(nombre)
        if w:
            return w
    return None


def main() -> int:
    import uvicorn

    puerto = _puerto_libre()
    url = f"http://127.0.0.1:{puerto}"

    _log(f"Base de datos: {os.environ.get('TS_DB_PATH')}")
    _log(f"¿existe la base?: {Path(os.environ.get('TS_DB_PATH','')).exists()}")
    try:
        from app.main import app
    except Exception as exc:  # noqa: BLE001
        import traceback
        _log("FALLO al importar la aplicación:\n" + traceback.format_exc())
        raise

    config = uvicorn.Config(
        app, host="127.0.0.1", port=puerto,
        log_config=None, log_level="critical", access_log=False,
    )
    server = uvicorn.Server(config)

    def _arrancar():
        try:
            server.run()
            _log("El servidor terminó (posible fallo de arranque).")
        except Exception:  # noqa: BLE001
            import traceback
            _log("FALLO al arrancar el servidor:\n" + traceback.format_exc())

    _log("Iniciando servidor…")
    threading.Thread(target=_arrancar, daemon=True).start()

    if not _esperar(url):
        # El servidor no levantó: se abre el navegador por si muestra algo y
        # se sale. Este es el ÚNICO caso de salida temprana.
        _log("El servidor no respondió a tiempo. Revisa los mensajes de arriba.")
        try:
            import webbrowser
            webbrowser.open(url)
        except Exception:  # noqa: BLE001
            pass
        return 1

    _log("El servidor respondió correctamente.")

    nav = _navegador()
    _log(f"Navegador encontrado: {nav}")
    if nav:
        # Perfil dedicado para la ventana, FUERA de la carpeta del programa
        # (si estuviera dentro, bloquearía la carpeta al reconstruir). Ventana
        # limpia, sin pestañas ni la sesión de Edge del usuario.
        base_perfil = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
        perfil = os.path.join(base_perfil, "TextosSagradosApp", "ventana")
        proc = subprocess.Popen([
            nav, f"--app={url}", f"--user-data-dir={perfil}",
            "--window-size=1220,840", "--no-first-run",
            "--no-default-browser-check",
            "--no-proxy-server",
            "--proxy-bypass-list=127.0.0.1;localhost;<local>",
        ])
        _log("Ventana abierta en " + url)
        inicio = time.time()
        proc.wait()               # espera a que el usuario cierre la ventana
        # Si el proceso terminó enseguida, Edge delegó la ventana en otra
        # instancia. Mantener el servidor vivo para que la página funcione.
        if time.time() - inicio < 4:
            _log("La ventana se delegó a otra instancia; servidor activo.")
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                pass
    else:
        # Sin Edge ni Chrome (raro en Windows): navegador por defecto y espera.
        import webbrowser
        webbrowser.open(url)
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass

    server.should_exit = True
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
