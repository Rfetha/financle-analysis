"""RSS → NewsItem. Market bilmez; feed URL'lerini plugin verir.

ponytail: feedparser bağımlılığı eklemiyoruz — email.utils + XML parse yetiyor.

Why defusedxml: bu XML *uzaktan* geliyor (güven sınırı). Stdlib ElementTree XXE ve
billion-laughs saldırılarına açık; defusedxml aynı API'yi güvenli haliyle verir.
Aynı gerekçe Faz B'deki Form 4 XML parse'ı için de geçerli.
"""

from email.utils import parsedate_to_datetime

from defusedxml import ElementTree

from sonar.domain.news import NewsItem


def _timestamp(text: str | None) -> int | None:
    if not text:
        return None
    try:
        return int(parsedate_to_datetime(text).timestamp())
    except (TypeError, ValueError):
        return None


def parse_rss(xml: str, source: str) -> list[NewsItem]:
    root = ElementTree.fromstring(xml)
    items = []
    for node in root.iter("item"):
        title = (node.findtext("title") or "").strip()
        url = (node.findtext("link") or "").strip()
        if not title or not url:
            continue
        items.append(
            NewsItem(
                title=title,
                url=url,
                source=source,
                published_at=_timestamp(node.findtext("pubDate")),
            )
        )
    return items
