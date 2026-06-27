from typing import Protocol, runtime_checkable
from sonar.domain.symbol import Symbol
from sonar.domain.quote import Quote


class Unsupported(Exception):
    """Market bu yeteneği sağlayamıyor."""


class UnknownSymbol(Exception):
    """Market'te böyle bir sembol yok / veri bulunamadı."""


@runtime_checkable
class MarketPlugin(Protocol):
    market: str

    def get_quote(self, symbol: Symbol) -> Quote: ...
