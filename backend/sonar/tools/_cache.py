"""Tool'ların cache sarmalı tek yerde. Bu olmadan her tool aynı 6 satırı tekrar ederdi
(Duplicated Code — Fowler). Tool'un işi: anahtarı ve hesabı vermek."""

import json
from typing import Callable

from sonar.store.cache import Cache


def cached(cache: Cache, key: str, ttl: int, compute: Callable[[], dict]) -> dict:
    hit = cache.get(key)
    if hit is not None:
        return json.loads(hit)
    out = compute()
    cache.set(key, json.dumps(out), ttl)
    return out
