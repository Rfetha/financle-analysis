import pytest
from sonar.domain.symbol import Symbol
from sonar.market.base import BaseMarketPlugin, Unsupported


class BareMarket(BaseMarketPlugin):
    market = "BARE"


def test_unimplemented_capability_raises_unsupported():
    plugin = BareMarket()
    with pytest.raises(Unsupported, match="BARE: ohlcv"):
        plugin.get_ohlcv(Symbol("AAPL", "BARE"), "6mo", "1d")


def test_unimplemented_holders_raises_unsupported():
    with pytest.raises(Unsupported, match="BARE: 13F"):
        BareMarket().get_institutional_holders(Symbol("AAPL", "BARE"))
