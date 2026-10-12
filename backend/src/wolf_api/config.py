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

# The public URL of the web app. OAuth providers redirect back to <PUBLIC_URL>/api/auth/<provider>/callback,
# which the web app serves (or proxies to this backend), so the session cookie lands on the web app's origin.
PUBLIC_URL = os.getenv("WOLF_PUBLIC_URL", "http://localhost:5173").rstrip("/")
# Signs short-lived OAuth state cookies. Set it in production; a random key means pending sign-ins
# are lost on restart (finished sign-ins are unaffected).
SECRET_KEY = os.getenv("WOLF_SECRET_KEY") or os.urandom(32).hex()

# Social sign-in. A provider is offered only when both of its values are set.
GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID", "")
GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET", "")
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
SESSION_DAYS = int(os.getenv("WOLF_SESSION_DAYS", "30"))
MAX_AGENT_TURNS = int(os.getenv("WOLF_MAX_AGENT_TURNS", "30"))
# The component catalog, exported from web/packages/schema by its tests (see catalog.test.ts).
CATALOG_PATH = Path(__file__).resolve().parent / "agent" / "catalog.json"
