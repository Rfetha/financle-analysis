"""Tek swappable AI provider (ADR-0002) — M1'de yalnız API-key yolu.

Provider/model env ile seçilir (`SONAR_MODEL`, ör. "anthropic:claude-sonnet-5"
ya da "openai:gpt-4o"). Settings UI + OAuth/MCP yolları M6.
"""

import os

from langchain.chat_models import init_chat_model

DEFAULT_MODEL = "anthropic:claude-sonnet-5"


def default_model():
    # ponytail: env-driven provider (ADR-0002 API-key yolu). Provider paketi kurulu +
    # ilgili API key ortamda olmalı; yoksa ilk çağrıda hata → SSE error event'i.
    return init_chat_model(os.environ.get("SONAR_MODEL", DEFAULT_MODEL))
