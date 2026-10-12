"""Email + password accounts with server-side sessions in an httpOnly cookie."""

from __future__ import annotations

import hashlib
import hmac
import re
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import config
from .db import AuthSession, User, get_db, utcnow

COOKIE = "wolf_session"
router = APIRouter(prefix="/api/auth", tags=["auth"])

_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_SCRYPT = {"n": 2**14, "r": 8, "p": 1}


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, **_SCRYPT)
    return f"scrypt${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _, salt_hex, digest_hex = stored.split("$")
    except ValueError:
        return False
    digest = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt_hex), **_SCRYPT)
    return hmac.compare_digest(digest.hex(), digest_hex)


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _start_session(db: Session, user: User, response: Response) -> None:
    token = secrets.token_urlsafe(32)
    db.add(AuthSession(token_hash=_token_hash(token), user_id=user.id, expires_at=utcnow() + timedelta(days=config.SESSION_DAYS)))
    db.commit()
    response.set_cookie(
        COOKIE, token, max_age=config.SESSION_DAYS * 86400, httponly=True, samesite="lax", secure=config.COOKIE_SECURE, path="/",
    )


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


class UserOut(BaseModel):
    id: str
    email: str
    name: str


class SignupIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: str = Field(max_length=320)
    password: str = Field(min_length=8, max_length=200)

    @field_validator("email")
    @classmethod
    def _email(cls, v: str) -> str:
        v = v.strip().lower()
        if not _EMAIL.match(v):
            raise ValueError("Enter a valid email address.")
        return v


class LoginIn(BaseModel):
    email: str
    password: str


def _out(user: User) -> UserOut:
    return UserOut(id=user.id, email=user.email, name=user.name)


@router.post("/signup", response_model=UserOut)
def signup(body: SignupIn, response: Response, db: Session = Depends(get_db)) -> UserOut:
    if db.scalar(select(User).where(User.email == body.email)):
        raise HTTPException(409, "An account with this email already exists. Sign in instead.")
    user = User(email=body.email, name=body.name.strip(), password_hash=hash_password(body.password))
    db.add(user)
    db.commit()
    _start_session(db, user, response)
    return _out(user)


@router.post("/login", response_model=UserOut)
def login(body: LoginIn, response: Response, db: Session = Depends(get_db)) -> UserOut:
    user = db.scalar(select(User).where(User.email == body.email.strip().lower()))
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(401, "Wrong email or password.")
    _start_session(db, user, response)
    return _out(user)


@router.post("/logout", status_code=204)
def logout(response: Response, wolf_session: str | None = Cookie(default=None), db: Session = Depends(get_db)) -> None:
    if wolf_session:
        session = db.get(AuthSession, _token_hash(wolf_session))
        if session:
            db.delete(session)
            db.commit()
    response.delete_cookie(COOKIE, path="/")


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(current_user)) -> UserOut:
    return _out(user)
