"""Contratos de la API. Son también la fuente de verdad para los modelos Dart
del cliente Flutter."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class WorkOut(BaseModel):
    id: str
    tradition: str
    title: str
    edition: str
    language: str
    year: int | None = None
    license: str
    source_url: str | None = None
    division_label: str
    verse_label: str
    total_tokens: int
    total_verses: int
    total_divisions: int = 0


class DivisionOut(BaseModel):
    id: int
    work_id: str
    ordinal: int
    name: str
    name_alt: str | None = None
    section: str | None = None
    total_tokens: int


class VerseOut(BaseModel):
    id: int
    work_id: str
    ref: str
    text: str
    division: str | None = None
    chapter: int | None = None
    number: int | None = None


class SemanticFieldOut(BaseModel):
    key: str
    label: str
    description: str = ""
    term_count: int
    languages: list[str]


class FrequencyRequest(BaseModel):
    term: str = ""
    semantic_field: str | None = None
    extra_terms: list[str] = Field(default_factory=list)
    language: Literal["es", "en"] = "en"
    work_ids: list[str] | None = None


class WorkFrequencyOut(BaseModel):
    work_id: str
    work_title: str
    tradition: str
    language: str
    raw_count: int
    verse_count: int
    total_tokens: int
    per_10k: float
    dispersion: float
    divisions_present: int
    divisions_total: int


class FrequencyResponse(BaseModel):
    query: dict[str, Any]
    resolved_stems: list[str]
    results: list[WorkFrequencyOut]
    keyness: list[dict[str, Any]]
    caveat: str = Field(description="Clave de aviso; la app la traduce")


class DivisionFrequencyOut(BaseModel):
    division_id: int
    name: str
    ordinal: int
    section: str | None = None
    raw_count: int
    total_tokens: int
    per_10k: float


class ConcordanceItem(BaseModel):
    verse_id: int
    ref: str
    text: str
    work_id: str
    work_title: str
    tradition: str
    division: str
    matched_forms: list[str]
    hits: int


class ConcordanceResponse(BaseModel):
    total: int
    items: list[ConcordanceItem]


class SimilarVerse(BaseModel):
    verse_id: int
    ref: str
    text: str
    work_id: str
    tradition: str
    similarity: float


class SemanticSearchResponse(BaseModel):
    query: str
    model: str
    results: list[SimilarVerse]
    caveat: str = Field(description="Clave de aviso; la app la traduce")


class ParallelRequest(BaseModel):
    term: str = ""
    semantic_field: str | None = None
    extra_terms: list[str] = Field(default_factory=list)
    # Opcional: sin obras indicadas se comparan todas, que es lo que quiere el
    # usuario el 90 % de las veces. Exigirlo obligaba al cliente a pedir antes
    # el catálogo solo para repetirlo.
    work_ids: list[str] | None = None
    language: Literal["es", "en"] = "en"
    limit_per_work: int = 10


class WebResult(BaseModel):
    title: str
    url: str
    snippet: str
    source: str
