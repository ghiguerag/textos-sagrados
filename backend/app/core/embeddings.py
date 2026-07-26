"""
Similitud semántica entre versículos.

Permite responder "¿qué dice el Corán que se parezca a Mateo 5:7?" aunque no
compartan una sola palabra. Es lo que ninguna búsqueda por palabra clave puede
hacer.

Advertencia metodológica que la app debe mostrar al usuario: la similitud
vectorial mide parecido de superficie lingüística, NO equivalencia teológica.
Dos versículos con 0.9 de similitud pueden significar cosas muy distintas en
sus tradiciones. Es una herramienta de descubrimiento, no de prueba.
"""

from __future__ import annotations

import sqlite3
import struct
from pathlib import Path
from typing import Any, Callable, Sequence

import numpy as np

def get_model(name: str):
    """Devuelve el codificador correspondiente a un identificador de índice,
    a un nombre de preajuste o a un modelo de sentence-transformers."""
    from .encoders import resolve_encoder

    return resolve_encoder(name)


def pack_vector(vec: np.ndarray) -> bytes:
    return np.asarray(vec, dtype=np.float32).tobytes()


def unpack_vector(blob: bytes) -> np.ndarray:
    return np.frombuffer(blob, dtype=np.float32)


def _pending_query(model_name: str, work_ids: Sequence[str] | None):
    where = ""
    params: list[Any] = [model_name]
    if work_ids:
        where = f" AND v.work_id IN ({','.join('?' * len(work_ids))})"
        params += list(work_ids)
    return where, params


def pending_count(
    conn: sqlite3.Connection,
    model_name: str,
    *,
    work_ids: Sequence[str] | None = None,
) -> int:
    """Versículos que aún no tienen vector. Permite estimar el trabajo antes
    de empezar y saber si hace falta hacer algo."""
    where, params = _pending_query(model_name, work_ids)
    return conn.execute(
        f"""SELECT COUNT(*) AS n FROM verses v
            LEFT JOIN embeddings e ON e.verse_id = v.id AND e.model = ?
            WHERE e.verse_id IS NULL{where}""",
        params,
    ).fetchone()["n"]


def build_index(
    conn: sqlite3.Connection,
    model_name: str,
    *,
    batch_size: int = 128,
    work_ids: Sequence[str] | None = None,
    on_progress: Callable[[int, int], None] | None = None,
    encoder_preset: str | None = None,
) -> int:
    """Calcula y almacena un vector por versículo.

    Reanudable: solo procesa los que faltan, y guarda cada lote. Si el proceso
    se interrumpe a mitad —y con 61.000 versículos es fácil que alguien cierre
    la ventana—, al volver a ejecutarlo continúa desde donde iba.
    """
    encoder = get_model(encoder_preset or model_name)
    where, params = _pending_query(model_name, work_ids)

    rows = conn.execute(
        f"""SELECT v.id, v.text FROM verses v
            LEFT JOIN embeddings e ON e.verse_id = v.id AND e.model = ?
            WHERE e.verse_id IS NULL{where}
            ORDER BY v.id""",
        params,
    ).fetchall()

    total = len(rows)
    hechos = 0
    for i in range(0, total, batch_size):
        batch = rows[i : i + batch_size]
        # El codificador ya devuelve vectores normalizados: la búsqueda
        # compara con producto escalar, que equivale al coseno.
        vectors = encoder.encode([r["text"] for r in batch])
        conn.executemany(
            "INSERT OR REPLACE INTO embeddings (verse_id, model, vector) VALUES (?,?,?)",
            [(r["id"], model_name, pack_vector(v)) for r, v in zip(batch, vectors)],
        )
        conn.commit()          # guardar por lotes: hace el proceso reanudable
        hechos += len(batch)
        if on_progress:
            on_progress(hechos, total)
    return hechos


def _huella(texto: str) -> frozenset[str]:
    """Conjunto de palabras significativas de un versículo.

    Se usa para detectar el mismo pasaje en ediciones distintas. La Biblia
    King James y el Tanaj JPS comparten toda la Biblia hebrea, así que sin
    esto el usuario ve el mismo versículo dos veces y cree que ha encontrado
    dos cosas.
    """
    import re
    palabras = re.findall(r"[a-z']+", texto.lower())
    return frozenset(p for p in palabras if len(p) > 3)


def _mismo_pasaje(a: str, b: str, umbral: float = 0.6) -> bool:
    """Índice de Jaccard entre dos versículos.

    Umbral relativamente bajo a propósito: dos traducciones del mismo
    versículo hebreo comparten muchas palabras pero no todas, porque cada
    traductor eligió distinto. Con 0,6 se agrupan las traducciones del mismo
    pasaje sin fusionar versículos que solo tratan del mismo tema.
    """
    ha, hb = _huella(a), _huella(b)
    if not ha or not hb:
        return False
    return len(ha & hb) / len(ha | hb) >= umbral


