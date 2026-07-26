"""
Traducción bajo demanda de versículos.

Principio que rige todo este módulo: **la traducción automática nunca
sustituye al texto**. Se muestra debajo del original, marcada como automática,
y no se usa jamás para el análisis léxico. Presentar texto sagrado traducido
por una máquina como si fuera el texto sería un problema grave en una
aplicación que presume de rigor, y además invalidaría todas las frecuencias.

Es una ayuda a la lectura para quien no domina el inglés, nada más.

Todo lo traducido se guarda en la base de datos. Así cada versículo se traduce
una sola vez en la vida de la aplicación, y con el uso el corpus se va
traduciendo solo sin coste añadido.
"""

from __future__ import annotations

import sqlite3
from abc import ABC, abstractmethod
from typing import Sequence
from urllib.parse import quote, urlparse

# Límite del proveedor gratuito por petición. Los versículos rara vez lo
# superan, pero algunos del Corán y de Ester son largos.
MAX_CHARS = 480


class TranslationError(RuntimeError):
    """El proveedor no pudo traducir. No es motivo para romper la pantalla."""


class Translator(ABC):
    name: str
    allowed_host: str

    @abstractmethod
    async def translate(self, text: str, source: str, target: str) -> str: ...


class MyMemoryTranslator(Translator):
    """Proveedor gratuito sin clave de API.

    Se eligió porque no exige registro ni tarjeta, lo que mantiene la promesa
    de que la aplicación funcione nada más instalarla. A cambio tiene un
    límite diario generoso pero real, de ahí que la caché sea obligatoria.
    """

    name = "MyMemory"
    allowed_host = "api.mymemory.translated.net"

    def __init__(self, timeout: int = 12, email: str = ""):
        self.timeout = timeout
        self.email = email.strip()

    async def translate(self, text: str, source: str, target: str) -> str:
        if not text.strip():
            return ""

        import httpx      # solo necesario aquí: la caché es Python puro

        recorte = text[:MAX_CHARS]
        url = (
            f"https://{self.allowed_host}/get"
            f"?q={quote(recorte)}&langpair={source}|{target}"
        )
        if self.email:
            url += f"&de={quote(self.email)}"     # amplía la cuota diaria
        if urlparse(url).hostname != self.allowed_host:
            raise TranslationError("Destino no permitido")

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                r = await client.get(url)
                r.raise_for_status()
                data = r.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise TranslationError(f"El traductor no respondió: {exc}") from exc

        estado = data.get("responseStatus")
        if estado not in (200, "200"):
            raise TranslationError(
                data.get("responseDetails") or "El traductor rechazó la petición"
            )
        traducido = (data.get("responseData") or {}).get("translatedText", "")
        if not traducido:
            raise TranslationError("El traductor devolvió una respuesta vacía")

        if len(text) > MAX_CHARS:
            traducido += " […]"        # el recorte debe ser visible
        return traducido


# --------------------------------------------------------------------------
# Caché en base de datos
# --------------------------------------------------------------------------

SCHEMA = """
CREATE TABLE IF NOT EXISTS translations (
    verse_id  INTEGER NOT NULL,
    lang      TEXT NOT NULL,
    text      TEXT NOT NULL,
    provider  TEXT NOT NULL,
    created   TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (verse_id, lang)
) WITHOUT ROWID;
"""


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    conn.commit()


def cached(conn: sqlite3.Connection, verse_ids: Sequence[int], lang: str) -> dict[int, str]:
    if not verse_ids:
        return {}
    marcas = ",".join("?" * len(verse_ids))
    try:
        filas = conn.execute(
            f"SELECT verse_id, text FROM translations "
            f"WHERE lang = ? AND verse_id IN ({marcas})",
            [lang, *verse_ids],
        ).fetchall()
    except sqlite3.OperationalError:
        return {}                      # la tabla aún no existe
    return {r["verse_id"]: r["text"] for r in filas}


def store(conn: sqlite3.Connection, verse_id: int, lang: str,
          text: str, provider: str) -> None:
    conn.execute(
        "INSERT OR REPLACE INTO translations (verse_id, lang, text, provider) "
        "VALUES (?,?,?,?)",
        (verse_id, lang, text, provider),
    )
    conn.commit()
