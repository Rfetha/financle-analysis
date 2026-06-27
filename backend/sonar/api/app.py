from fastapi import FastAPI
from sonar import config
from sonar.store.db import connect
from sonar.store.cache import Cache
from sonar.market.registry import MarketRegistry
from sonar.market.us import USMarketPlugin
from sonar.tools.quote import get_quote


def _default_registry() -> MarketRegistry:
    reg = MarketRegistry()
    reg.register(USMarketPlugin())
    return reg


def create_app(registry: MarketRegistry | None = None, cache: Cache | None = None) -> FastAPI:
    app = FastAPI(title="Sonar")
    registry = registry or _default_registry()
    cache = cache or Cache(connect(config.DB_PATH))

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/quote/{ticker}")
    def quote(ticker: str) -> dict:
        return get_quote(ticker, registry=registry, cache=cache, ttl=config.QUOTE_TTL_SECONDS)

    from pathlib import Path
    from fastapi.staticfiles import StaticFiles

    static_dir = Path(__file__).parent.parent / "web" / "static"
    if static_dir.exists():
        app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")

    return app
