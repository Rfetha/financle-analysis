import pytest
from sonar.market.registry import MarketRegistry
from sonar.market.base import Unsupported


class _FakePlugin:
    market = "US"
    def get_quote(self, symbol):
        raise Unsupported("no quote")


def test_registry_get_returns_registered_plugin():
    reg = MarketRegistry()
    p = _FakePlugin()
    reg.register(p)
    assert reg.get("US") is p


def test_registry_unknown_market_raises():
    with pytest.raises(KeyError):
        MarketRegistry().get("TR")
