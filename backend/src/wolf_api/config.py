import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# The Anthropic client reads ANTHROPIC_API_KEY from the environment itself.
MODEL = os.getenv("WOLF_MODEL", "claude-opus-5-5")
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
# AI requests each user may make per rolling 24 hours (0 = unlimited). Protects your Anthropic bill.
DAILY_GENERATION_LIMIT = int(os.getenv("WOLF_DAILY_GENERATION_LIMIT", "30"))
# The component catalog, exported from web/packages/schema by its tests (see catalog.test.ts).
CATALOG_PATH = Path(__file__).resolve().parent / "agent" / "catalog.json"
