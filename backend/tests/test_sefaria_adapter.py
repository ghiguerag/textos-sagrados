"""Pruebas del adaptador de Sefaria con respuestas simuladas.

No tocan la red: se le pasa al adaptador la forma exacta que devuelve la API v3
y se comprueba que reacciona bien, incluido el caso peligroso de que la fuente
sirva una edición con copyright.
"""

import pytest

from scripts import fetch_corpus as FC


@pytest.fixture
def respuesta_pd():
    """Forma real de /api/v3/texts/Obadiah, abreviada."""
    return {
        "versions": [{
            "license": "Public Domain",
            "versionTitle": "The Holy Scriptures: A New Translation (JPS 1917)",
            "text": [[
                "The vision of Obadiah.",
                "Behold, I make thee small among the nations;",
            ]],
        }]
    }


class TestValidacionDeLicencia:
    """El control más importante del proyecto: no redistribuir con copyright."""

    def test_acepta_dominio_publico(self, respuesta_pd, monkeypatch):
        monkeypatch.setattr(FC, "fetch_json", lambda url, **kw: respuesta_pd)
        monkeypatch.setattr(FC, "TANAJ_BOOKS", [("Obadiah", "Abdías", "Neviim")])
        versos = list(FC.load_sefaria_tanakh())
        assert len(versos) == 2
        assert versos[0].text.startswith("The vision")
        assert versos[0].division_name == "Abdías"

    @pytest.mark.parametrize("licencia", [
        "CC-BY-NC",                      # la edición JPS de 2023
        "Copyright: Schocken",
        "CC-BY-SA",
        "unknown",
        "",
    ])
    def test_rechaza_licencias_no_libres(self, licencia, monkeypatch):
        payload = {"versions": [{
            "license": licencia,
            "versionTitle": "THE JPS TANAKH: Gender-Sensitive Edition",
            "text": [["texto con derechos"]],
        }]}
        monkeypatch.setattr(FC, "fetch_json", lambda url, **kw: payload)
        monkeypatch.setattr(FC, "TANAJ_BOOKS", [("Obadiah", "Abdías", "Neviim")])
        with pytest.raises(FC.LicenseError):
            list(FC.load_sefaria_tanakh())

    def test_acepta_variantes_de_dominio_publico(self, monkeypatch):
        for licencia in ("PD", "public domain", "CC0"):
            payload = {"versions": [{
                "license": licencia, "versionTitle": "x",
                "text": [["texto libre"]],
            }]}
            monkeypatch.setattr(FC, "fetch_json", lambda url, **kw: payload)
            monkeypatch.setattr(FC, "TANAJ_BOOKS", [("Obadiah", "Abdías", "Neviim")])
            assert len(list(FC.load_sefaria_tanakh())) == 1

    def test_falla_si_no_existe_la_version(self, monkeypatch):
        monkeypatch.setattr(FC, "fetch_json", lambda url, **kw: {"versions": []})
        monkeypatch.setattr(FC, "TANAJ_BOOKS", [("Obadiah", "Abdías", "Neviim")])
        with pytest.raises(RuntimeError):
            list(FC.load_sefaria_tanakh())


class TestLimpiezaDeTexto:
    def test_elimina_el_contenido_de_las_notas(self):
        # Las notas del traductor no son texto bíblico: si se cuentan, inflan
        # las frecuencias con vocabulario editorial.
        crudo = ('When God began to create<sup class="footnote-marker">a</sup>'
                 '<i class="footnote"><b>When God began to create </b>'
                 'In contrast to others progenitor.</i> heaven and earth')
        limpio = FC._strip_html(crudo)
        assert "progenitor" not in limpio
        assert "In contrast" not in limpio
        assert limpio == "When God began to create heaven and earth"

    def test_elimina_etiquetas_normales(self):
        assert FC._strip_html("<b>Holy</b> is <i>His</i> name") == "Holy is His name"

    def test_normaliza_espacios(self):
        assert FC._strip_html("uno   \n  dos") == "uno dos"

    def test_valores_no_texto(self):
        assert FC._strip_html(None) == ""
        assert FC._strip_html(42) == ""


class TestEstructura:
    def test_libro_de_un_solo_capitulo(self, monkeypatch):
        # Abdías es un caso especial: la API devuelve una lista plana.
        payload = {"versions": [{
            "license": "Public Domain", "versionTitle": "x",
            "text": ["verso uno", "verso dos"],
        }]}
        monkeypatch.setattr(FC, "fetch_json", lambda url, **kw: payload)
        monkeypatch.setattr(FC, "TANAJ_BOOKS", [("Obadiah", "Abdías", "Neviim")])
        versos = list(FC.load_sefaria_tanakh())
        assert [v.chapter for v in versos] == [1, 1]
        assert [v.number for v in versos] == [1, 2]

    def test_omite_versiculos_vacios(self, monkeypatch):
        payload = {"versions": [{
            "license": "Public Domain", "versionTitle": "x",
            "text": [["uno", "", "   ", "cuatro"]],
        }]}
        monkeypatch.setattr(FC, "fetch_json", lambda url, **kw: payload)
        monkeypatch.setattr(FC, "TANAJ_BOOKS", [("Obadiah", "Abdías", "Neviim")])
        versos = list(FC.load_sefaria_tanakh())
        assert len(versos) == 2

    def test_los_39_libros_del_tanaj(self):
        assert len(FC.TANAJ_BOOKS) == 39
        secciones = {s for _, _, s in FC.TANAJ_BOOKS}
        assert secciones == {"Torá", "Neviim", "Ketuvim"}
        assert sum(1 for _, _, s in FC.TANAJ_BOOKS if s == "Torá") == 5


class TestConfiguracion:
    def test_user_agent_es_de_navegador(self):
        # Sefaria devuelve 403 a los clientes que no se identifican como
        # navegador. Fue la causa del fallo original.
        assert FC.USER_AGENT.startswith("Mozilla/5.0")

    def test_todas_las_fuentes_declaran_dominio_publico(self):
        for name, (source, _) in FC.SOURCES.items():
            assert source.license == "public-domain", f"{name} sin licencia libre"
