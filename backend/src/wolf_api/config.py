import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# The Anthropic client reads ANTHROPIC_API_KEY from the environment itself.
MODEL = os.getenv("WOLF_MODEL", "claude-opus-5-5")
DATA_DIR = Path(os.getenv("WOLF_DATA_DIR", Path(__file__).resolve().parents[2] / "data"))
DATABASE_URL = os.getenv("WOLF_DATABASE_URL", f"sqlite:///{DATA_DIR / 'wolf.db'}")
CORS_ORIGINS = [o.strip() for o in os.getenv("WOLF_CORS_ORIGINS", "http://localhost:5173").split(",") if o.strip()]
COOKIE_SECURE = os.getenv("WOLF_COOKIE_SECURE", "false").lower() == "true"
SESSION_DAYS = int(os.getenv("WOLF_SESSION_DAYS", "30"))
MAX_AGENT_TURNS = int(os.getenv("WOLF_MAX_AGENT_TURNS", "30"))
# The component catalog, exported from web/packages/schema by its tests (see catalog.test.ts).
CATALOG_PATH = Path(__file__).resolve().parent / "agent" / "catalog.json"
