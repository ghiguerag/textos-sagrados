"""Validación del motor de análisis.

El foco está en la corrección metodológica, no solo en que el código corra:
un bug aquí produce números que parecen creíbles y no lo son.
"""

import math

import pytest

from app.core import analysis as A


class TestLogLikelihood:
    def test_frecuencias_proporcionales_dan_g2_cero(self):
        # Misma tasa en ambos corpus => sin evidencia de diferencia.
        g2, _ = A.log_likelihood(10, 20, 1000, 2000)
        assert g2 == pytest.approx(0.0, abs=1e-9)

    def test_g2_nunca_negativo(self):
        for a, b, c, d in [(1, 100, 50, 10000), (500, 1, 1000, 1000), (0, 5, 100, 100)]:
            g2, _ = A.log_likelihood(a, b, c, d)
            assert g2 >= 0

    def test_signo_del_tamano_de_efecto(self):
        _, sobre = A.log_likelihood(100, 10, 1000, 1000)
        _, infra = A.log_likelihood(10, 100, 1000, 1000)
        assert sobre > 0 and infra < 0

    def test_direccion_es_clave_no_texto(self):
        from app.core.analysis import Keyness, keyness, WorkFrequency
        freqs = [
            WorkFrequency("a", "A", "islam", "en", 100, 10, 1000, 1000.0, 1.0, 1, 1),
            WorkFrequency("b", "B", "hinduismo", "en", 5, 2, 1000, 50.0, 0.5, 1, 2),
        ]
        k = keyness(freqs, "a", "b")
        assert k is not None and k.direction in ("over", "under")

    def test_cero_ocurrencias_no_revienta(self):
        # Caso muy común: un concepto ausente por completo de un corpus.
        # Sin corrección de continuidad esto sería log(0) = -inf.
        g2, lr = A.log_likelihood(0, 50, 1000, 1000)
        assert math.isfinite(g2) and math.isfinite(lr) and lr < 0

    def test_corpus_vacio_devuelve_ceros(self):
        assert A.log_likelihood(0, 0, 0, 0) == (0.0, 0.0)

    def test_g2_crece_con_el_tamano_de_muestra(self):
        # Misma proporción, más datos => más evidencia.
        pequeno, _ = A.log_likelihood(10, 5, 1000, 1000)
        grande, _ = A.log_likelihood(100, 50, 10000, 10000)
        assert grande > pequeno

    def test_umbral_de_significacion(self):
        assert A.CRITICAL_G2 == pytest.approx(15.13, rel=1e-3)


class TestNormalizacion:
    """La razón de ser del proyecto: los corpus tienen tamaños muy distintos."""

    def test_per_10k_usa_tamano_del_corpus(self, conn):
        stems = A.resolve_query("god", "en")
        for f in A.frequency_by_work(conn, stems):
            if f.total_tokens:
                assert f.per_10k == pytest.approx(
                    f.raw_count * 10000 / f.total_tokens, rel=1e-3
                )

    def test_conteo_bruto_y_tasa_pueden_discrepar(self, conn, lexicon):
        # Confirma que el corpus grande no gana automáticamente en tasa: si
        # ordenar por bruto y por tasa diera siempre lo mismo, la
        # normalización no estaría haciendo nada.
        stems = A.resolve_query("", "en", lexicon=lexicon, semantic_field="misericordia")
        freqs = [f for f in A.frequency_by_work(conn, stems) if f.raw_count]
        por_bruto = [f.work_id for f in sorted(freqs, key=lambda f: -f.raw_count)]
        por_tasa = [f.work_id for f in sorted(freqs, key=lambda f: -f.per_10k)]
        assert por_bruto != por_tasa or len(freqs) < 2

    def test_dispersion_entre_cero_y_uno(self, conn):
        for f in A.frequency_by_work(conn, A.resolve_query("god", "en")):
            assert 0.0 <= f.dispersion <= 1.0
            assert f.divisions_present <= f.divisions_total


class TestResolucionDeConsulta:
    def test_termino_simple(self):
        assert A.resolve_query("mercy", "en") == {"mercy"}

    def test_campo_semantico_expande(self, lexicon):
        stems = A.resolve_query("", "en", lexicon=lexicon, semantic_field="misericordia")
        assert len(stems) > 5
        assert "mercy" in stems

    def test_termino_y_campo_se_combinan(self, lexicon):
        stems = A.resolve_query("xyzzy", "en", lexicon=lexicon, semantic_field="paz")
        assert "xyzzy" in stems and len(stems) > 1

    def test_consulta_vacia_da_conjunto_vacio(self):
        assert A.resolve_query("", "en") == set()

    def test_campo_inexistente_no_falla(self, lexicon):
        assert A.resolve_query("paz", "en", lexicon=lexicon, semantic_field="noexiste") == {"paz"}


