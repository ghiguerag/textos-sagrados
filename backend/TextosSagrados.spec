# -*- mode: python ; coding: utf-8 -*-
# Receta de empaquetado para PyInstaller.
#   pyinstaller TextosSagrados.spec
#
# Recoge por completo las librerías del servidor (FastAPI, Starlette, uvicorn,
# pydantic…), que son las que más a menudo se quedan fuera y hacen que el
# servidor no arranque dentro del ejecutable.
#
# Los textos (corpus.db, 195 MB) NO van dentro del ejecutable: el instalador
# los copia al lado y la app los busca ahí. Así el .exe es ligero.

from PyInstaller.utils.hooks import collect_all

datas = [
    ("app/static", "app/static"),
    ("data/lexicon.json", "data"),
]
binaries = []
hiddenimports = ["anyio", "sniffio", "click", "h11"]

for paquete in [
    "fastapi", "starlette", "uvicorn",
    "pydantic", "pydantic_core", "pydantic_settings",
]:
    d, b, h = collect_all(paquete)
    datas += d
    binaries += b
    hiddenimports += h

a = Analysis(
    ["desktop.py"],
    pathex=["."],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    excludes=[
        # Fuera los pesos de la búsqueda por significado: cientos de MB, y la
        # versión de escritorio funciona sin ellos.
        "torch", "sentence_transformers", "transformers", "scipy",
    ],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz, a.scripts, [],
    exclude_binaries=True,
    name="Textos Sagrados",
    console=False,
    icon="../assets/icono.ico",
)
coll = COLLECT(
    exe, a.binaries, a.datas,
    name="Textos Sagrados",
)
