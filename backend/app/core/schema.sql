-- Esquema unificado para corpus religiosos heterogéneos.
--
-- El reto de diseño: la Biblia se cita libro/capítulo/versículo, el Corán
-- sura/aleya, el Gita capítulo/sloka. Se resuelve con una jerarquía genérica
-- de tres niveles (work -> division -> verse) más un campo `ref` canónico
-- legible por humanos que cada ingestor construye según su tradición.

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS works (
    id            TEXT PRIMARY KEY,          -- 'rv1909', 'kjv', 'quran-pickthall'
    tradition     TEXT NOT NULL,             -- cristianismo | islam | judaismo | hinduismo
    title         TEXT NOT NULL,
    edition       TEXT NOT NULL,             -- traducción concreta
    language      TEXT NOT NULL,             -- es | en | ar | he | sa
    year          INTEGER,
    license       TEXT NOT NULL,             -- 'public-domain', 'CC-BY-4.0', ...
    source_url    TEXT,
    division_label   TEXT NOT NULL DEFAULT 'libro',    -- libro | sura | capitulo
    subdivision_label TEXT NOT NULL DEFAULT 'capitulo',
    verse_label      TEXT NOT NULL DEFAULT 'versiculo', -- versiculo | aleya | sloka
    total_tokens  INTEGER NOT NULL DEFAULT 0, -- denominador para normalizar
    total_verses  INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS divisions (
    id          INTEGER PRIMARY KEY,
    work_id     TEXT NOT NULL REFERENCES works(id) ON DELETE CASCADE,
    ordinal     INTEGER NOT NULL,            -- orden canónico
    name        TEXT NOT NULL,               -- 'Génesis', 'Al-Fatiha'
    name_alt    TEXT,                        -- transliteración / nombre original
    section     TEXT,                        -- 'Pentateuco', 'Meca', 'Medina'
    total_tokens INTEGER NOT NULL DEFAULT 0,
    UNIQUE (work_id, ordinal)
);

CREATE TABLE IF NOT EXISTS verses (
    id           INTEGER PRIMARY KEY,
    work_id      TEXT NOT NULL REFERENCES works(id) ON DELETE CASCADE,
    division_id  INTEGER NOT NULL REFERENCES divisions(id) ON DELETE CASCADE,
    chapter      INTEGER NOT NULL,
    number       INTEGER NOT NULL,
    ref          TEXT NOT NULL,              -- 'Gn 1:1', 'Q 2:255', 'BG 2:47'
    text         TEXT NOT NULL,
    token_count  INTEGER NOT NULL DEFAULT 0,
    UNIQUE (work_id, division_id, chapter, number)
);

CREATE INDEX IF NOT EXISTS idx_verses_work ON verses(work_id);
CREATE INDEX IF NOT EXISTS idx_verses_div  ON verses(division_id, chapter, number);

-- Índice invertido propio: permite frecuencias por lema sin reescanear texto.
CREATE TABLE IF NOT EXISTS lemma_index (
    lemma       TEXT NOT NULL,
    work_id     TEXT NOT NULL REFERENCES works(id) ON DELETE CASCADE,
    division_id INTEGER NOT NULL REFERENCES divisions(id) ON DELETE CASCADE,
    verse_id    INTEGER NOT NULL REFERENCES verses(id) ON DELETE CASCADE,
    surface     TEXT NOT NULL,               -- forma real, para mostrar variantes
    position    INTEGER NOT NULL,            -- para KWIC
    PRIMARY KEY (lemma, verse_id, position)
) WITHOUT ROWID;

CREATE INDEX IF NOT EXISTS idx_lemma_work ON lemma_index(lemma, work_id);
-- Necesario para borrar una obra entera en un tiempo razonable: sin él, el
-- borrado en cascada recorre los millones de filas de la tabla.
CREATE INDEX IF NOT EXISTS idx_lemma_solo_work ON lemma_index(work_id);
CREATE INDEX IF NOT EXISTS idx_lemma_div  ON lemma_index(lemma, division_id);

-- Tabla agregada precalculada: la consulta más frecuente de la app.
CREATE TABLE IF NOT EXISTS lemma_totals (
    lemma       TEXT NOT NULL,
    work_id     TEXT NOT NULL REFERENCES works(id) ON DELETE CASCADE,
    count       INTEGER NOT NULL,
    verse_count INTEGER NOT NULL,
    PRIMARY KEY (lemma, work_id)
) WITHOUT ROWID;

-- Búsqueda de texto libre.
CREATE VIRTUAL TABLE IF NOT EXISTS verses_fts USING fts5(
    text,
    ref UNINDEXED,
    work_id UNINDEXED,
    content='verses',
    content_rowid='id',
    tokenize='unicode61 remove_diacritics 2'
);

CREATE TRIGGER IF NOT EXISTS verses_ai AFTER INSERT ON verses BEGIN
    INSERT INTO verses_fts(rowid, text, ref, work_id)
    VALUES (new.id, new.text, new.ref, new.work_id);
END;
CREATE TRIGGER IF NOT EXISTS verses_ad AFTER DELETE ON verses BEGIN
    INSERT INTO verses_fts(verses_fts, rowid, text, ref, work_id)
    VALUES ('delete', old.id, old.text, old.ref, old.work_id);
END;

-- Vectores de similitud semántica (opcional, poblado por embeddings.py).
CREATE TABLE IF NOT EXISTS embeddings (
    verse_id  INTEGER PRIMARY KEY REFERENCES verses(id) ON DELETE CASCADE,
    model     TEXT NOT NULL,
    vector    BLOB NOT NULL                  -- float32 little-endian
);
