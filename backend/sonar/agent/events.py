"""SSE event taksonomisi + LangGraph astream_events -> Sonar event map'i.

Taksonomi tau/AG-UI ile hizalı (ADR-0008): M1 = text-delta · tool-call ·
tool-result · error · done. M2'de quote-tick · chart **eklenir** (yeniden yazma
değil). Frontend part-registry bu tiplerle birebir eşleşir.
"""

import json

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
