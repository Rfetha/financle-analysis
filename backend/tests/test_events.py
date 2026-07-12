from claude_agent_sdk import (
    AssistantMessage,
    ResultMessage,
    StreamEvent,
    TextBlock,
    ToolResultBlock,
    ToolUseBlock,
    UserMessage,
)
from langchain_core.messages import AIMessageChunk

from sonar.agent import events


def _stream_event(event: dict) -> StreamEvent:
    return StreamEvent(uuid="u1", session_id="s1", event=event)


def test_sse_frame_format():
    frame = events.sse("text-delta", {"delta": "hi"})
    assert frame == 'event: text-delta\ndata: {"delta": "hi"}\n\n'


def test_map_chat_model_stream_yields_text_delta():
    ev = {"event": "on_chat_model_stream", "data": {"chunk": AIMessageChunk(content="AAPL ")}}
    assert events.map_lc_event(ev) == [(events.TEXT_DELTA, {"delta": "AAPL "})]


def test_map_empty_chunk_yields_nothing():
    ev = {"event": "on_chat_model_stream", "data": {"chunk": AIMessageChunk(content="")}}
    assert events.map_lc_event(ev) == []


def test_map_tool_start_and_end():
    start = {"event": "on_tool_start", "name": "get_stock_quote", "data": {"input": {"ticker": "AAPL"}}}
    end = {"event": "on_tool_end", "name": "get_stock_quote", "data": {"output": {"price": "1"}}}
    assert events.map_lc_event(start) == [(events.TOOL_CALL, {"name": "get_stock_quote", "input": {"ticker": "AAPL"}})]
    assert events.map_lc_event(end)[0][0] == events.TOOL_RESULT


def test_map_unrelated_event_ignored():
    assert events.map_lc_event({"event": "on_chain_start", "data": {}}) == []


def test_map_sdk_text_delta():
    msg = _stream_event(
        {"type": "content_block_delta", "delta": {"type": "text_delta", "text": "AAPL "}}
    )
    assert events.map_sdk_message(msg, {}) == [(events.TEXT_DELTA, {"delta": "AAPL "})]


def test_map_sdk_non_text_stream_event_ignored():
    msg = _stream_event({"type": "content_block_start", "content_block": {"type": "tool_use"}})
    assert events.map_sdk_message(msg, {}) == []


def test_map_sdk_tool_use_strips_mcp_prefix_and_records_name():
    names: dict[str, str] = {}
    msg = AssistantMessage(
        content=[
            TextBlock(text="bakıyorum"),
            ToolUseBlock(id="t1", name="mcp__sonar__get_stock_quote", input={"ticker": "AAPL"}),
        ],
        model="claude-sonnet-5",
    )
    assert events.map_sdk_message(msg, names) == [
        (events.TOOL_CALL, {"name": "get_stock_quote", "input": {"ticker": "AAPL"}})
    ]
    assert names == {"t1": "get_stock_quote"}  # tool-result adı buradan gelir


def test_map_sdk_tool_result_uses_recorded_name():
    msg = UserMessage(
        content=[ToolResultBlock(tool_use_id="t1", content=[{"type": "text", "text": '{"p":1}'}])]
    )
    out = events.map_sdk_message(msg, {"t1": "get_stock_quote"})
    assert out == [(events.TOOL_RESULT, {"name": "get_stock_quote", "output": '{"p":1}'})]


def test_map_sdk_error_result_yields_error_event():
    msg = ResultMessage(
        subtype="error_during_execution",
        duration_ms=1,
        duration_api_ms=1,
        is_error=True,
        num_turns=1,
        session_id="s1",
        result="auth yok",
    )
    assert events.map_sdk_message(msg, {}) == [(events.ERROR, {"message": "auth yok"})]


def test_map_sdk_success_result_yields_nothing():
    msg = ResultMessage(
        subtype="success",
        duration_ms=1,
        duration_api_ms=1,
        is_error=False,
        num_turns=1,
        session_id="s1",
        result="ok",
    )
    assert events.map_sdk_message(msg, {}) == []
