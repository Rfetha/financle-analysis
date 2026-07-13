import pytest

from sonar.agent.model import default_model


def test_default_model_points_at_local_llama_server(monkeypatch):
    monkeypatch.delenv("SONAR_MODEL", raising=False)
    monkeypatch.delenv("SONAR_BASE_URL", raising=False)

    model = default_model()

    assert "localhost:8080" in str(model.openai_api_base)


def test_openrouter_model_points_at_openrouter_with_its_key(monkeypatch):
    monkeypatch.setenv("SONAR_MODEL", "openrouter:anthropic/claude-sonnet-4.6")
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-test")

    model = default_model()

    assert "openrouter.ai" in str(model.openai_api_base)
    assert model.model_name == "anthropic/claude-sonnet-4.6"


def test_base_url_override_wins_for_other_openai_compatible_servers(monkeypatch):
    monkeypatch.setenv("SONAR_MODEL", "local:qwen3:14b")
    monkeypatch.setenv("SONAR_BASE_URL", "http://localhost:11434/v1")  # ollama

    model = default_model()

    assert "11434" in str(model.openai_api_base)
    assert model.model_name == "qwen3:14b"


def test_openrouter_without_key_fails_loudly(monkeypatch):
    monkeypatch.setenv("SONAR_MODEL", "openrouter:anthropic/claude-sonnet-4.6")
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)

    with pytest.raises(RuntimeError, match="OPENROUTER_API_KEY"):
        default_model()


def test_direct_api_key_provider_still_supported(monkeypatch):
    monkeypatch.setenv("SONAR_MODEL", "anthropic:claude-sonnet-5")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")

    model = default_model()

    assert type(model).__name__ == "ChatAnthropic"
