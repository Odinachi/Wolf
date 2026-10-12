"""Sign-in through Firebase Auth, limited to GitHub and Google.

The web app signs in with Firebase and sends the user's ID token as `Authorization: Bearer <token>`.
We verify it with the Firebase Admin SDK on every request, reject any sign-in method other than
GitHub or Google, and keep a local user row (keyed by the Firebase uid) for ownership.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Header, HTTPException
from firebase_admin import auth as firebase_auth
from pydantic import BaseModel
from sqlalchemy.orm import Session

from . import config, firebase
from .db import User, get_db

log = logging.getLogger("wolf.auth")
router = APIRouter(prefix="/api/auth", tags=["auth"])

ALLOWED_PROVIDERS = {"github.com", "google.com"}


def verify_token(token: str) -> dict:
    """Returns the decoded Firebase ID token claims. Raises ValueError if it isn't valid."""
    try:
        return firebase_auth.verify_id_token(token, app=firebase.app())
    except (firebase_auth.InvalidIdTokenError, firebase_auth.ExpiredIdTokenError, firebase_auth.RevokedIdTokenError) as e:
        raise ValueError(str(e)) from None


def current_user(authorization: str | None = Header(default=None), db: Session = Depends(get_db)) -> User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(401, "Sign in to continue.")
    try:
        claims = verify_token(authorization[7:].strip())
    except ValueError:
        raise HTTPException(401, "Your sign-in has expired. Sign in again.") from None
    except RuntimeError as e:  # Firebase isn't configured on this server
        log.error("Auth unavailable: %s", e)
        raise HTTPException(503, "Sign-in isn't set up on this server.") from None

    provider = (claims.get("firebase") or {}).get("sign_in_provider")
    if provider not in ALLOWED_PROVIDERS:
        raise HTTPException(403, "Wolf only supports signing in with GitHub or Google.")

    uid = claims["uid"]
    name = claims.get("name") or (claims.get("email") or "Wolf user").split("@")[0]
    email = claims.get("email") if claims.get("email_verified") else None
    if config.ACCESS_MODE == "waitlist" and (email or "").lower() not in config.ALLOWED_EMAILS:
        raise HTTPException(403, "Wolf is invite-only for now. Join the waitlist and we'll let you know when it's your turn.")

    user = db.get(User, uid)
    if not user:
        user = User(id=uid, name=name[:120], email=email, avatar_url=claims.get("picture"))
        db.add(user)
        db.commit()
    elif (user.name, user.email, user.avatar_url) != (name[:120], email, claims.get("picture")):
        # Keep the profile in step with the provider.
        user.name, user.email, user.avatar_url = name[:120], email, claims.get("picture")
        db.commit()
    return user


class UserOut(BaseModel):
    id: str
    name: str
    email: str | None
    avatar_url: str | None


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(current_user)) -> UserOut:
    return UserOut(id=user.id, name=user.name, email=user.email, avatar_url=user.avatar_url)
