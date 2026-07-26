#!/usr/bin/env python3
"""
Construye el índice de búsqueda por significado.

    python scripts/build_embeddings.py

Convierte cada versículo en un vector numérico que representa su significado.
Después, buscar una idea consiste en encontrar los vectores más próximos, lo
que permite encontrar pasajes afines aunque no compartan ni una palabra.

La primera vez descarga un modelo de unos 470 MB. El cálculo de ~61.000
versículos tarda entre 3 y 15 minutos según el ordenador.

El proceso es reanudable: si se interrumpe, al volver a ejecutarlo continúa
desde donde lo dejó.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import get_settings          # noqa: E402
from app.core.db import connect               # noqa: E402
from app.core.encoders import PRESETS, encoder_id   # noqa: E402


def formato_tiempo(segundos: float) -> str:
    if segundos < 60:
        return f"{segundos:.0f} s"
    if segundos < 3600:
        return f"{segundos / 60:.0f} min {segundos % 60:.0f} s"
    return f"{segundos / 3600:.1f} h"


def barra(hecho: int, total: int, ancho: int = 34) -> str:
    if total <= 0:
        return ""
    lleno = int(ancho * hecho / total)
    return "[" + "#" * lleno + "." * (ancho - lleno) + "]"


def main() -> int:
    settings = get_settings()
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--db", default=str(settings.db_path))
    parser.add_argument("--engine", default="calidad", choices=sorted(PRESETS),
                        help=" | ".join(f"{k}: {v['descripcion']}"
                                        for k, v in PRESETS.items()))
    parser.add_argument("--work", nargs="*", help="limitar a ciertas obras")
    parser.add_argument("--batch", type=int, default=128,
                        help="versículos por lote; baja a 32 si te quedas sin memoria")
    args = parser.parse_args()

    modelo_id = encoder_id(args.engine)
    tipo = PRESETS[args.engine]["tipo"]

    # ---- comprobación de dependencias, con mensaje útil si faltan ----
    try:
        if tipo == "torch":
            import sentence_transformers   # noqa: F401
        else:
            import model2vec               # noqa: F401
    except ImportError:
        print(f"\nFalta lo necesario para el motor «{args.engine}».\n")
        if tipo == "torch":
            print("En Windows:  doble clic en INSTALAR-BUSQUEDA-Windows.bat")
            print("A mano:      pip install --only-binary=:all: -r requirements-semantic.txt\n")
        else:
            print("En Windows:  doble clic en INSTALAR-BUSQUEDA-LIGERA-Windows.bat")
            print("A mano:      pip install --only-binary=:all: -r requirements-light.txt\n")
        return 1

    db = Path(args.db)
    if not db.exists():
        print(f"\nNo encuentro la base de datos en {db}")
        print("Ejecuta primero el instalador para descargar los textos.\n")
        return 1

    conn = connect(db)

    from app.core.embeddings import build_index, pending_count  # noqa: E402

    pendientes = pending_count(conn, modelo_id, work_ids=args.work)
    ya_hechos = conn.execute(
        "SELECT COUNT(*) AS n FROM embeddings WHERE model = ?", (modelo_id,)
    ).fetchone()["n"]

    if not pendientes:
        print(f"\nEl índice ya está completo: {ya_hechos:,} versículos.".replace(",", "."))
        print("Reinicia el servidor si aún no lo has hecho.\n")
        conn.close()
        return 0

    print(f"\nMotor:       {args.engine} — {PRESETS[args.engine]['descripcion']}")
    print(f"Identificador: {modelo_id}")
    print(f"Base:        {db}")
    if ya_hechos:
        print(f"Ya hechos:   {ya_hechos:,}".replace(",", "."))
    print(f"Pendientes:  {pendientes:,}".replace(",", "."))
    print("\nLa primera vez descarga el modelo. Ten paciencia:")
    print("durante la descarga no se ve progreso.\n")

    inicio = time.time()
    ultimo = [0.0]

    def progreso(hechos: int, total: int) -> None:
        ahora = time.time()
        if ahora - ultimo[0] < 0.5 and hechos < total:
            return
        ultimo[0] = ahora
        transcurrido = ahora - inicio
        ritmo = hechos / transcurrido if transcurrido > 0 else 0
        restante = (total - hechos) / ritmo if ritmo > 0 else 0
        pct = 100 * hechos / total if total else 100
        sys.stdout.write(
            f"\r  {barra(hechos, total)} {pct:5.1f}%  "
            f"{hechos:>6,}/{total:,}".replace(",", ".") +
            f"  {ritmo:>5.0f}/s  faltan {formato_tiempo(restante)}   "
        )
        sys.stdout.flush()

    try:
        n = build_index(conn, modelo_id, batch_size=args.batch,
                        work_ids=args.work, on_progress=progreso,
                        encoder_preset=args.engine)
    except KeyboardInterrupt:
        print("\n\nInterrumpido. Lo calculado se ha guardado.")
        print("Vuelve a ejecutar este script para continuar donde lo dejaste.\n")
        conn.close()
        return 1

    total = conn.execute(
        "SELECT COUNT(*) AS n FROM embeddings WHERE model = ?", (modelo_id,)
    ).fetchone()["n"]
    conn.close()

    print(f"\n\nListo. {n:,} vectores nuevos, {total:,} en total."
          .replace(",", "."))
    print(f"Tiempo: {formato_tiempo(time.time() - inicio)}")
    print("\nReinicia el servidor y aparecerá la pestaña «Por significado».\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
