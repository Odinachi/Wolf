import uuid
from urllib.parse import parse_qs, urlparse

from conftest import sign_in
from fastapi.testclient import TestClient

from wolf_api.main import app


def test_providers_lists_configured_ones(client):
    assert client.get("/api/auth/providers").json() == {"providers": ["github", "google"]}


def test_login_redirects_to_provider(client):
    r = client.get("/api/auth/google/login", params={"next": "https://evil.example"}, follow_redirects=False)
    assert r.status_code == 302
    url = urlparse(r.headers["location"])
    q = parse_qs(url.query)
    assert url.netloc == "accounts.google.com"
    assert q["redirect_uri"] == ["http://localhost:5173/api/auth/google/callback"]
    assert q["code_challenge_method"] == ["S256"] and q["state"]
    assert "wolf_oauth" in r.cookies
    gh = client.get("/api/auth/github/login", follow_redirects=False)
    assert urlparse(gh.headers["location"]).netloc == "github.com"
    assert client.get("/api/auth/twitter/login", follow_redirects=False).status_code == 404


def test_sign_in_sign_out(client, monkeypatch):
    sign_in(client, monkeypatch, email="ada@example.com")
    me = client.get("/api/auth/me").json()
    assert me["name"] == "Ada Lovelace" and me["email"] == "ada@example.com" and me["avatar_url"]
    client.post("/api/auth/logout")
    assert client.get("/api/auth/me").status_code == 401


def test_rejects_bad_or_missing_state(client, monkeypatch):
    client.get("/api/auth/github/login", follow_redirects=False)
    r = client.get("/api/auth/github/callback", params={"code": "the-code", "state": "forged"}, follow_redirects=False)
    assert r.status_code == 302 and r.headers["location"].startswith("/?auth_error=")
    assert client.get("/api/auth/me").status_code == 401

    with TestClient(app) as fresh:  # no state cookie at all
        r = fresh.get("/api/auth/github/callback", params={"code": "x", "state": "y"}, follow_redirects=False)
        assert "auth_error" in r.headers["location"]

    cancelled = client.get("/api/auth/github/callback", params={"error": "access_denied"}, follow_redirects=False)
    assert "cancelled" in cancelled.headers["location"]


def test_open_redirects_are_blocked(client, monkeypatch):
    from wolf_api.auth import safe_next
    assert safe_next("https://evil.example") == "/"
    assert safe_next("//evil.example") == "/"
    assert safe_next("/\\evil.example") == "/"
    assert safe_next("/p/123") == "/p/123"


def test_github_and_google_link_by_verified_email(monkeypatch):
    email = f"{uuid.uuid4().hex[:8]}@example.com"
    with TestClient(app) as a:
        sign_in(a, monkeypatch, provider="github", email=email)
        first = a.get("/api/auth/me").json()
    with TestClient(app) as b:
        sign_in(b, monkeypatch, provider="google", email=email)
        assert b.get("/api/auth/me").json()["id"] == first["id"]
    # No verified email: never linked, always a separate account.
    with TestClient(app) as c:
        sign_in(c, monkeypatch, provider="google", email=None)
        assert c.get("/api/auth/me").json()["id"] != first["id"]


def test_same_identity_returns_same_user(monkeypatch):
    with TestClient(app) as a:
        sign_in(a, monkeypatch, uid="gh-42")
        first = a.get("/api/auth/me").json()["id"]
    with TestClient(app) as b:
        sign_in(b, monkeypatch, uid="gh-42")
        assert b.get("/api/auth/me").json()["id"] == first


def test_projects_require_auth(client):
    assert client.get("/api/projects").status_code == 401
    assert client.post("/api/projects", json={"prompt": "x"}).status_code == 401


def test_project_crud_and_ownership(authed, monkeypatch):
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
        sign_in(other, monkeypatch, name="Eve")
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
    with TestClient(app) as anon:
        assert anon.get(f"/api/share/{token}").json()["app_name"] == "Demo"
        assert anon.get(f"/api/share/{token}/download").content[:2] == b"PK"
        assert anon.get("/api/share/nope").status_code == 404


def test_backend_test_without_provider(authed):
    pid = authed.post("/api/projects", json={"name": "Demo"}).json()["id"]
    assert authed.post(f"/api/projects/{pid}/backend/test").json()["ok"] is True
