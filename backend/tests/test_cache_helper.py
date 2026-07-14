from sonar.store.cache import Cache
from sonar.tools._cache import cached


def test_cached_computes_on_miss_and_reuses_on_hit(conn):
    calls = {"n": 0}

    def compute():
        calls["n"] += 1
        return {"v": 42}

    cache = Cache(conn, now=lambda: 1.0)
    assert cached(cache, "k", 60, compute) == {"v": 42}
    assert cached(cache, "k", 60, compute) == {"v": 42}
    assert calls["n"] == 1  # ikinci çağrı cache'ten


def test_cached_key_isolation(conn):
    cache = Cache(conn, now=lambda: 1.0)
    cached(cache, "a", 60, lambda: {"v": 1})
    assert cached(cache, "b", 60, lambda: {"v": 2}) == {"v": 2}
