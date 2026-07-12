"""Claude aboneliği yolu (ADR-0002): agent loop'unu Claude Code SDK sürer.

Claude aboneliği kendi loop'umuzda kullanılamaz (ToS) → beyin Claude Code üzerinden
sürülür; API key gerekmez, lokal Claude Code auth'u kullanılır. Tool'lar aynı çekirdek
(ADR-0003), SSE taksonomisi aynı (ADR-0008) — fark yalnız döngünün kimde olduğu.
"""

import asyncio
import json

from claude_agent_sdk import ClaudeAgentOptions, create_sdk_mcp_server, query, tool

from sonar.agent import events
from sonar.agent.graph import SYSTEM
from sonar.market.base import UnknownSymbol
from sonar.tools.quote import get_quote

SERVER = "sonar"
MAX_TURNS = 8


def _make_quote_tool(*, registry, cache, ttl):
    @tool(
        "get_stock_quote",
        "Bir ABD hissesinin güncel fiyatını, günlük % değişimini ve kaynağını döner.",
        {"ticker": str},
    )
    async def get_stock_quote(args: dict) -> dict:
        ticker = args["ticker"]
        try:
            # get_quote senkron (yfinance + sqlite) → event loop'u bloklamasın.
            quote = await asyncio.to_thread(
                get_quote, ticker, registry=registry, cache=cache, ttl=ttl
            )
        except UnknownSymbol:
            return {
                "content": [{"type": "text", "text": f"Bilinmeyen sembol: {ticker.upper()}"}],
                "is_error": True,
            }
        return {"content": [{"type": "text", "text": json.dumps(quote, ensure_ascii=False)}]}

    return get_stock_quote


def make_streamer(*, registry, cache, ttl):
    """(message, thread_id) -> Sonar SSE event akışı üreten async generator."""
    server = create_sdk_mcp_server(SERVER, tools=[_make_quote_tool(registry=registry, cache=cache, ttl=ttl)])
    # ponytail: thread -> SDK session_id, process-içi dict (LangGraph yolundaki MemorySaver'ın
    # dengi). Restart'lar arası kalıcılık gerekirse SDK `session_store` / ADR-0004 SQLite'a taşı.
    sessions: dict[str, str] = {}

    async def stream(message: str, thread_id: str):
        tool_names: dict[str, str] = {}
        options = ClaudeAgentOptions(
            system_prompt=SYSTEM,
            mcp_servers={SERVER: server},
            allowed_tools=[f"mcp__{SERVER}__get_stock_quote"],
            tools=[],  # dahili Read/Bash/Edit yok — Sonar yalnız kendi tool'larını kullanır
            permission_mode="dontAsk",  # pre-approved dışı = reddet, kullanıcıya sorma
            setting_sources=[],  # repo CLAUDE.md / settings.json sızmasın
            max_turns=MAX_TURNS,
            include_partial_messages=True,  # token-token text-delta
            resume=sessions.get(thread_id),
        )
        async for msg in query(prompt=message, options=options):
            session_id = getattr(msg, "session_id", None)
            if session_id:
                sessions[thread_id] = session_id
            for event in events.map_sdk_message(msg, tool_names):
                yield event

    return stream
