#!/usr/bin/env python3
"""
Mide cuánta calidad se pierde al usar el motor ligero en lugar del pesado.

    python scripts/comparar_motores.py --base calidad --contra minimo

La pregunta que responde es concreta: si empaqueto el modelo pequeño en la app,
¿el usuario recibirá resultados peores? ¿Cuánto peores?

Se mide de tres formas, porque una sola cifra engañaría:

  1. SOLAPAMIENTO@10. De los 10 mejores resultados del motor bueno, cuántos
     aparecen también en los 10 del ligero. Es lo que percibe el usuario.

  2. COINCIDENCIA DEL PRIMERO. Si el resultado más relevante es el mismo.
     Importa más que el resto: es el que la gente lee.

  3. CORRELACIÓN DE ORDEN. Si además los ordena igual.

Requiere tener ambos índices construidos:
    python scripts/build_embeddings.py --engine calidad
    python scripts/build_embeddings.py --engine minimo
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np                                    # noqa: E402

from app.config import get_settings                    # noqa: E402
from app.core.db import connect                        # noqa: E402
from app.core.encoders import PRESETS, encoder_id, get_encoder   # noqa: E402
from app.core.embeddings import VectorStore            # noqa: E402

# Consultas de prueba en varios idiomas y de distinta dificultad. Mezclar
# idiomas es deliberado: el punto débil de un modelo pequeño suele ser
# precisamente el cruce entre idiomas.
CONSULTAS = [
    "perdonar a quien te ha hecho daño",
    "el destino del alma tras la muerte",
    "cómo debe tratarse al extranjero",
    "la riqueza es un obstáculo espiritual",
    "no juzgues a los demás",
    "el sufrimiento tiene un sentido",
    "la humildad ante lo divino",
    "obligación de socorrer al pobre",
    "forgiving those who wronged you",
    "the fate of the soul after death",
    "wealth as a spiritual obstacle",
    "duty to help the poor",
    "war is sometimes justified",
    "the value of silence and solitude",
    "parents deserve respect",
]


def solapamiento(a: list[int], b: list[int]) -> float:
    return len(set(a) & set(b)) / len(a) if a else 0.0


def rho_spearman(a: list[int], b: list[int]) -> float:
    """Correlación de orden sobre los elementos que ambos comparten."""
    comunes = [x for x in a if x in b]
    if len(comunes) < 2:
        return float("nan")
    ra = [a.index(x) for x in comunes]
    rb = [b.index(x) for x in comunes]
    n = len(comunes)
    d2 = sum((x - y) ** 2 for x, y in zip(ra, rb))
    return 1 - (6 * d2) / (n * (n * n - 1))


def main() -> int:
    settings = get_settings()
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--db", default=str(settings.db_path))
    p.add_argument("--base", default="calidad", choices=sorted(PRESETS),
                   help="motor de referencia")
    p.add_argument("--contra", default="minimo", choices=sorted(PRESETS),
                   help="motor a evaluar")
    p.add_argument("--k", type=int, default=10)
    p.add_argument("--ejemplos", type=int, default=3,
                   help="cuántas consultas mostrar en detalle")
    args = p.parse_args()

    conn = connect(args.db, readonly=True)

    tiendas = {}
    for preset in (args.base, args.contra):
        mid = encoder_id(preset)
        n = conn.execute(
            "SELECT COUNT(*) AS n FROM embeddings WHERE model = ?", (mid,)
        ).fetchone()["n"]
        if not n:
            print(f"\nFalta el índice del motor «{preset}».")
            print(f"Constrúyelo con:  python scripts/build_embeddings.py --engine {preset}\n")
            return 1
        tiendas[preset] = VectorStore(conn, mid)
        print(f"  {preset:12} {n:>7,} vectores, {tiendas[preset].matrix.shape[1]} dimensiones"
              .replace(",", "."))

    print(f"\nComparando {args.contra} contra {args.base} en {len(CONSULTAS)} consultas\n")
    print(f"  {'consulta':42} {'solap@' + str(args.k):>9} {'1º igual':>9} {'orden':>8}")
    print("  " + "-" * 70)

    solapes, primeros, ordenes = [], [], []
    detalles = []

    for q in CONSULTAS:
        res = {}
        for preset, tienda in tiendas.items():
            enc = get_encoder(preset)
            v = enc.encode_one(q).astype(np.float32)
            scores = tienda.matrix @ v
            idx = np.argsort(-scores)[: args.k]
            res[preset] = [tienda.meta[i]["verse_id"] for i in idx]

        a, b = res[args.base], res[args.contra]
        s = solapamiento(a, b)
        prim = 1.0 if a and b and a[0] == b[0] else 0.0
        rho = rho_spearman(a, b)

        solapes.append(s); primeros.append(prim)
        if not np.isnan(rho):
            ordenes.append(rho)

        print(f"  {q[:40]:42} {s:>8.0%} {'sí' if prim else 'no':>9} "
              f"{'—' if np.isnan(rho) else format(rho, '.2f'):>8}")
        detalles.append((q, a, b))

    print("  " + "-" * 70)
    print(f"  {'MEDIA':42} {np.mean(solapes):>8.0%} {np.mean(primeros):>8.0%} "
          f"{np.mean(ordenes) if ordenes else float('nan'):>8.2f}")

    # Ejemplos concretos: una cifra media no deja ver si los fallos son
    # catastróficos o irrelevantes.
    tienda_a, tienda_b = tiendas[args.base], tiendas[args.contra]
    ref = {m["verse_id"]: m for m in tienda_a.meta}
    ref.update({m["verse_id"]: m for m in tienda_b.meta})

    print("\n\nEJEMPLOS CONCRETOS")
    for q, a, b in detalles[: args.ejemplos]:
        print(f"\n  «{q}»")
        print(f"    {args.base:10} → {ref.get(a[0], {}).get('ref', '?')}: "
              f"{ref.get(a[0], {}).get('text', '')[:80]}")
        print(f"    {args.contra:10} → {ref.get(b[0], {}).get('ref', '?')}: "
              f"{ref.get(b[0], {}).get('text', '')[:80]}")

    media = np.mean(solapes)
    print("\n\nLECTURA DEL RESULTADO")
    if media >= 0.7:
        print("  Solapamiento alto. El motor ligero es un sustituto razonable:")
        print("  el usuario vería prácticamente los mismos pasajes.")
    elif media >= 0.5:
        print("  Solapamiento medio. Sirve para descubrir, pero cambia bastante")
        print("  el orden. Aceptable si se prioriza el tamaño de la app.")
    else:
        print("  Solapamiento bajo. Los resultados difieren demasiado: conviene")
        print("  el motor pesado en servidor, o una opción intermedia.")
    print()

    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
