import uuid

from fastapi.testclient import TestClient

from wolf_api.main import app


def test_signup_login_logout_flow(client):
    email = f"x{uuid.uuid4().hex[:6]}@Example.com"
    r = client.post("/api/auth/signup", json={"name": "Ada", "email": email, "password": "correct horse"})
    assert r.status_code == 200 and r.json()["email"] == email.lower()
    assert client.get("/api/auth/me").json()["name"] == "Ada"
    assert client.post("/api/auth/signup", json={"name": "Ada", "email": email, "password": "correct horse"}).status_code == 409

    client.post("/api/auth/logout")
    assert client.get("/api/auth/me").status_code == 401
    assert client.post("/api/auth/login", json={"email": email, "password": "wrong"}).status_code == 401
    assert client.post("/api/auth/login", json={"email": email, "password": "correct horse"}).status_code == 200
    assert client.get("/api/auth/me").status_code == 200


def test_signup_validation(client):
    assert client.post("/api/auth/signup", json={"name": "A", "email": "nope", "password": "correct horse"}).status_code == 422
    assert client.post("/api/auth/signup", json={"name": "A", "email": "a@b.co", "password": "short"}).status_code == 422


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
        other.post("/api/auth/signup", json={"name": "Eve", "email": f"e{uuid.uuid4().hex[:6]}@x.io", "password": "correct horse"})
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
