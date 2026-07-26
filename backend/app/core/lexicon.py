"""
Campos semánticos: agrupan varios lemas bajo un concepto único.

Por qué existe: contar "misericordia" por separado de "compasión", "clemencia"
y "piedad" produce una comparación engañosa entre tradiciones, porque cada
traductor eligió un vocabulario distinto para el mismo concepto de origen. El
campo semántico es la unidad de comparación honesta.

El lexicón vive en data/lexicon.json para poder editarlo sin tocar código.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from .tokenizer import normalize, stem

DEFAULT_LEXICON = Path(__file__).resolve().parents[2] / "data" / "lexicon.json"


FALLBACK_UI_LANG = "en"


@dataclass
class SemanticField:
    key: str
    labels: dict[str, str]                                       # idioma UI -> rótulo
    descriptions: dict[str, str] = field(default_factory=dict)   # idioma UI -> texto
    terms: dict[str, list[str]] = field(default_factory=dict)    # idioma CORPUS -> palabras

    def label(self, ui_lang: str) -> str:
        """Rótulo en el idioma de la interfaz.

        Cadena de reserva: idioma pedido -> inglés -> primero disponible. La app
        nunca debe quedarse sin texto que mostrar.
        """
        return (
            self.labels.get(ui_lang)
            or self.labels.get(FALLBACK_UI_LANG)
            or next(iter(self.labels.values()), self.key)
        )

    def description(self, ui_lang: str) -> str:
        return (
            self.descriptions.get(ui_lang)
            or self.descriptions.get(FALLBACK_UI_LANG)
            or ""
        )

    def stems(self, lang: str) -> set[str]:
        """Raíces a buscar. `lang` es el idioma del CORPUS, no el de la
        interfaz: son ejes independientes. Un usuario puede tener la app en
        árabe y analizar un corpus en inglés."""
        return {stem(normalize(w, lang=lang), lang) for w in self.terms.get(lang, [])}


class Lexicon:
    def __init__(self, fields: dict[str, SemanticField]):
        self._fields = fields

    @classmethod
    def load(cls, path: Path | str = DEFAULT_LEXICON) -> "Lexicon":
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        fields = {}
        for key, item in raw["fields"].items():
            label = item["label"]
            description = item.get("description", "")
            # Compatibilidad con lexicon.json v1, donde label y description
            # eran cadenas sueltas en español.
            if isinstance(label, str):
                label = {"es": label}
            if isinstance(description, str):
                description = {"es": description} if description else {}
            fields[key] = SemanticField(
                key=key,
                labels=label,
                descriptions=description,
                terms=item.get("terms", {}),
            )
        return cls(fields)

    def __iter__(self):
        return iter(self._fields.values())

    def __len__(self) -> int:
        return len(self._fields)

    def get(self, key: str) -> SemanticField | None:
        return self._fields.get(key)

    def expand(self, key: str, lang: str) -> set[str]:
        """Devuelve el conjunto de raíces a buscar para un concepto."""
        f = self._fields.get(key)
        return f.stems(lang) if f else set()

    def fields_containing(self, word: str, lang: str) -> list[SemanticField]:
        target = stem(normalize(word, lang=lang), lang)
        return [f for f in self._fields.values() if target in f.stems(lang)]


@lru_cache(maxsize=1)
def default_lexicon() -> Lexicon:
    return Lexicon.load()
