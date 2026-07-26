#!/usr/bin/env python3
"""
Revisa la salud del corpus ya descargado.

    python scripts/revisar_corpus.py

Comprueba que cada obra contiene lo que dice contener. Se escribió después de
descubrir que el Corán se había descargado en árabe declarándose inglés, lo
que hacía que todas sus comparaciones dieran cero sin que nada fallara.

Ejecútalo después de cada ingesta.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.db import connect                     # noqa: E402
from app.core.validacion import validar_idioma      # noqa: E402

def _ruta_por_defecto() -> str:
    """Ruta de la base de datos sin depender de la configuración completa.

    Un script de mantenimiento debe poder ejecutarse aunque falte alguna
    dependencia de la aplicación: precisamente se usa cuando algo va mal.
    """
    try:
        from app.config import get_settings
        return str(get_settings().db_path)
    except Exception:                       # noqa: BLE001
        return str(Path(__file__).resolve().parents[1] / "data" / "corpus.db")



# Palabras que deben aparecer en cualquier traducción inglesa de estos textos.
# Su ausencia total delata un corpus equivocado.
CONTROLES: dict[str, list[str]] = {
    "en": ["god", "man", "day", "said", "people", "earth"],
}


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--db", default=_ruta_por_defecto())
    args = p.parse_args()

    db = Path(args.db)
    if not db.exists():
        print(f"\nNo encuentro la base de datos en {db}\n")
        return 1

    conn = connect(db, readonly=True)
    obras = conn.execute(
        "SELECT id, title, edition, language, total_verses, total_tokens "
        "FROM works ORDER BY tradition"
    ).fetchall()

    if not obras:
        print("\nLa base de datos no contiene ninguna obra.\n")
        return 1

    print(f"\nRevisando {len(obras)} obras en {db}\n")
    problemas: list[str] = []

    for w in obras:
        print(f"  {w['title']} — {w['edition']}")
        print(f"    {w['total_verses']:,} versículos · {w['total_tokens']:,} palabras"
              .replace(",", "."))

        muestra = [
            r["text"] for r in conn.execute(
                "SELECT text FROM verses WHERE work_id = ? "
                "ORDER BY id LIMIT 60", (w["id"],))
        ]

        # 1. ¿Está en el idioma que dice?
        diag = validar_idioma(muestra, w["language"])
        if diag.valido:
            print(f"    idioma: {w['language']} correcto "
                  f"({diag.alfabeto_detectado}, {diag.proporcion:.0%})")
        else:
            print(f"    IDIOMA INCORRECTO: dice «{w['language']}» pero el texto "
                  f"está en alfabeto {diag.alfabeto_detectado}")
            print(f"    muestra: {diag.muestra[:70]}")
            problemas.append(
                f"{w['id']}: declarado {w['language']}, "
                f"contiene {diag.alfabeto_detectado}"
            )

        # 2. ¿Contiene el vocabulario básico que cabría esperar?
        controles = CONTROLES.get(w["language"], [])
        if controles:
            ausentes = [
                c for c in controles
                if not conn.execute(
                    "SELECT 1 FROM lemma_index WHERE work_id = ? AND surface = ? "
                    "LIMIT 1", (w["id"], c)).fetchone()
            ]
            if len(ausentes) > len(controles) // 2:
                print(f"    VOCABULARIO SOSPECHOSO: faltan {ausentes}")
                problemas.append(f"{w['id']}: sin vocabulario básico {ausentes}")
            else:
                print("    vocabulario: normal")

        # 3. ¿Tiene un tamaño plausible?
        if w["total_verses"] and w["total_tokens"]:
            media = w["total_tokens"] / w["total_verses"]
            if media < 5:
                print(f"    AVISO: solo {media:.1f} palabras por versículo, "
                      f"puede faltar texto")
                problemas.append(f"{w['id']}: versículos muy cortos ({media:.1f})")
        print()

    conn.close()

    if problemas:
        print("=" * 60)
        print(f"{len(problemas)} PROBLEMA(S) ENCONTRADO(S):\n")
        for x in problemas:
            print(f"  - {x}")
        print("\nPara rehacer una obra concreta:")
        print("  python scripts/fetch_corpus.py --source ID --force\n")
        return 1

    print("=" * 60)
    print("Todas las obras contienen lo que declaran.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
