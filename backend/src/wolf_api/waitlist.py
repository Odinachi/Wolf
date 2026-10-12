"""Public endpoints for the pre-launch site: access mode and waitlist signups."""

from __future__ import annotations

import re
import time
from collections import defaultdict, deque

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import config
from .db import WaitlistEntry, get_db

router = APIRouter(prefix="/api", tags=["public"])

_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_RATE_LIMIT = 10  # signups per IP per hour
_recent: dict[str, deque[float]] = defaultdict(deque)


class PublicConfig(BaseModel):
    access_mode: str


@router.get("/config", response_model=PublicConfig)
def public_config() -> PublicConfig:
    return PublicConfig(access_mode="waitlist" if config.ACCESS_MODE == "waitlist" else "open")


class WaitlistIn(BaseModel):
    email: str = Field(max_length=320)
    idea: str | None = Field(None, max_length=2000)
    # Honeypot: hidden from people, filled in by bots.
    website: str | None = None

    @field_validator("email")
    @classmethod
    def _email(cls, v: str) -> str:
        v = v.strip().lower()
        if not _EMAIL.match(v):
            raise ValueError("Enter a valid email address.")
        return v


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    return forwarded.split(",")[0].strip() if forwarded else (request.client.host if request.client else "unknown")


@router.post("/waitlist")
def join_waitlist(body: WaitlistIn, request: Request, db: Session = Depends(get_db)) -> dict[str, bool]:
    if body.website:  # a bot: pretend it worked
        return {"ok": True}
    now = time.monotonic()
    hits = _recent[_client_ip(request)]
    while hits and now - hits[0] > 3600:
        hits.popleft()
    if len(hits) >= _RATE_LIMIT:
        raise HTTPException(429, "Too many signups from this network. Try again later.")
    hits.append(now)

    existing = db.scalar(select(WaitlistEntry).where(WaitlistEntry.email == body.email))
    idea = (body.idea or "").strip() or None
    if existing:
        if idea and not existing.idea:
            existing.idea = idea
            db.commit()
    else:
        db.add(WaitlistEntry(email=body.email, idea=idea))
        db.commit()
    # Same answer either way, so the endpoint can't be used to check who signed up.
    return {"ok": True}
