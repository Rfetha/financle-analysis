"""Model katmanı (ADR-0002): env → chat model. Agent katmanı buradan habersizdir.

`SONAR_MODEL` = "<provider>:<model>", varsayılan `local:qwen3-14b` (llama-server):

    local:qwen3-14b                          key yok            http://localhost:8080/v1
    openrouter:anthropic/claude-sonnet-4.6   OPENROUTER_API_KEY
    anthropic:claude-sonnet-5                ANTHROPIC_API_KEY
    openai:gpt-5                             OPENAI_API_KEY

`SONAR_BASE_URL` OpenAI-uyumlu endpoint'i override eder (Ollama, LM Studio, gateway).
Local ve OpenRouter aynı istemciden geçer — fark yalnız base_url.
"""

import os

from langchain.chat_models import init_chat_model
from langchain_openai import ChatOpenAI

DEFAULT_MODEL = "local:qwen3-14b"
LOCAL_BASE_URL = "http://localhost:8080/v1"  # llama-server
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


def default_model():
    provider, _, name = os.environ.get("SONAR_MODEL", DEFAULT_MODEL).partition(":")
    override = os.environ.get("SONAR_BASE_URL")

    if provider == "local":
        # llama-server key istemez; OpenAI istemcisi boş bırakmaz → placeholder.
        return ChatOpenAI(model=name, base_url=override or LOCAL_BASE_URL, api_key="local")

    if provider == "openrouter":
        key = os.environ.get("OPENROUTER_API_KEY")
        if not key:
            raise RuntimeError("OPENROUTER_API_KEY yok — key ver ya da SONAR_MODEL=local:... kullan")
        return ChatOpenAI(model=name, base_url=override or OPENROUTER_BASE_URL, api_key=key)

    # Doğrudan sağlayıcılar (anthropic/openai/...): key ortamda yoksa burada patlar → SSE error.
    return init_chat_model(f"{provider}:{name}")
