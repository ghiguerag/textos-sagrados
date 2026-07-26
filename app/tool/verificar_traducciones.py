#!/usr/bin/env python3
"""
Comprueba la coherencia de las traducciones.

    python tool/verificar_traducciones.py

Verifica cinco cosas:
  1. Los 6 ficheros ARB tienen exactamente las mismas claves
  2. Ninguna traducción está vacía o quedó sin traducir
  3. Los marcadores {variable} coinciden en todos los idiomas
  4. Toda clave usada en el código Dart existe en los ARB
  5. No quedan textos en español incrustados en la interfaz

Ejecútalo antes de cada entrega: añadir una cadena y olvidar cinco idiomas es
el fallo más fácil de cometer y el más difícil de ver.
"""

from __future__ import annotations

import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]

# Cadenas que legítimamente coinciden entre idiomas: nombres propios, símbolos
# y palabras que el español y el portugués comparten.
SHARED_OK = {
    "appTitle", "tradIslam", "perTenK",
    "versesCount", "concShowing", "errInvalidQuery",
}

# Métodos de la extensión L10nMapping, no claves de los ARB.
HELPERS = {"caveat", "keynessDirection", "apiError", "of", "delegate"}

SPANISH_LITERAL = re.compile(
    r"(?:Text|hintText|message|label|title|tooltip)\s*:\s*"
    r"(?:const\s+)?(?:Text\()?'([^']*[áéíóúñ¿¡][^']*)'"
)


def main() -> int:
    problems: list[str] = []

    arbs = {
        f.stem.split("_")[1]: json.loads(f.read_text(encoding="utf-8"))
        for f in sorted((ROOT / "lib" / "l10n").glob("app_*.arb"))
    }
    if "es" not in arbs:
        print("No encuentro lib/l10n/app_es.arb (plantilla)")
        return 1

    base_keys = {k for k in arbs["es"] if not k.startswith("@")}

    # 1. Paridad
    for lang, d in arbs.items():
        keys = {k for k in d if not k.startswith("@")}
        if keys != base_keys:
            problems.append(
                f"{lang}: faltan {sorted(base_keys - keys)}, "
                f"sobran {sorted(keys - base_keys)}"
            )

    # 2. Vacíos y sin traducir
    for lang, d in arbs.items():
        if lang == "es":
            continue
        for k in base_keys & {x for x in d if not x.startswith("@")}:
            if not str(d[k]).strip():
                problems.append(f"{lang}.{k}: vacío")
            elif d[k] == arbs["es"][k] and k not in SHARED_OK and len(str(d[k])) > 12:
                problems.append(f"{lang}.{k}: sin traducir (idéntico al español)")

    # 3. Marcadores
    for k in base_keys:
        ref = set(re.findall(r"\{(\w+)\}", arbs["es"][k]))
        for lang, d in arbs.items():
            if k not in d:
                continue
            got = set(re.findall(r"\{(\w+)\}", d[k]))
            if got != ref:
                problems.append(f"{lang}.{k}: marcadores {sorted(got)} != {sorted(ref)}")

    # 4. Claves usadas en el código
    used: set[str] = set()
    for f in (ROOT / "lib").rglob("*.dart"):
        if "l10n" in f.parts:
            continue
        src = f.read_text(encoding="utf-8")
        used |= set(re.findall(r"\bl\.(\w+)", src))
        used |= set(re.findall(r"\bl10n\.(\w+)", src))

    # Dentro de la extensión L10nMapping el receptor es implícito, así que las
    # claves aparecen desnudas. Sin esto, todas darían falso positivo.
    helpers_src = (ROOT / "lib" / "core" / "l10n_helpers.dart")
    if helpers_src.exists():
        used |= set(re.findall(r"=>\s*(\w+)[,;\n]", helpers_src.read_text(encoding="utf-8")))
        used |= set(re.findall(r"\?\?\s*(\w+)[,;\n)]", helpers_src.read_text(encoding="utf-8")))
    for k in sorted(used - base_keys - HELPERS):
        problems.append(f"código usa L.{k}, que no existe en los ARB")

    # 5. Español incrustado
    for f in (ROOT / "lib").rglob("*.dart"):
        if "l10n" in f.parts:
            continue
        for m in SPANISH_LITERAL.finditer(f.read_text(encoding="utf-8")):
            problems.append(f'{f.relative_to(ROOT)}: sin localizar -> "{m.group(1)[:45]}"')

    unused = sorted(base_keys - used - HELPERS)

    print(f"{len(arbs)} idiomas · {len(base_keys)} claves · "
          f"{len(used - HELPERS)} usadas en el código")
    if unused:
        print(f"\nClaves definidas pero no usadas ({len(unused)}): {', '.join(unused)}")
        print("No es un error, pero conviene revisarlas.")
    if problems:
        print("\nPROBLEMAS:")
        for p in problems:
            print("  -", p)
        return 1
    print("\nTraducciones coherentes y completas.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