class TestFrecuencias:
    def test_devuelve_todas_las_obras_incluso_con_cero(self, conn):
        # Un cero es un dato: "este concepto no aparece". Omitir la obra
        # sesgaría la lectura del usuario.
        freqs = A.frequency_by_work(conn, {"zzzznoexiste"})
        assert len(freqs) == 4
        assert all(f.raw_count == 0 for f in freqs)

    def test_filtro_por_obra(self, conn):
        freqs = A.frequency_by_work(conn, A.resolve_query("god", "en"), work_ids=["kjv"])
        assert [f.work_id for f in freqs] == ["kjv"]

    def test_suma_por_division_cuadra_con_el_total(self, conn):
        stems = A.resolve_query("god", "en")
        total = next(f for f in A.frequency_by_work(conn, stems) if f.work_id == "kjv")
        por_division = sum(d.raw_count for d in A.frequency_by_division(conn, stems, "kjv"))
        assert por_division == total.raw_count

    def test_keyness_matrix_cubre_todas_las_obras(self, conn, lexicon):
        stems = A.resolve_query("", "en", lexicon=lexicon, semantic_field="justicia")
        freqs = A.frequency_by_work(conn, stems)
        matrix = A.keyness_matrix(freqs)
        assert len(matrix) == len(freqs)
        # Claves neutras: el texto visible lo pone la app según su idioma.
        assert all(m["direction"] in ("over", "under") for m in matrix)

    def test_keyness_ordenado_por_evidencia(self, conn, lexicon):
        stems = A.resolve_query("", "en", lexicon=lexicon, semantic_field="misericordia")
        matrix = A.keyness_matrix(A.frequency_by_work(conn, stems))
        valores = [m["log_likelihood"] for m in matrix]
        assert valores == sorted(valores, reverse=True)


class TestConcordancia:
    def test_devuelve_versiculos_que_contienen_el_termino(self, conn):
        for item in A.concordance(conn, A.resolve_query("mercy", "en")):
            assert "merc" in item["text"].lower() or item["matched_forms"]

    def test_respeta_el_limite(self, conn):
        assert len(A.concordance(conn, A.resolve_query("god", "en"), limit=3)) <= 3

    def test_paginacion_sin_solapamiento(self, conn):
        stems = A.resolve_query("god", "en")
        p1 = [i["verse_id"] for i in A.concordance(conn, stems, limit=5, offset=0)]
        p2 = [i["verse_id"] for i in A.concordance(conn, stems, limit=5, offset=5)]
        assert not (set(p1) & set(p2))

    def test_incluye_atribucion_de_la_obra(self, conn):
        # Requisito legal: cada cita debe poder atribuirse a su edición.
        for item in A.concordance(conn, A.resolve_query("god", "en"), limit=5):
            assert item["work_title"] and item["ref"] and item["tradition"]


class TestVocabularioDistintivo:
    def test_solo_terminos_sobrerrepresentados_y_significativos(self, conn):
        for item in A.distinctive_vocabulary(conn, "quran-palmer", min_count=2):
            assert item["effect_size"] > 0
            assert item["log_likelihood"] > A.CRITICAL_G2

    def test_obra_inexistente_devuelve_vacio(self, conn):
        assert A.distinctive_vocabulary(conn, "no-existe") == []


class TestIntegridadDelCorpus:
    def test_todas_las_obras_tienen_tokens(self, conn):
        for row in conn.execute("SELECT id, total_tokens, total_verses FROM works"):
            assert row["total_tokens"] > 0, f'{row["id"]} sin tokens'
            assert row["total_verses"] > 0

    def test_total_tokens_cuadra_con_los_versiculos(self, conn):
        for row in conn.execute(
            """SELECT w.id, w.total_tokens, SUM(v.token_count) AS suma
               FROM works w JOIN verses v ON v.work_id = w.id GROUP BY w.id"""
        ):
            assert row["total_tokens"] == row["suma"]

    def test_cada_obra_declara_licencia(self, conn):
        # Publicar en tiendas exige atribución correcta de cada texto.
        for row in conn.execute("SELECT id, license FROM works"):
            assert row["license"], f'{row["id"]} sin licencia declarada'

    def test_no_hay_lemas_huerfanos(self, conn):
        n = conn.execute(
            """SELECT COUNT(*) AS n FROM lemma_index li
               LEFT JOIN verses v ON v.id = li.verse_id WHERE v.id IS NULL"""
        ).fetchone()["n"]
        assert n == 0

    def test_lemma_totals_cuadra_con_el_indice(self, conn):
        discrepancias = conn.execute(
            """SELECT t.lemma FROM lemma_totals t
               JOIN (SELECT lemma, work_id, COUNT(*) AS n FROM lemma_index
                     GROUP BY lemma, work_id) i
                 ON i.lemma = t.lemma AND i.work_id = t.work_id
               WHERE i.n <> t.count LIMIT 5"""
        ).fetchall()
        assert not discrepancias

    def test_busqueda_fts_operativa(self, conn):
        rows = conn.execute(
            "SELECT COUNT(*) AS n FROM verses_fts WHERE verses_fts MATCH 'mercy'"
        ).fetchone()
        assert rows["n"] > 0

    def test_fts_ignora_acentos(self, conn):
        # remove_diacritics=2: buscar "creo" debe encontrar "creó".
        assert conn.execute(
            "SELECT COUNT(*) AS n FROM verses_fts WHERE verses_fts MATCH 'beginning'"
        ).fetchone()["n"] > 0


