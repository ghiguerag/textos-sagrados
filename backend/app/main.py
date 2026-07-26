"""
API de Textos Sagrados.

    uvicorn app.main:app --reload

Documentación interactiva en /docs
"""

from __future__ import annotations

import logging
import sqlite3
import traceback
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated, Any

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse

from .config import Settings, get_settings
from .core import analysis as A
from .core.db import connect
from .core.lexicon import Lexicon
from .schemas import (
    ConcordanceResponse, DivisionFrequencyOut, DivisionOut, FrequencyRequest,
    FrequencyResponse, ParallelRequest, SemanticFieldOut,
    SemanticSearchResponse, VerseOut, WorkOut,
)

# La API no devuelve texto para mostrar al usuario: devuelve identificadores.
# Así la aplicación puede presentarlo en cualquiera de sus idiomas sin que el
# servidor sepa nada de localización.
# Versión de la API. La interfaz web la compara con la suya y avisa si el
# servidor arrancó con código antiguo, que es lo que pasa al copiar archivos
# nuevos sin reiniciar: el proceso mantiene en memoria la versión anterior y
# las rutas nuevas devuelven 404 sin explicación.
API_VERSION = "1.10.0"

# Prestaciones que la interfaz puede comprobar antes de usarlas.
FEATURES = [
    "frequency", "divisions", "concordance", "parallel",
    "forms", "collocations", "search", "semantic-fields",
    "sections", "distinctive", "semantic-status", "translate", "dedup",
    "resolver-termino",
]

CAVEAT_FREQ = "frequency_normalization"
CAVEAT_SEMANTIC = "semantic_similarity"


class State:
    conn: sqlite3.Connection
    lexicon: Lexicon
    vectors: Any = None
    model_id: str = ""
    write_conn: Any = None


state = State()


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    if not settings.db_path.exists():
        raise RuntimeError(
            f"No existe la base de datos en {settings.db_path}. "
            "Ejecuta: python scripts/fetch_corpus.py --all"
        )
    state.conn = connect(settings.db_path, readonly=True, thread_safe=True)
    state.lexicon = Lexicon.load(settings.lexicon_path)

    # Conexión aparte, escribible, solo para guardar traducciones. El resto de
    # la aplicación sigue abriendo la base en modo lectura, que es lo correcto
    # para un servidor que nunca debería modificar el corpus.
    try:
        from .core.translate import ensure_schema
        state.write_conn = connect(settings.db_path, thread_safe=True)
        ensure_schema(state.write_conn)
    except sqlite3.OperationalError:
        state.write_conn = None       # base en un volumen de solo lectura

    if settings.enable_embeddings:
        # Se detecta qué índices hay construidos en lugar de exigir que el
        # usuario configure cuál. Si hay varios, gana el de mayor calidad.
        PREFERENCIA = ["torch:", "static:"]
        try:
            disponibles = [
                r["model"] for r in state.conn.execute(
                    "SELECT model, COUNT(*) AS n FROM embeddings "
                    "GROUP BY model HAVING n > 0 ORDER BY n DESC")
            ]
            elegido = next(
                (m for pref in PREFERENCIA for m in disponibles if m.startswith(pref)),
                disponibles[0] if disponibles else None,
            )
            if elegido:
                from .core.embeddings import VectorStore
                store = VectorStore(state.conn, elegido)
                state.vectors = store if len(store) else None
                state.model_id = elegido
        except (ImportError, sqlite3.OperationalError):
            state.vectors = None      # motor no instalado o tabla ausente
    yield
    state.conn.close()
    if state.write_conn:
        state.write_conn.close()


app = FastAPI(
    title="Textos Sagrados API",
    description=(
        "Análisis léxico comparado de textos sagrados en dominio público. "
        "Herramienta descriptiva: no emite juicios sobre las tradiciones."
    ),
    version="1.0.0",
    lifespan=lifespan,
)
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

SettingsDep = Annotated[Settings, Depends(get_settings)]

log = logging.getLogger("textos_sagrados")


