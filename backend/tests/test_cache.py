from sonar.store.cache import Cache


def test_cache_miss_returns_none(conn):
    assert Cache(conn).get("k") is None


def test_cache_set_then_get(conn):
    cache = Cache(conn)
    cache.set("k", "v", ttl_seconds=60)
    assert cache.get("k") == "v"


def test_cache_expired_returns_none(conn):
    clock = {"t": 1000.0}
    cache = Cache(conn, now=lambda: clock["t"])
    cache.set("k", "v", ttl_seconds=60)
    clock["t"] = 1061.0
    assert cache.get("k") is None
