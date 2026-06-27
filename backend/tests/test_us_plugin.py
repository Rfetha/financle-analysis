from decimal import Decimal
import pytest
from sonar.market.us import USMarketPlugin
from sonar.domain.symbol import Symbol


def test_us_get_quote_builds_domain_quote():
    plugin = USMarketPlugin(now=lambda: 123.0, fetch=lambda ticker: (110.0, 100.0))
    q = plugin.get_quote(Symbol("AAPL", "US"))
    assert q.symbol == Symbol("AAPL", "US")
    assert q.price.amount == Decimal("110.0")
    assert q.previous_close.amount == Decimal("100.0")
    assert q.provenance.source == "yfinance"
    assert q.provenance.fetched_at == 123.0
    assert q.change_pct == pytest.approx(10.0)


@pytest.mark.slow
def test_us_get_quote_real_yfinance():
    q = USMarketPlugin().get_quote(Symbol("AAPL", "US"))
    assert q.price.amount > 0
