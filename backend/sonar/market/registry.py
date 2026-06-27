from sonar.market.base import MarketPlugin


class MarketRegistry:
    def __init__(self) -> None:
        self._plugins: dict[str, MarketPlugin] = {}

    def register(self, plugin: MarketPlugin) -> None:
        self._plugins[plugin.market] = plugin

    def get(self, market: str) -> MarketPlugin:
        return self._plugins[market]
