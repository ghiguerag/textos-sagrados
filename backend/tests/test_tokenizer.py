import pytest

from app.core.tokenizer import (
    ngrams, normalize, stem, token_count, tokenize,
)


class TestStemming:
    """Si singular y plural no convergen, todas las frecuencias quedan
    fragmentadas. Es el fallo más caro del sistema."""

    @pytest.mark.parametrize("a,b", [
        ("cielo", "cielos"), ("misericordia", "misericordias"),
        ("profeta", "profetas"), ("vida", "vidas"), ("ley", "leyes"),
        ("luz", "luces"), ("dios", "dioses"), ("eterno", "eterna"),
        ("justo", "justos"), ("mandamiento", "mandamientos"),
    ])
    def test_variantes_convergen_es(self, a, b):
        assert stem(a, "es") == stem(b, "es")

    @pytest.mark.parametrize("a,b", [
        ("mercy", "mercies"), ("god", "gods"), ("love", "loved"),
        ("spirit", "spirits"), ("witness", "witnesses"),
        ("righteous", "righteousness"), ("prophet", "prophets"),
    ])
    def test_variantes_convergen_en(self, a, b):
        assert stem(a, "en") == stem(b, "en")

    @pytest.mark.parametrize("a,b", [
        ("guerra", "guarda"),
        ("amor", "temor"),
        ("justicia", "malicia"),
        ("sabiduria", "sabor"),
    ])
    def test_palabras_distintas_no_colapsan(self, a, b):
        assert stem(a, "es") != stem(b, "es")

    def test_pares_de_genero_si_colapsan(self):
        # Deliberado: "dios/diosa" y "santo/santa" son el mismo concepto y
        # deben contarse juntos.
        assert stem("dios", "es") == stem("diosa", "es")
        assert stem("santo", "es") == stem("santa", "es")

    def test_palabras_cortas_intactas(self):
        for w in ("dios", "fe", "sol", "paz", "rey"):
            assert stem(w, "es") == w

    def test_arabe_y_hebreo_sin_stemming(self):
        # La morfología semítica no es concatenativa: un stemmer de sufijos
        # destruiría las raíces. Debe devolver la palabra intacta.
        assert stem("رحمن", "ar") == "رحمن"
        assert stem("שלום", "he") == "שלום"

    def test_stem_es_idempotente(self):
        for w in ("misericordias", "cielos", "amaron", "mercies", "loved"):
            for lang in ("es", "en"):
                once = stem(w, lang)
                assert stem(once, lang) == once, f"{w} inestable en {lang}"


class TestNormalizacion:
    def test_quita_acentos_en_latinos(self):
        assert normalize("Salmón CREÓ Ángel") == "salmon creo angel"

    def test_quita_nikud_hebreo(self):
        assert normalize("בְּרֵאשִׁית", lang="he") == "בראשית"

    def test_quita_harakat_arabe(self):
        assert "َ" not in normalize("مَالِكِ", lang="ar")

    def test_elimina_marcas_editoriales(self):
        # Los corpus de dominio público marcan con corchetes lo que el
        # traductor añadió; contarlo falsearía las frecuencias.
        tokens = [t.surface for t in tokenize("the word [of God] came", lang="en")]
        assert "god" not in tokens
        assert "word" in tokens


class TestTokenizacion:
    def test_filtra_stopwords(self):
        surfaces = [t.surface for t in tokenize("el amor de dios en la tierra")]
        assert surfaces == ["amor", "dios", "tierra"]

    def test_dios_nunca_es_stopword(self):
        # 'dios' no está en la lista, pero PROTECTED garantiza el caso.
        assert "dios" in [t.surface for t in tokenize("dios")]

    def test_conserva_apostrofe_y_guion(self):
        surfaces = [t.surface for t in tokenize("loving-kindness", lang="en")]
        assert "loving-kindness" in surfaces

    def test_posiciones_correlativas_para_kwic(self):
        tokens = tokenize("the LORD is my shepherd i shall not want", lang="en")
        assert [t.position for t in tokens] == sorted(t.position for t in tokens)

    def test_token_count_incluye_stopwords(self):
        # Es el denominador de la normalización: debe contarlo TODO.
        texto = "In the beginning God created the heaven and the earth."
        assert token_count(texto, lang="en") == 10
        assert len(tokenize(texto, lang="en")) < 10

    def test_ignora_numeros_y_puntuacion(self):
        assert [t.surface for t in tokenize("Genesis 1:1 -- amor!", lang="es")] == ["genesis", "amor"]


class TestNgrams:
    def test_bigramas(self):
        assert ngrams(["a", "b", "c"], 2) == [("a", "b"), ("b", "c")]

    def test_secuencia_corta_no_falla(self):
        assert ngrams(["a"], 2) == []