def _diagnostico_semantico() -> dict[str, Any]:
    """Estado real de la búsqueda por significado.

    Se comprueba en el momento, no al arrancar: el fallo típico es que el
    índice exista pero falte el paquete que codifica la consulta, y eso solo
    se descubre al buscar.
    """
    paquetes = {}
    for nombre in ("sentence_transformers", "model2vec"):
        try:
            __import__(nombre)
            paquetes[nombre] = True
        except ImportError:
            paquetes[nombre] = False

    try:
        indices = [
            {"model": r["model"], "vectors": r["n"]}
            for r in state.conn.execute(
                "SELECT model, COUNT(*) AS n FROM embeddings GROUP BY model")
        ]
    except sqlite3.OperationalError:
        indices = []

    versiculos = state.conn.execute(
        "SELECT COUNT(*) AS n FROM verses").fetchone()["n"]

    return {
        "indice_elegido": state.model_id or None,
        "indices_en_base": indices,
        "paquetes_instalados": paquetes,
        "versiculos_totales": versiculos,
        "vectores_cargados": len(state.vectors) if state.vectors else 0,
    }


def _explicar_fallo_semantico(exc: Exception) -> str:
    """Convierte una excepción técnica en una instrucción accionable."""
    diag = _diagnostico_semantico()
    tipo = type(exc).__name__

    if isinstance(exc, ImportError):
        falta = "model2vec" if (state.model_id or "").startswith("static:") \
                else "sentence-transformers"
        instalador = ("INSTALAR-BUSQUEDA-LIGERA-Windows.bat"
                      if falta == "model2vec" else "INSTALAR-BUSQUEDA-Windows.bat")
        return (
            f"El índice está construido, pero falta el programa que convierte "
            f"tu consulta en números: {falta}. "
            f"Ejecuta {instalador} y reinicia el servidor."
        )

    if not diag["indices_en_base"]:
        return ("No hay ningún índice construido. Ejecuta "
                "INSTALAR-BUSQUEDA-LIGERA-Windows.bat")

    incompletos = [
        i for i in diag["indices_en_base"]
        if i["vectors"] < diag["versiculos_totales"]
    ]
    if incompletos and not any(
        i["vectors"] >= diag["versiculos_totales"] for i in diag["indices_en_base"]
    ):
        i = incompletos[0]
        return (
            f"El índice está a medias: {i['vectors']:,} de "
            f"{diag['versiculos_totales']:,} versículos. Vuelve a ejecutar el "
            f"instalador de la búsqueda; continuará donde lo dejó."
        ).replace(",", ".")

    return (
        f"Fallo inesperado en la búsqueda por significado ({tipo}: {exc}). "
        f"El detalle completo está en la ventana negra del servidor."
    )

STATIC_DIR = Path(__file__).parent / "static"


@app.get("/", include_in_schema=False)
def home() -> FileResponse:
    """Interfaz web. Se sirve desde el propio backend para que el usuario no
    tenga que instalar nada más: abrir el navegador y usarla."""
    index = STATIC_DIR / "index.html"
    if not index.exists():
        raise HTTPException(404, "Falta app/static/index.html")
    # Sin caché: el navegador guardaba la pantalla antigua y seguía hablando
    # con un servidor ya actualizado. Salía el aviso de versiones distintas y
    # había que forzar la recarga con Ctrl+F5, cosa que nadie adivina.
    return FileResponse(
        index,
        media_type="text/html",
        headers={"Cache-Control": "no-cache, no-store, must-revalidate",
                 "Pragma": "no-cache", "Expires": "0"},
    )


@app.get("/favicon.ico", include_in_schema=False)
def favicon() -> FileResponse:
    icon = STATIC_DIR / "favicon.svg"
    if not icon.exists():
        raise HTTPException(404)
    return FileResponse(icon, media_type="image/svg+xml")


# --------------------------------------------------------------------------
# Catálogo
# --------------------------------------------------------------------------

@app.get("/health")
def health() -> dict[str, Any]:
    works = state.conn.execute("SELECT COUNT(*) AS n FROM works").fetchone()["n"]
    verses = state.conn.execute("SELECT COUNT(*) AS n FROM verses").fetchone()["n"]
    return {
        "status": "ok",
        "version": API_VERSION,
        # La búsqueda semántica se anuncia solo si el índice está construido.
        # Así la interfaz distingue «servidor antiguo» de «extra no instalado»,
        # que requieren acciones distintas por parte del usuario.
        "features": FEATURES + (["semantic-search"] if state.vectors else []),
        "semantic_ready": bool(state.vectors),
        "semantic_engine": state.model_id,
        "works": works,
        "verses": verses,
        "semantic_fields": len(state.lexicon),
        "embeddings": len(state.vectors) if state.vectors else 0,
    }


