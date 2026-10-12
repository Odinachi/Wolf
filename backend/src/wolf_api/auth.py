"""Social sign-in (GitHub and Google only) with server-side sessions in an httpOnly cookie.

Flow: /api/auth/<provider>/login redirects to the provider with a signed state cookie; the provider
redirects back to /api/auth/<provider>/callback, where we verify the state, exchange the code for a
profile, find or create the user, start a session and redirect into the web app.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Literal
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import config
from .db import AuthSession, OAuthAccount, User, get_db, utcnow

SESSION_COOKIE = "wolf_session"
STATE_COOKIE = "wolf_oauth"
STATE_MAX_AGE = 600  # seconds to finish signing in at the provider

Provider = Literal["github", "google"]
router = APIRouter(prefix="/api/auth", tags=["auth"])


# ─── Providers ───────────────────────────────────────────────────────────────


def configured_providers() -> list[str]:
    out = []
    if config.GITHUB_CLIENT_ID and config.GITHUB_CLIENT_SECRET:
        out.append("github")
    if config.GOOGLE_CLIENT_ID and config.GOOGLE_CLIENT_SECRET:
        out.append("google")
    return out


def redirect_uri(provider: str) -> str:
    return f"{config.PUBLIC_URL}/api/auth/{provider}/callback"


def authorize_url(provider: str, state: str, verifier: str) -> str:
    if provider == "github":
        return "https://github.com/login/oauth/authorize?" + urlencode({
            "client_id": config.GITHUB_CLIENT_ID,
            "redirect_uri": redirect_uri(provider),
            "scope": "read:user user:email",
            "state": state,
            "allow_signup": "true",
        })
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    return "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode({
        "client_id": config.GOOGLE_CLIENT_ID,
        "redirect_uri": redirect_uri(provider),
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
        "prompt": "select_account",
    })


@dataclass
class Profile:
    provider: str
    provider_user_id: str
    name: str
    email: str | None  # only if the provider says it's verified
    avatar_url: str | None


class OAuthError(Exception):
    """Sign-in failed at the provider; the message is shown to the user."""


async def fetch_profile(provider: str, code: str, verifier: str) -> Profile:
    """Exchanges the authorization code and reads the user's profile from the provider."""
    async with httpx.AsyncClient(timeout=15) as client:
        if provider == "github":
            token = await client.post(
                "https://github.com/login/oauth/access_token",
                headers={"Accept": "application/json"},
                data={"client_id": config.GITHUB_CLIENT_ID, "client_secret": config.GITHUB_CLIENT_SECRET,
                      "code": code, "redirect_uri": redirect_uri(provider)},
            )
            access = token.json().get("access_token")
            if not access:
                raise OAuthError("GitHub didn't accept the sign-in. Try again.")
            headers = {"Authorization": f"Bearer {access}", "Accept": "application/vnd.github+json"}
            user = (await client.get("https://api.github.com/user", headers=headers)).json()
            emails = (await client.get("https://api.github.com/user/emails", headers=headers)).json()
            verified = next((e["email"] for e in emails if isinstance(e, dict) and e.get("primary") and e.get("verified")), None)
            return Profile("github", str(user["id"]), user.get("name") or user.get("login") or "GitHub user", verified, user.get("avatar_url"))

        token = await client.post(
            "https://oauth2.googleapis.com/token",
            data={"code": code, "client_id": config.GOOGLE_CLIENT_ID, "client_secret": config.GOOGLE_CLIENT_SECRET,
                  "redirect_uri": redirect_uri(provider), "grant_type": "authorization_code", "code_verifier": verifier},
        )
        access = token.json().get("access_token")
        if not access:
            raise OAuthError("Google didn't accept the sign-in. Try again.")
        info = (await client.get("https://openidconnect.googleapis.com/v1/userinfo", headers={"Authorization": f"Bearer {access}"})).json()
        email = info.get("email") if info.get("email_verified") else None
        return Profile("google", str(info["sub"]), info.get("name") or (email or "Google user").split("@")[0], email, info.get("picture"))


# ─── Signed state cookie ─────────────────────────────────────────────────────


def _sign(payload: dict) -> str:
    body = base64.urlsafe_b64encode(json.dumps(payload, separators=(",", ":")).encode()).decode()
    sig = hmac.new(config.SECRET_KEY.encode(), body.encode(), hashlib.sha256).hexdigest()
    return f"{body}.{sig}"


