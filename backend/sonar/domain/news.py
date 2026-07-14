from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class NewsItem:
    title: str
    url: str
    source: str
    published_at: int | None  # unix saniye
