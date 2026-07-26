"""
Motores de codificación: convierten texto en vectores.

Existen dos porque el compromiso tamaño/calidad es muy distinto según quién
ejecute el programa:

  - `torch`  (sentence-transformers): calidad máxima, ~3 GB de instalación.
    Apropiado para el desarrollador y para un servidor.

  - `static` (model2vec): el modelo es una tabla de consulta en lugar de una
    red neuronal. Sin PyTorch, solo numpy. Cientos de veces más rápido y entre
    30 y 60 veces más pequeño. Apropiado para empaquetar en la app publicada.

Ambos exponen la misma interfaz, así que el resto del código no sabe cuál está
usando. Eso permite medir la diferencia de calidad sobre datos reales en vez
de suponerla.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from functools import lru_cache
from typing import Sequence

import numpy as np


class Encoder(ABC):
    """Interfaz común a todos los motores."""

    name: str
    dimensions: int

    @abstractmethod
    def encode(self, texts: Sequence[str]) -> np.ndarray:
        """Devuelve una matriz (n_textos × dimensiones) normalizada por filas.

        La normalización es obligatoria: permite calcular la similitud coseno
        como un simple producto escalar, que es lo que hace el buscador.
        """

    def encode_one(self, text: str) -> np.ndarray:
        return self.encode([text])[0]


def _normalize(m: np.ndarray) -> np.ndarray:
    m = np.asarray(m, dtype=np.float32)
    if m.ndim == 1:
        m = m.reshape(1, -1)
    normas = np.linalg.norm(m, axis=1, keepdims=True)
    normas[normas == 0] = 1.0          # evita dividir por cero en textos vacíos
    return m / normas


class TorchEncoder(Encoder):
    """sentence-transformers sobre PyTorch. Calidad de referencia."""

    def __init__(self, model_name: str):
        from sentence_transformers import SentenceTransformer

        self.name = f"torch:{model_name}"
        self._model = SentenceTransformer(model_name)
        self.dimensions = int(self._model.get_sentence_embedding_dimension())

    def encode(self, texts: Sequence[str]) -> np.ndarray:
        return _normalize(
            self._model.encode(list(texts), normalize_embeddings=True,
                               show_progress_bar=False)
        )


class StaticEncoder(Encoder):
    """model2vec: tabla de vectores por token, sin red neuronal.

    `dimensionality` aplica reducción PCA al cargar. Bajar de 512 a 256
    dimensiones divide por dos el tamaño del modelo y de los vectores, con
    una pérdida de calidad que conviene medir, no suponer.
    """

    def __init__(self, model_name: str, *, dimensionality: int | None = None,
                 quantize_to: str | None = None):
        from model2vec import StaticModel

        kwargs = {}
        if dimensionality:
            kwargs["dimensionality"] = dimensionality
        if quantize_to:
            kwargs["quantize_to"] = quantize_to

        self._model = StaticModel.from_pretrained(model_name, **kwargs)
        self.name = f"static:{model_name}"
        if dimensionality:
            self.name += f":d{dimensionality}"
        if quantize_to:
            self.name += f":{quantize_to}"
        self.dimensions = int(self._model.dim)

    def encode(self, texts: Sequence[str]) -> np.ndarray:
        return _normalize(self._model.encode(list(texts)))

    def save(self, path) -> None:
        """Guarda el modelo ya reducido para empaquetarlo en la app."""
        self._model.save_pretrained(str(path))


# Motores conocidos. La clave es lo que se guarda en la columna `model` de la
# tabla de vectores, de modo que puedan convivir varios índices en la misma
# base de datos y compararse entre sí.
PRESETS: dict[str, dict] = {
    "calidad": {
        "tipo": "torch",
        "modelo": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        "descripcion": "Calidad máxima. ~3 GB de instalación.",
    },
    "ligero": {
        "tipo": "static",
        "modelo": "minishlab/potion-multilingual-128M",
        "descripcion": "101 idiomas, sin PyTorch. ~530 MB de descarga.",
    },
    "ligero-256": {
        "tipo": "static",
        "modelo": "minishlab/potion-multilingual-128M",
        "dimensionality": 256,
        "descripcion": "Mitad de dimensiones. ~265 MB.",
    },
    "minimo": {
        "tipo": "static",
        "modelo": "minishlab/potion-multilingual-128M",
        "dimensionality": 128,
        "quantize_to": "int8",
        "descripcion": "El más pequeño que sigue siendo multilingüe. ~32 MB.",
    },
}


@lru_cache(maxsize=4)
def get_encoder(preset: str) -> Encoder:
    """Construye (una vez) el motor indicado."""
    if preset not in PRESETS:
        raise ValueError(
            f"Motor desconocido: {preset}. Opciones: {', '.join(PRESETS)}"
        )
    cfg = dict(PRESETS[preset])
    tipo = cfg.pop("tipo")
    modelo = cfg.pop("modelo")
    cfg.pop("descripcion", None)

    if tipo == "torch":
        return TorchEncoder(modelo)
    return StaticEncoder(modelo, **cfg)


def encoder_id(preset: str) -> str:
    """Identificador estable que se guarda junto a cada vector."""
    cfg = PRESETS[preset]
    partes = [cfg["tipo"], cfg["modelo"].split("/")[-1]]
    if cfg.get("dimensionality"):
        partes.append(f"d{cfg['dimensionality']}")
    if cfg.get("quantize_to"):
        partes.append(str(cfg["quantize_to"]))
    return ":".join(partes)


def preset_from_id(model_id: str) -> str | None:
    """Camino inverso: del identificador guardado al preajuste.

    Es imprescindible. En la base de datos se guarda el `encoder_id`
    ('static:potion-multilingual-128M'), no el nombre del preajuste
    ('ligero'). Sin esta traducción, al recuperar el índice se intentaba
    cargar un modelo de HuggingFace llamado 'static:potion-...', que no
    existe, y la búsqueda fallaba con un error incomprensible.
    """
    for preset in PRESETS:
        if encoder_id(preset) == model_id:
            return preset
    return None


def resolve_encoder(model_id: str) -> Encoder:
    """Devuelve el motor correspondiente a lo que haya guardado en la base.

    Acepta tres formas, por orden de preferencia:
      1. Un identificador de índice ('static:potion-multilingual-128M')
      2. Un nombre de preajuste ('ligero', 'minimo')
      3. Un modelo de sentence-transformers ('sentence-transformers/…'),
         por compatibilidad con índices creados antes de esta refactorización
    """
    preset = preset_from_id(model_id)
    if preset:
        return get_encoder(preset)

    if model_id in PRESETS:
        return get_encoder(model_id)

    if model_id.startswith(("static:", "torch:")):
        # Tiene forma de identificador pero no coincide con ningún preajuste:
        # probablemente el índice se creó con una versión distinta del código.
        raise ValueError(
            f"El índice «{model_id}» no corresponde a ningún motor conocido. "
            f"Motores disponibles: {', '.join(sorted(PRESETS))}. "
            f"Reconstruye el índice con: "
            f"python scripts/build_embeddings.py --engine ligero"
        )

    return TorchEncoder(model_id)
