import os
import tempfile
import uuid
from urllib.parse import parse_qs, urlparse

# Point the API at a throwaway database and fake OAuth apps before it is imported.
os.environ["WOLF_DATA_DIR"] = tempfile.mkdtemp(prefix="wolf-test-")
os.environ.pop("WOLF_DATABASE_URL", None)
for key in ("GITHUB_CLIENT_ID", "GITHUB_CLIENT_SECRET", "GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET"):
    os.environ[key] = f"test-{key.lower()}"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from wolf_api import auth  # noqa: E402
from wolf_api.main import app  # noqa: E402


def sign_in(client: TestClient, monkeypatch, *, provider="github", uid=None, email=None, name="Ada Lovelace"):
    """Runs the real login + callback routes with the provider's HTTP calls faked out."""
    uid = uid or uuid.uuid4().hex[:10]

    async def fake_fetch_profile(p, code, verifier):
        assert p == provider and code == "the-code" and verifier
        return auth.Profile(provider, uid, name, email, f"https://avatars.example/{uid}.png")

    monkeypatch.setattr(auth, "fetch_profile", fake_fetch_profile)
    start = client.get(f"/api/auth/{provider}/login", params={"next": "/p/abc"}, follow_redirects=False)
    assert start.status_code == 302
    state = parse_qs(urlparse(start.headers["location"]).query)["state"][0]
    done = client.get(f"/api/auth/{provider}/callback", params={"code": "the-code", "state": state}, follow_redirects=False)
    assert done.status_code == 302 and done.headers["location"] == "/p/abc", done.headers
    return done


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def authed(client, monkeypatch):
    sign_in(client, monkeypatch, email=f"{uuid.uuid4().hex[:8]}@example.com")
    return client
