"""Pruebas del motor de búsqueda por significado.

Usan vectores sintéticos: no descargan el modelo de 470 MB ni requieren
PyTorch. Lo que se comprueba es la lógica de almacenamiento, búsqueda y
agrupación por tradición, que es donde puede haber errores.
"""

import numpy as np
import pytest

from app.core import embeddings as E
from app.core import encoders as E_enc


def encoder_falso(vector):
    """Doble de prueba que cumple el contrato de Encoder."""
    class Falso(E_enc.Encoder):
        name, dimensions = "falso", len(vector)
        def encode(self, texts):
            return np.tile(vector, (len(list(texts)), 1)).astype(np.float32)
    return lambda _nombre: Falso()


class TestEmpaquetado:
    def test_ida_y_vuelta(self):
        v = np.array([0.1, -0.5, 0.9, 0.0], dtype=np.float32)
        assert np.allclose(E.unpack_vector(E.pack_vector(v)), v)

    def test_siempre_float32(self):
        # float64 duplicaría el tamaño del índice sin ganar precisión útil.
        v = np.array([1.0, 2.0], dtype=np.float64)
        assert E.unpack_vector(E.pack_vector(v)).dtype == np.float32

    def test_acepta_listas(self):
        assert len(E.unpack_vector(E.pack_vector([1.0, 2.0, 3.0]))) == 3


@pytest.fixture
def store(conn, monkeypatch):
    """Almacén con vectores deterministas, uno por tradición.

    Se construyen para que las distancias sean predecibles: dos vectores casi
    idénticos en cristianismo e islam, y uno ortogonal en hinduismo.
    """
    filas = conn.execute(
        """SELECT v.id, v.ref, v.text, v.work_id, w.tradition
           FROM verses v JOIN works w ON w.id = v.work_id
           ORDER BY w.tradition, v.id"""
    ).fetchall()

    base = {"cristianismo": [1.0, 0.0, 0.0], "islam": [0.98, 0.20, 0.0],
            "judaismo": [0.70, 0.70, 0.0], "hinduismo": [0.0, 0.0, 1.0]}

    s = E.VectorStore.__new__(E.VectorStore)
    s.model_name = "test"
    s.meta = [{"verse_id": r["id"], "ref": r["ref"], "text": r["text"],
               "work_id": r["work_id"], "tradition": r["tradition"]} for r in filas]
    vecs = []
    for r in filas:
        v = np.array(base[r["tradition"]], dtype=np.float32)
        vecs.append(v / np.linalg.norm(v))
    s.matrix = np.vstack(vecs)
    return s


class TestBusqueda:
    def test_encuentra_lo_mas_cercano(self, store, monkeypatch):
        # Consulta idéntica al vector cristiano: debe salir esa tradición.
        monkeypatch.setattr(E, "get_model", encoder_falso([1.0, 0.0, 0.0]))
        r = store.search("lo que sea", top_k=5)
        assert r and r[0]["tradition"] == "cristianismo"

    def test_similitud_ordenada_descendente(self, store, monkeypatch):
        monkeypatch.setattr(E, "get_model", encoder_falso([1.0, 0.0, 0.0]))
        sims = [x["similarity"] for x in store.search("q", top_k=20)]
        assert sims == sorted(sims, reverse=True)

    def test_umbral_descarta_lo_irrelevante(self, store, monkeypatch):
        # Vector ortogonal a casi todo: con umbral alto no debe devolver nada.
        monkeypatch.setattr(E, "get_model", encoder_falso([0.0, 0.0, 1.0]))
        assert store.search("q", top_k=10, min_similarity=0.99, exclude_work="gita-arnold") == []

    def test_filtro_por_obra(self, store, monkeypatch):
        monkeypatch.setattr(E, "get_model", encoder_falso([1.0, 0.0, 0.0]))
        r = store.search("q", top_k=10, work_ids=["kjv"], min_similarity=0.0)
        assert all(x["work_id"] == "kjv" for x in r)

    def test_almacen_vacio_no_rompe(self, monkeypatch):
        s = E.VectorStore.__new__(E.VectorStore)
        s.model_name, s.meta = "test", []
        s.matrix = np.zeros((0, 3), dtype=np.float32)
        assert len(s) == 0
        assert s.search("q") == []


class TestParalelosEntreTradiciones:
    def test_excluye_la_tradicion_de_origen(self, store):
        origen = next(m for m in store.meta if m["tradition"] == "cristianismo")
        r = store.cross_tradition_matches(origen["verse_id"])
        assert r and all(t["tradition"] != "cristianismo" for t in r)

    def test_una_entrada_por_tradicion(self, store):
        origen = next(m for m in store.meta if m["tradition"] == "cristianismo")
        r = store.cross_tradition_matches(origen["verse_id"])
        tradiciones = [t["tradition"] for t in r]
        assert len(tradiciones) == len(set(tradiciones)), "tradición repetida"

    def test_respeta_top_k(self, store):
        origen = next(m for m in store.meta if m["tradition"] == "cristianismo")
        for t in store.cross_tradition_matches(origen["verse_id"], top_k=2):
            assert len(t["matches"]) <= 2

    def test_el_corpus_grande_no_copa_los_resultados(self, store):
        # Sin agrupar por tradición, la Biblia (40 veces el Gita) llenaría
        # todos los huecos por puro volumen. Esta es la razón de agrupar.
        origen = next(m for m in store.meta if m["tradition"] == "cristianismo")
        r = store.cross_tradition_matches(origen["verse_id"], top_k=3)
        assert len(r) >= 2, "deberían aparecer varias tradiciones distintas"

    def test_ordenadas_por_parecido(self, store):
        origen = next(m for m in store.meta if m["tradition"] == "cristianismo")
        r = store.cross_tradition_matches(origen["verse_id"])
        mejores = [t["matches"][0]["similarity"] for t in r]
        assert mejores == sorted(mejores, reverse=True)

    def test_versiculo_inexistente(self, store):
        assert store.cross_tradition_matches(999999) == []


class TestConstruccionDelIndice:
    def test_cuenta_pendientes(self, conn):
        total = conn.execute("SELECT COUNT(*) AS n FROM verses").fetchone()["n"]
        # Sin ningún vector calculado, están todos pendientes.
        assert E.pending_count(conn, "modelo-inexistente") == total

    def test_pendientes_filtrado_por_obra(self, conn):
        kjv = conn.execute(
            "SELECT COUNT(*) AS n FROM verses WHERE work_id='kjv'").fetchone()["n"]
        assert E.pending_count(conn, "m", work_ids=["kjv"]) == kjv
