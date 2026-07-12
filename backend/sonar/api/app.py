from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
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
    reg = MarketRegistry()
    reg.register(USMarketPlugin())
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
        # Provider'a göre agent'ı lazy kur (ADR-0002): abonelik → Claude Code SDK loop'u,
        # API-key → LangGraph ReAct. İkisi de aynı (message, thread_id) -> SSE event akışı.
        nonlocal streamer
        if streamer is None:
            if config.PROVIDER == "claude-code":
                from sonar.agent.claude_code import make_streamer
            else:
                from sonar.agent.graph import make_streamer

            streamer = make_streamer(
                registry=registry, cache=cache, ttl=config.QUOTE_TTL_SECONDS
            )
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
            try:
                async for etype, data in _get_streamer()(
                    req.message, req.thread_id or "default"
                ):
                    yield events.sse(etype, data)
            except Exception as e:  # provider/auth/tool hatası → tek error event, sessiz düşme yok
                yield events.sse(events.ERROR, {"message": str(e)})
            yield events.sse(events.DONE, {})

        return StreamingResponse(stream(), media_type="text/event-stream")

    from pathlib import Path
    from fastapi.staticfiles import StaticFiles

    static_dir = Path(__file__).parent.parent / "web" / "static"
    if static_dir.exists():
        app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")

    return app
