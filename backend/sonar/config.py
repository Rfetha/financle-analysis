import os
from pathlib import Path

DB_PATH = Path(os.environ.get("SONAR_DB", Path.home() / ".sonar" / "sonar.db"))
QUOTE_TTL_SECONDS = 60
OHLCV_TTL_SECONDS = 900           # 15 dk (gün-içi bar)
FUNDAMENTALS_TTL_SECONDS = 86400  # 24 sa — çeyreklik veri
NEWS_TTL_SECONDS = 900
MACRO_TTL_SECONDS = 21600         # 6 sa
PEERS_TTL_SECONDS = 86400

# Model seçimi model katmanında yaşar (sonar/agent/model.py) — burada kopyalanmaz.
