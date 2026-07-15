"""US haber kaynakları. Feed listesi burada (market bilgisi), parse ortakta."""

import httpx
from defusedxml.common import DefusedXmlException
from xml.etree.ElementTree import ParseError

from sonar.domain.news import NewsItem
from sonar.domain.symbol import Symbol
from sonar.market.sources.http import HttpClient
from sonar.market.sources.rss import parse_rss

YAHOO_FEED = "https://feeds.finance.yahoo.com/rss/2.0/headline?s={ticker}&region=US&lang=en-US"


class USNews:
    def __init__(self, http: HttpClient) -> None:
        self._http = http

    def for_symbol(self, symbol: Symbol, limit: int = 10) -> list[NewsItem]:
        # Why: Yahoo'nun bu RSS feed'i tarihsel olarak kararsız (403/HTML/boş gövde
        # dönebiliyor) — fetch/parse hatası tüm haber bölümünü Unavailable'a
        # düşürmesin, boş liste dönsün (recipe bunu "haber yok" olarak yorumlar).
        try:
            xml = self._http.get_text(YAHOO_FEED.format(ticker=symbol.ticker))
            items = parse_rss(xml, source="Yahoo Finance")
        except (httpx.HTTPError, ParseError, DefusedXmlException):
            return []
        items.sort(key=lambda i: i.published_at or 0, reverse=True)
        return items[:limit]
