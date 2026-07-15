import httpx
import pytest
from sonar.domain.symbol import Symbol
from sonar.market.sources.http import HttpClient
from sonar.market.sources.rss import parse_rss
from sonar.market.us.news import USNews

FEED = """<?xml version="1.0"?>
<rss version="2.0"><channel>
  <item>
    <title>NVIDIA beats estimates</title>
    <link>https://example.com/a</link>
    <pubDate>Mon, 13 Jul 2026 14:00:00 GMT</pubDate>
  </item>
  <item>
    <title>Chip demand rises</title>
    <link>https://example.com/b</link>
    <pubDate>Mon, 13 Jul 2026 09:00:00 GMT</pubDate>
  </item>
</channel></rss>"""


def test_parse_rss_extracts_items():
    items = parse_rss(FEED, source="Yahoo Finance")
    assert len(items) == 2
    assert items[0].title == "NVIDIA beats estimates"
    assert items[0].url == "https://example.com/a"
    assert items[0].source == "Yahoo Finance"
    assert items[0].published_at == 1783951200  # 2026-07-13 14:00 UTC (spec constant was wrong)


def test_parse_rss_tolerates_missing_date():
    xml = "<rss><channel><item><title>T</title><link>u</link></item></channel></rss>"
    items = parse_rss(xml, source="X")
    assert items[0].published_at is None


def test_us_news_fetches_and_sorts_newest_first():
    http = HttpClient(
        "Sonar/0.1 (t@e.com)", min_interval=0,
        transport=httpx.MockTransport(lambda r: httpx.Response(200, text=FEED)),
    )
    items = USNews(http).for_symbol(Symbol("NVDA", "US"))
    assert [i.title for i in items][:1] == ["NVIDIA beats estimates"]


@pytest.mark.slow
def test_real_yahoo_news_returns_items_or_empty():
    from sonar.market.us import _default_http

    items = USNews(_default_http()).for_symbol(Symbol("AAPL", "US"))
    assert isinstance(items, list)  # boş de olabilir, ama crash olmamalı
    for item in items:
        assert item.title and item.url and item.source
