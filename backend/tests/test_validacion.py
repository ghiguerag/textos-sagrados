"""
Validación del idioma del corpus.

Este fichero existe por el fallo más grave que ha tenido el proyecto: se pidió
la traducción inglesa del Corán y la API devolvió el árabe original, sin dar
ningún error. El corpus quedó con 6.236 aleyas en árabe declaradas como
inglés, y todas las comparaciones con el Corán daban cero.

Ese cero parecía un dato. Salió a la luz porque un usuario preguntó si era
real que el Corán no mencionara nunca a las mujeres.
"""

import pytest

from app.core import validacion as V

ARABE = "بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ الْحَمْدُ لِلَّهِ رَبِّ الْعَالَمِينَ"
HEBREO = "בְּרֵאשִׁית בָּרָא אֱלֹהִים אֵת הַשָּׁמַיִם וְאֵת הָאָרֶץ"
INGLES = "In the beginning God created the heaven and the earth."
ESPANOL = "En el principio creó Dios los cielos y la tierra."
DEVANAGARI = "धृतराष्ट्र उवाच धर्मक्षेत्रे कुरुक्षेत्रे समवेता युयुत्सवः"


class TestDeteccionDeAlfabeto:
    @pytest.mark.parametrize("texto,esperado", [
        (INGLES, "latino"), (ESPANOL, "latino"),
        (ARABE, "arabe"), (HEBREO, "hebreo"), (DEVANAGARI, "devanagari"),
    ])
    def test_identifica_el_alfabeto(self, texto, esperado):
        alfabeto, _ = V.detectar_alfabeto(texto)
        assert alfabeto == esperado

    def test_texto_sin_letras(self):
        assert V.detectar_alfabeto("123 !!! ...")[0] == "ninguno"

    def test_texto_vacio(self):
        assert V.detectar_alfabeto("")[0] == "ninguno"


class TestElFalloReal:
    """El caso exacto que ocurrió."""

    def test_rechaza_el_coran_arabe_declarado_ingles(self):
        d = V.validar_idioma([ARABE], "en")
        assert not d.valido
        assert d.alfabeto_detectado == "arabe"

    def test_el_mensaje_explica_la_causa(self):
        d = V.validar_idioma([ARABE], "en")
        mensaje = d.explicar("Corán (Palmer)", "en")
        assert "identificador de edición" in mensaje
        assert "arabe" in mensaje
        assert "Corán" in mensaje

    def test_acepta_el_coran_declarado_arabe(self):
        # La misma descarga es válida si se declara correctamente.
        assert V.validar_idioma([ARABE], "ar").valido


class TestTolerancia:
    def test_admite_nombres_transliterados(self):
        # Una traducción inglesa del Corán contiene Allah, Rahman, surah…
        texto = ("In the name of Allah, the Beneficent, the Merciful. "
                 "Praise be to Allah, Lord of the Worlds.")
        assert V.validar_idioma([texto], "en").valido

    def test_admite_cifras_y_puntuacion(self):
        assert V.validar_idioma(["Genesis 1:1 — 'And God said...' (v. 3)"], "en").valido

    def test_rechaza_mezcla_mayoritariamente_ajena(self):
        # Un poco de inglés dentro de texto árabe no debe colar.
        d = V.validar_idioma([ARABE * 5 + " Allah"], "en")
        assert not d.valido

    def test_umbral_declarado(self):
        assert 0.5 <= V.UMBRAL <= 0.9


class TestIntegracionConLaIngesta:
    def test_la_ingesta_aborta_con_idioma_incorrecto(self, tmp_path_factory):
        from app.core.db import connect, init_schema
        from app.core.ingest import CorpusSource, VerseRecord, ingest_source

        db = tmp_path_factory.mktemp("val") / "x.db"
        conn = connect(db)
        init_schema(conn)

        fuente = CorpusSource(
            id="falso", tradition="islam", title="Corán",
            edition="edición inexistente", language="en", license="public-domain",
        )
        versos = (VerseRecord(division_ordinal=1, division_name="Sura 1",
                              chapter=1, number=i, text=ARABE)
                  for i in range(1, 60))

        with pytest.raises(V.IdiomaIncorrectoError):
            ingest_source(conn, fuente, versos)

        # Y no debe haber dejado nada a medias.
        n = conn.execute("SELECT COUNT(*) AS n FROM verses").fetchone()["n"]
        assert n == 0, "la ingesta escribió antes de validar"
        conn.close()

    def test_la_ingesta_acepta_el_idioma_correcto(self, tmp_path_factory):
        from app.core.db import connect, init_schema
        from app.core.ingest import CorpusSource, VerseRecord, ingest_source

        db = tmp_path_factory.mktemp("val2") / "y.db"
        conn = connect(db)
        init_schema(conn)

        fuente = CorpusSource(
            id="bueno", tradition="cristianismo", title="Biblia",
            edition="KJV", language="en", license="public-domain",
        )
        versos = (VerseRecord(division_ordinal=1, division_name="Genesis",
                              chapter=1, number=i, text=INGLES)
                  for i in range(1, 10))

        stats = ingest_source(conn, fuente, versos)
        assert stats["verses"] == 9, "se han perdido los versículos de la muestra"
        conn.close()

    def test_no_se_pierden_versiculos_de_la_muestra(self, tmp_path_factory):
        # La validación consume los primeros versículos para inspeccionarlos:
        # hay que devolverlos al flujo o se perderían silenciosamente.
        from app.core.db import connect, init_schema
        from app.core.ingest import (MUESTRA_VALIDACION, CorpusSource,
                                     VerseRecord, ingest_source)

        db = tmp_path_factory.mktemp("val3") / "z.db"
        conn = connect(db)
        init_schema(conn)
        total = MUESTRA_VALIDACION * 3

        fuente = CorpusSource(id="c", tradition="cristianismo", title="B",
                              edition="e", language="en", license="public-domain")
        versos = (VerseRecord(division_ordinal=1, division_name="G",
                              chapter=1, number=i, text=f"{INGLES} number {i}")
                  for i in range(1, total + 1))

        stats = ingest_source(conn, fuente, versos)
        assert stats["verses"] == total
        conn.close()


class TestCorpusRegistrado:
    def test_ninguna_fuente_usa_la_edicion_inexistente(self):
        from scripts.fetch_corpus import SOURCES
        for nombre, (fuente, _) in SOURCES.items():
            assert "palmer" not in fuente.edition.lower(), (
                f"{nombre} usa una edición que la API no reconoce"
            )

    def test_el_coran_por_defecto_es_una_edicion_verificada(self):
        from scripts.fetch_corpus import DEFAULT_SET, SOURCES
        coranes = [n for n in DEFAULT_SET if "quran" in n]
        assert coranes, "el conjunto por defecto no incluye el Corán"
        for n in coranes:
            assert SOURCES[n][0].language == "en"
