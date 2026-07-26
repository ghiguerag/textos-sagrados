#!/usr/bin/env python3
"""
Espera a que el servidor responda y entonces abre el navegador.

Existe por un fallo real: el script de arranque abría el navegador
inmediatamente, antes de que el servidor estuviera escuchando, y el usuario
veía «localhost rechazó la conexión». Normalmente el servidor tarda un par de
segundos y no se nota, pero si los archivos están en una carpeta sincronizada
con la nube puede tardar un minuto en cargar.
"""

from __future__ import annotations

import sys
import time
import urllib.error
import urllib.request
import webbrowser

URL = "http://localhost:8000"
ESPERA_MAX = 180          # tres minutos: suficiente incluso descargando de OneDrive
INTERVALO = 0.7


def main() -> int:
    limite = time.time() + ESPERA_MAX
    while time.time() < limite:
        try:
            with urllib.request.urlopen(f"{URL}/health", timeout=2):
                webbrowser.open(URL)
                return 0
        except (urllib.error.URLError, OSError, TimeoutError):
            time.sleep(INTERVALO)

    # Si no respondió, no se abre el navegador: mostrar una página de error
    # confunde más que no mostrar nada. El mensaje queda en la ventana negra.
    print(f"El servidor no respondió en {ESPERA_MAX} segundos.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