@app.get("/works", response_model=list[WorkOut])
def list_works() -> list[dict[str, Any]]:
    rows = state.conn.execute(
        """SELECT w.*, (SELECT COUNT(*) FROM divisions d WHERE d.work_id = w.id) AS total_divisions
           FROM works w ORDER BY w.tradition, w.title"""
    ).fetchall()
    return [dict(r) for r in rows]


@app.get("/works/{work_id}/divisions", response_model=list[DivisionOut])
def list_divisions(work_id: str) -> list[dict[str, Any]]:
    rows = state.conn.execute(
        "SELECT * FROM divisions WHERE work_id = ? ORDER BY ordinal", (work_id,)
    ).fetchall()
    if not rows:
        raise HTTPException(404, f"Obra desconocida: {work_id}")
    return [dict(r) for r in rows]


@app.get("/works/{work_id}/distinctive")
def distinctive(work_id: str, limit: int = Query(50, le=200)) -> dict[str, Any]:
    """Vocabulario que más distingue esta obra del resto del corpus."""
    return {
        "work_id": work_id,
        "method": "log-likelihood (Dunning 1993) contra el resto del corpus",
        "results": A.distinctive_vocabulary(state.conn, work_id, limit=limit),
    }


@app.get("/semantic-fields", response_model=list[SemanticFieldOut])
def semantic_fields(
    lang: str = Query("en", description="Idioma de la interfaz (es, en, pt, fr, ar, hi)"),
) -> list[dict[str, Any]]:
    """Los rótulos vienen ya traducidos: los campos semánticos se definen en
    data/lexicon.json y es ahí donde deben mantenerse sus nombres."""
    return [
        {
            "key": f.key,
            "label": f.label(lang),
            "description": f.description(lang),
            "term_count": sum(len(v) for v in f.terms.values()),
            "languages": sorted(f.terms),
        }
        for f in state.lexicon
    ]


# --------------------------------------------------------------------------
# Análisis
# --------------------------------------------------------------------------

@app.post("/frequency", response_model=FrequencyResponse)
def frequency(req: FrequencyRequest) -> dict[str, Any]:
    stems = A.resolve_query(
        req.term, req.language,
        lexicon=state.lexicon,
        semantic_field=req.semantic_field,
        extra_terms=req.extra_terms,
    )
    if not stems:
        raise HTTPException(400, "Indica un término o un campo semántico.")

    results = A.frequency_by_work(state.conn, stems, work_ids=req.work_ids)
    return {
        "query": req.model_dump(),
        "resolved_stems": sorted(stems),
        "results": [r.to_dict() for r in results],
        "keyness": A.keyness_matrix(results),
        "caveat": CAVEAT_FREQ,
    }


@app.post("/frequency/{work_id}/divisions", response_model=list[DivisionFrequencyOut])
def frequency_divisions(work_id: str, req: FrequencyRequest) -> list[dict[str, Any]]:
    """Distribución interna: alimenta el mapa de calor."""
    stems = A.resolve_query(
        req.term, req.language, lexicon=state.lexicon,
        semantic_field=req.semantic_field, extra_terms=req.extra_terms,
    )
    if not stems:
        raise HTTPException(400, "Indica un término o un campo semántico.")
    return [d.to_dict() for d in A.frequency_by_division(state.conn, stems, work_id)]


@app.post("/concordance", response_model=ConcordanceResponse)
def concordance(
    req: FrequencyRequest,
    settings: SettingsDep,
    limit: int = Query(100),
    offset: int = Query(0, ge=0),
) -> dict[str, Any]:
    limit = min(limit, settings.max_page_size)
    stems = A.resolve_query(
        req.term, req.language, lexicon=state.lexicon,
        semantic_field=req.semantic_field, extra_terms=req.extra_terms,
    )
    if not stems:
        raise HTTPException(400, "Indica un término o un campo semántico.")

    items = A.concordance(state.conn, stems, work_ids=req.work_ids, limit=limit, offset=offset)
    placeholders = ",".join("?" * len(stems))
    total = state.conn.execute(
        f"SELECT COUNT(DISTINCT verse_id) AS n FROM lemma_index WHERE lemma IN ({placeholders})",
        list(stems),
    ).fetchone()["n"]
    return {"total": total, "items": items}


