"""
Validación del texto descargado antes de incorporarlo al corpus.

Existe por un fallo grave y silencioso: se pidió a la API del Corán la
traducción inglesa de Palmer y devolvió el texto árabe original. Nada falló:
la descarga fue correcta, la ingesta también, y el corpus quedó con 6.236
aleyas en árabe declaradas como inglés.

El resultado fue que todas las comparaciones con el Corán daban cero, y ese
cero parecía un dato. Un corpus con texto equivocado es peor que un corpus
vacío, porque no se nota.

La lección: no basta con comprobar que la descarga funciona. Hay que verificar
que lo descargado es lo que se pidió.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass

# Rangos Unicode de cada alfabeto. Se comprueba el alfabeto, no el idioma:
# distinguir inglés de francés requeriría un modelo, pero distinguir alfabeto
# latino de árabe basta para detectar el error que nos ocupa.
ALFABETOS: dict[str, tuple[tuple[int, int], ...]] = {
    "latino":      ((0x0041, 0x024F),),
    "arabe":       ((0x0600, 0x06FF), (0x0750, 0x077F), (0xFB50, 0xFDFF)),
    "hebreo":      ((0x0590, 0x05FF), (0xFB1D, 0xFB4F)),
    "devanagari":  ((0x0900, 0x097F),),
    "griego":      ((0x0370, 0x03FF),),
    "cirilico":    ((0x0400, 0x04FF),),
}

# Alfabeto que debe tener el texto según el idioma declarado.
IDIOMA_A_ALFABETO: dict[str, str] = {
    "en": "latino", "es": "latino", "pt": "latino", "fr": "latino",
    "de": "latino", "it": "latino", "la": "latino",
    "ar": "arabe", "he": "hebreo", "sa": "devanagari", "hi": "devanagari",
    "el": "griego", "ru": "cirilico",
}

# Proporción mínima de caracteres del alfabeto esperado. No se exige el 100 %
# porque las traducciones incluyen nombres transliterados, cifras y signos.
UMBRAL = 0.60


@dataclass
class Diagnostico:
    alfabeto_detectado: str
    proporcion: float
    esperado: str
    valido: bool
    muestra: str

    def explicar(self, obra: str, idioma: str) -> str:
        return (
            f"El texto descargado para «{obra}» no está en {idioma}.\n"
            f"  Alfabeto esperado: {self.esperado}\n"
            f"  Alfabeto recibido: {self.alfabeto_detectado} "
            f"({self.proporcion:.0%} de los caracteres)\n"
            f"  Muestra: {self.muestra[:90]}\n\n"
            f"Causa habitual: el identificador de edición no existe y el "
            f"servicio devuelve otra cosa sin avisar. Comprueba el "
            f"identificador en la documentación de la fuente."
        )


def detectar_alfabeto(texto: str) -> tuple[str, float]:
    """Alfabeto dominante y qué proporción del texto ocupa."""
    letras = [c for c in texto if unicodedata.category(c).startswith("L")]
    if not letras:
        return "ninguno", 0.0

    cuenta: dict[str, int] = {}
    for c in letras:
        punto = ord(c)
        for nombre, rangos in ALFABETOS.items():
            if any(ini <= punto <= fin for ini, fin in rangos):
                cuenta[nombre] = cuenta.get(nombre, 0) + 1
                break

    if not cuenta:
        return "otro", 0.0
    dominante = max(cuenta, key=cuenta.get)
    return dominante, cuenta[dominante] / len(letras)


def validar_idioma(textos: list[str], idioma: str) -> Diagnostico:
    """Comprueba que una muestra de versículos está en el idioma declarado."""
    esperado = IDIOMA_A_ALFABETO.get(idioma, "latino")
    muestra = " ".join(t for t in textos if t)[:4000]
    detectado, proporcion = detectar_alfabeto(muestra)

    return Diagnostico(
        alfabeto_detectado=detectado,
        proporcion=round(proporcion, 4),
        esperado=esperado,
        valido=(detectado == esperado and proporcion >= UMBRAL),
        muestra=muestra[:120],
    )


class IdiomaIncorrectoError(RuntimeError):
    """Lo descargado no está en el idioma que se pidió."""
