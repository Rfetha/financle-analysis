"""Insider (Form 4) değer nesnesi."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class InsiderTrade:
    name: str
    title: str
    action: str       # "buy" (açık piyasa alımı, kod P) | "sell" (kod S)
    shares: int
    price: float | None
    traded_at: int    # unix saniye
