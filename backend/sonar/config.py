import os
from pathlib import Path

DB_PATH = Path(os.environ.get("SONAR_DB", Path.home() / ".sonar" / "sonar.db"))
QUOTE_TTL_SECONDS = 60

# ADR-0002: abonelik OAuth öncelikli. "claude-code" = lokal Claude Code auth'u (key gerekmez);
# "api-key" = SONAR_MODEL + ilgili API key ile LangGraph ReAct yolu.
PROVIDER = os.environ.get("SONAR_PROVIDER", "claude-code")
