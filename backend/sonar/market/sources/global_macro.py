"""Global rejim serileri — her market plugin'i bunu KULLANIR (miras almaz)."""

from sonar.domain.macro import GlobalSnapshot
from sonar.market.sources.fred import FredClient

VIX = "VIXCLS"
DXY = "DTWEXBGS"   # Broad Dollar Index
WTI = "DCOILWTICO"


class GlobalMacro:
    def __init__(self, fred: FredClient) -> None:
        self._fred = fred

    def snapshot(self) -> GlobalSnapshot:
        v = self._fred.latest([VIX, DXY, WTI])
        return GlobalSnapshot(vix=v.get(VIX), dxy=v.get(DXY), wti=v.get(WTI))
