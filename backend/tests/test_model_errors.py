import httpx
from openai import APIConnectionError

from sonar.agent.model import explain


def _conn_error() -> APIConnectionError:
    return APIConnectionError(request=httpx.Request("POST", "http://localhost:8080/v1/chat/completions"))


def test_local_server_down_explains_how_to_start_it(monkeypatch):
    monkeypatch.delenv("SONAR_MODEL", raising=False)  # varsayılan: local

    message = explain(_conn_error())

    assert "llama-server" in message
    assert "SONAR_MODEL=openrouter:" in message  # kaçış kapısı da söylenir


def test_cloud_provider_connection_error_does_not_mention_llama_server(monkeypatch):
    monkeypatch.setenv("SONAR_MODEL", "openrouter:anthropic/claude-sonnet-4.6")

    message = explain(_conn_error())

    assert "llama-server" not in message


def test_other_errors_pass_through(monkeypatch):
    monkeypatch.delenv("SONAR_MODEL", raising=False)

    assert explain(RuntimeError("OPENROUTER_API_KEY yok")) == "OPENROUTER_API_KEY yok"
