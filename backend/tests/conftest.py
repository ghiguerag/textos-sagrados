import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.core.db import connect                    # noqa: E402
from app.core.ingest import VerseRecord, build_database  # noqa: E402
from app.core.lexicon import Lexicon               # noqa: E402
from scripts.fetch_corpus import SOURCES           # noqa: E402


@pytest.fixture(scope="session")
def sample_db(tmp_path_factory):
    payload = json.loads((ROOT / "data" / "sample_corpus.json").read_text(encoding="utf-8"))

    def load(work_id):
        for item in payload["works"][work_id]:
            yield VerseRecord(
                division_ordinal=item["division_ordinal"],
                division_name=item["division_name"],
                chapter=item["chapter"], number=item["number"],
                text=item["text"], section=item.get("section"),
            )

    db = tmp_path_factory.mktemp("db") / "sample.db"
    build_database(db, [(SOURCES[w][0], load(w)) for w in payload["works"]])
    return db


@pytest.fixture(scope="session")
def conn(sample_db):
    c = connect(sample_db, readonly=True)
    yield c
    c.close()


@pytest.fixture(scope="session")
def lexicon():
    return Lexicon.load(ROOT / "data" / "lexicon.json")
