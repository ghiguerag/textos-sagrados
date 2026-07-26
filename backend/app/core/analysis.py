"""
Motor de análisis comparativo.

Tres decisiones metodológicas que sostienen la credibilidad de la app:

1. NUNCA se comparan conteos brutos. La Biblia tiene ~790.000 palabras y el
   Bhagavad Gita ~20.000. Decir "la Biblia menciona 'amor' 300 veces y el Gita
   40" no significa nada. Todo se expresa en tasas por 10.000 palabras.

2. La significación se mide con log-likelihood (Dunning 1993), el estándar de
   la lingüística de corpus para "keyness". Una diferencia de tasas puede ser
   ruido; G² dice si lo es.

3. Se reporta también la dispersión (en cuántas divisiones aparece el término).
   Un término que sale 50 veces en un solo capítulo no describe la obra igual
   que uno que sale 50 veces repartidas por todo el texto.
"""

from __future__ import annotations

import math
import sqlite3
from dataclasses import dataclass, asdict
from typing import Any, Iterable, Sequence

from .tokenizer import normalize, stem

PER = 10_000  # base de normalización


# --------------------------------------------------------------------------
# Modelos de resultado
# --------------------------------------------------------------------------

@dataclass
class WorkFrequency:
    work_id: str
    work_title: str
    tradition: str
    language: str
    raw_count: int
    verse_count: int
    total_tokens: int
    per_10k: float
    dispersion: float          # 0-1: proporción de divisiones donde aparece
    divisions_present: int
    divisions_total: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class DivisionFrequency:
    division_id: int
    name: str
    ordinal: int
    section: str | None
    raw_count: int
    total_tokens: int
    per_10k: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Keyness:
    work_id: str
    reference_id: str
    log_likelihood: float
    effect_size: float         # log ratio, más interpretable que G²
    direction: str             # 'over' | 'under' (clave, la traduce el cliente)
    significant: bool          # p < 0.0001 (G² > 15.13, 1 gl)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# --------------------------------------------------------------------------
# Resolución de la consulta a un conjunto de raíces
# --------------------------------------------------------------------------

def resolve_query(
    term: str,
    lang: str,
    *,
    lexicon=None,
    semantic_field: str | None = None,
    extra_terms: Sequence[str] = (),
) -> set[str]:
    """Convierte lo que pide el usuario en el conjunto de lemas a contar."""
    stems: set[str] = set()
    if term:
        stems.add(stem(normalize(term, lang=lang), lang))
    for w in extra_terms:
        stems.add(stem(normalize(w, lang=lang), lang))
    if semantic_field and lexicon is not None:
        stems |= lexicon.expand(semantic_field, lang)
    return {s for s in stems if s}


# --------------------------------------------------------------------------
# Frecuencia por obra
# --------------------------------------------------------------------------

def frequency_by_work(
    conn: sqlite3.Connection,
    stems: Iterable[str],
    *,
    work_ids: Sequence[str] | None = None,
) -> list[WorkFrequency]:
    stems = list(stems)
    if not stems:
        return []

    placeholders = ",".join("?" * len(stems))
    params: list[Any] = list(stems)
    work_filter = ""
    if work_ids:
        work_filter = f" AND w.id IN ({','.join('?' * len(work_ids))})"
        params += list(work_ids)

    rows = conn.execute(
        f"""
        SELECT
            w.id, w.title, w.edition, w.tradition, w.language, w.total_tokens,
            COALESCE(SUM(t.count), 0)       AS raw_count,
            COALESCE(SUM(t.verse_count), 0) AS verse_count
        FROM works w
        LEFT JOIN lemma_totals t
               ON t.work_id = w.id AND t.lemma IN ({placeholders})
        WHERE 1=1{work_filter}
        GROUP BY w.id
        ORDER BY w.tradition, w.title
        """,
        params,
    ).fetchall()

    dispersion = _dispersion_by_work(conn, stems)

    results: list[WorkFrequency] = []
    for r in rows:
        present, total = dispersion.get(r["id"], (0, 0))
        results.append(
            WorkFrequency(
                work_id=r["id"],
                work_title=f'{r["title"]} ({r["edition"]})',
                tradition=r["tradition"],
                language=r["language"],
                raw_count=r["raw_count"],
                verse_count=r["verse_count"],
                total_tokens=r["total_tokens"],
                per_10k=round(r["raw_count"] * PER / r["total_tokens"], 3) if r["total_tokens"] else 0.0,
                dispersion=round(present / total, 3) if total else 0.0,
                divisions_present=present,
                divisions_total=total,
            )
        )
    return results


