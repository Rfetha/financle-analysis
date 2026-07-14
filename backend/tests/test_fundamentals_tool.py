from sonar.domain.fundamentals import Fundamentals
from sonar.domain.quote import Provenance
from sonar.market.base import BaseMarketPlugin
from sonar.market.registry import MarketRegistry
from sonar.store.cache import Cache
from sonar.tools.fundamentals import get_fundamentals


class FakeMarket(BaseMarketPlugin):
    market = "US"

    def get_fundamentals(self, symbol):
        return Fundamentals(
            symbol=symbol, period="FY2026", revenue=150.0, net_income=30.0,
            net_margin=20.0, revenue_growth_yoy=50.0,
            provenance=Provenance("SEC EDGAR companyfacts", 1.0),
        )


def test_fundamentals_tool_shape(conn):
    reg = MarketRegistry()
    reg.register(FakeMarket())
    out = get_fundamentals("nvda", registry=reg, cache=Cache(conn), ttl=86400)
    assert out == {
        "ticker": "NVDA", "period": "FY2026", "revenue": 150.0, "net_income": 30.0,
        "net_margin": 20.0, "revenue_growth_yoy": 50.0, "source": "SEC EDGAR companyfacts",
    }
