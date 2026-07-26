"""
Glosa de palabras: caché y reconstrucción de la forma real.

El vocabulario distintivo y las colocaciones se muestran lematizados
(«discipl», «tabernacl»), formas que ningún traductor reconoce. El endpoint
/traducir-palabra resuelve dos cosas antes de traducir:

  1. reconstruye la forma de superficie más frecuente del lema, y
  2. cachea el resultado —incluso el fallo— para no repetir la petición.

Estas pruebas cubren esas dos piezas con SQLite en memoria, sin red.
"""

import sqlite3

import pytest

from app.core import analysis as A
from app.core import translate as T


@pytest.fixture
def cache_conn():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    T.ensure_schema(c)
    return c


@pytest.fixture
def indice_conn():
    """Un mini índice de formas, como el que produce la ingesta."""
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.execute("CREATE TABLE lemma_index (lemma TEXT, surface TEXT, "
              "verse_id INTEGER, work_id TEXT)")
    c.executemany(
        "INSERT INTO lemma_index VALUES (?,?,?,?)",
        [("discipl", "disciples", 1, "kjv"),
         ("discipl", "disciples", 2, "kjv"),
         ("discipl", "disciple", 3, "kjv"),
         ("tabernacl", "tabernacle", 4, "kjv")],
    )
    c.commit()
    return c


class TestCacheDePalabras:
    def test_sin_registro_devuelve_None(self, cache_conn):
        assert T.cached_word(cache_conn, "disciples", "es") is None

    def test_roundtrip(self, cache_conn):
        T.store_word(cache_conn, "disciples", "es", "discípulos", "test")
        assert T.cached_word(cache_conn, "disciples", "es") == "discípulos"

    def test_el_fallo_se_cachea_como_vacio(self, cache_conn):
        # Guardar '' distingue «intentada sin éxito» de «nunca intentada»,
        # y evita volver a molestar al traductor con una palabra intraducible.
        T.store_word(cache_conn, "syria", "es", "", "test")
        assert T.cached_word(cache_conn, "syria", "es") == ""
        assert T.cached_word(cache_conn, "syria", "es") is not None

    def test_la_tabla_inexistente_no_rompe(self):
        vacia = sqlite3.connect(":memory:")
        vacia.row_factory = sqlite3.Row
        assert T.cached_word(vacia, "x", "es") is None


class TestReconstruccionDeForma:
    def test_elige_la_forma_mas_frecuente(self, indice_conn):
        formas = A.surface_forms(indice_conn, ["discipl"])
        assert formas[0]["surface"] == "disciples"

    def test_forma_unica(self, indice_conn):
        assert A.surface_forms(indice_conn, ["tabernacl"])[0]["surface"] == "tabernacle"

    def test_lema_inexistente_da_lista_vacia(self, indice_conn):
        assert A.surface_forms(indice_conn, ["noexiste"]) == []