def _dispersion_by_work(conn: sqlite3.Connection, stems: Sequence[str]) -> dict[str, tuple[int, int]]:
    placeholders = ",".join("?" * len(stems))
    totals = {
        r["work_id"]: r["n"]
        for r in conn.execute("SELECT work_id, COUNT(*) AS n FROM divisions GROUP BY work_id")
    }
    present = {
        r["work_id"]: r["n"]
        for r in conn.execute(
            f"""SELECT work_id, COUNT(DISTINCT division_id) AS n
                FROM lemma_index WHERE lemma IN ({placeholders}) GROUP BY work_id""",
            list(stems),
        )
    }
    return {wid: (present.get(wid, 0), n) for wid, n in totals.items()}


# --------------------------------------------------------------------------
# Distribución interna: el mapa de calor
# --------------------------------------------------------------------------

def frequency_by_division(
    conn: sqlite3.Connection,
    stems: Iterable[str],
    work_id: str,
) -> list[DivisionFrequency]:
    stems = list(stems)
    if not stems:
        return []
    placeholders = ",".join("?" * len(stems))
    rows = conn.execute(
        f"""
        SELECT d.id, d.name, d.ordinal, d.section, d.total_tokens,
               COALESCE(COUNT(li.verse_id), 0) AS raw_count
        FROM divisions d
        LEFT JOIN lemma_index li
               ON li.division_id = d.id AND li.lemma IN ({placeholders})
        WHERE d.work_id = ?
        GROUP BY d.id
        ORDER BY d.ordinal
        """,
        [*stems, work_id],
    ).fetchall()

    return [
        DivisionFrequency(
            division_id=r["id"],
            name=r["name"],
            ordinal=r["ordinal"],
            section=r["section"],
            raw_count=r["raw_count"],
            total_tokens=r["total_tokens"],
            per_10k=round(r["raw_count"] * PER / r["total_tokens"], 3) if r["total_tokens"] else 0.0,
        )
        for r in rows
    ]


# --------------------------------------------------------------------------
# Keyness (log-likelihood de Dunning)
# --------------------------------------------------------------------------

def log_likelihood(a: int, b: int, c: int, d: int) -> tuple[float, float]:
    """G² y log ratio.

    a = ocurrencias en el corpus objetivo      c = tamaño del corpus objetivo
    b = ocurrencias en el corpus de referencia d = tamaño del de referencia
    """
    if c <= 0 or d <= 0:
        return 0.0, 0.0

    e1 = c * (a + b) / (c + d)
    e2 = d * (a + b) / (c + d)
    g2 = 0.0
    if a > 0 and e1 > 0:
        g2 += a * math.log(a / e1)
    if b > 0 and e2 > 0:
        g2 += b * math.log(b / e2)
    g2 *= 2.0

    # Corrección de continuidad: evita división por cero cuando un corpus
    # tiene cero ocurrencias, que es un caso muy común aquí.
    rate_a = (a + 0.5) / c
    rate_b = (b + 0.5) / d
    log_ratio = math.log2(rate_a / rate_b)

    return round(g2, 3), round(log_ratio, 3)


CRITICAL_G2 = 15.13  # p < 0.0001, 1 grado de libertad


