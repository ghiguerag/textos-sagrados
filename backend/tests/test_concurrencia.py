"""
Acceso concurrente a la base de datos.

Este fichero existe por un fallo que solo aparecía con la aplicación en uso
real. La interfaz lanza varias peticiones a la vez —frecuencias, secciones,
divisiones y colocaciones—, el servidor atiende cada una en un hilo distinto,
y todas compartían una única conexión SQLite.

Los errores eran distintos cada vez y ninguno señalaba la causa:
«sqlite3.InterfaceError: another row available», «'NoneType' object is not
subscriptable»… Compartir una conexión SQLite entre hilos no es seguro aunque
check_same_thread lo permita.
"""

import shutil
import tempfile
import threading
from pathlib import Path

import pytest

from app.core import analysis as A
from app.core.db import ThreadLocalConnection, connect
from app.core.lexicon import Lexicon

RAIZ = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def db_local(sample_db):
    # Copia a disco local: SQLite falla al abrir en modo lectura sobre
    # algunos sistemas de archivos montados.
    tmp = Path(tempfile.gettempdir()) / "ts_concurrencia.db"
    shutil.copy2(sample_db, tmp)
    return tmp


class TestConexionPorHilo:
    def test_cada_hilo_recibe_la_suya(self, db_local):
        conn = connect(db_local, readonly=True, thread_safe=True)
        vistas = {}

        def trabajo(n):
            vistas[n] = id(conn._conn)

        hilos = [threading.Thread(target=trabajo, args=(i,)) for i in range(6)]
        [h.start() for h in hilos]
        [h.join() for h in hilos]

        assert len(set(vistas.values())) == len(hilos), (
            "dos hilos comparten conexión: es exactamente el fallo original"
        )
        conn.close()

    def test_se_comporta_como_una_conexion_normal(self, db_local):
        conn = connect(db_local, readonly=True, thread_safe=True)
        fila = conn.execute("SELECT COUNT(*) AS n FROM verses").fetchone()
        assert fila["n"] > 0, "row_factory no se aplica"
        conn.close()

    def test_cierra_todas_las_conexiones(self, db_local):
        conn = ThreadLocalConnection(db_local, readonly=True)
        conn.execute("SELECT 1")
        hilo = threading.Thread(target=lambda: conn.execute("SELECT 1"))
        hilo.start(); hilo.join()
        assert len(conn._todas) == 2
        conn.close()
        assert conn._todas == []


class TestAnalisisConcurrente:
    """Reproduce el escenario que fallaba: varias consultas pesadas a la vez."""

    def test_colocaciones_en_paralelo(self, db_local):
        conn = connect(db_local, readonly=True, thread_safe=True)
        lx = Lexicon.load(RAIZ / "data" / "lexicon.json")
        stems = A.resolve_query("", "en", lexicon=lx, semantic_field="divinidad")

        errores: list[Exception] = []
        resultados: list[int] = []

        def consulta(work_id):
            try:
                r = A.collocations(conn, stems, work_id=work_id,
                                   min_freq=1, limit=20)
                resultados.append(len(r))
            except Exception as exc:            # noqa: BLE001
                errores.append(exc)

        obras = ["kjv", "tanaj-jps", "quran-palmer", "gita-arnold"] * 4
        hilos = [threading.Thread(target=consulta, args=(w,)) for w in obras]
        [h.start() for h in hilos]
        [h.join() for h in hilos]

        assert not errores, f"fallos con acceso concurrente: {errores[:3]}"
        assert len(resultados) == len(obras)
        conn.close()

    def test_mezcla_de_consultas_a_la_vez(self, db_local):
        # Igual que hace la interfaz: cuatro tipos de consulta en paralelo.
        conn = connect(db_local, readonly=True, thread_safe=True)
        lx = Lexicon.load(RAIZ / "data" / "lexicon.json")
        stems = A.resolve_query("", "en", lexicon=lx, semantic_field="misericordia")

        errores: list[Exception] = []

        def envolver(fn):
            def _():
                try:
                    fn()
                except Exception as exc:        # noqa: BLE001
                    errores.append(exc)
            return _

        tareas = []
        for _ in range(3):
            tareas += [
                envolver(lambda: A.frequency_by_work(conn, stems)),
                envolver(lambda: A.frequency_by_division(conn, stems, "kjv")),
                envolver(lambda: A.frequency_by_section(conn, stems, "quran-palmer")),
                envolver(lambda: A.collocations(conn, stems, min_freq=1, limit=15)),
                envolver(lambda: A.concordance(conn, stems, limit=20)),
                envolver(lambda: A.surface_forms(conn, stems)),
            ]

        hilos = [threading.Thread(target=t) for t in tareas]
        [h.start() for h in hilos]
        [h.join() for h in hilos]

        assert not errores, f"fallos con acceso concurrente: {errores[:3]}"
        conn.close()


class TestColocacionesEnUnaConsulta:
    """El patrón N+1 era lo que alargaba la ventana de colisión."""

    def test_no_consulta_dentro_del_bucle(self):
        import inspect
        codigo = inspect.getsource(A.collocations)
        cuerpo = codigo.split("for r in rows:")[-1]
        assert "conn.execute" not in cuerpo, (
            "hay una consulta dentro del bucle: vuelve el patrón N+1"
        )

    def test_devuelve_resultados_correctos(self, conn, lexicon):
        stems = A.resolve_query("", "en", lexicon=lexicon, semantic_field="divinidad")
        r = A.collocations(conn, stems, work_id="quran-palmer", min_freq=1, limit=10)
        assert r
        assert all("pmi" in x and "joint_count" in x for x in r)
        pmis = [x["pmi"] for x in r]
        assert pmis == sorted(pmis, reverse=True), "no está ordenado por PMI"

    def test_consulta_vacia(self, conn):
        assert A.collocations(conn, []) == []