def _unsign(value: str | None) -> dict | None:
    if not value or "." not in value:
        return None
    body, sig = value.rsplit(".", 1)
    expected = hmac.new(config.SECRET_KEY.encode(), body.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(sig, expected):
        return None
    try:
        payload = json.loads(base64.urlsafe_b64decode(body))
    except ValueError:
        return None
    return payload if payload.get("exp", 0) > time.time() else None


def safe_next(value: str | None) -> str:
    """Only allow redirects to paths in this app (no open redirects)."""
    if not value or not value.startswith("/") or value.startswith("//") or "\\" in value:
        return "/"
    return value


# ─── Sessions ────────────────────────────────────────────────────────────────


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _start_session(db: Session, user: User, response: Response) -> None:
    token = secrets.token_urlsafe(32)
    db.add(AuthSession(token_hash=_token_hash(token), user_id=user.id, expires_at=utcnow() + timedelta(days=config.SESSION_DAYS)))
    db.commit()
    response.set_cookie(SESSION_COOKIE, token, max_age=config.SESSION_DAYS * 86400, httponly=True, samesite="lax", secure=config.COOKIE_SECURE, path="/")


def current_user(wolf_session: str | None = Cookie(default=None), db: Session = Depends(get_db)) -> User:
    if not wolf_session:
        raise HTTPException(401, "Sign in to continue.")
    session = db.get(AuthSession, _token_hash(wolf_session))
    expires = session.expires_at if session else None
    if expires and expires.tzinfo is None:  # SQLite drops tzinfo
        expires = expires.replace(tzinfo=timezone.utc)
    if not session or not expires or expires < datetime.now(timezone.utc):
        raise HTTPException(401, "Your session has expired. Sign in again.")
    return session.user


def upsert_user(db: Session, profile: Profile) -> User:
    """Finds the user for this identity, linking by verified email, or creates one."""
    account = db.scalar(select(OAuthAccount).where(OAuthAccount.provider == profile.provider, OAuthAccount.provider_user_id == profile.provider_user_id))
    if account:
        user = db.get(User, account.user_id)
    else:
        user = db.scalar(select(User).where(User.email == profile.email)) if profile.email else None
        if not user:
            user = User(name=profile.name[:120], email=profile.email, avatar_url=profile.avatar_url)
            db.add(user)
            db.flush()
        db.add(OAuthAccount(provider=profile.provider, provider_user_id=profile.provider_user_id, user_id=user.id))
    if user.email is None and profile.email and not db.scalar(select(User).where(User.email == profile.email)):
        user.email = profile.email
    if profile.avatar_url and not user.avatar_url:
        user.avatar_url = profile.avatar_url
    db.commit()
    return user


# ─── Routes ──────────────────────────────────────────────────────────────────


class UserOut(BaseModel):
    id: str
    name: str
    email: str | None
    avatar_url: str | None


def _out(user: User) -> UserOut:
    return UserOut(id=user.id, name=user.name, email=user.email, avatar_url=user.avatar_url)


@router.get("/providers")
def providers() -> dict[str, list[str]]:
    return {"providers": configured_providers()}


def _check(provider: str) -> None:
    if provider not in ("github", "google"):
        raise HTTPException(404, "Unknown sign-in provider.")
    if provider not in configured_providers():
        raise HTTPException(404, f"Sign-in with {provider.capitalize()} isn't set up on this server.")


@router.get("/{provider}/login")
def login(provider: str, next: str | None = None) -> RedirectResponse:
    _check(provider)
    state, verifier = secrets.token_urlsafe(24), secrets.token_urlsafe(48)
    response = RedirectResponse(authorize_url(provider, state, verifier), status_code=302)
    payload = {"s": state, "v": verifier, "p": provider, "n": safe_next(next), "exp": int(time.time()) + STATE_MAX_AGE}
    response.set_cookie(STATE_COOKIE, _sign(payload), max_age=STATE_MAX_AGE, httponly=True, samesite="lax", secure=config.COOKIE_SECURE, path="/api/auth")
    return response


def _back_with_error(message: str) -> RedirectResponse:
    response = RedirectResponse("/?" + urlencode({"auth_error": message}), status_code=302)
    response.delete_cookie(STATE_COOKIE, path="/api/auth")
    return response


@router.get("/{provider}/callback")
async def callback(provider: str, request: Request, db: Session = Depends(get_db)) -> RedirectResponse:
    _check(provider)
    params = request.query_params
    pending = _unsign(request.cookies.get(STATE_COOKIE))
    if params.get("error"):
        return _back_with_error("Sign-in was cancelled.")
    if not pending or pending.get("p") != provider or not hmac.compare_digest(pending.get("s", ""), params.get("state", "")):
        return _back_with_error("Your sign-in link expired. Please try again.")
    if not params.get("code"):
        return _back_with_error("Sign-in didn't complete. Please try again.")
    try:
        profile = await fetch_profile(provider, params["code"], pending["v"])
    except (OAuthError, httpx.HTTPError, KeyError, ValueError) as e:
        return _back_with_error(str(e) if isinstance(e, OAuthError) else f"Couldn't reach {provider.capitalize()}. Please try again.")

    user = upsert_user(db, profile)
    response = RedirectResponse(safe_next(pending.get("n")), status_code=302)
    response.delete_cookie(STATE_COOKIE, path="/api/auth")
    _start_session(db, user, response)
    return response


@router.post("/logout", status_code=204)
def logout(response: Response, wolf_session: str | None = Cookie(default=None), db: Session = Depends(get_db)) -> None:
    if wolf_session:
        session = db.get(AuthSession, _token_hash(wolf_session))
        if session:
            db.delete(session)
            db.commit()
    response.delete_cookie(SESSION_COOKIE, path="/")


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(current_user)) -> UserOut:
    return _out(user)
