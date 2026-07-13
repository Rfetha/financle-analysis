import os
from pathlib import Path

DB_PATH = Path(os.environ.get("SONAR_DB", Path.home() / ".sonar" / "sonar.db"))
QUOTE_TTL_SECONDS = 60

# Model seçimi model katmanında yaşar (sonar/agent/model.py) — burada kopyalanmaz.
