"""Alpaca canlı tick akışı (IEX, ücretsiz katman). Çıktı: polling ile AYNI tick sözlüğü."""

import json
from datetime import datetime

WS_URL = "wss://stream.data.alpaca.markets/v2/iex"


def parse_ws_message(raw: str) -> list[dict]:
    """Alpaca mesajı → tick listesi. Kontrol mesajları (auth/subscribe) atlanır."""
    out = []
    for msg in json.loads(raw):
        if msg.get("T") != "t":  # yalnız trade mesajları
            continue
        ts = datetime.fromisoformat(msg["t"].replace("Z", "+00:00")).timestamp()
        out.append({"ticker": msg["S"], "price": str(msg["p"]), "ts": ts})
    return out


class AlpacaStream:
    def __init__(self, key: str, secret: str, url: str = WS_URL) -> None:
        self._key, self._secret, self._url = key, secret, url

    async def ticks(self, tickers: list[str]):
        import websockets

        async with websockets.connect(self._url) as ws:
            await ws.send(json.dumps({"action": "auth", "key": self._key, "secret": self._secret}))
            await ws.send(json.dumps({"action": "subscribe", "trades": tickers}))
            async for raw in ws:
                for tick in parse_ws_message(raw):
                    yield tick
