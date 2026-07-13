import os
from pathlib import Path

DB_PATH = Path(os.environ.get("SONAR_DB", Path.home() / ".sonar" / "sonar.db"))
QUOTE_TTL_SECONDS = 60

# Model seçimi model katmanında (sonar/agent/model.py); burada yalnız log/settings için görünür.
MODEL = os.environ.get("SONAR_MODEL", "local:qwen3-14b")
