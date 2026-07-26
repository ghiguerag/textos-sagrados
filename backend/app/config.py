from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="TS_", env_file=".env", extra="ignore")

    app_name: str = "Textos Sagrados API"
    version: str = "1.0.0"
    db_path: Path = BASE_DIR / "data" / "corpus.db"
    lexicon_path: Path = BASE_DIR / "data" / "lexicon.json"

    # CORS: en producción restringir a los orígenes reales de la app.
    cors_origins: list[str] = ["*"]

    # Embeddings. El modelo multilingüe permite emparejar un versículo en
    # español con uno en inglés, que es justo lo que hace falta aquí.
    embedding_model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    enable_embeddings: bool = True

    # Traducción. El correo es opcional: MyMemory amplía mucho la cuota
    # diaria si las peticiones se identifican. Nunca se envía a nadie más.
    translate_email: str = ""

    # Búsqueda en línea (contexto académico externo).
    enable_web_search: bool = True
    web_search_timeout: int = 15
    web_search_allowlist: list[str] = [
        "sefaria.org", "quran.com", "corpus.quran.com", "biblehub.com",
        "www.gutenberg.org", "plato.stanford.edu", "en.wikipedia.org",
        "es.wikipedia.org", "www.perseus.tufts.edu", "archive.org",
    ]

    # Límite de resultados por petición: evita que un cliente pida 50.000
    # versículos y tumbe el servidor.
    max_page_size: int = 500
    cache_ttl_seconds: int = 3600


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
