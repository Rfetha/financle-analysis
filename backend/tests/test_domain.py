from decimal import Decimal
import pytest
from sonar.domain.money import Money
from sonar.domain.symbol import Symbol
from sonar.domain.quote import Quote, Provenance


def test_money_add_same_currency():
    assert Money(Decimal("1.5"), "USD") + Money(Decimal("2.5"), "USD") == Money(Decimal("4.0"), "USD")


def test_money_add_currency_mismatch_raises():
    with pytest.raises(ValueError):
        Money(Decimal("1"), "USD") + Money(Decimal("1"), "EUR")


def test_symbol_uppercases_ticker():
    assert Symbol("aapl", "US").ticker == "AAPL"


def test_quote_change_pct():
    q = Quote(
        symbol=Symbol("AAPL", "US"),
        price=Money(Decimal("110"), "USD"),
        previous_close=Money(Decimal("100"), "USD"),
        provenance=Provenance("yfinance", 0.0),
    )
    assert q.change_pct == pytest.approx(10.0)


def test_quote_change_pct_zero_previous_close():
    q = Quote(
        symbol=Symbol("AAPL", "US"),
        price=Money(Decimal("110"), "USD"),
        previous_close=Money(Decimal("0"), "USD"),
        provenance=Provenance("yfinance", 0.0),
    )
    assert q.change_pct == 0.0
