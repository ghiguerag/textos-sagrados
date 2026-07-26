"""Capa de acceso a SQLite. Sin ORM: las consultas analíticas son agregaciones
a medida y un ORM solo añadiría ruido."""

from __future__ import annotations

import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

SCHEMA_PATH = Path(__file__).with_name("schema.sql")


def connect(db_path: str | Path, *, readonly: bool = False,
            thread_safe: bool = False):
    """Abre la base de datos.

    `thread_safe=True` devuelve una conexión por hilo. Obligatorio en el
    servidor, donde cada petición se atiende en un hilo distinto.
    """
    if thread_safe:
        return ThreadLocalConnection(db_path, readonly=readonly)
    return _abrir(db_path, readonly=readonly)


def _abrir(db_path: str | Path, *, readonly: bool = False) -> sqlite3.Connection:
    db_path = Path(db_path)
    if readonly:
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, check_same_thread=False)
    else:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA temp_store = MEMORY")
    try:
        conn.execute("PRAGMA cache_size = -64000")  # 64 MB
    except sqlite3.OperationalError:
        # Algunos volúmenes rechazan este PRAGMA en modo solo lectura.
        # Es una optimización: sin ella todo funciona igual, algo más lento.
        pass
    if not readonly:
        # WAL da mucha mejor concurrencia de lectura, pero falla en volúmenes
        # de red y en algunos sistemas de archivos montados. Degradar en vez
        # de romper.
        try:
            conn.execute("PRAGMA journal_mode = WAL")
        except sqlite3.OperationalError:
            conn.execute("PRAGMA journal_mode = DELETE")
    return conn


class ThreadLocalConnection:
    """Una conexión SQLite por hilo, creada bajo demanda.

    Existe por un fallo real en producción. El servidor atiende cada petición
    en un hilo distinto, y todas compartían una única conexión. Con consultas
    sueltas casi nunca chocaban, pero el cálculo de colocaciones lanza
    decenas de consultas seguidas: el tiempo suficiente para que otra petición
    se cruzara y ambas se pisaran el cursor.

    Los síntomas eran desconcertantes y distintos cada vez: «another row
    available», «'NoneType' object is not subscriptable»… Todos eran la misma
    causa. Compartir una conexión SQLite entre hilos no es seguro, aunque
    check_same_thread lo permita.

    Se comporta como una conexión normal, así que el resto del código no
    necesita cambiar.
    """

    def __init__(self, db_path: str | Path, *, readonly: bool = False):
        self._path = db_path
        self._readonly = readonly
        self._local = threading.local()
        self._todas: list[sqlite3.Connection] = []
        self._candado = threading.Lock()

    @property
    def _conn(self) -> sqlite3.Connection:
        c = getattr(self._local, "conn", None)
        if c is None:
            c = _abrir(self._path, readonly=self._readonly)
            self._local.conn = c
            with self._candado:
                self._todas.append(c)
        return c

    def execute(self, *a: Any, **k: Any) -> sqlite3.Cursor:
        return self._conn.execute(*a, **k)

    def executemany(self, *a: Any, **k: Any) -> sqlite3.Cursor:
        return self._conn.executemany(*a, **k)

    def executescript(self, *a: Any, **k: Any) -> sqlite3.Cursor:
        return self._conn.executescript(*a, **k)

    def commit(self) -> None:
        self._conn.commit()

    def rollback(self) -> None:
        self._conn.rollback()

    def close(self) -> None:
        with self._candado:
            for c in self._todas:
                try:
                    c.close()
                except sqlite3.Error:
                    pass
            self._todas.clear()

    @property
    def row_factory(self):
        return self._conn.row_factory

    @row_factory.setter
    def row_factory(self, valor) -> None:
        self._conn.row_factory = valor


def init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    conn.commit()


@contextmanager
def transaction(conn: sqlite3.Connection) -> Iterator[sqlite3.Connection]:
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise


def rebuild_aggregates(conn: sqlite3.Connection) -> None:
    """Recalcula lemma_totals y los denominadores de normalización.

    Debe ejecutarse tras cada ingesta: la app depende de total_tokens para
    convertir conteos brutos en tasas comparables entre corpus.
    """
    with transaction(conn):
        conn.execute("DELETE FROM lemma_totals")
        conn.execute(
            """
            INSERT INTO lemma_totals (lemma, work_id, count, verse_count)
            SELECT lemma, work_id, COUNT(*), COUNT(DISTINCT verse_id)
            FROM lemma_index GROUP BY lemma, work_id
            """
        )
        conn.execute(
            """
            UPDATE divisions SET total_tokens = COALESCE((
                SELECT SUM(token_count) FROM verses WHERE verses.division_id = divisions.id
            ), 0)
            """
        )
        conn.execute(
            """
            UPDATE works SET
                total_tokens = COALESCE((
                    SELECT SUM(token_count) FROM verses WHERE verses.work_id = works.id), 0),
                total_verses = COALESCE((
                    SELECT COUNT(*) FROM verses WHERE verses.work_id = works.id), 0)
            """
        )
    conn.execute("ANALYZE")
