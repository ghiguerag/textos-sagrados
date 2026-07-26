"""
Consulta en línea de contexto académico.

Objetivo: cuando el usuario mira un versículo, poder traer comentario
filológico e histórico de fuentes reconocidas, sin que la app invente nada.

Diseño defensivo por dos razones:
  - Solo se consultan dominios de la allowlist (config.web_search_allowlist).
    Es un tema sensible; abrir la búsqueda a todo internet arrastraría
    material polémico o de baja calidad al producto.
  - Todo resultado se devuelve con su URL para que el usuario verifique. La
    app nunca presenta contenido externo como afirmación propia.
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote, urlparse

import httpx


@dataclass
class ExternalResult:
    title: str
    url: str
    snippet: str
    source: str


class WebContext:
    def __init__(self, allowlist: list[str], timeout: int = 15):
        self.allowlist = allowlist
        self.timeout = timeout

    def _allowed(self, url: str) -> bool:
        host = (urlparse(url).hostname or "").lower()
        return any(host == d or host.endswith("." + d) for d in self.allowlist)

    async def sefaria_commentary(self, ref: str, limit: int = 5) -> list[ExternalResult]:
        """Comentario rabínico clásico (Rashi, Ibn Ezra, Ramban) sobre un
        pasaje del Tanaj. Sefaria es de acceso abierto."""
        url = f"https://www.sefaria.org/api/related/{quote(ref)}"
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                resp = await client.get(url)
                resp.raise_for_status()
                data = resp.json()
            except (httpx.HTTPError, json.JSONDecodeError):
                return []

        out: list[ExternalResult] = []
        for link in (data.get("links") or [])[: limit * 4]:
            if link.get("category") != "Commentary":
                continue
            target = link.get("sourceRef") or ""
            out.append(ExternalResult(
                title=target,
                url=f"https://www.sefaria.org/{quote(target.replace(' ', '_'))}",
                snippet=link.get("commentator", ""),
                source="Sefaria",
            ))
            if len(out) >= limit:
                break
        return out

    async def quran_context(self, surah: int, ayah: int) -> list[ExternalResult]:
        """Análisis morfológico y traducciones paralelas de una aleya."""
        url = f"https://api.quran.com/api/v4/verses/by_key/{surah}:{ayah}?words=true&fields=text_uthmani"
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                resp = await client.get(url)
                resp.raise_for_status()
                data = resp.json()
            except (httpx.HTTPError, json.JSONDecodeError):
                return []

        verse = data.get("verse", {})
        return [ExternalResult(
            title=f"Corán {surah}:{ayah}",
            url=f"https://quran.com/{surah}/{ayah}",
            snippet=verse.get("text_uthmani", ""),
            source="Quran.com",
        )]

    async def wikipedia_summary(self, topic: str, lang: str = "es") -> list[ExternalResult]:
        """Contexto enciclopédico de un concepto o figura. Se marca claramente
        como fuente terciaria en la interfaz."""
        url = f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{quote(topic)}"
        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
            try:
                resp = await client.get(url)
                resp.raise_for_status()
                data = resp.json()
            except (httpx.HTTPError, json.JSONDecodeError):
                return []

        page = data.get("content_urls", {}).get("desktop", {}).get("page", "")
        if not page or not self._allowed(page):
            return []
        return [ExternalResult(
            title=data.get("title", topic),
            url=page,
            snippet=data.get("extract", ""),
            source="Wikipedia",
        )]

    async def gather(self, *, ref: str | None = None, topic: str | None = None,
                     lang: str = "es") -> list[dict[str, Any]]:
        """Lanza en paralelo las consultas pertinentes y devuelve lo que
        responda a tiempo. Una fuente caída no debe bloquear las demás."""
        tasks = []
        if topic:
            tasks.append(self.wikipedia_summary(topic, lang))
        if ref and ref.startswith("Q "):
            try:
                s, a = ref[2:].split(":")
                tasks.append(self.quran_context(int(s), int(a)))
            except ValueError:
                pass
        elif ref:
            tasks.append(self.sefaria_commentary(ref))

        if not tasks:
            return []

        gathered = await asyncio.gather(*tasks, return_exceptions=True)
        results: list[dict[str, Any]] = []
        for item in gathered:
            if isinstance(item, Exception):
                continue
            results.extend(r.__dict__ for r in item)
        return results
