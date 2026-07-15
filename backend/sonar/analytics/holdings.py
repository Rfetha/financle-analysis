"""13F pozisyon matematiği — saf, market bilmez.

Opsiyon pozisyonları (put/call) hisse sayısına KARIŞTIRILMAZ: 13F'te ayrı satır olarak gelirler
ve "BofA 100M lot aldı" ile "BofA 2M lot PUT aldı" bambaşka şeylerdir (spec §7).
"""

from sonar.domain.holdings import HolderPosition


def classify_delta(prev_shares: int, cur_shares: int) -> str:
    if prev_shares == 0 and cur_shares > 0:
        return "new"
    if prev_shares > 0 and cur_shares == 0:
        return "exit"
    if cur_shares > prev_shares:
        return "add"
    if cur_shares < prev_shares:
        return "trim"
    return "hold"


def _long_by_cik(positions: list[HolderPosition]) -> dict[str, HolderPosition]:
    return {p.cik: p for p in positions if not p.put_call}


def delta_report(
    prev: list[HolderPosition], cur: list[HolderPosition], top: int = 10
) -> dict:
    prev_map = _long_by_cik(prev)
    cur_map = _long_by_cik(cur)

    movers = []
    for cik in prev_map.keys() | cur_map.keys():
        before = prev_map[cik].shares if cik in prev_map else 0
        after = cur_map[cik].shares if cik in cur_map else 0
        action = classify_delta(before, after)
        if action == "hold":
            continue
        holder = cur_map.get(cik) or prev_map[cik]
        movers.append({
            "cik": cik,
            "filer_name": holder.filer_name,
            "action": action,
            "shares": after,
            "delta_shares": after - before,
        })
    movers.sort(key=lambda m: abs(m["delta_shares"]), reverse=True)

    return {
        "total_shares": sum(p.shares for p in cur_map.values()),
        "filer_count": sum(1 for p in cur_map.values() if p.shares > 0),
        "new": sum(1 for m in movers if m["action"] == "new"),
        "exit": sum(1 for m in movers if m["action"] == "exit"),
        "movers": movers[:top],
        "options": [
            {"filer_name": p.filer_name, "put_call": p.put_call, "shares": p.shares}
            for p in cur
            if p.put_call
        ],
    }
