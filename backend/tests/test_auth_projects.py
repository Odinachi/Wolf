import uuid

from conftest import sign_in
from fastapi.testclient import TestClient

from wolf_api import auth
from wolf_api.main import app


def test_me_creates_and_updates_the_user(client):
    uid = sign_in(client, email="ada@example.com")
    me = client.get("/api/auth/me").json()
    assert me == {"id": uid, "name": "Ada Lovelace", "email": "ada@example.com", "avatar_url": f"https://avatars.example/{uid}.png"}
    sign_in(client, uid=uid, name="Ada King", email="ada@example.com")
    assert client.get("/api/auth/me").json()["name"] == "Ada King"


def test_only_github_and_google_are_accepted(client):
    for provider in ("github.com", "google.com"):
        sign_in(client, provider=provider)
        assert client.get("/api/auth/me").status_code == 200
    for provider in ("password", "anonymous", "phone"):
        sign_in(client, provider=provider)
        assert client.get("/api/auth/me").status_code == 403


def test_unverified_email_is_not_stored(client):
    sign_in(client, email="maybe@example.com", verified=False)
    assert client.get("/api/auth/me").json()["email"] is None


def test_missing_or_invalid_token(client):
    assert client.get("/api/auth/me").status_code == 401
    client.headers["Authorization"] = "Bearer not-a-real-token"
    assert client.get("/api/auth/me").status_code == 401


def test_firebase_not_configured(client, monkeypatch):
    def unconfigured(token):
        raise RuntimeError("Set FIREBASE_PROJECT_ID to enable sign-in.")
    monkeypatch.setattr(auth, "verify_token", unconfigured)
    client.headers["Authorization"] = "Bearer anything"
    assert client.get("/api/auth/me").status_code == 503


def test_projects_require_auth(client):
    assert client.get("/api/projects").status_code == 401
    assert client.post("/api/projects", json={"prompt": "x"}).status_code == 401


def test_project_crud_and_ownership(authed):
    r = authed.post("/api/projects", json={"prompt": "A habit tracker with daily streaks"})
    assert r.status_code == 201
    project = r.json()
    assert project["name"] == "Habit Tracker"
    assert project["schema"]["screens"][0]["name"] == "Home"
    assert project["schema"]["build"]["platforms"] == ["android", "ios"]

    listing = authed.get("/api/projects").json()
    assert listing[0]["id"] == project["id"] and listing[0]["cover"]["screen"]["name"] == "Home"

    schema = project["schema"]
    schema["theme"]["primary"] = "#FF5722"
    assert authed.patch(f"/api/projects/{project['id']}", json={"schema": schema, "name": "Streaks"}).status_code == 200
    again = authed.get(f"/api/projects/{project['id']}").json()
    assert again["name"] == "Streaks" and again["schema"]["theme"]["primary"] == "#FF5722"
    assert authed.patch(f"/api/projects/{project['id']}", json={"schema": {"bad": True}}).status_code == 422

    with TestClient(app) as other:
        sign_in(other, name="Eve")
        assert other.get(f"/api/projects/{project['id']}").status_code == 404

    assert authed.delete(f"/api/projects/{project['id']}").status_code == 204
    assert authed.get(f"/api/projects/{project['id']}").status_code == 404


def test_code_and_source_zip(authed):
    pid = authed.post("/api/projects", json={"name": "Demo"}).json()["id"]
    code = authed.get(f"/api/projects/{pid}/code").json()
    assert "lib/main.dart" in code["files"] and "pubspec.yaml" in code["files"]
    r = authed.get(f"/api/projects/{pid}/source.zip")
    assert r.status_code == 200 and r.headers["content-type"] == "application/zip" and r.content[:2] == b"PK"


def test_source_build_and_share(authed):
    import time
    pid = authed.post("/api/projects", json={"name": "Demo"}).json()["id"]
    build = authed.post(f"/api/projects/{pid}/builds", json={"platform": "source"}).json()
    for _ in range(50):
        build = authed.get(f"/api/builds/{build['id']}").json()
        if build["status"] in ("succeeded", "failed"):
            break
        time.sleep(0.1)
    assert build["status"] == "succeeded", build["logs"]
    shared = authed.post(f"/api/builds/{build['id']}/share").json()
    token = shared["share_token"]
    with TestClient(app) as anon:  # share links work without signing in
        assert anon.get(f"/api/share/{token}").json()["app_name"] == "Demo"
        assert anon.get(f"/api/share/{token}/download").content[:2] == b"PK"
        assert anon.get("/api/share/nope").status_code == 404


def test_backend_test_without_provider(authed):
    pid = authed.post("/api/projects", json={"name": "Demo"}).json()["id"]
    assert authed.post(f"/api/projects/{pid}/backend/test").json()["ok"] is True


def test_deleting_a_project_removes_its_files(authed):
    import time
    from wolf_api.storage import get_storage
    pid = authed.post("/api/projects", json={"name": "Demo"}).json()["id"]
    build = authed.post(f"/api/projects/{pid}/builds", json={"platform": "source"}).json()
    for _ in range(50):
        build = authed.get(f"/api/builds/{build['id']}").json()
        if build["status"] != "queued" and build["status"] != "running":
            break
        time.sleep(0.1)
    key = f"builds/{pid}/{build['id']}/source.zip"
    assert get_storage().local_path(key) is not None
    authed.delete(f"/api/projects/{pid}")
    assert get_storage().local_path(key) is None


def test_local_storage_rejects_path_escape(tmp_path):
    import pytest
    from wolf_api.storage import LocalStorage
    with pytest.raises(ValueError):
        LocalStorage(tmp_path).local_path("../../etc/passwd")


def test_real_firebase_verification_wiring(monkeypatch):
    """Exercises firebase-admin itself (no network: a malformed token fails before key lookup)."""
    import pytest
    from wolf_api import config, firebase
    from conftest import REAL_VERIFY_TOKEN as real_verify

    firebase.app.cache_clear()
    monkeypatch.setattr(config, "FIREBASE_PROJECT_ID", "")
    with pytest.raises(RuntimeError):
        real_verify("x.y.z")

    firebase.app.cache_clear()
    monkeypatch.setattr(config, "FIREBASE_PROJECT_ID", "wolf-test-project")
    with pytest.raises(ValueError):
        real_verify("not-a-jwt")
    firebase.app.cache_clear()
