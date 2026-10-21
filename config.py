from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent
ENV_FILE = BASE_DIR / ".env"


def _load_env_file(path: Path = ENV_FILE) -> None:
    """Carga un .env sencillo sin depender de python-dotenv."""
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("\"'")
        if key and key not in os.environ:
            os.environ[key] = value


_load_env_file()

AMAZON_TAG = os.getenv("AMAZON_TAG", "")
ALI_APP_KEY = os.getenv("ALI_APP_KEY", "")
ALI_APP_SECRET = os.getenv("ALI_APP_SECRET", "")
ALI_TRACKING_ID = os.getenv("ALI_TRACKING_ID", "")

MAX_PRODUCTS_PER_QUERY = int(os.getenv("MAX_PRODUCTS_PER_QUERY", "3"))
FULL_CATALOG = os.getenv("FULL_CATALOG", "1") not in {"0", "false", "no"}

# Telegram V2. Seguro por defecto: nunca publica hasta poner TELEGRAM_DRY_RUN=0.
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
TELEGRAM_DRY_RUN = os.getenv("TELEGRAM_DRY_RUN", "1") not in {"0", "false", "no"}
MAX_PUBLICATIONS_PER_RUN = int(os.getenv("MAX_PUBLICATIONS_PER_RUN", "6"))
MAX_PUBLICATIONS_PER_DAY = int(os.getenv("MAX_PUBLICATIONS_PER_DAY", "60"))
