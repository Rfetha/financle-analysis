from sonar.analytics.indicators import days_to_cover
from sonar.domain.holdings import ShortInterest
from sonar.domain.symbol import Symbol
from sonar.market.base import BaseMarketPlugin
from sonar.market.registry import MarketRegistry
from sonar.market.us.finra import FinraShort
from sonar.store.cache import Cache
from sonar.tools.short_interest import get_short_interest


def test_days_to_cover():
    assert days_to_cover(shares_short=1_000_000, avg_daily_volume=500_000) == 2.0


def test_days_to_cover_zero_volume_is_none():
    assert days_to_cover(shares_short=1_000_000, avg_daily_volume=0) is None


def test_finra_short_from_yfinance_info():
    fetch = lambda ticker: {"sharesShort": 5_000_000, "shortRatio": 2.5}  # noqa: E731
    si = FinraShort(fetch=fetch).short_interest(Symbol("NVDA", "US"))
    assert si.shares_short == 5_000_000
    assert si.days_to_cover == 2.5
    assert si.source == "Yahoo (ikinci-el)"


def test_finra_short_missing_fields_no_crash():
    si = FinraShort(fetch=lambda ticker: {}).short_interest(Symbol("NVDA", "US"))
    assert si.shares_short == 0
    assert si.days_to_cover is None


class FakeMarket(BaseMarketPlugin):
    market = "US"

    def get_short_interest(self, symbol):
        return ShortInterest(
            symbol=symbol, shares_short=5_000_000, days_to_cover=2.5,
            as_of="", source="Yahoo (ikinci-el)",
        )


def test_short_interest_tool_shape(conn):
    reg = MarketRegistry()
    reg.register(FakeMarket())
    out = get_short_interest("nvda", registry=reg, cache=Cache(conn), ttl=86400)
    assert out["shares_short"] == 5_000_000
    assert out["days_to_cover"] == 2.5
    assert out["source"] == "Yahoo (ikinci-el)"


def test_short_interest_note_says_aggregate_no_names(conn):
    reg = MarketRegistry()
    reg.register(FakeMarket())
    out = get_short_interest("nvda", registry=reg, cache=Cache(conn), ttl=86400)
    assert "toplam" in out["provenance_note"].lower()
    assert "kim" in out["provenance_note"].lower()