@app.post("/frequency/{work_id}/sections")
def frequency_sections(work_id: str, req: FrequencyRequest) -> dict[str, Any]:
    """Comparación entre las secciones de una misma obra.

    Metodológicamente es la comparación más sólida de la aplicación: dentro de
    una obra el traductor es el mismo, así que las diferencias de vocabulario
    son del texto original y no de la traducción.
    """
    stems = A.resolve_query(
        req.term, req.language, lexicon=state.lexicon,
        semantic_field=req.semantic_field, extra_terms=req.extra_terms,
    )
    if not stems:
        raise HTTPException(400, "Indica un término o un campo semántico.")
    return {
        "work_id": work_id,
        "method": "log-likelihood de cada sección contra el resto de la misma obra",
        "results": A.frequency_by_section(state.conn, stems, work_id),
    }


@app.post("/forms")
def forms(req: FrequencyRequest) -> dict[str, Any]:
    """Desglose de las formas concretas que componen el recuento.

    Alimenta el detalle del contador de «apariciones»: el usuario ve que sus
    120 resultados de «mercy» son en realidad 70 mercy, 30 merciful y 20
    mercies.
    """
    stems = A.resolve_query(
        req.term, req.language, lexicon=state.lexicon,
        semantic_field=req.semantic_field, extra_terms=req.extra_terms,
    )
    if not stems:
        raise HTTPException(400, "Indica un término o un campo semántico.")
    work_id = req.work_ids[0] if req.work_ids else None
    return {
        "work_id": work_id,
        "results": A.surface_forms(state.conn, stems, work_id=work_id),
    }


@app.post("/collocations")
def collocations(
    req: FrequencyRequest,
    window: int = Query(5, ge=1, le=15),
    min_freq: int = Query(3, ge=1),
    limit: int = Query(40, le=200),
) -> dict[str, Any]:
    stems = A.resolve_query(
        req.term, req.language, lexicon=state.lexicon,
        semantic_field=req.semantic_field, extra_terms=req.extra_terms,
    )
    work_id = req.work_ids[0] if req.work_ids else None
    return {
        "method": "PMI sobre ventana de ±N tokens dentro del mismo versículo",
        "results": A.collocations(
            state.conn, stems, work_id=work_id, window=window,
            min_freq=min_freq, limit=limit,
        ),
    }


@app.post("/parallel")
def parallel(req: ParallelRequest) -> dict[str, Any]:
    """Lectura en paralelo: los pasajes más relevantes de cada obra elegida."""
    stems = A.resolve_query(
        req.term, req.language, lexicon=state.lexicon, semantic_field=req.semantic_field
    )
    if not stems:
        raise HTTPException(400, "Indica un término o un campo semántico.")

    obras = req.work_ids or [
        r["id"] for r in state.conn.execute(
            "SELECT id FROM works ORDER BY tradition, title")
    ]

    columns = []
    for work_id in obras:
        items = A.concordance(state.conn, stems, work_ids=[work_id], limit=req.limit_per_work)
        row = state.conn.execute(
            "SELECT title, edition, tradition FROM works WHERE id = ?", (work_id,)
        ).fetchone()
        if not row:
            continue
        columns.append({
            "work_id": work_id,
            "title": f'{row["title"]} ({row["edition"]})',
            "tradition": row["tradition"],
            "verses": items,
        })
    return {"columns": columns, "resolved_stems": sorted(stems)}


# --------------------------------------------------------------------------
# Búsqueda
# --------------------------------------------------------------------------

