"""
Contrato entre la interfaz web y la API.

Este fichero existe por un fallo concreto: la interfaz enviaba
`work_ids: null` a `/parallel`, cuyo esquema declaraba ese campo como
obligatorio. El resultado era un 422 que además se mostraba como
«[object Object]», ilegible.

Los tests del backend pasaban y los de la interfaz también: cada mitad
funcionaba, pero no encajaban. Estas pruebas comprueban la junta.
"""

import ast
import json
import re
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
HTML = (RAIZ / "app" / "static" / "index.html").read_text(encoding="utf-8")
SCHEMAS = (RAIZ / "app" / "schemas.py").read_text(encoding="utf-8")
MAIN = (RAIZ / "app" / "main.py").read_text(encoding="utf-8")


def campos_opcionales(nombre_clase: str) -> dict[str, bool]:
    """Para cada campo del esquema, si admite ausencia o nulo."""
    arbol = ast.parse(SCHEMAS)
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.ClassDef) and nodo.name == nombre_clase:
            campos = {}
            for item in nodo.body:
                if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                    anot = ast.unparse(item.annotation)
                    tiene_defecto = item.value is not None
                    admite_nulo = "None" in anot or "Optional" in anot
                    campos[item.target.id] = tiene_defecto or admite_nulo
            return campos
    raise AssertionError(f"No existe el esquema {nombre_clase}")


def payload_de_la_interfaz() -> dict:
    """Lo que devuelve la función query() del JavaScript."""
    m = re.search(r"function query\(\)\{(.*?)\n\}", HTML, re.S)
    assert m, "no encuentro query() en la interfaz"
    cuerpo = m.group(1)
    campos = re.findall(r"(\w+)\s*:", cuerpo.split("return", 1)[1])
    return {c: None for c in campos}


class TestParallel:
    """El endpoint que falló."""

    def test_work_ids_admite_ausencia(self):
        # La interfaz manda null cuando el usuario no ha filtrado obras.
        assert campos_opcionales("ParallelRequest")["work_ids"], (
            "work_ids es obligatorio, pero la interfaz envía null: dará 422"
        )

    def test_todos_los_campos_que_envia_la_interfaz_son_opcionales(self):
        enviados = payload_de_la_interfaz()
        esquema = campos_opcionales("ParallelRequest")
        for campo in enviados:
            if campo in esquema:
                assert esquema[campo], (
                    f"la interfaz envía «{campo}» como null pero el esquema "
                    f"lo exige: producirá un error 422"
                )

    def test_el_endpoint_resuelve_todas_las_obras(self):
        # Sin work_ids debe comparar todas, no fallar ni devolver vacío.
        assert "req.work_ids or [" in MAIN, (
            "el endpoint no tiene reserva para cuando no se indican obras"
        )


class TestFrequencyRequest:
    @pytest.mark.parametrize("campo", ["term", "semantic_field", "work_ids",
                                       "language", "extra_terms"])
    def test_campos_opcionales(self, campo):
        esquema = campos_opcionales("FrequencyRequest")
        assert campo in esquema, f"el esquema no declara {campo}"
        assert esquema[campo], f"{campo} debería admitir ausencia o nulo"

    def test_la_interfaz_no_envia_campos_desconocidos(self):
        # No es un error en pydantic, pero suele significar que alguien
        # renombró un campo en un lado y no en el otro.
        enviados = set(payload_de_la_interfaz())
        esquema = set(campos_opcionales("FrequencyRequest"))
        assert enviados <= esquema, (
            f"la interfaz envía campos que el esquema ignora: {enviados - esquema}"
        )


class TestErroresLegibles:
    def test_la_interfaz_entiende_los_errores_de_validacion(self):
        # FastAPI devuelve el detalle del 422 como lista de objetos. Sin
        # tratarla, el usuario ve «[object Object]».
        assert "Array.isArray(det)" in HTML, (
            "la interfaz no sabe leer los errores de validación"
        )

    def test_muestra_el_campo_que_falla(self):
        assert "x.loc" in HTML, "el mensaje no indica qué campo causó el error"


class TestFuncionesConectadas:
    """Comprueba que lo que se escribe se llega a usar.

    Existe porque varias veces una función quedó definida pero sin conectar:
    el código estaba, las pruebas de esa función pasaban, y en pantalla seguía
    apareciendo el comportamiento antiguo. Definir no es conectar.
    """

    @pytest.mark.parametrize("funcion", [
        "sinResultados", "traducirTodoLoVisible", "activarTraduccion",
        "pintarSecciones", "pintarColocaciones", "viewPerfil", "viewGuia",
        "activarDetalles", "activarParalelos", "montarIdiomas",
    ])
    def test_cada_funcion_se_invoca(self, funcion):
        definiciones = len(re.findall(rf"function {funcion}\b", HTML))
        llamadas = len(re.findall(rf"(?<!function ){funcion}\(", HTML))
        assert definiciones >= 1, f"{funcion} no está definida"
        assert llamadas >= 1, (
            f"{funcion} está definida pero nunca se llama: el código nuevo no "
            f"llega a ejecutarse y en pantalla sigue el comportamiento viejo"
        )

    def test_no_queda_el_callejon_sin_salida_antiguo(self):
        # El mensaje que se limitaba a decir «prueba mercy en vez de
        # misericordia», que trasladaba el problema al usuario.
        assert "Recuerda que los textos están en inglés" not in HTML, (
            "sigue el mensaje antiguo en lugar de la búsqueda de alternativas"
        )

    def test_la_vista_de_frecuencias_delega_el_caso_vacio(self):
        cuerpo = HTML.split("async function viewFreq")[1].split("async function")[0]
        assert "sinResultados" in cuerpo, (
            "viewFreq no llama a sinResultados cuando no hay resultados"
        )


class TestVersiones:
    def test_servidor_e_interfaz_declaran_la_misma(self):
        api = re.search(r'API_VERSION = "([^"]+)"', MAIN).group(1)
        ui = re.search(r"VERSION_ESPERADA = '([^']+)'", HTML).group(1)
        assert api == ui, (
            f"servidor v{api} e interfaz v{ui}: el aviso de desfase saltaría "
            f"nada más abrir la aplicación"
        )

    def test_las_prestaciones_declaradas_cubren_lo_que_exige_la_interfaz(self):
        feats = set(re.search(r"FEATURES = \[(.*?)\]", MAIN, re.S).group(1)
                    .replace('"', "").replace("\n", "").split(","))
        feats = {f.strip() for f in feats if f.strip()}
        req = set(re.search(r"const REQUIERE = \[(.*?)\]", HTML, re.S).group(1)
                  .replace("'", "").replace("\n", "").split(","))
        req = {r.strip() for r in req if r.strip()}
        assert req <= feats, f"la interfaz exige prestaciones no declaradas: {req - feats}"