def agrupar_duplicados(resultados: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Fusiona los resultados que son el mismo pasaje en ediciones distintas.

    Se conserva el de mayor similitud como principal y los demás quedan
    dentro, en `tambien_en`. Que un pasaje aparezca en varias tradiciones es
    información valiosa: no se descarta, se presenta bien.
    """
    agrupados: list[dict[str, Any]] = []
    for r in resultados:
        for g in agrupados:
            if _mismo_pasaje(g["text"], r["text"]):
                g.setdefault("tambien_en", []).append({
                    "verse_id": r["verse_id"], "ref": r["ref"],
                    "work_id": r["work_id"], "tradition": r["tradition"],
                    "text": r["text"], "similarity": r.get("similarity"),
                })
                break
        else:
            agrupados.append(dict(r))
    return agrupados


class VectorStore:
    """Índice en memoria. Con ~40.000 versículos son ~60 MB en float32 y la
    búsqueda exhaustiva tarda milisegundos: no hace falta FAISS."""

    def __init__(self, conn: sqlite3.Connection, model_name: str):
        rows = conn.execute(
            """SELECT e.verse_id, e.vector, v.ref, v.text, v.work_id, w.tradition
               FROM embeddings e
               JOIN verses v ON v.id = e.verse_id
               JOIN works w  ON w.id = v.work_id
               WHERE e.model = ?""",
            (model_name,),
        ).fetchall()

        self.model_name = model_name
        self.meta = [
            {"verse_id": r["verse_id"], "ref": r["ref"], "text": r["text"],
             "work_id": r["work_id"], "tradition": r["tradition"]}
            for r in rows
        ]
        self.matrix = (
            np.vstack([unpack_vector(r["vector"]) for r in rows])
            # La dimensión depende del motor (384, 512, 256 o 128), así que
            # se deduce de los datos en lugar de fijarse a mano.
            if rows else np.zeros((0, 0), dtype=np.float32)
        )

    def __len__(self) -> int:
        return len(self.meta)

    def search(
        self,
        query: str,
        *,
        top_k: int = 20,
        work_ids: Sequence[str] | None = None,
        exclude_work: str | None = None,
        min_similarity: float = 0.3,
        agrupar: bool = True,
    ) -> list[dict[str, Any]]:
        if not len(self):
            return []
        encoder = get_model(self.model_name)
        q = np.asarray(encoder.encode_one(query), dtype=np.float32)
        scores = self.matrix @ q       # coseno, porque todo está normalizado

        allowed = set(work_ids) if work_ids else None
        candidates = []
        for idx in np.argsort(-scores)[: top_k * 8]:
            m = self.meta[idx]
            if allowed and m["work_id"] not in allowed:
                continue
            if exclude_work and m["work_id"] == exclude_work:
                continue
            score = float(scores[idx])
            if score < min_similarity:
                break
            candidates.append({**m, "similarity": round(score, 4)})
            # Se recogen más de los pedidos porque al agrupar duplicados el
            # número final baja: si no, se devolverían menos de top_k.
            if len(candidates) >= top_k * 2:
                break

        if agrupar:
            candidates = agrupar_duplicados(candidates)
        return candidates[:top_k]

    def cross_tradition_matches(self, verse_id: int, *, top_k: int = 3) -> list[dict[str, Any]]:
        """Para un versículo dado, los más parecidos de CADA otra tradición.

        Es la función más interesante de la app: pone en paralelo cómo cuatro
        tradiciones expresan una idea próxima. Se agrupa por tradición a
        propósito, porque si no el corpus más grande (la Biblia, 40 veces el
        Gita) copaba todos los resultados por puro volumen.
        """
        try:
            idx = next(i for i, m in enumerate(self.meta) if m["verse_id"] == verse_id)
        except StopIteration:
            return []

        origen = self.meta[idx]
        scores = self.matrix @ self.matrix[idx]

        por_tradicion: dict[str, list[dict[str, Any]]] = {}
        for j in np.argsort(-scores):
            m = self.meta[j]
            if m["tradition"] == origen["tradition"]:
                continue
            bucket = por_tradicion.setdefault(m["tradition"], [])
            if len(bucket) < top_k:
                bucket.append({**m, "similarity": round(float(scores[j]), 4)})

        return [
            {"tradition": t, "matches": v}
            for t, v in sorted(por_tradicion.items(), key=lambda x: -x[1][0]["similarity"])
        ]
