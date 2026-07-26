#!/usr/bin/env python3
"""
Elimina del corpus las obras cuyo texto no está en el idioma declarado.

    python scripts/limpiar_corpus.py          # muestra qué haría
    python scripts/limpiar_corpus.py --si     # lo hace

Se escribió tras descubrir un Corán descargado en árabe pero declarado como
inglés. Una obra así no solo es inútil: contamina las comparaciones, porque
sus ceros parecen datos.
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




def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--db", default=_ruta_por_defecto())
    p.add_argument("--si", action="store_true",
                   help="ejecutar de verdad; sin esto solo informa")
    args = p.parse_args()

    db = Path(args.db)
    if not db.exists():
        print(f"\nNo encuentro la base de datos en {db}\n")
        return 1

    conn = connect(db)
    corruptas: list[tuple[str, str, str]] = []

    for w in conn.execute(
        "SELECT id, title, edition, language FROM works ORDER BY tradition"
    ).fetchall():
        muestra = [
            r["text"] for r in conn.execute(
                "SELECT text FROM verses WHERE work_id = ? ORDER BY id LIMIT 60",
                (w["id"],))
        ]
        if not muestra:
            continue
        diag = validar_idioma(muestra, w["language"])
        if not diag.valido:
            corruptas.append((w["id"], f"{w['title']} — {w['edition']}",
                              diag.alfabeto_detectado))

    if not corruptas:
        print("\nNinguna obra está en un idioma equivocado. No hay nada que limpiar.\n")
        conn.close()
        return 0

    print(f"\n{len(corruptas)} obra(s) en el idioma equivocado:\n")
    for wid, nombre, alfabeto in corruptas:
        n = conn.execute(
            "SELECT COUNT(*) AS n FROM verses WHERE work_id = ?", (wid,)
        ).fetchone()["n"]
        print(f"  {wid:18} {nombre}")
        print(f"  {'':18} {n:,} versículos en alfabeto {alfabeto}".replace(",", "."))

    if not args.si:
        print("\nEsto es solo un informe. Para eliminarlas:")
        print("  python scripts/limpiar_corpus.py --si\n")
        conn.close()
        return 0

    print()
    # Sin este índice, el borrado en cascada recorre los millones de filas de
    # lemma_index y tarda minutos. Crearlo cuesta segundos y lo deja en varios
    # órdenes de magnitud menos.
    print("  preparando índices… ", end="", flush=True)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_lemma_solo_work "
                 "ON lemma_index(work_id)")
    conn.commit()
    print("hecho")

    conn.execute("PRAGMA foreign_keys = ON")
    for wid, nombre, _ in corruptas:
        print(f"  eliminando {wid}… ", end="", flush=True)
        conn.execute("DELETE FROM works WHERE id = ?", (wid,))
        conn.commit()
        print("hecho")

    # No se recalculan agregados ni se reconstruye el índice de búsqueda.
    # El esquema declara ON DELETE CASCADE en divisions, verses, lemma_index
    # y lemma_totals, y hay un disparador que limpia el índice de texto al
    # borrar cada versículo. Todo queda coherente solo.
    #
    # Reconstruirlo a mano tardaba varios minutos sobre un corpus de 60.000
    # versículos, para no cambiar absolutamente nada: los totales de las
    # obras que se conservan no dependen de las que se van.

    quedan = conn.execute("SELECT COUNT(*) AS n FROM works").fetchone()["n"]
    conn.close()
    print(f"\nListo. Quedan {quedan} obras en el corpus.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
