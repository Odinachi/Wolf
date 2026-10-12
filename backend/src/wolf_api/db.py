"""Database models. SQLite by default; any SQLAlchemy URL works via WOLF_DATABASE_URL."""

from __future__ import annotations

import secrets
from datetime import datetime, timezone
from typing import Any, Iterator

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text, UniqueConstraint, create_engine, event, inspect
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship, sessionmaker

from . import config


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def new_id(prefix: str) -> str:
    return f"{prefix}_{secrets.token_urlsafe(12)}"


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: new_id("usr"))
    # A verified email from a provider, used to link GitHub and Google sign-ins to one account.
    email: Mapped[str | None] = mapped_column(String(320), unique=True, index=True, nullable=True)
    name: Mapped[str] = mapped_column(String(120))
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class OAuthAccount(Base):
    """A GitHub or Google identity that signs in as a user."""

    __tablename__ = "oauth_accounts"
    __table_args__ = (UniqueConstraint("provider", "provider_user_id"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: new_id("oac"))
    provider: Mapped[str] = mapped_column(String(16))  # "github" | "google"
    provider_user_id: Mapped[str] = mapped_column(String(64))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AuthSession(Base):
    __tablename__ = "sessions"

    # SHA-256 of the cookie token, so a leaked database doesn't leak live sessions.
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    user: Mapped[User] = relationship()


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: new_id("prj"))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    schema: Mapped[dict[str, Any]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    messages: Mapped[list["Message"]] = relationship(cascade="all, delete-orphan", order_by="Message.created_at")


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: new_id("msg"))
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(16))  # "user" | "assistant"
    content: Mapped[str] = mapped_column(Text)
    # For assistant messages: human-readable list of the changes made.
    changes: Mapped[list[str]] = mapped_column(JSON, default=list)
    # The version saved before this run, so the user can roll back to it.
    version_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Version(Base):
    __tablename__ = "versions"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: new_id("ver"))
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    label: Mapped[str] = mapped_column(String(200))
    schema: Mapped[dict[str, Any]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Build(Base):
    __tablename__ = "builds"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: new_id("bld"))
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    platform: Mapped[str] = mapped_column(String(16))  # "android" | "ios" | "source"
    status: Mapped[str] = mapped_column(String(16), default="queued")  # queued | running | succeeded | failed
    logs: Mapped[str] = mapped_column(Text, default="")
    artifact_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # Anyone with this token can download the artifact (for sharing installs).
    share_token: Mapped[str | None] = mapped_column(String(64), nullable=True, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


config.DATA_DIR.mkdir(parents=True, exist_ok=True)
engine = create_engine(config.DATABASE_URL, connect_args={"check_same_thread": False} if config.DATABASE_URL.startswith("sqlite") else {})

if config.DATABASE_URL.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def _sqlite_pragmas(dbapi_conn, _):  # pragma: no cover - trivial
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA foreign_keys=ON")
        cur.execute("PRAGMA journal_mode=WAL")
        cur.close()

SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def init_db() -> None:
    existing = inspect(engine)
    if existing.has_table("users") and "password_hash" in {c["name"] for c in existing.get_columns("users")}:
        raise RuntimeError(
            "This database predates social sign-in (it still has password accounts). "
            f"Delete {config.DATA_DIR / 'wolf.db'} to start fresh."
        )
    Base.metadata.create_all(engine)


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
