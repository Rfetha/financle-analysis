"""US market plugin — ince composer. Yetenekleri kaynaklara dağıtır, domain VO'ya çevirir.
Hangi kaynağın hangi yeteneği doldurduğu buranın bilgisi; tool yüzeyine sızmaz.
"""

from sonar.domain.quote import Quote
from sonar.domain.symbol import Symbol
from sonar.market.base import BaseMarketPlugin
from sonar.market.us.prices import PriceSource, YFinancePrices


class USMarketPlugin(BaseMarketPlugin):
    market = "US"

    def __init__(self, prices: PriceSource | None = None) -> None:
        self._prices = prices or YFinancePrices()

    def get_quote(self, symbol: Symbol) -> Quote:
        return self._prices.quote(symbol)