def keyness(
    frequencies: Sequence[WorkFrequency],
    target_id: str,
    reference_id: str,
) -> Keyness | None:
    by_id = {f.work_id: f for f in frequencies}
    target, reference = by_id.get(target_id), by_id.get(reference_id)
    if not target or not reference:
        return None

    g2, lr = log_likelihood(
        target.raw_count, reference.raw_count,
        target.total_tokens, reference.total_tokens,
    )
    return Keyness(
        work_id=target_id,
        reference_id=reference_id,
        log_likelihood=g2,
        effect_size=lr,
        direction="over" if lr > 0 else "under",
        significant=g2 > CRITICAL_G2,
    )


def keyness_matrix(frequencies: Sequence[WorkFrequency]) -> list[dict[str, Any]]:
    """Compara cada obra contra la suma de todas las demás.

    Es más informativo que comparar pares: responde "¿qué distingue a este
    texto del resto del conjunto?"
    """
    total_count = sum(f.raw_count for f in frequencies)
    total_tokens = sum(f.total_tokens for f in frequencies)

    out: list[dict[str, Any]] = []
    for f in frequencies:
        g2, lr = log_likelihood(
            f.raw_count, total_count - f.raw_count,
            f.total_tokens, total_tokens - f.total_tokens,
        )
        out.append({
            "work_id": f.work_id,
            "work_title": f.work_title,
            "log_likelihood": g2,
            "effect_size": lr,
            "direction": "over" if lr > 0 else "under",
            "significant": g2 > CRITICAL_G2,
        })
    return sorted(out, key=lambda x: -x["log_likelihood"])


# --------------------------------------------------------------------------
# Concordancia KWIC (keyword in context)
# --------------------------------------------------------------------------

