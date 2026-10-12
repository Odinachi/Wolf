import os
import tempfile
import uuid

# Point the API at a throwaway database (and local file storage) before it is imported.
os.environ["WOLF_DATA_DIR"] = tempfile.mkdtemp(prefix="wolf-test-")
for key in ("WOLF_DATABASE_URL", "FIREBASE_SERVICE_ACCOUNT", "FIREBASE_STORAGE_BUCKET"):
    os.environ.pop(key, None)

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from wolf_api import auth  # noqa: E402
from wolf_api.main import app  # noqa: E402

REAL_VERIFY_TOKEN = auth.verify_token  # kept for the test that exercises firebase-admin itself

# Fake Firebase ID tokens: "token-<uid>" -> claims registered by sign_in().
_CLAIMS: dict[str, dict] = {}


def _fake_verify(token: str) -> dict:
    if token not in _CLAIMS:
        raise ValueError("invalid token")
    return _CLAIMS[token]


@pytest.fixture(autouse=True)
def fake_firebase(monkeypatch):
    monkeypatch.setattr(auth, "verify_token", _fake_verify)


def sign_in(client: TestClient, *, uid=None, provider="github.com", name="Ada Lovelace", email=None, verified=True):
    """Signs the client in as a Firebase user by sending a (fake) ID token."""
    uid = uid or uuid.uuid4().hex
    token = f"token-{uid}"
    _CLAIMS[token] = {
        "uid": uid, "name": name, "email": email, "email_verified": verified,
        "picture": f"https://avatars.example/{uid}.png", "firebase": {"sign_in_provider": provider},
    }
    client.headers["Authorization"] = f"Bearer {token}"
    return uid


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def authed(client):
    sign_in(client, email=f"{uuid.uuid4().hex[:8]}@example.com")
    return client
