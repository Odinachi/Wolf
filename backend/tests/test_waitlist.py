from conftest import sign_in

from wolf_api import config, waitlist
from wolf_api.db import SessionLocal, WaitlistEntry


def test_join_waitlist_stores_email_and_confirms(client):
    waitlist._recent.clear()
    r = client.post("/api/waitlist", json={"email": "Fan@Example.com"})
    assert r.status_code == 200
    assert r.json() == {"message": "You've been added to the waitlist. We'll email you when your spot opens up."}
    # Joining again gives the same answer and doesn't duplicate the entry.
    assert client.post("/api/waitlist", json={"email": "fan@example.com"}).json() == r.json()
    with SessionLocal() as db:
        assert db.query(WaitlistEntry).filter_by(email="fan@example.com").count() == 1


def test_waitlist_validation_honeypot_and_rate_limit(client):
    waitlist._recent.clear()
    assert client.post("/api/waitlist", json={"email": "nope"}).status_code == 422
    assert client.post("/api/waitlist", json={}).status_code == 422
    assert client.post("/api/waitlist", json={"email": "bot@example.com", "website": "spam"}).status_code == 200
    with SessionLocal() as db:
        assert db.query(WaitlistEntry).filter_by(email="bot@example.com").count() == 0
    for i in range(10):
        assert client.post("/api/waitlist", json={"email": f"p{i}@example.com"}).status_code == 200
    assert client.post("/api/waitlist", json={"email": "late@example.com"}).status_code == 429


def test_waitlist_mode_blocks_everyone_but_allowed_emails(client, monkeypatch):
    monkeypatch.setattr(config, "ACCESS_MODE", "waitlist")
    monkeypatch.setattr(config, "ALLOWED_EMAILS", {"founder@example.com"})
    sign_in(client, email="random@example.com")
    r = client.get("/api/auth/me")
    assert r.status_code == 403 and "waitlist" in r.json()["detail"]
    sign_in(client, email="founder@example.com", verified=False)  # unverified emails don't count
    assert client.get("/api/auth/me").status_code == 403
    sign_in(client, email="Founder@Example.com")
    assert client.get("/api/auth/me").status_code == 200
