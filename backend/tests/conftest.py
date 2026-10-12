import os
import tempfile

# Point the API at a throwaway database before it is imported.
os.environ["WOLF_DATA_DIR"] = tempfile.mkdtemp(prefix="wolf-test-")
os.environ.pop("WOLF_DATABASE_URL", None)

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from wolf_api.main import app  # noqa: E402


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def authed(client):
    import uuid
    email = f"u{uuid.uuid4().hex[:8]}@example.com"
    r = client.post("/api/auth/signup", json={"name": "Ada", "email": email, "password": "correct horse"})
    assert r.status_code == 200, r.text
    return client
