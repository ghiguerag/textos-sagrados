"""Pruebas de los motores de codificación.

No descargan modelos: comprueban la lógica de configuración, identificadores y
normalización, que es donde un error pasaría inadvertido y corrompería el
índice entero.
"""

import numpy as np
import pytest

from app.core import encoders as E


class TestNormalizacion:
    """Todo vector debe tener norma 1: la búsqueda usa producto escalar como
    equivalente del coseno, y eso solo vale si están normalizados."""

    def test_norma_uno(self):
        m = E._normalize(np.array([[3.0, 4.0], [1.0, 0.0]]))
        assert np.allclose(np.linalg.norm(m, axis=1), 1.0)

    def test_vector_cero_no_divide_por_cero(self):
        m = E._normalize(np.array([[0.0, 0.0]]))
        assert np.all(np.isfinite(m))

    def test_acepta_vector_suelto(self):
        assert E._normalize(np.array([3.0, 4.0])).shape == (1, 2)

    def test_siempre_float32(self):
        assert E._normalize(np.array([[1.0, 2.0]], dtype=np.float64)).dtype == np.float32

    def test_preserva_direccion(self):
        original = np.array([[2.0, 4.0, 4.0]])
        n = E._normalize(original)
        assert np.allclose(n[0] / n[0][0], original[0] / original[0][0])


class TestPreajustes:
    def test_todos_declaran_lo_necesario(self):
        for nombre, cfg in E.PRESETS.items():
            assert cfg["tipo"] in ("torch", "static"), nombre
            assert "/" in cfg["modelo"], nombre
            assert cfg["descripcion"], nombre

    def test_identificadores_unicos(self):
        ids = [E.encoder_id(k) for k in E.PRESETS]
        assert len(ids) == len(set(ids)), "dos motores comparten identificador"

    def test_el_identificador_refleja_la_configuracion(self):
        # Si no reflejara dimensiones y cuantización, dos índices distintos
        # se mezclarían en la misma clave y los resultados serían basura.
        assert "d128" in E.encoder_id("minimo")
        assert "int8" in E.encoder_id("minimo")
        assert "d256" in E.encoder_id("ligero-256")
        assert "d" not in E.encoder_id("calidad").split(":")[-1]

    def test_los_ligeros_son_multilingues(self):
        # El corpus está en inglés y la interfaz en seis idiomas: un motor
        # monolingüe rompería la búsqueda en español.
        for nombre, cfg in E.PRESETS.items():
            if cfg["tipo"] == "static":
                assert "multilingual" in cfg["modelo"], nombre

    def test_motor_desconocido_falla_claro(self):
        with pytest.raises(ValueError) as exc:
            E.get_encoder("no-existe")
        assert "no-existe" in str(exc.value)


class TestResolucionDeIdentificadores:
    """El fallo más caro que ha tenido este proyecto.

    En la base de datos se guarda el identificador del índice
    ('static:potion-multilingual-128M'), no el nombre del preajuste
    ('ligero'). Al recuperar el índice había que traducir de vuelta, y no se
    hacía: se intentaba cargar un modelo de HuggingFace con ese nombre, que no
    existe, y la búsqueda entera fallaba con un error incomprensible.

    Existían pruebas de que los identificadores eran únicos, pero ninguna de
    que se pudiera volver desde ellos. La ida sin la vuelta no sirve de nada.
    """

    @pytest.mark.parametrize("preset", sorted(E.PRESETS))
    def test_ida_y_vuelta(self, preset):
        assert E.preset_from_id(E.encoder_id(preset)) == preset

    def test_el_caso_real_que_fallo(self):
        assert E.preset_from_id("static:potion-multilingual-128M") == "ligero"

    def test_identificador_desconocido_devuelve_none(self):
        assert E.preset_from_id("static:modelo-inventado") is None

    def test_identificador_desconocido_falla_con_instrucciones(self):
        # Un identificador con forma válida pero desconocido debe explicar qué
        # hacer, no intentar descargarlo de internet.
        with pytest.raises(ValueError) as exc:
            E.resolve_encoder("static:modelo-inventado")
        mensaje = str(exc.value)
        assert "build_embeddings" in mensaje
        assert "modelo-inventado" in mensaje

    def test_nunca_se_pasa_un_identificador_a_huggingface(self):
        # La causa exacta del error original: 'static:...' acababa como nombre
        # de repositorio en HuggingFace.
        for preset in E.PRESETS:
            ident = E.encoder_id(preset)
            assert E.preset_from_id(ident) is not None, (
                f"«{ident}» no se resuelve y acabaría en HuggingFace")


class TestInterfazComun:
    def test_ambos_motores_cumplen_el_contrato(self):
        for clase in (E.TorchEncoder, E.StaticEncoder):
            assert issubclass(clase, E.Encoder)
            assert hasattr(clase, "encode")

    def test_encode_one_usa_encode(self):
        class Falso(E.Encoder):
            name, dimensions = "falso", 3
            def encode(self, texts):
                return np.tile([1.0, 0.0, 0.0], (len(texts), 1)).astype(np.float32)

        f = Falso()
        assert f.encode_one("hola").shape == (3,)
        assert np.allclose(f.encode_one("hola"), [1.0, 0.0, 0.0])
