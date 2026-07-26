"""
Ingesta de corpus: convierte cualquier fuente al esquema unificado.

Un `CorpusSource` describe de dónde viene un texto y cómo mapear su estructura
nativa (libro/capítulo/versículo, sura/aleya, capítulo/sloka) al modelo común.
Añadir un texto nuevo = añadir un adaptador, sin tocar el motor.
"""

from __future__ import annotations

import itertools
import json
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterator

from .db import init_schema, rebuild_aggregates, transaction
from .tokenizer import token_count, tokenize
from .validacion import IdiomaIncorrectoError, validar_idioma


@dataclass
class VerseRecord:
    division_ordinal: int
    division_name: str
    chapter: int
    number: int
    text: str
    section: str | None = None
    division_name_alt: str | None = None


@dataclass
class CorpusSource:
    """Metadatos + adaptador de un texto."""
    id: str
    tradition: str
    title: str
    edition: str
    language: str
    license: str
    year: int | None = None
    source_url: str | None = None
    division_label: str = "libro"
    subdivision_label: str = "capitulo"
    verse_label: str = "versiculo"
    ref_format: Callable[[VerseRecord], str] | None = None
    loader: Callable[[], Iterator[VerseRecord]] | None = None

    def make_ref(self, v: VerseRecord) -> str:
        if self.ref_format:
            return self.ref_format(v)
        return f"{v.division_name} {v.chapter}:{v.number}"


MUESTRA_VALIDACION = 40


def ingest_source(conn: sqlite3.Connection, source: CorpusSource,
                  verses: Iterator[VerseRecord]) -> dict[str, int]:
    """Inserta una obra completa y construye su índice de lemas.

    Antes de tocar la base de datos comprueba que el texto está realmente en
    el idioma declarado. Una fuente puede devolver algo distinto de lo pedido
    sin dar ningún error, y un corpus con el texto equivocado es peor que uno
    vacío: no se nota, y todos los análisis salen mal en silencio.
    """
    verses = iter(verses)
    cabecera: list[VerseRecord] = []
    for v in verses:
        cabecera.append(v)
        if len(cabecera) >= MUESTRA_VALIDACION:
            break

    if cabecera:
        diag = validar_idioma([v.text for v in cabecera], source.language)
        if not diag.valido:
            raise IdiomaIncorrectoError(
                diag.explicar(f"{source.title} ({source.edition})", source.language)
            )

    # La muestra ya consumida se vuelve a encadenar con el resto.
    verses = itertools.chain(cabecera, verses)

    with transaction(conn):
        conn.execute("DELETE FROM works WHERE id = ?", (source.id,))
        conn.execute(
            """INSERT INTO works
               (id, tradition, title, edition, language, year, license, source_url,
                division_label, subdivision_label, verse_label)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (source.id, source.tradition, source.title, source.edition, source.language,
             source.year, source.license, source.source_url,
             source.division_label, source.subdivision_label, source.verse_label),
        )

        division_ids: dict[int, int] = {}
        n_verses = 0
        n_tokens = 0

        for v in verses:
            if v.division_ordinal not in division_ids:
                cur = conn.execute(
                    """INSERT INTO divisions (work_id, ordinal, name, name_alt, section)
                       VALUES (?,?,?,?,?)""",
                    (source.id, v.division_ordinal, v.division_name,
                     v.division_name_alt, v.section),
                )
                division_ids[v.division_ordinal] = cur.lastrowid
            div_id = division_ids[v.division_ordinal]

            tc = token_count(v.text, lang=source.language)
            cur = conn.execute(
                """INSERT OR IGNORE INTO verses
                   (work_id, division_id, chapter, number, ref, text, token_count)
                   VALUES (?,?,?,?,?,?,?)""",
                (source.id, div_id, v.chapter, v.number, source.make_ref(v), v.text, tc),
            )
            if cur.rowcount == 0:
                continue
            verse_id = cur.lastrowid
            n_verses += 1
            n_tokens += tc

            conn.executemany(
                """INSERT OR IGNORE INTO lemma_index
                   (lemma, work_id, division_id, verse_id, surface, position)
                   VALUES (?,?,?,?,?,?)""",
                [(t.lemma, source.id, div_id, verse_id, t.surface, t.position)
                 for t in tokenize(v.text, lang=source.language)],
            )

    rebuild_aggregates(conn)
    return {"verses": n_verses, "tokens": n_tokens, "divisions": len(division_ids)}


def already_ingested(conn: sqlite3.Connection, work_id: str) -> bool:
    row = conn.execute(
        "SELECT total_verses FROM works WHERE id = ?", (work_id,)
    ).fetchone()
    return bool(row and row["total_verses"] > 0)


def build_database(
    db_path: Path | str,
    sources: list[tuple[CorpusSource, Any]],
    *,
    skip_failed: bool = False,
    resume: bool = True,
    on_progress: Callable[[str, str], None] | None = None,
) -> dict[str, Any]:
    """Construye la base obra por obra.

    `resume` evita repetir descargas ya completadas: el instalador puede
    ejecutarse varias veces sin penalización. `skip_failed` hace que una fuente
    caída no aborte todo el proceso, que es lo habitual con endpoints públicos
    gratuitos.

    Cada elemento de `sources` es (CorpusSource, callable-que-devuelve-versos).
    Se pasa un callable y no un generador ya creado para que la descarga no
    empiece hasta que se sepa que hace falta.
    """
    from .db import connect

    conn = connect(db_path)
    init_schema(conn)
    report: dict[str, Any] = {}

    def notify(work_id: str, status: str) -> None:
        if on_progress:
            on_progress(work_id, status)

    for source, factory in sources:
        if resume and already_ingested(conn, source.id):
            report[source.id] = {"status": "ya-descargado"}
            notify(source.id, "ya-descargado")
            continue
        try:
            notify(source.id, "descargando")
            verses = factory() if callable(factory) else factory
            stats = ingest_source(conn, source, verses)
            report[source.id] = {"status": "ok", **stats}
            notify(source.id, "ok")
        except Exception as exc:  # noqa: BLE001
            if not skip_failed:
                conn.close()
                raise
            report[source.id] = {"status": "error", "error": str(exc)}
            notify(source.id, "error")

    conn.execute("INSERT INTO verses_fts(verses_fts) VALUES('rebuild')")
    conn.commit()
    conn.close()
    return report


# --------------------------------------------------------------------------
# Adaptadores de formato
# --------------------------------------------------------------------------

def from_flat_json(path: Path | str) -> Iterator[VerseRecord]:
    """Formato interno: lista de objetos con las claves de VerseRecord."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    for item in data["verses"]:
        yield VerseRecord(
            division_ordinal=item["division_ordinal"],
            division_name=item["division_name"],
            chapter=item["chapter"],
            number=item["number"],
            text=item["text"],
            section=item.get("section"),
            division_name_alt=item.get("division_name_alt"),
        )
