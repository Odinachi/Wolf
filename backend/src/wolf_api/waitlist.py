"""Public endpoint for the pre-launch site: join the waitlist with an email."""

from __future__ import annotations

import re
import time
from collections import defaultdict, deque

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from .db import WaitlistEntry, get_db

router = APIRouter(prefix="/api", tags=["public"])

_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_RATE_LIMIT = 10  # signups per IP per hour
_recent: dict[str, deque[float]] = defaultdict(deque)

ADDED_MESSAGE = "You've been added to the waitlist. We'll email you when your spot opens up."


class WaitlistIn(BaseModel):
    email: str = Field(max_length=320)
    # Honeypot: hidden from people, filled in by bots.
    website: str | None = None

    @field_validator("email")
    @classmethod
    def _email(cls, v: str) -> str:
        v = v.strip().lower()
        if not _EMAIL.match(v):
            raise ValueError("Enter a valid email address.")
        return v


class WaitlistOut(BaseModel):
    message: str


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    return forwarded.split(",")[0].strip() if forwarded else (request.client.host if request.client else "unknown")


@router.post("/waitlist", response_model=WaitlistOut)
def join_waitlist(body: WaitlistIn, request: Request, db: Session = Depends(get_db)) -> WaitlistOut:
    if body.website:  # a bot: pretend it worked
        return WaitlistOut(message=ADDED_MESSAGE)
    now = time.monotonic()
    hits = _recent[_client_ip(request)]
    while hits and now - hits[0] > 3600:
        hits.popleft()
    if len(hits) >= _RATE_LIMIT:
        raise HTTPException(429, "Too many signups from this network. Try again later.")
    hits.append(now)

    if not db.scalar(select(WaitlistEntry).where(WaitlistEntry.email == body.email)):
        db.add(WaitlistEntry(email=body.email))
        db.commit()
    # The same answer whether or not they were already on the list, so the endpoint can't be used
    # to check who signed up.
    return WaitlistOut(message=ADDED_MESSAGE)
