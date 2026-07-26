"""
Tokenización y normalización multilingüe para corpus religiosos.

Funciona SIN dependencias externas (solo stdlib), de modo que el motor sea
reproducible y empaquetable en dispositivos. Si spaCy está instalado se usa
automáticamente para lematización de mayor calidad (ver config.settings).

Flujo: texto crudo -> normalización -> tokens -> lemas.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from functools import lru_cache
from typing import Iterable, Sequence

# --------------------------------------------------------------------------
# Marcas diacríticas de escrituras no latinas. Filtrarlas es esencial: los
# textos vocalizados (nikud hebreo / harakat árabe) rompen cualquier conteo.
# --------------------------------------------------------------------------

_HEBREW_POINTS = r"֑-ׇ"
_ARABIC_MARKS = r"ؐ-ًؚ-ٰٟۖ-ۭ"
_DEVANAGARI_MARKS = r"॑-॔"

_STRIP_MARKS_RE = re.compile(f"[{_HEBREW_POINTS}{_ARABIC_MARKS}{_DEVANAGARI_MARKS}]")

# Palabra = secuencia de letras Unicode, con apóstrofe o guion internos
# permitidos ("d'entre", "Qur'an", "Bhagavad-Gita").
_WORD_RE = re.compile(r"[^\W\d_]+(?:['’\-][^\W\d_]+)*", re.UNICODE)

# Marcadores editoriales que contaminan los corpus de dominio público:
# corchetes de texto añadido por el traductor, llamadas de nota, etc.
_EDITORIAL_RE = re.compile(r"\[[^\]]{0,80}\]|\{[^\}]{0,80}\}|<[^>]{0,80}>")


# --------------------------------------------------------------------------
# Stopwords
# --------------------------------------------------------------------------

STOPWORDS: dict[str, frozenset[str]] = {
    "es": frozenset("""
        a al algo algun alguna algunas alguno algunos ante antes aquel aquella
        aquellas aquello aquellos aqui asi aun aunque cada casi como con contra
        cual cuales cuando cuanto de del desde donde dos e el ella ellas ello
        ellos en entre era eran eres es esa esas ese eso esos esta estaba estan
        estas este esto estos fue fueron fui ha habia han has hasta hay he la
        las le les lo los mas me mi mia mio mis mucho muy nada ni no nos nosotros
        nuestra nuestro o os otra otras otro otros para pero poco por porque que
        quien quienes se sea sean segun ser si sido sin sobre son su sus tal
        tambien tan tanto te tener ti tiene tienen toda todas todo todos tu tus
        un una unas uno unos vosotros vuestra vuestro y ya yo
        """.split()),
    "en": frozenset("""
        a about above after again against all am an and any are as at be because
        been before being below between both but by cannot could did do does
        doing down during each few for from further had has have having he her
        here hers herself him himself his how i if in into is it its itself me
        more most my myself no nor not of off on once only or other ought our
        ours ourselves out over own same shall she should so some such than that
        the their theirs them themselves then there these they this those
        through to too under until up unto very was we were what when where
        which while who whom why with would you your yours yourself yourselves
        thou thee thy thine ye hath doth shalt
        """.split()),
}

# Términos que NUNCA deben filtrarse aunque coincidan con una stopword, porque
# son teológicamente sustantivos en estos corpus.
PROTECTED = frozenset({"dios", "god", "lord", "senor", "allah", "alma", "soul"})


# --------------------------------------------------------------------------
# Stemmer ligero. No es un lematizador filológico: agrupa
# "misericordia/misericordias", "amar/amaba/amaron". Para precisión académica
# activa spaCy (settings.use_spacy).
# --------------------------------------------------------------------------

_ES_SUFFIXES: tuple[tuple[str, str], ...] = (
    ("amiento", ""), ("imiento", ""),
    ("acion", "acion"), ("ucion", "ucion"),
    ("adora", ""), ("ador", ""), ("ancia", ""), ("encia", ""),
    ("abamos", "ar"), ("aremos", "ar"), ("eremos", "er"), ("iremos", "ir"),
    ("aran", "ar"), ("eran", "er"), ("iran", "ir"),
    ("aria", "ar"), ("eria", "er"), ("iria", "ir"),
    ("aron", "ar"), ("ieron", "er"), ("aban", "ar"), ("ian", "er"),
    ("ando", "ar"), ("iendo", "er"), ("ado", "ar"), ("ido", "er"),
    ("amos", ""), ("emos", ""), ("imos", ""),
    ("mente", ""),
)

_EN_SUFFIXES: tuple[tuple[str, str], ...] = (
    ("ational", "ate"), ("fulness", "ful"), ("ousness", "ous"),
    ("iveness", "ive"), ("ization", "ize"),
    ("ement", ""), ("ment", ""), ("ness", ""),
    ("ingly", ""), ("edly", ""), ("ing", ""), ("eth", ""), ("est", ""),
    ("ed", ""), ("ly", ""),
)

# Vocales finales que marcan género/tema en español y que se eliminan al final
# para que "eterno"/"eterna" y "cielo"/"cielos" converjan al mismo lema.
_ES_FINAL_VOWELS = ("o", "a", "e")

# Longitud mínima de la raíz resultante. El español necesita 4 (si no,
# "dios" -> "dio"); el inglés tolera 3 ("gods" -> "god").
_MIN_STEM = {"es": 4, "en": 3}

# Terminaciones inglesas en -s que NO son plurales.
_EN_NOT_PLURAL = ("ss", "us", "is", "ous", "as")


def _apply_suffixes(word: str, rules: Sequence[tuple[str, str]], floor: int) -> str:
    for suffix, replacement in rules:
        if word.endswith(suffix) and len(word) - len(suffix) + len(replacement) >= floor:
            return word[: -len(suffix)] + replacement
    return word


def _depluralize(word: str, lang: str, floor: int) -> str:
    """Singulariza ANTES de aplicar el resto de reglas.

    Sin este paso "cielos" y "cielo" caerían en lemas distintos y todo el
    conteo de frecuencias quedaría fragmentado.
    """
    if lang == "es":
        if word.endswith("ces") and len(word) - 2 >= 3:      # luces -> luz
            return word[:-3] + "z"
        if word.endswith("yes") and len(word) - 2 >= 3:      # reyes -> rey
            return word[:-2]
        for suffix in ("es", "s"):
            if word.endswith(suffix) and len(word) - len(suffix) >= floor:
                return word[: -len(suffix)]
    elif lang == "en":
        if word.endswith(_EN_NOT_PLURAL):
            return word
        if word.endswith("ies") and len(word) - 2 >= floor:   # mercies -> mercy
            return word[:-3] + "y"
        for suffix in ("es", "s"):
            if word.endswith(suffix) and len(word) - len(suffix) >= floor:
                return word[: -len(suffix)]
    return word


@lru_cache(maxsize=200_000)
def stem(word: str, lang: str = "es") -> str:
    """Reduce una palabra normalizada a su raíz aproximada.

    Español: singularizar -> sufijo derivativo/verbal -> vocal temática final.
    Inglés:  singularizar -> sufijo derivativo/verbal -> -e final.

    Árabe, hebreo y sánscrito quedan sin stemming a propósito: la morfología
    semítica es no concatenativa y un stemmer de sufijos haría más daño que
    bien. Para esos idiomas se usa el lexicón de raíces (lexicon.py).
    """
    floor = _MIN_STEM.get(lang)
    if floor is None or len(word) <= floor:
        return word

    if lang == "es":
        word = _depluralize(word, "es", floor)
        word = _apply_suffixes(word, _ES_SUFFIXES, floor)
        if len(word) - 1 >= floor and word.endswith(_ES_FINAL_VOWELS):
            word = word[:-1]
        return word

    if lang == "en":
        word = _depluralize(word, "en", floor)
        word = _apply_suffixes(word, _EN_SUFFIXES, floor)
        if len(word) - 1 >= floor and word.endswith("e"):
            word = word[:-1]
        return word

    return word


# --------------------------------------------------------------------------
# Normalización
# --------------------------------------------------------------------------

def strip_accents(text: str) -> str:
    """Quita diacríticos latinos. No afecta a hebreo/árabe (ya filtrados)."""
    decomposed = unicodedata.normalize("NFD", text)
    return "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")


def normalize(text: str, *, lang: str = "es", fold_accents: bool = True) -> str:
    """Limpieza previa a la tokenización."""
    text = unicodedata.normalize("NFC", text)
    text = _EDITORIAL_RE.sub(" ", text)
    text = _STRIP_MARKS_RE.sub("", text)
    text = text.replace("’", "'").replace("­", "")
    text = text.lower()
    if fold_accents and lang in ("es", "en"):
        text = strip_accents(text)
    return text


# --------------------------------------------------------------------------
# API pública
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class Token:
    surface: str   # forma tal como aparece (ya normalizada)
    lemma: str     # raíz usada para agrupar
    position: int  # índice dentro del versículo, para concordancia KWIC


def tokenize(
    text: str,
    *,
    lang: str = "es",
    remove_stopwords: bool = True,
    fold_accents: bool = True,
) -> list[Token]:
    """Convierte un versículo en tokens analizables."""
    cleaned = normalize(text, lang=lang, fold_accents=fold_accents)
    stops = STOPWORDS.get(lang, frozenset()) if remove_stopwords else frozenset()

    tokens: list[Token] = []
    for position, match in enumerate(_WORD_RE.finditer(cleaned)):
        surface = match.group(0)
        if len(surface) < 2:
            continue
        if surface in stops and surface not in PROTECTED:
            continue
        tokens.append(Token(surface=surface, lemma=stem(surface, lang), position=position))
    return tokens


def token_count(text: str, *, lang: str = "es") -> int:
    """Total de palabras SIN filtrar stopwords.

    Es el denominador para normalizar frecuencias por cada 10.000 palabras.
    Debe contarlo todo: si no, las tasas entre corpus no son comparables.
    """
    return sum(1 for _ in _WORD_RE.finditer(normalize(text, lang=lang)))


def lemmas(text: str, *, lang: str = "es") -> list[str]:
    return [t.lemma for t in tokenize(text, lang=lang)]


def ngrams(tokens: Iterable[str], n: int = 2) -> list[tuple[str, ...]]:
    items = list(tokens)
    return [tuple(items[i : i + n]) for i in range(len(items) - n + 1)]