@app.get("/search", response_model=list[VerseOut])
def search_text(
    q: str,
    settings: SettingsDep,
    work_id: str | None = None,
    limit: int = Query(50),
) -> list[dict[str, Any]]:
    """Búsqueda literal por texto (FTS5)."""
    limit = min(limit, settings.max_page_size)
    params: list[Any] = [q]
    filt = ""
    if work_id:
        filt = " AND v.work_id = ?"
        params.append(work_id)
    params.append(limit)

    rows = state.conn.execute(
        f"""SELECT v.id, v.work_id, v.ref, v.text, v.chapter, v.number, d.name AS division
            FROM verses_fts f
            JOIN verses v    ON v.id = f.rowid
            JOIN divisions d ON d.id = v.division_id
            WHERE verses_fts MATCH ?{filt}
            ORDER BY rank LIMIT ?""",
        params,
    ).fetchall()
    return [dict(r) for r in rows]


@app.get("/semantic-search", response_model=SemanticSearchResponse)
def semantic_search(
    q: str,
    settings: SettingsDep,
    top_k: int = Query(20, le=100),
    work_ids: list[str] | None = Query(None),
) -> dict[str, Any]:
    if state.vectors is None:
        raise HTTPException(
            503,
            "La búsqueda por significado no está instalada. Ejecuta "
            "INSTALAR-BUSQUEDA-LIGERA-Windows.bat y reinicia el servidor.",
        )
    try:
        resultados = state.vectors.search(q, top_k=top_k, work_ids=work_ids)
    except Exception as exc:                       # noqa: BLE001
        # El traceback va a la consola para poder diagnosticarlo; al usuario
        # se le devuelve una instrucción concreta, no una excepción.
        log.error("Fallo en /semantic-search:\n%s", traceback.format_exc())
        raise HTTPException(503, _explicar_fallo_semantico(exc)) from exc

    return {
        "query": q,
        "model": state.model_id or settings.embedding_model,
        "results": resultados,
        "caveat": CAVEAT_SEMANTIC,
    }


@app.get("/semantic-status")
def semantic_status() -> dict[str, Any]:
    """Diagnóstico de la búsqueda por significado.

    Pensado para responder de un vistazo por qué no funciona: qué índices hay,
    cuántos vectores tienen y qué paquetes están instalados.
    """
    diag = _diagnostico_semantico()
    listo = bool(state.vectors) and any(
        p for p in diag["paquetes_instalados"].values())
    diag["listo"] = listo
    if not diag["indices_en_base"]:
        diag["siguiente_paso"] = "Ejecuta INSTALAR-BUSQUEDA-LIGERA-Windows.bat"
    elif not any(diag["paquetes_instalados"].values()):
        diag["siguiente_paso"] = ("Hay índice pero falta el motor. Ejecuta el "
                                  "instalador de la búsqueda otra vez.")
    elif not listo:
        diag["siguiente_paso"] = "Reinicia el servidor."
    else:
        diag["siguiente_paso"] = "Todo listo."
    return diag


@app.get("/verses/{verse_id}/parallels")
def verse_parallels(verse_id: int, top_k: int = Query(3, le=10)) -> dict[str, Any]:
    """Pasajes semánticamente próximos en las otras tradiciones."""
    if state.vectors is None:
        raise HTTPException(
            503, "La búsqueda por significado no está instalada.")
    row = state.conn.execute(
        """SELECT v.id, v.ref, v.text, v.work_id, w.tradition
           FROM verses v JOIN works w ON w.id = v.work_id WHERE v.id = ?""",
        (verse_id,),
    ).fetchone()
    if not row:
        raise HTTPException(404, "Versículo no encontrado")
    try:
        traditions = state.vectors.cross_tradition_matches(verse_id, top_k=top_k)
    except Exception as exc:                       # noqa: BLE001
        log.error("Fallo en /verses/%s/parallels:\n%s", verse_id, traceback.format_exc())
        raise HTTPException(503, _explicar_fallo_semantico(exc)) from exc

    return {
        "source": dict(row),
        "traditions": traditions,
        "caveat": CAVEAT_SEMANTIC,
    }