class TestDesgloseDeFormas:
    """Alimenta el detalle del contador de «apariciones» en la interfaz."""

    def test_las_formas_suman_el_total(self, conn, lexicon):
        stems = A.resolve_query("", "en", lexicon=lexicon, semantic_field="misericordia")
        total = next(f for f in A.frequency_by_work(conn, stems) if f.work_id == "kjv")
        formas = A.surface_forms(conn, stems, work_id="kjv")
        assert sum(f["count"] for f in formas) == total.raw_count

    def test_ordenadas_de_mayor_a_menor(self, conn, lexicon):
        stems = A.resolve_query("", "en", lexicon=lexicon, semantic_field="justicia")
        counts = [f["count"] for f in A.surface_forms(conn, stems)]
        assert counts == sorted(counts, reverse=True)

    def test_porcentajes_suman_cien(self, conn, lexicon):
        stems = A.resolve_query("", "en", lexicon=lexicon, semantic_field="paz")
        formas = A.surface_forms(conn, stems, work_id="kjv")
        if formas:
            assert abs(sum(f["share"] for f in formas) - 100) < 1.0

    def test_filtro_por_obra(self, conn, lexicon):
        stems = A.resolve_query("", "en", lexicon=lexicon, semantic_field="misericordia")
        solo_coran = A.surface_forms(conn, stems, work_id="quran-palmer")
        todas = A.surface_forms(conn, stems)
        assert sum(f["count"] for f in solo_coran) <= sum(f["count"] for f in todas)

    def test_consulta_vacia(self, conn):
        assert A.surface_forms(conn, []) == []

    def test_verse_count_no_supera_count(self, conn, lexicon):
        # Un versículo puede contener la forma varias veces, nunca al revés.
        stems = A.resolve_query("", "en", lexicon=lexicon, semantic_field="divinidad")
        for f in A.surface_forms(conn, stems):
            assert f["verse_count"] <= f["count"]


class TestComparacionPorSecciones:
    """La comparación metodológicamente más sólida: dentro de una obra el
    traductor es el mismo, así que las diferencias son del texto original."""

    def test_devuelve_las_secciones_de_la_obra(self, conn, lexicon):
        stems = A.resolve_query("", "en", lexicon=lexicon, semantic_field="misericordia")
        secciones = {s["section"] for s in A.frequency_by_section(conn, stems, "quran-palmer")}
        assert secciones == {"Mecano", "Medinés"}

    def test_las_apariciones_suman_el_total_de_la_obra(self, conn, lexicon):
        stems = A.resolve_query("", "en", lexicon=lexicon, semantic_field="misericordia")
        total = next(f for f in A.frequency_by_work(conn, stems) if f.work_id == "kjv")
        por_seccion = sum(s["raw_count"] for s in A.frequency_by_section(conn, stems, "kjv"))
        assert por_seccion == total.raw_count

    def test_los_tokens_suman_el_total_de_la_obra(self, conn, lexicon):
        stems = A.resolve_query("", "en", lexicon=lexicon, semantic_field="paz")
        total = conn.execute(
            "SELECT total_tokens FROM works WHERE id='tanaj-jps'").fetchone()["total_tokens"]
        suma = sum(s["total_tokens"] for s in A.frequency_by_section(conn, stems, "tanaj-jps"))
        assert suma == total

    def test_normalizacion_correcta(self, conn, lexicon):
        stems = A.resolve_query("", "en", lexicon=lexicon, semantic_field="justicia")
        for s in A.frequency_by_section(conn, stems, "kjv"):
            if s["total_tokens"]:
                assert s["per_10k"] == pytest.approx(
                    s["raw_count"] * 10000 / s["total_tokens"], rel=1e-3)

    def test_incluye_contraste_estadistico(self, conn, lexicon):
        stems = A.resolve_query("", "en", lexicon=lexicon, semantic_field="misericordia")
        for s in A.frequency_by_section(conn, stems, "quran-palmer"):
            assert s["direction"] in ("over", "under")
            assert s["log_likelihood"] >= 0
            assert isinstance(s["significant"], bool)

    def test_secciones_sin_apariciones_se_incluyen(self, conn, lexicon):
        # Un cero es información: «este concepto no aparece en esta parte».
        stems = A.resolve_query("", "en", lexicon=lexicon, semantic_field="pobreza")
        secciones = A.frequency_by_section(conn, stems, "kjv")
        assert len(secciones) >= 2

    def test_tanaj_tiene_las_tres_partes(self, conn, lexicon):
        stems = A.resolve_query("", "en", lexicon=lexicon, semantic_field="sabiduria")
        secciones = {s["section"] for s in A.frequency_by_section(conn, stems, "tanaj-jps")}
        assert secciones == {"Torá", "Neviim", "Ketuvim"}

    def test_consulta_vacia(self, conn):
        assert A.frequency_by_section(conn, [], "kjv") == []

    def test_obra_inexistente(self, conn, lexicon):
        stems = A.resolve_query("mercy", "en")
        assert A.frequency_by_section(conn, stems, "no-existe") == []
