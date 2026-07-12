"""SSE event taksonomisi + provider akışlarından Sonar event map'i.

Taksonomi tau/AG-UI ile hizalı (ADR-0008): M1 = text-delta · tool-call ·
tool-result · error · done. M2'de quote-tick · chart **eklenir** (yeniden yazma
değil). Frontend part-registry bu tiplerle birebir eşleşir.

İki kaynak, tek taksonomi (ADR-0002): LangGraph `astream_events` (API-key yolu) ve
Claude Code SDK mesajları (abonelik yolu) aynı event'lere çevrilir.
"""

import json

from claude_agent_sdk import (
    AssistantMessage,
    ResultMessage,
    StreamEvent,
    ToolResultBlock,
    ToolUseBlock,
    UserMessage,
)

TEXT_DELTA = "text-delta"
TOOL_CALL = "tool-call"
TOOL_RESULT = "tool-result"
ERROR = "error"
DONE = "done"


def sse(event: str, data: dict) -> str:
    """Tek bir SSE frame'i (event + JSON data)."""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _text_of(content) -> str:
    # Anthropic streaming chunk.content str ya da blok listesi olabilir.
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(
            b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text"
        )
    return ""


def map_lc_event(ev: dict) -> list[tuple[str, dict]]:
    """Bir LangChain astream_events (v2) event'ini 0+ Sonar SSE event'ine çevirir."""
    kind = ev.get("event")
    if kind == "on_chat_model_stream":
        text = _text_of(ev["data"]["chunk"].content)
        return [(TEXT_DELTA, {"delta": text})] if text else []
    if kind == "on_tool_start":
        return [(TOOL_CALL, {"name": ev.get("name", ""), "input": ev["data"].get("input")})]
    if kind == "on_tool_end":
        return [(TOOL_RESULT, {"name": ev.get("name", ""), "output": str(ev["data"].get("output"))})]
    return []


def _result_text(content) -> str:
    if isinstance(content, list):
        return "".join(b.get("text", "") for b in content if isinstance(b, dict))
    return content or ""


def map_sdk_message(msg, tool_names: dict[str, str]) -> list[tuple[str, dict]]:
    """Bir Claude Code SDK mesajını 0+ Sonar SSE event'ine çevirir.

    `tool_names` çağıranın tuttuğu tool_use_id -> tool adı defteri; SDK tool-result
    bloğu yalnız id taşır, frontend ad bekler.
    """
    if isinstance(msg, StreamEvent):
        ev = msg.event
        delta = ev.get("delta") or {}
        if ev.get("type") == "content_block_delta" and delta.get("type") == "text_delta":
            text = delta.get("text", "")
            return [(TEXT_DELTA, {"delta": text})] if text else []
        return []
    if isinstance(msg, AssistantMessage):
        # Text zaten StreamEvent'lerden token-token aktı; burada yalnız tool adımları.
        calls = []
        for block in msg.content:
            if isinstance(block, ToolUseBlock):
                name = block.name.split("__")[-1]  # mcp__sonar__get_stock_quote -> get_stock_quote
                tool_names[block.id] = name
                calls.append((TOOL_CALL, {"name": name, "input": block.input}))
        return calls
    if isinstance(msg, UserMessage) and isinstance(msg.content, list):
        return [
            (
                TOOL_RESULT,
                {
                    "name": tool_names.get(block.tool_use_id, ""),
                    "output": _result_text(block.content),
                },
            )
            for block in msg.content
            if isinstance(block, ToolResultBlock)
        ]
    if isinstance(msg, ResultMessage) and msg.is_error:
        return [(ERROR, {"message": msg.result or f"agent hatası ({msg.subtype})"})]
    return []
