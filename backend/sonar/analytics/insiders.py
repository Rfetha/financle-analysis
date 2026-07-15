"""Insider cluster tespiti — saf matematik.

Tek yöneticinin alımı gürültüdür; AYNI pencerede BİRDEN FAZLA farklı yönetici açık piyasadan
alıyorsa haber vardır (cluster buying — ücretsiz veride bulunan en sağlam sinyallerden biri).
"""

import time
from typing import Callable

from sonar.domain.insider import InsiderTrade

MIN_CLUSTER_BUYERS = 2


def cluster(
    trades: list[InsiderTrade],
    window_days: int = 30,
    now: float | Callable[[], float] = time.time,
) -> dict:
    current = now() if callable(now) else now
    cutoff = current - window_days * 86400
    recent = [t for t in trades if t.traded_at >= cutoff]

    buyers = {t.name for t in recent if t.action == "buy"}
    sellers = {t.name for t in recent if t.action == "sell"}
    return {
        "window_days": window_days,
        "buyers": len(buyers),
        "sellers": len(sellers),
        "bought_shares": sum(t.shares for t in recent if t.action == "buy"),
        "sold_shares": sum(t.shares for t in recent if t.action == "sell"),
        "is_cluster_buy": len(buyers) >= MIN_CLUSTER_BUYERS and not sellers,
    }
