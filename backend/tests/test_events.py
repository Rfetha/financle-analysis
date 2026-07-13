from langchain_core.messages import AIMessageChunk

from sonar.agent import events


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
