"""
Reparto justo de la concordancia entre obras.

Este fichero existe por un fallo real que reportó un probador: la concordancia
"solo mostraba cristianismo". La causa era un LIMIT global ordenado por
tradición: como la Biblia es enorme y "cristianismo" va primero, los primeros
150 resultados se llenaban con la Biblia y las demás tradiciones no salían
nunca. La corrección acota los resultados por obra con una función de ventana.
"""

import sqlite3

import pytest

from app.core import analysis as A


@pytest.fixture
def conn_desbalanceado():
    """Dos obras: una gigante y una pequeña, ambas con el mismo término."""
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.executescript(
        """
        CREATE TABLE works (id TEXT PRIMARY KEY, title TEXT, tradition TEXT);
        CREATE TABLE divisions (id INTEGER PRIMARY KEY, work_id TEXT,
                                ordinal INTEGER, name TEXT);
        CREATE TABLE verses (id INTEGER PRIMARY KEY, work_id TEXT,
                             division_id INTEGER, chapter INTEGER, number INTEGER,
                             ref TEXT, text TEXT);
        CREATE TABLE lemma_index (lemma TEXT, surface TEXT, verse_id INTEGER,
                                  position INTEGER);
        """
    )
    c.execute("INSERT INTO works VALUES ('grande','Obra grande','cristianismo')")
    c.execute("INSERT INTO works VALUES ('chica','Obra chica','islam')")
    c.execute("INSERT INTO divisions VALUES (1,'grande',1,'Libro G')")
    c.execute("INSERT INTO divisions VALUES (2,'chica',1,'Sura C')")

    vid = 0
    # La obra grande contiene el término en 100 versículos.
    for n in range(1, 101):
        vid += 1
        c.execute("INSERT INTO verses VALUES (?,?,?,?,?,?,?)",
                  (vid, "grande", 1, 1, n, f"G 1:{n}", "habla de paz aqui"))
        c.execute("INSERT INTO lemma_index VALUES ('paz','paz',?,0)", (vid,))
    # La obra chica, en solo 5.
    for n in range(1, 6):
        vid += 1
        c.execute("INSERT INTO verses VALUES (?,?,?,?,?,?,?)",
                  (vid, "chica", 2, 1, n, f"C 1:{n}", "tambien la paz"))
        c.execute("INSERT INTO lemma_index VALUES ('paz','paz',?,0)", (vid,))
    c.commit()
    return c


class TestRepartoJusto:
    def test_aparecen_ambas_obras(self, conn_desbalanceado):
        # Con el fallo antiguo, un LIMIT de 50 traía 50 versos de la obra grande
        # y ninguno de la chica. Ahora la chica debe estar representada.
        items = A.concordance(conn_desbalanceado, ["paz"], limit=50, per_work=40)
        trads = {it["tradition"] for it in items}
        assert "cristianismo" in trads and "islam" in trads, (
            f"la concordancia no reparte entre obras: solo salió {trads}"
        )

    def test_respeta_el_tope_por_obra(self, conn_desbalanceado):
        items = A.concordance(conn_desbalanceado, ["paz"], limit=500, per_work=40)
        de_grande = sum(1 for it in items if it["work_id"] == "grande")
        de_chica = sum(1 for it in items if it["work_id"] == "chica")
        assert de_grande == 40, f"la obra grande debería quedar acotada a 40, dio {de_grande}"
        assert de_chica == 5, f"la obra chica tiene 5 y deberían salir las 5, dio {de_chica}"

    def test_filtrar_por_obra_sigue_funcionando(self, conn_desbalanceado):
        items = A.concordance(conn_desbalanceado, ["paz"], work_ids=["chica"], limit=50)
        assert items and all(it["work_id"] == "chica" for it in items)
