import sqlite3
import pytest
from sonar.store.db import connect


@pytest.fixture()
def conn(tmp_path) -> sqlite3.Connection:
    c = connect(tmp_path / "test.db")
    yield c
    c.close()
