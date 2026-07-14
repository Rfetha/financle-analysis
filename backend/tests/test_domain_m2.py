from sonar.domain.candle import Candle, OhlcvSeries
from sonar.domain.fundamentals import Fundamentals
from sonar.domain.macro import GlobalSnapshot, LocalSnapshot, MacroSnapshot
from sonar.domain.news import NewsItem
from sonar.domain.quote import Provenance
from sonar.domain.symbol import Symbol


def test_candle_and_series_are_frozen():
    c = Candle(ts=1, open=1.0, high=2.0, low=0.5, close=1.5, volume=100)
    series = OhlcvSeries(Symbol("NVDA", "US"), "1d", [c], Provenance("fake", 1.0))
    assert series.candles[0].close == 1.5
    assert series.interval == "1d"


def test_fundamentals_holds_optional_fields():
    f = Fundamentals(Symbol("NVDA", "US"), "FY2026", 150.0, 30.0, 20.0, 50.0, Provenance("edgar", 1.0))
    assert f.period == "FY2026" and f.net_margin == 20.0


def test_news_item_allows_missing_date():
    assert NewsItem("t", "u", "src", None).published_at is None


def test_macro_snapshot_nests_global_and_local():
    snap = MacroSnapshot(
        GlobalSnapshot(15.1, 122.0, 79.0),
        LocalSnapshot(4.5, 3.0, 4.3, 3.9, 0.4),
        Provenance("FRED", 1.0),
    )
    assert snap.global_.vix == 15.1 and snap.local.curve_10y_2y == 0.4