def concordance(
    conn: sqlite3.Connection,
    stems: Iterable[str],
    *,
    work_ids: Sequence[str] | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[dict[str, Any]]:
    stems = list(stems)
    if not stems:
        return []
    placeholders = ",".join("?" * len(stems))
    params: list[Any] = list(stems)
    work_filter = ""
    if work_ids:
        work_filter = f" AND v.work_id IN ({','.join('?' * len(work_ids))})"
        params += list(work_ids)
    params += [limit, offset]

    rows = conn.execute(
        f"""
        SELECT v.id, v.ref, v.text, v.work_id, w.title, w.tradition,
               d.name AS division_name,
               GROUP_CONCAT(DISTINCT li.surface) AS matched_forms,
               COUNT(li.position) AS hits
        FROM lemma_index li
        JOIN verses v    ON v.id = li.verse_id
        JOIN works w     ON w.id = v.work_id
        JOIN divisions d ON d.id = v.division_id
        WHERE li.lemma IN ({placeholders}){work_filter}
        GROUP BY v.id
        ORDER BY w.tradition, d.ordinal, v.chapter, v.number
        LIMIT ? OFFSET ?
        """,
        params,
    ).fetchall()

    return [
        {
            "verse_id": r["id"],
            "ref": r["ref"],
            "text": r["text"],
            "work_id": r["work_id"],
            "work_title": r["title"],
            "tradition": r["tradition"],
            "division": r["division_name"],
            "matched_forms": (r["matched_forms"] or "").split(","),
            "hits": r["hits"],
        }
        for r in rows
    ]


# --------------------------------------------------------------------------
# Comparación por secciones dentro de una misma obra
# --------------------------------------------------------------------------

def frequency_by_section(
    conn: sqlite3.Connection,
    stems: Iterable[str],
    work_id: str,
) -> list[dict[str, Any]]:
    """Frecuencia agrupada por sección, con contraste entre secciones.

    Es el análisis más interesante que permite este corpus y el menos obvio.
    Las suras de La Meca y las de Medina se escribieron en circunstancias muy
    distintas, y su vocabulario lo refleja. Lo mismo ocurre entre el Antiguo y
    el Nuevo Testamento, o entre la Torá, los Profetas y los Escritos.

    Comparar secciones de una misma obra evita además el problema de fondo de
    comparar traducciones distintas: aquí el traductor es el mismo, así que
    las diferencias son del texto, no del traductor. Metodológicamente es la
    comparación más sólida que ofrece la aplicación.
    """
    stems = list(stems)
    if not stems:
        return []

    placeholders = ",".join("?" * len(stems))
    rows = conn.execute(
        f"""
        SELECT COALESCE(d.section, 'Sin sección') AS section,
               COUNT(DISTINCT d.id)      AS divisions,
               SUM(d.total_tokens)       AS total_tokens,
               COALESCE((
                   SELECT COUNT(*) FROM lemma_index li
                   JOIN divisions dd ON dd.id = li.division_id
                   WHERE dd.work_id = d.work_id
                     AND COALESCE(dd.section, 'Sin sección') = COALESCE(d.section, 'Sin sección')
                     AND li.lemma IN ({placeholders})
               ), 0) AS raw_count
        FROM divisions d
        WHERE d.work_id = ?
        GROUP BY COALESCE(d.section, 'Sin sección')
        ORDER BY MIN(d.ordinal)
        """,
        [*stems, work_id],
    ).fetchall()

    secciones = [
        {
            "section": r["section"],
            "divisions": r["divisions"],
            "total_tokens": r["total_tokens"] or 0,
            "raw_count": r["raw_count"],
            "per_10k": round(r["raw_count"] * PER / r["total_tokens"], 3)
            if r["total_tokens"] else 0.0,
        }
        for r in rows
    ]

    # Contraste de cada sección contra el resto de la MISMA obra.
    total_count = sum(s["raw_count"] for s in secciones)
    total_tokens = sum(s["total_tokens"] for s in secciones)
    for s in secciones:
        g2, lr = log_likelihood(
            s["raw_count"], total_count - s["raw_count"],
            s["total_tokens"], total_tokens - s["total_tokens"],
        )
        s["log_likelihood"] = g2
        s["effect_size"] = lr
        s["direction"] = "over" if lr > 0 else "under"
        s["significant"] = g2 > CRITICAL_G2

    return secciones


# --------------------------------------------------------------------------
# Desglose por forma de palabra
# --------------------------------------------------------------------------

def surface_forms(
    conn: sqlite3.Connection,
    stems: Iterable[str],
    *,
    work_id: str | None = None,
) -> list[dict[str, Any]]:
    """Qué formas concretas componen el recuento.

    Una búsqueda por «mercy» agrupa mercy, merciful, mercies… Este desglose
    muestra el reparto real, que a menudo es más revelador que el total: dos
    corpus pueden empatar en frecuencia y usar formas muy distintas, uno
    volcado en el sustantivo y otro en el adjetivo.
    """
    stems = list(stems)
    if not stems:
        return []

    placeholders = ",".join("?" * len(stems))
    params: list[Any] = list(stems)
    filt = ""
    if work_id:
        filt = " AND work_id = ?"
        params.append(work_id)

    rows = conn.execute(
        f"""SELECT surface, COUNT(*) AS count, COUNT(DISTINCT verse_id) AS verse_count
            FROM lemma_index
            WHERE lemma IN ({placeholders}){filt}
            GROUP BY surface
            ORDER BY count DESC, surface""",
        params,
    ).fetchall()

    total = sum(r["count"] for r in rows) or 1
    return [
        {
            "surface": r["surface"],
            "count": r["count"],
            "verse_count": r["verse_count"],
            "share": round(r["count"] * 100 / total, 1),
        }
        for r in rows
    ]


# --------------------------------------------------------------------------
# Colocaciones: qué palabras acompañan al término
# --------------------------------------------------------------------------

def collocations(
    conn: sqlite3.Connection,
    stems: Iterable[str],
    *,
    work_id: str | None = None,
    window: int = 5,
    min_freq: int = 3,
    limit: int = 40,
) -> list[dict[str, Any]]:
    """Vecinos frecuentes dentro de una ventana, puntuados por información
    mutua (PMI). Revela el marco conceptual: junto a 'guerra' ¿aparece
    'justicia', 'santo', 'castigo'?"""
    stems = list(stems)
    if not stems:
        return []

    placeholders = ",".join("?" * len(stems))
    filt = " AND a.work_id = ?" if work_id else ""
    extra = [work_id] if work_id else []

    # Todo en una sola consulta. Antes se lanzaba una consulta por cada
    # palabra vecina —hasta cuarenta seguidas— y ese tiempo bastaba para que
    # otra petición se cruzara y corrompiera el cursor compartido. Además de
    # ser correcto, esto es mucho más rápido.
    rows = conn.execute(
        f"""
        WITH anchors AS (
            SELECT verse_id, position, work_id FROM lemma_index
            WHERE lemma IN ({placeholders})
        ),
        totales AS (
            SELECT
                (SELECT COALESCE(SUM(total_tokens), 0) FROM works)               AS corpus,
                (SELECT COUNT(*) FROM lemma_index WHERE lemma IN ({placeholders})) AS anclas
        )
        SELECT b.lemma,
               COUNT(*)          AS joint,
               MIN(b.surface)    AS example,
               COALESCE((SELECT SUM(count) FROM lemma_totals t
                         WHERE t.lemma = b.lemma), 0) AS collocate_total,
               (SELECT corpus FROM totales) AS corpus_total,
               (SELECT anclas FROM totales) AS anchor_total
        FROM anchors a
        JOIN lemma_index b ON b.verse_id = a.verse_id
                          AND b.position <> a.position
                          AND ABS(b.position - a.position) <= ?
        WHERE b.lemma NOT IN ({placeholders}){filt}
        GROUP BY b.lemma
        HAVING joint >= ?
        ORDER BY joint DESC
        LIMIT ?
        """,
        [*stems, *stems, window, *stems, *extra, min_freq, limit],
    ).fetchall()

    out: list[dict[str, Any]] = []
    for r in rows:
        corpus = r["corpus_total"] or 1
        anclas = r["anchor_total"] or 1
        vecina = r["collocate_total"] or 1

        p_joint = r["joint"] / corpus
        p_esperado = (anclas / corpus) * (vecina / corpus)
        pmi = math.log2(p_joint / p_esperado) if p_esperado > 0 and p_joint > 0 else 0.0

        out.append({
            "lemma": r["lemma"],
            "example": r["example"],
            "joint_count": r["joint"],
            "pmi": round(pmi, 3),
        })
    return sorted(out, key=lambda x: -x["pmi"])


# --------------------------------------------------------------------------
# Vocabulario distintivo de una obra
# --------------------------------------------------------------------------

def distinctive_vocabulary(
    conn: sqlite3.Connection,
    work_id: str,
    *,
    limit: int = 50,
    min_count: int = 5,
) -> list[dict[str, Any]]:
    """Los lemas que más distinguen esta obra del resto del corpus, por G²."""
    target_tokens = conn.execute(
        "SELECT total_tokens FROM works WHERE id = ?", (work_id,)
    ).fetchone()
    if not target_tokens:
        return []
    c = target_tokens["total_tokens"]
    d = conn.execute(
        "SELECT COALESCE(SUM(total_tokens), 0) AS n FROM works WHERE id <> ?", (work_id,)
    ).fetchone()["n"]

    rows = conn.execute(
        """
        SELECT t.lemma,
               SUM(CASE WHEN t.work_id = ?  THEN t.count ELSE 0 END) AS a,
               SUM(CASE WHEN t.work_id <> ? THEN t.count ELSE 0 END) AS b
        FROM lemma_totals t
        GROUP BY t.lemma
        HAVING a >= ?
        """,
        (work_id, work_id, min_count),
    ).fetchall()

    scored = []
    for r in rows:
        g2, lr = log_likelihood(r["a"], r["b"], c, d)
        if lr > 0 and g2 > CRITICAL_G2:
            scored.append({
                "lemma": r["lemma"],
                "count": r["a"],
                "count_elsewhere": r["b"],
                "per_10k": round(r["a"] * PER / c, 3) if c else 0.0,
                "log_likelihood": g2,
                "effect_size": lr,
            })
    return sorted(scored, key=lambda x: -x["log_likelihood"])[:limit]
