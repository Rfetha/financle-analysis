import time

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from loguru import logger
from pydantic import BaseModel
from sonar import config
from sonar.store.db import connect
from sonar.store.cache import Cache
from sonar.market.registry import MarketRegistry
from sonar.market.us import USMarketPlugin
from sonar.market.base import UnknownSymbol
from sonar.tools.quote import get_quote
from sonar.agent import events


class ChatRequest(BaseModel):
    message: str
    thread_id: str | None = None


def _default_registry() -> MarketRegistry:
    from sonar.market.us.prices import make_price_source

    reg = MarketRegistry()
    reg.register(USMarketPlugin(make_price_source()))
    return reg


def create_app(
    registry: MarketRegistry | None = None,
    cache: Cache | None = None,
    streamer=None,
) -> FastAPI:
    app = FastAPI(title="Sonar")
    registry = registry or _default_registry()
    cache = cache or Cache(connect(config.DB_PATH))

    def _get_streamer():
        # Agent'ı lazy kur: model init ilk chat isteğinde (model katmanı env'den seçer).
        nonlocal streamer
        if streamer is None:
            from sonar.agent.graph import make_streamer

            streamer = make_streamer(registry=registry, cache=cache)
        return streamer

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/quote/{ticker}")
    def quote(ticker: str) -> dict:
        try:
            return get_quote(ticker, registry=registry, cache=cache, ttl=config.QUOTE_TTL_SECONDS)
        except UnknownSymbol:
            raise HTTPException(status_code=404, detail=f"Sembol bulunamadı: {ticker.upper()}")

    @app.post("/api/chat")
    async def chat(req: ChatRequest) -> StreamingResponse:
        async def stream():
            thread = req.thread_id or "default"
            started = time.perf_counter()
            logger.info("chat[{}] ← {!r}", thread, req.message)
            deltas = 0
            try:
                async for etype, data in _get_streamer()(req.message, thread):
                    if etype == events.TEXT_DELTA:
                        deltas += 1  # tek tek loglamak gürültü; sonda sayısı yazılır
                    elif etype == events.TOOL_CALL:
                        logger.info("chat[{}] tool → {}({})", thread, data["name"], data["input"])
                    elif etype == events.TOOL_RESULT:
                        logger.info("chat[{}] tool ← {} {:.200}", thread, data["name"], data["output"])
                    elif etype == events.ERROR:
                        logger.error("chat[{}] agent hatası: {}", thread, data["message"])
                    yield events.sse(etype, data)
            except Exception as e:  # model/auth/tool hatası → tek error event, sessiz düşme yok
                from sonar.agent.model import explain

                logger.exception("chat[{}] akış çöktü", thread)
                yield events.sse(events.ERROR, {"message": explain(e)})
            logger.info(
                "chat[{}] ✓ {} text-delta, {:.1f}s", thread, deltas, time.perf_counter() - started
            )
            yield events.sse(events.DONE, {})

        return StreamingResponse(stream(), media_type="text/event-stream")

    from pathlib import Path
    from fastapi.staticfiles import StaticFiles

    static_dir = Path(__file__).parent.parent / "web" / "static"
    if static_dir.exists():
        app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")

    return app
