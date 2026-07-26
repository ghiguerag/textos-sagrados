#!/usr/bin/env python3
"""
Descarga los cuatro corpus en dominio público y construye la base de datos.

    python scripts/fetch_corpus.py --all --out data/corpus.db
    python scripts/fetch_corpus.py --check          # solo comprueba las URLs
    python scripts/fetch_corpus.py --source kjv quran-pickthall

IMPORTANTE SOBRE LICENCIAS
--------------------------
Solo se incluyen ediciones en dominio público. Las traducciones modernas
(Reina-Valera 1960/1995, NVI, NIV, Corán de Cortés, Sahih International)
están protegidas por copyright y NO deben añadirse aquí sin licencia expresa.
Cada fuente declara su licencia en el campo `license`; el endpoint /works de la
API la expone para que la app pueda mostrar la atribución exigida.

Los endpoints públicos cambian con el tiempo. Ejecuta --check antes de una
ingesta larga: verifica cada URL y avisa de las que hayan caído, sin descargar
los corpus completos.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Iterator

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.ingest import CorpusSource, VerseRecord, build_database  # noqa: E402
from app.core.validacion import IdiomaIncorrectoError, validar_idioma  # noqa: E402

# Sefaria y otros servicios devuelven 403 a los clientes que no se identifican
# como navegador. Nos identificamos como uno, pero manteniendo las pausas entre
# peticiones: el objetivo es que nos atiendan, no saturarlos.
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)
CACHE = Path(__file__).resolve().parents[1] / "data" / "cache"


def fetch_json(url: str, *, retries: int = 3, delay: float = 1.0) -> Any:
    """GET con caché en disco. La caché evita martillear APIs públicas
    gratuitas durante el desarrollo, y las hace reproducibles."""
    CACHE.mkdir(parents=True, exist_ok=True)
    key = CACHE / (str(abs(hash(url))) + ".json")
    if key.exists():
        return json.loads(key.read_text(encoding="utf-8"))

    last: Exception | None = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=45) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            key.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            time.sleep(delay)          # cortesía con el servidor
            return data
        except (urllib.error.URLError, json.JSONDecodeError, TimeoutError) as exc:
            last = exc
            time.sleep(delay * (attempt + 2))
    raise RuntimeError(f"No se pudo descargar {url}: {last}")


def fetch_text(url: str) -> str:
    CACHE.mkdir(parents=True, exist_ok=True)
    key = CACHE / (str(abs(hash(url))) + ".txt")
    if key.exists():
        return key.read_text(encoding="utf-8")
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=90) as resp:
        text = resp.read().decode("utf-8", errors="replace")
    key.write_text(text, encoding="utf-8")
    return text


# ==========================================================================
# ADAPTADORES
# Cada uno traduce el formato nativo de una fuente a VerseRecord.
# ==========================================================================

# --- Biblia: scrollmapper/bible_databases (KJV, dominio público) ----------

SCROLLMAPPER = ("https://raw.githubusercontent.com/scrollmapper/"
                "bible_databases/master/formats/json/{version}.json")


def load_scrollmapper(version: str) -> Iterator[VerseRecord]:
    data = fetch_json(SCROLLMAPPER.format(version=version))
    books = data["books"] if isinstance(data, dict) and "books" in data else data
    for ordinal, book in enumerate(books, start=1):
        name = book.get("name") or book.get("book")
        for chapter in book["chapters"]:
            ch_num = int(chapter.get("chapter", chapter.get("num", 0)))
            for verse in chapter["verses"]:
                yield VerseRecord(
                    division_ordinal=ordinal,
                    division_name=name,
                    chapter=ch_num,
                    number=int(verse.get("verse", verse.get("num", 0))),
                    text=verse["text"].strip(),
                    section="Antiguo Testamento" if ordinal <= 39 else "Nuevo Testamento",
                )


# --- Biblia en español: getbible.net v2 (Reina-Valera 1909) ---------------

GETBIBLE = "https://api.getbible.net/v2/{translation}/{book}.json"
GETBIBLE_INDEX = "https://api.getbible.net/v2/{translation}/books.json"


def load_getbible(translation: str) -> Iterator[VerseRecord]:
    index = fetch_json(GETBIBLE_INDEX.format(translation=translation))
    books = index if isinstance(index, list) else index.get("books", [])
    for ordinal, meta in enumerate(books, start=1):
        nr = meta.get("nr") or meta.get("book_nr") or ordinal
        payload = fetch_json(GETBIBLE.format(translation=translation, book=nr))
        name = payload.get("name") or meta.get("name")
        for chapter in payload.get("chapters", []):
            ch_num = int(chapter.get("chapter", 0))
            for verse in chapter.get("verses", []):
                yield VerseRecord(
                    division_ordinal=int(nr),
                    division_name=name,
                    chapter=ch_num,
                    number=int(verse["verse"]),
                    text=verse["text"].strip(),
                    section="Antiguo Testamento" if int(nr) <= 39 else "Nuevo Testamento",
                )


# --- Tanaj: Sefaria (JPS 1917, dominio público) ---------------------------

# API v3. La v1 (/api/texts/) sigue existiendo pero devuelve por defecto la
# edición de 2023, que es CC-BY-NC y NO se puede redistribuir. La v3 permite
# pedir una versión concreta y, sobre todo, informa de su licencia.
SEFARIA_V3 = "https://www.sefaria.org/api/v3/texts/{ref}?version=english|{version}"

# Única edición del Tanaj en inglés y en dominio público que ofrece Sefaria.
JPS_1917 = "The Holy Scriptures: A New Translation (JPS 1917)"

TANAJ_BOOKS: list[tuple[str, str, str]] = [
    ("Genesis", "Génesis", "Torá"), ("Exodus", "Éxodo", "Torá"),
    ("Leviticus", "Levítico", "Torá"), ("Numbers", "Números", "Torá"),
    ("Deuteronomy", "Deuteronomio", "Torá"),
    ("Joshua", "Josué", "Neviim"), ("Judges", "Jueces", "Neviim"),
    ("I Samuel", "1 Samuel", "Neviim"), ("II Samuel", "2 Samuel", "Neviim"),
    ("I Kings", "1 Reyes", "Neviim"), ("II Kings", "2 Reyes", "Neviim"),
    ("Isaiah", "Isaías", "Neviim"), ("Jeremiah", "Jeremías", "Neviim"),
    ("Ezekiel", "Ezequiel", "Neviim"), ("Hosea", "Oseas", "Neviim"),
    ("Joel", "Joel", "Neviim"), ("Amos", "Amós", "Neviim"),
    ("Obadiah", "Abdías", "Neviim"), ("Jonah", "Jonás", "Neviim"),
    ("Micah", "Miqueas", "Neviim"), ("Nahum", "Nahúm", "Neviim"),
    ("Habakkuk", "Habacuc", "Neviim"), ("Zephaniah", "Sofonías", "Neviim"),
    ("Haggai", "Hageo", "Neviim"), ("Zechariah", "Zacarías", "Neviim"),
    ("Malachi", "Malaquías", "Neviim"),
    ("Psalms", "Salmos", "Ketuvim"), ("Proverbs", "Proverbios", "Ketuvim"),
    ("Job", "Job", "Ketuvim"), ("Song of Songs", "Cantar de los Cantares", "Ketuvim"),
    ("Ruth", "Rut", "Ketuvim"), ("Lamentations", "Lamentaciones", "Ketuvim"),
    ("Ecclesiastes", "Eclesiastés", "Ketuvim"), ("Esther", "Ester", "Ketuvim"),
    ("Daniel", "Daniel", "Ketuvim"), ("Ezra", "Esdras", "Ketuvim"),
    ("Nehemiah", "Nehemías", "Ketuvim"),
    ("I Chronicles", "1 Crónicas", "Ketuvim"), ("II Chronicles", "2 Crónicas", "Ketuvim"),
]

ACCEPTED_LICENSES = ("public domain", "pd", "cc0")


class LicenseError(RuntimeError):
    """La fuente devolvió un texto que no podemos redistribuir."""


def load_sefaria_tanakh(version: str = JPS_1917) -> Iterator[VerseRecord]:
    """Tanaj completo, libro a libro, validando la licencia en cada respuesta.

    La validación no es una formalidad: si Sefaria cambia qué versión sirve por
    defecto, o si el título de la edición cambia, sin esta comprobación
    acabaríamos empaquetando y distribuyendo texto con copyright sin enterarnos.
    Es preferible que la ingesta falle a que produzca un problema legal.
    """
    for ordinal, (en_name, es_name, section) in enumerate(TANAJ_BOOKS, start=1):
        url = SEFARIA_V3.format(
            ref=urllib.parse.quote(en_name),
            version=urllib.parse.quote(version),
        )
        payload = fetch_json(url)

        versions = payload.get("versions") or []
        if not versions:
            raise RuntimeError(
                f"Sefaria no devolvió la edición «{version}» para {en_name}. "
                f"Comprueba el título exacto en "
                f"https://www.sefaria.org/api/texts/versions/{en_name}"
            )

        block = versions[0]
        license_name = str(block.get("license", "")).strip().lower()
        if license_name not in ACCEPTED_LICENSES:
            raise LicenseError(
                f"{en_name}: Sefaria devolvió la edición "
                f"«{block.get('versionTitle')}» con licencia "
                f"«{block.get('license')}», que no es de dominio público. "
                f"Ingesta abortada para no redistribuir material con copyright."
            )

        chapters = block.get("text") or []
        if chapters and isinstance(chapters[0], str):   # libro de un solo capítulo
            chapters = [chapters]

        for ch_index, chapter in enumerate(chapters, start=1):
            for v_index, raw in enumerate(chapter, start=1):
                text = _strip_html(raw)
                if text:
                    yield VerseRecord(
                        division_ordinal=ordinal, division_name=es_name,
                        division_name_alt=en_name, chapter=ch_index,
                        number=v_index, text=text, section=section,
                    )


# --- Corán: alquran.cloud -------------------------------------------------

ALQURAN = "https://api.alquran.cloud/v1/quran/{edition}"


def load_quran(edition: str = "en.pickthall") -> Iterator[VerseRecord]:
    """Descarga el Corán en la edición indicada.

    CUIDADO CON EL IDENTIFICADOR. Si no existe, la API no da error: devuelve
    el texto árabe original. Así entró en el corpus un Corán en árabe
    declarado como inglés, y todas las comparaciones con él daban cero.

    Ediciones verificadas: en.pickthall (Marmaduke Pickthall, 1930, dominio
    público) y quran-uthmani (árabe original).
    """
    payload = fetch_json(ALQURAN.format(edition=edition))

    # Comprobación inmediata sobre la primera aleya, antes de recorrer las
    # 6.236: si la edición no era la pedida, mejor fallar ya.
    primera = payload["data"]["surahs"][0]["ayahs"][0]["text"]
    diag = validar_idioma([primera], edition.split(".")[0])
    if not diag.valido:
        raise IdiomaIncorrectoError(
            f"La edición «{edition}» no devolvió el idioma esperado.\n"
            f"  Recibido: {diag.alfabeto_detectado} — {diag.muestra[:70]}\n\n"
            f"Ese identificador probablemente no existe y la API ha devuelto "
            f"el árabe por defecto. Consulta las ediciones disponibles en:\n"
            f"  https://api.alquran.cloud/v1/edition/language/en"
        )
    for sura in payload["data"]["surahs"]:
        revelation = sura.get("revelationType", "")
        section = {"Meccan": "Mecano", "Medinan": "Medinés"}.get(revelation, revelation)
        for aya in sura["ayahs"]:
            yield VerseRecord(
                division_ordinal=int(sura["number"]),
                division_name=sura.get("englishName", f"Sura {sura['number']}"),
                division_name_alt=sura.get("name"),
                chapter=int(sura["number"]),
                number=int(aya["numberInSurah"]),
                text=aya["text"].strip(),
                section=section,
            )


# --- Bhagavad Gita: Project Gutenberg, "The Song Celestial" (Arnold 1885) --

GITA_GUTENBERG = "https://www.gutenberg.org/cache/epub/2388/pg2388.txt"


def load_gita_gutenberg() -> Iterator[VerseRecord]:
    """El texto de Arnold es verso libre sin numeración de slokas, así que se
    segmenta por capítulo y se numeran las estrofas secuencialmente. Para
    numeración canónica de slokas usa `load_gita_api`."""
    raw = fetch_text(GITA_GUTENBERG)
    body = raw.split("*** START", 1)[-1].split("*** END", 1)[0]
    chunks = re.split(r"\nCHAPTER\s+([IVXL]+)\s*\n", body)
    roman = {"I":1,"II":2,"III":3,"IV":4,"V":5,"VI":6,"VII":7,"VIII":8,"IX":9,
             "X":10,"XI":11,"XII":12,"XIII":13,"XIV":14,"XV":15,"XVI":16,
             "XVII":17,"XVIII":18}
    for i in range(1, len(chunks), 2):
        num = roman.get(chunks[i].strip())
        if not num:
            continue
        stanzas = [s.strip() for s in re.split(r"\n\s*\n", chunks[i + 1]) if s.strip()]
        for j, stanza in enumerate(stanzas, start=1):
            text = " ".join(line.strip() for line in stanza.splitlines())
            if len(text) > 20:
                yield VerseRecord(
                    division_ordinal=num,
                    division_name=f"Capítulo {num}",
                    chapter=num, number=j, text=text,
                )


# El Gita de Arnold, empaquetado en el propio repositorio. Se incluye como
# archivo local porque sus fuentes web son intermitentes —una devuelve 504 y la
# otra cambió su API—, y sin él el corpus se quedaba sin la tradición hinduista
# al desplegar en la nube. Es pequeño (~145 KB) y de dominio público.
GITA_LOCAL = Path(__file__).resolve().parents[1] / "data" / "gita_arnold.json"


def load_gita_local() -> Iterator[VerseRecord]:
    """Bhagavad Gita (Arnold, 1885) desde el archivo empaquetado en el repo."""
    datos = json.loads(GITA_LOCAL.read_text(encoding="utf-8"))
    for item in datos:
        yield VerseRecord(
            division_ordinal=item["division_ordinal"],
            division_name=item["division_name"],
            chapter=item["chapter"], number=item["number"],
            text=item["text"], section=item.get("section"),
        )


GITA_API = "https://bhagavadgitaapi.in/slok/{ch}/{v}/"
GITA_CHAPTER_VERSES = [47,72,43,42,29,47,30,28,34,42,55,20,35,27,20,24,28,78]


def load_gita_api(translator: str = "siva") -> Iterator[VerseRecord]:
    """Numeración canónica de slokas. `translator` puede ser 'siva'
    (Swami Sivananda), 'purohit', 'chinmay', etc."""
    for ch, n_verses in enumerate(GITA_CHAPTER_VERSES, start=1):
        for v in range(1, n_verses + 1):
            payload = fetch_json(GITA_API.format(ch=ch, v=v), delay=0.3)
            block = payload.get(translator) or {}
            text = (block.get("et") or block.get("ht") or "").strip()
            if text:
                yield VerseRecord(
                    division_ordinal=ch, division_name=f"Capítulo {ch}",
                    chapter=ch, number=v, text=text,
                )


# Las notas del traductor van dentro de <i class="footnote">…</i> y de
# <sup class="footnote-marker">. Son comentario editorial, no texto bíblico:
# contarlas inflaría las frecuencias con vocabulario que no es del original.
_FOOTNOTE_RE = re.compile(
    r"<sup[^>]*class=\"[^\"]*footnote-marker[^\"]*\"[^>]*>.*?</sup>"
    r"|<i[^>]*class=\"[^\"]*footnote[^\"]*\"[^>]*>.*?</i>",
    re.DOTALL | re.IGNORECASE,
)


def _strip_html(text: Any) -> str:
    if not isinstance(text, str):
        return ""
    text = _FOOTNOTE_RE.sub(" ", text)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


# ==========================================================================
# REGISTRO DE FUENTES
# ==========================================================================

SOURCES: dict[str, tuple[CorpusSource, Any]] = {
    "kjv": (
        CorpusSource(
            id="kjv", tradition="cristianismo", title="Biblia", edition="King James Version",
            language="en", year=1611, license="public-domain",
            source_url="https://github.com/scrollmapper/bible_databases",
            division_label="libro", verse_label="versiculo",
            ref_format=lambda v: f"{v.division_name} {v.chapter}:{v.number}",
        ),
        lambda: load_scrollmapper("KJV"),
    ),
    "rv1909": (
        CorpusSource(
            id="rv1909", tradition="cristianismo", title="Biblia",
            edition="Reina-Valera 1909", language="es", year=1909,
            license="public-domain", source_url="https://api.getbible.net/",
            ref_format=lambda v: f"{v.division_name} {v.chapter}:{v.number}",
        ),
        lambda: load_getbible("spanish"),
    ),
    "tanaj-jps": (
        CorpusSource(
            id="tanaj-jps", tradition="judaismo", title="Tanaj",
            edition="JPS 1917 (dominio público)", language="en", year=1917,
            license="public-domain", source_url="https://www.sefaria.org/",
            division_label="libro",
            ref_format=lambda v: f"{v.division_name} {v.chapter}:{v.number}",
        ),
        lambda: load_sefaria_tanakh(),
    ),
    "quran-pickthall": (
        CorpusSource(
            id="quran-pickthall", tradition="islam", title="Corán",
            edition="M. Pickthall 1930", language="en", year=1930,
            license="public-domain", source_url="https://alquran.cloud/",
            division_label="sura", subdivision_label="sura", verse_label="aleya",
            ref_format=lambda v: f"Q {v.chapter}:{v.number}",
        ),
        lambda: load_quran("en.pickthall"),
    ),
    "gita-arnold": (
        CorpusSource(
            id="gita-arnold", tradition="hinduismo", title="Bhagavad Gita",
            edition="Edwin Arnold, The Song Celestial 1885", language="en",
            year=1885, license="public-domain",
            source_url="https://www.gutenberg.org/ebooks/2388",
            division_label="capitulo", verse_label="sloka",
            ref_format=lambda v: f"BG {v.chapter}:{v.number}",
        ),
        load_gita_local,
    ),
    "gita-sivananda": (
        CorpusSource(
            id="gita-sivananda", tradition="hinduismo", title="Bhagavad Gita",
            edition="Swami Sivananda", language="en", license="public-domain",
            source_url="https://bhagavadgitaapi.in/",
            division_label="capitulo", verse_label="sloka",
            ref_format=lambda v: f"BG {v.chapter}:{v.number}",
        ),
        lambda: load_gita_api("siva"),
    ),
}

# Conjunto por defecto: un texto por tradición, todos en inglés para que la
# comparación léxica sea metodológicamente válida (comparar frecuencias entre
# idiomas distintos no tiene sentido lingüístico).
DEFAULT_SET = ["kjv", "tanaj-jps", "quran-pickthall", "gita-arnold"]


def check_sources(names: list[str]) -> int:
    """Comprueba que cada endpoint responde, sin descargar el corpus entero."""
    probes = {
        "kjv": SCROLLMAPPER.format(version="KJV"),
        "rv1909": GETBIBLE_INDEX.format(translation="spanish"),
        "tanaj-jps": SEFARIA_V3.format(
            ref="Obadiah", version=urllib.parse.quote(JPS_1917)),
        "quran-pickthall": "https://api.alquran.cloud/v1/surah/1/en.pickthall",
        "gita-arnold": GITA_GUTENBERG,
        "gita-sivananda": GITA_API.format(ch=1, v=1),
    }
    failures = 0
    for name in names:
        url = probes.get(name)
        if not url:
            print(f"  ?  {name}: sin sonda definida")
            continue
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT}, method="GET")
            with urllib.request.urlopen(req, timeout=30) as resp:
                size = len(resp.read(4096))
            print(f"  OK {name}: {resp.status} ({size} bytes leídos) {url}")
        except Exception as exc:
            failures += 1
            print(f"  XX {name}: FALLO -> {exc}\n     {url}")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--source", nargs="+", choices=sorted(SOURCES), help="fuentes concretas")
    parser.add_argument("--all", action="store_true", help="todas las fuentes registradas")
    parser.add_argument("--check", action="store_true", help="solo verificar endpoints")
    parser.add_argument("--out", default="data/corpus.db")
    parser.add_argument("--skip-failed", action="store_true",
                        help="continuar aunque alguna fuente falle")
    parser.add_argument("--force", action="store_true",
                        help="volver a descargar lo que ya esté en la base")
    args = parser.parse_args()

    names = sorted(SOURCES) if args.all else (args.source or DEFAULT_SET)

    if args.check:
        print("Verificando endpoints...")
        failures = check_sources(names)
        print(f"\n{len(names) - failures}/{len(names)} disponibles")
        return 1 if failures else 0

    payload = [(SOURCES[name][0], SOURCES[name][1]) for name in names]

    def progress(work_id: str, status: str) -> None:
        label = {
            "descargando": "  descargando  ",
            "ok": "  completado   ",
            "error": "  FALLO        ",
            "ya-descargado": "  ya lo tenías ",
        }.get(status, f"  {status} ")
        print(f"{label}{work_id}", flush=True)

    report = build_database(
        args.out, payload,
        skip_failed=args.skip_failed,
        resume=not args.force,
        on_progress=progress,
    )

    print(f"\nBase de datos: {args.out}\n")
    ok = failed = 0
    for work_id, stats in report.items():
        if stats.get("status") == "error":
            failed += 1
            print(f"  {work_id:18} no se pudo descargar")
            print(f"                     motivo: {stats['error'][:90]}")
        elif stats.get("status") == "ya-descargado":
            ok += 1
            print(f"  {work_id:18} ya estaba descargado")
        else:
            ok += 1
            print(f"  {work_id:18} {stats['verses']:>7} versículos  "
                  f"{stats['tokens']:>9} palabras  {stats['divisions']:>4} divisiones")

    print(f"\n{ok} de {len(report)} textos disponibles.")
    if failed:
        print("Vuelve a ejecutar el instalador más tarde para reintentar "
              "los que fallaron: no repetirá los que ya están.")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
