import os
from pathlib import Path


def _load_dotenv(path: Path | None = None) -> None:
    """Repo kökündeki `.env`'i os.environ'a yükler — yalnız EKSİK olanları (gerçek env üstün gelir).

    python-dotenv yok (ponytail): KEY=VALUE · # yorum · tırnak sıyırma yeter. `.env` = kullanıcı
    key'leri (gitignored); kod sabitleri bu dosyada. M6 Settings UI bu .env'i yazacak → format bizde.
    """
    env_path = path or Path(__file__).resolve().parents[2] / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:  # gerçek ortam değişkeni .env'i ezer
            os.environ[key] = value


_load_dotenv()

DB_PATH = Path(os.environ.get("SONAR_DB", Path.home() / ".sonar" / "sonar.db"))
QUOTE_TTL_SECONDS = 60
OHLCV_TTL_SECONDS = 900           # 15 dk (gün-içi bar)
FUNDAMENTALS_TTL_SECONDS = 86400  # 24 sa — çeyreklik veri
NEWS_TTL_SECONDS = 900
MACRO_TTL_SECONDS = 21600         # 6 sa
PEERS_TTL_SECONDS = 86400
HOLDERS_TTL_SECONDS = 86400       # 24 sa — 13F çeyreklik
INSIDERS_TTL_SECONDS = 21600      # 6 sa — Form 4 gün-içi
SHORT_TTL_SECONDS = 43200         # 12 sa — short interest ayda 2x

# Model seçimi model katmanında yaşar (sonar/agent/model.py) — burada kopyalanmaz.
