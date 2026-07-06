import sqlite3
import threading
import time
from typing import Callable


class Cache:
    def __init__(self, conn: sqlite3.Connection, now: Callable[[], float] = time.time) -> None:
        self._conn = conn
        self._now = now
        # ponytail: one shared connection guarded by a global lock. Single-user app
        # (multi-user is a non-goal), so serialized DB access is fine; switch to a
        # per-thread connection only if throughput ever matters.
        self._lock = threading.Lock()

    def get(self, key: str) -> str | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT value, expires_at FROM cache WHERE key = ?", (key,)
            ).fetchone()
        if row is None or row[1] <= self._now():
            return None
        return row[0]

    def set(self, key: str, value: str, ttl_seconds: int) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT OR REPLACE INTO cache(key, value, expires_at) VALUES (?, ?, ?)",
                (key, value, self._now() + ttl_seconds),
            )
            self._conn.commit()