@app.get("/resolver-termino")
async def resolver_termino(
    settings: SettingsDep,
    q: str,
    desde: str = Query("es", description="Idioma en que escribe el usuario"),
    hasta: str = Query("en", description="Idioma del corpus"),
) -> dict[str, Any]:
    """Convierte lo que escribe el usuario en algo buscable.

    El corpus está en inglés pero toda la interfaz está en español, así que es
    natural escribir «pecado» y recibir cero resultados. Devolver ese cero es
    técnicamente correcto y pésimo como producto.

    Se intentan dos vías, por orden de calidad:

    1. Buscar la palabra en el lexicón de campos semánticos. Si «pecado»
       aparece entre los términos españoles del campo «Pecado y transgresión»,
       lo mejor que se puede ofrecer es ese campo entero: está curado a mano y
       cubre todas las variantes.

    2. Traducirla. Menos preciso —una palabra sin contexto es ambigua— pero
       siempre disponible.
    """
    q = q.strip()
    if not q:
        return {"original": q, "campos": [], "traduccion": None}

    campos = [
        {"key": f.key, "label": f.label(desde),
         "terminos": len(f.terms.get(hasta, []))}
        for f in state.lexicon.fields_containing(q, desde)
    ]

    traduccion = None
    if desde != hasta:
        try:
            from .core.translate import MyMemoryTranslator, TranslationError
            traductor = MyMemoryTranslator(settings.web_search_timeout,
                                           settings.translate_email)
            traduccion = (await traductor.translate(q, desde, hasta)).strip()
            # El traductor a veces devuelve la frase con puntuación o
            # mayúscula inicial; para buscar interesa solo la palabra.
            traduccion = traduccion.strip(".,;:!¡?¿ ").lower() or None
        except (TranslationError, Exception):        # noqa: BLE001
            traduccion = None

    return {
        "original": q,
        "campos": campos,
        "traduccion": traduccion if traduccion and traduccion.lower() != q.lower() else None,
    }


@app.post("/translate")
async def translate(
    settings: SettingsDep,
    verse_ids: list[int],
    lang: str = Query("es", description="Idioma destino: es, pt, fr, ar, hi"),
) -> dict[str, Any]:
    """Traducción automática de versículos, como apoyo a la lectura.

    Nunca sustituye al original ni se usa para el análisis: las frecuencias se
    calculan siempre sobre el texto de la edición. La interfaz debe mostrarla
    debajo y marcada como automática.
    """
    if not settings.enable_web_search:
        raise HTTPException(503, "La traducción está desactivada en este servidor.")
    if not verse_ids:
        return {"results": {}, "provider": None}
    if len(verse_ids) > 25:
        raise HTTPException(400, "Máximo 25 versículos por petición.")

    from .core.translate import (MyMemoryTranslator, TranslationError,
                                 cached, store)

    origen = state.conn.execute(
        f"""SELECT v.id, v.text, w.language
            FROM verses v JOIN works w ON w.id = v.work_id
            WHERE v.id IN ({','.join('?' * len(verse_ids))})""",
        verse_ids,
    ).fetchall()

    ya = cached(state.conn, verse_ids, lang)
    resultados: dict[int, str] = dict(ya)
    traductor = MyMemoryTranslator(settings.web_search_timeout,
                                   settings.translate_email)
    errores: list[str] = []

    for fila in origen:
        vid = fila["id"]
        if vid in resultados:
            continue
        if fila["language"] == lang:
            continue                   # ya está en el idioma pedido
        try:
            texto = await traductor.translate(fila["text"], fila["language"], lang)
            resultados[vid] = texto
            if state.write_conn:
                store(state.write_conn, vid, lang, texto, traductor.name)
        except TranslationError as exc:
            errores.append(str(exc))

    return {
        "results": resultados,
        "provider": traductor.name,
        "cached": len(ya),
        "errors": errores[:3],
        "disclaimer": "machine_translation",
    }


@app.get("/context")
async def external_context(
    settings: SettingsDep,
    ref: str | None = None,
    topic: str | None = None,
    lang: str = "es",
) -> dict[str, Any]:
    """Contexto académico externo (Sefaria, Quran.com, Wikipedia).

    Solo dominios de la allowlist. Todo resultado se devuelve con su URL para
    que el usuario verifique la fuente.
    """
    if not settings.enable_web_search:
        raise HTTPException(503, "Búsqueda en línea desactivada.")
    from .core.websearch import WebContext
    client = WebContext(settings.web_search_allowlist, settings.web_search_timeout)
    return {
        "results": await client.gather(ref=ref, topic=topic, lang=lang),
        "disclaimer": "Fuentes externas. La aplicación no avala su contenido.",
    }
