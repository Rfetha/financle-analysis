import pytest
from sonar.agent import events
from sonar.agent.recipes.deep_analysis import gather, make_analyzer
from sonar.market.base import BaseMarketPlugin, Unsupported
from sonar.market.registry import MarketRegistry
from sonar.store.cache import Cache
from sonar.domain.candle import Candle, OhlcvSeries
from sonar.domain.fundamentals import Fundamentals
from sonar.domain.macro import GlobalSnapshot, LocalSnapshot, MacroSnapshot
from sonar.domain.news import NewsItem
from sonar.domain.quote import Provenance


class PartialMarket(BaseMarketPlugin):
    """Fundamentals patlar (EDGAR 500), gerisi çalışır — rapor ayakta kalmalı."""

    market = "US"

    def get_ohlcv(self, symbol, range_, interval):
        candles = [
            Candle(ts=i, open=100 + i, high=101 + i, low=99 + i, close=100 + i, volume=1000)
            for i in range(250)
        ]
        return OhlcvSeries(symbol, interval, candles, Provenance("fake", 1.0))

    def get_fundamentals(self, symbol):
        raise RuntimeError("EDGAR 500")

    def get_news(self, symbol):
        return [NewsItem("Haber", "https://x", "Yahoo Finance", 1)]

    def get_peers(self, symbol):
        raise Unsupported("US: peers")

    def get_macro_snapshot(self):
        return MacroSnapshot(
            GlobalSnapshot(15.1, 122.0, 79.0),
            LocalSnapshot(4.5, 3.0, 4.3, 3.9, 0.4),
            Provenance("FRED", 1.0),
        )


def _ctx(conn):
    reg = MarketRegistry()
    reg.register(PartialMarket())
    return {"registry": reg, "cache": Cache(conn)}


def test_gather_marks_failed_section_unavailable_and_keeps_others(conn):
    out = gather("NVDA", **_ctx(conn))
    assert out["fundamentals"]["unavailable"]          # patladı ama rapor ayakta
    assert out["peers"]["unavailable"] == "US: peers"  # Unsupported da aynı yoldan
    assert out["technicals"]["rsi"] == 100.0
    assert out["macro"]["global"]["vix"] == 15.1
    assert out["news"]["items"][0]["title"] == "Haber"


@pytest.mark.asyncio
async def test_analyzer_streams_steps_chart_then_text(conn):
    class FakeModel:
        async def astream(self, prompt):
            for chunk in ("Makro ", "olumlu."):
                yield type("C", (), {"content": chunk})()

    analyze = make_analyzer(**_ctx(conn), model_factory=lambda: FakeModel())
    seen = [(etype, data) async for etype, data in analyze("NVDA")]
    types = [t for t, _ in seen]

    assert types.count(events.ANALYSIS_STEP) >= 5   # her bölüm bir adım
    assert events.CHART in types
    assert types[-1] == events.TEXT_DELTA
    text = "".join(d["delta"] for t, d in seen if t == events.TEXT_DELTA)
    assert text == "Makro olumlu."


@pytest.mark.asyncio
async def test_analyzer_handles_anthropic_content_block_list(conn):
    """Anthropic streaming chunk.content bir blok listesi olabilir (str değil) — I2."""

    class FakeModel:
        async def astream(self, prompt):
            yield type("C", (), {"content": [{"type": "text", "text": "Makro "}]})()
            yield type("C", (), {"content": [{"type": "text", "text": "olumlu."}]})()

    analyze = make_analyzer(**_ctx(conn), model_factory=lambda: FakeModel())
    seen = [(etype, data) async for etype, data in analyze("NVDA")]
    text = "".join(d["delta"] for t, d in seen if t == events.TEXT_DELTA)
    assert text == "Makro olumlu."
