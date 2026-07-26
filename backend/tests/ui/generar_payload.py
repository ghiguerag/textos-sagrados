#!/usr/bin/env python3
"""Genera datos reales de la API para las pruebas de la interfaz."""
import json
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.core import analysis as A          # noqa: E402
from app.core.db import connect             # noqa: E402
from app.core.lexicon import Lexicon        # noqa: E402

RAIZ = Path(__file__).resolve().parents[2]
db = sys.argv[1] if len(sys.argv) > 1 else str(RAIZ / "data" / "sample.db")

# Copia previa a disco local: SQLite falla al abrir en modo solo lectura sobre
# algunos sistemas de archivos (unidades de red, carpetas sincronizadas con
# OneDrive o Google Drive). Copiar evita el problema de raíz.
tmp = Path(tempfile.gettempdir()) / "ts_payload_src.db"
shutil.copy2(db, tmp)

conn = connect(tmp, readonly=True)
lx = Lexicon.load(RAIZ / "data" / "lexicon.json")
stems = A.resolve_query("", "en", lexicon=lx, semantic_field="misericordia")

freqs = A.frequency_by_work(conn, stems)
row = next(f.to_dict() for f in freqs if f.work_id == "kjv")

payload = {
    "row": row,
    "forms": {"work_id": "kjv", "results": A.surface_forms(conn, stems, work_id="kjv")},
    "books": [d.to_dict() for d in A.frequency_by_division(conn, stems, "kjv")],
    "verses": {"total": row["verse_count"],
               "items": A.concordance(conn, stems, work_ids=["kjv"], limit=400)},
}
destino = Path("/tmp/payload.json")
destino.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
print(f"payload en {destino}")
