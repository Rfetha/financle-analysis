"""Market bilmeyen ortak HTTP makinesi: rate-limit + User-Agent + retry.

SEC EDGAR zorunlu tutuyor: gerçek iletişim bilgisi içeren User-Agent ve ≤10 req/s.
İhlal = IP ban. Bunu üç kaynak (EDGAR, FRED, FINRA) paylaşıyor → tek yerde (Rule of Three).
"""

import time
from typing import Callable

import httpx


class HttpClient:
    def __init__(
        self,
        user_agent: str,
        *,
        min_interval: float = 0.11,  # ~9 req/s — SEC'in 10 req/s sınırının altında
        retries: int = 2,
        transport: httpx.BaseTransport | None = None,
        now: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
        extra_headers: dict[str, str] | None = None,
    ) -> None:
        self._min_interval = min_interval
        self._retries = retries
        self._now = now
        self._sleep = sleep
        self._last: float | None = None
        self._client = httpx.Client(
            headers={"User-Agent": user_agent, **(extra_headers or {})},
            timeout=30.0,
            follow_redirects=True,
            transport=transport,
        )

    def _throttle(self) -> None:
        # Why: _last=None yerine 0.0 kullanılsaydı, gerçek time.monotonic()
        # dışındaki (ör. testte donmuş) saatlerde ilk çağrı da gereksiz bekletilirdi.
        if self._last is not None:
            wait = self._min_interval - (self._now() - self._last)
            if wait > 0:
                self._sleep(wait)
        self._last = self._now()

    def _get(self, url: str) -> httpx.Response:
        last_error: Exception | None = None
        for attempt in range(self._retries + 1):
            self._throttle()
            try:
                resp = self._client.get(url)
                resp.raise_for_status()
                return resp
            except (httpx.HTTPStatusError, httpx.TransportError) as e:
                # Why: 429/5xx ve geçici ağ hataları retry'lanabilir; 4xx (404 gibi) değil.
                status = getattr(getattr(e, "response", None), "status_code", None)
                if status is not None and status < 500 and status != 429:
                    raise
                last_error = e
                if attempt < self._retries:
                    self._sleep(2**attempt)
        assert last_error is not None
        raise last_error

    def get_json(self, url: str) -> dict:
        return self._get(url).json()

    def get_text(self, url: str) -> str:
        return self._get(url).text

    def get_bytes(self, url: str) -> bytes:
        return self._get(url).content
