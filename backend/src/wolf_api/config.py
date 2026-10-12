import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# The AI runs through OpenRouter (https://openrouter.ai). Any tool-capable model id works.
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
MODEL = os.getenv("WOLF_MODEL", "anthropic/claude-haiku-5.5")
# Send a reasoning effort to models that support it (WOLF_REASONING=off to never send it).
REASONING = os.getenv("WOLF_REASONING", "on").strip().lower() != "off"
# Shown to OpenRouter for app attribution (optional).
SITE_URL = os.getenv("WOLF_SITE_URL", "https://github.com/Odinachi/Wolf")
DATA_DIR = Path(os.getenv("WOLF_DATA_DIR", Path(__file__).resolve().parents[2] / "data"))
DATABASE_URL = os.getenv("WOLF_DATABASE_URL", f"sqlite:///{DATA_DIR / 'wolf.db'}")
CORS_ORIGINS = [o.strip() for o in os.getenv("WOLF_CORS_ORIGINS", "http://localhost:5173").split(",") if o.strip()]

# Firebase: sign-in (GitHub and Google via Firebase Auth) and file storage (Firebase Storage).
# The project id is enough to verify sign-ins. Storage also needs a service account: paste its JSON
# (or base64 of it) into FIREBASE_SERVICE_ACCOUNT. Without storage config, files stay in DATA_DIR.
FIREBASE_PROJECT_ID = os.getenv("FIREBASE_PROJECT_ID", "")
FIREBASE_SERVICE_ACCOUNT = os.getenv("FIREBASE_SERVICE_ACCOUNT", "")
FIREBASE_STORAGE_BUCKET = os.getenv("FIREBASE_STORAGE_BUCKET", "")
MAX_AGENT_TURNS = int(os.getenv("WOLF_MAX_AGENT_TURNS", "30"))
# Projects whose full snapshot is larger than this (characters) are sent as an outline; the agent
# fetches a screen's props and styles with get_screen when it needs them.
SNAPSHOT_BUDGET_CHARS = int(os.getenv("WOLF_SNAPSHOT_BUDGET_CHARS", "12000"))

# "open": anyone can sign in. "waitlist": the site collects waitlist signups and only the verified
# emails in WOLF_ALLOWED_EMAILS can sign in (set this in production until launch).
ACCESS_MODE = os.getenv("WOLF_ACCESS_MODE", "open").strip().lower()
ALLOWED_EMAILS = {e.strip().lower() for e in os.getenv("WOLF_ALLOWED_EMAILS", "").split(",") if e.strip()}
# AI requests each user may make per rolling 24 hours (0 = unlimited). Protects your AI bill.
DAILY_GENERATION_LIMIT = int(os.getenv("WOLF_DAILY_GENERATION_LIMIT", "30"))
# The component catalog, exported from web/packages/schema by its tests (see catalog.test.ts).
CATALOG_PATH = Path(__file__).resolve().parent / "agent" / "catalog.json"
