#!/usr/bin/env python3
"""Construye una base de datos de desarrollo a partir de data/sample_corpus.json.

    python scripts/build_sample.py --out data/sample.db

No requiere red. Sirve para desarrollar la app y ejecutar los tests. Las cifras
que produce NO son analíticamente válidas: el fixture son ~100 versículos.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Iterator

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.ingest import VerseRecord, build_database  # noqa: E402
from scripts.fetch_corpus import SOURCES  # noqa: E402

SAMPLE = Path(__file__).resolve().parents[1] / "data" / "sample_corpus.json"


def load(work_id: str, payload: dict) -> Iterator[VerseRecord]:
    for item in payload["works"][work_id]:
        yield VerseRecord(
            division_ordinal=item["division_ordinal"],
            division_name=item["division_name"],
            chapter=item["chapter"],
            number=item["number"],
            text=item["text"],
            section=item.get("section"),
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="data/sample.db")
    args = parser.parse_args()

    payload = json.loads(SAMPLE.read_text(encoding="utf-8"))
    sources = [(SOURCES[wid][0], (lambda w=wid: load(w, payload))) for wid in payload["works"]]
    report = build_database(args.out, sources, resume=False)

    print(f"Base de muestra en {args.out}")
    for work_id, stats in report.items():
        print(f"  {work_id:16} {stats['verses']:>4} versículos  "
              f"{stats['tokens']:>6} palabras  {stats['divisions']:>3} divisiones")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
