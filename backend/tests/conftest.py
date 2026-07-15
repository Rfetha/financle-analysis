import os
import sqlite3

import pytest

# Testlerde 13F arka plan ingestion'ı asla tetiklenmesin (ağ + startup task).
os.environ.setdefault("SONAR_SKIP_INGEST", "1")

from sonar.store.db import connect


@pytest.fixture()
def conn(tmp_path) -> sqlite3.Connection:
    c = connect(tmp_path / "test.db")
    yield c
    c.close()
