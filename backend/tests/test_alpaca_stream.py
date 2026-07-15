import json
import os

import pytest
from sonar.market.us.stream import AlpacaStream, parse_ws_message


def test_parse_trade_message():
    raw = json.dumps([{"T": "t", "S": "NVDA", "p": 180.42, "t": "2026-07-13T14:00:00Z"}])
    ticks = parse_ws_message(raw)
    assert ticks == [{"ticker": "NVDA", "price": "180.42", "ts": 1783951200.0}]


def test_parse_ignores_control_messages():
    raw = json.dumps([{"T": "success", "msg": "authenticated"}])
    assert parse_ws_message(raw) == []


@pytest.mark.slow
@pytest.mark.skipif(not os.environ.get("SONAR_ALPACA_KEY"), reason="Alpaca key yok")
async def test_real_stream_first_tick():
    stream = AlpacaStream(key="...", secret="...")
    async for tick in stream.ticks(["AAPL"]):
        assert float(tick["price"]) > 0
        break
