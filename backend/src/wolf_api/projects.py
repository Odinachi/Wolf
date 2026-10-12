"""Projects: CRUD, the AI chat stream, versions, generated code and backend checks."""

from __future__ import annotations

import io
import json
import logging
import zipfile
from datetime import datetime, timedelta
from typing import Any, AsyncIterator, Literal

import httpx
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from wolf_flutter import generate_project

from . import config
from .agent.runner import run_agent
from .auth import current_user
from .db import Build, Message, Project, SessionLocal, User, Version, get_db, utcnow
from .schema import SchemaShape, blank_schema, name_from_prompt

log = logging.getLogger("wolf.projects")
router = APIRouter(prefix="/api/projects", tags=["projects"])

# Projects with an AI run in progress (single-process; use a shared lock if you run several workers).
_running: set[str] = set()


def owned(project_id: str, user: User, db: Session) -> Project:
    project = db.get(Project, project_id)
    if not project or project.user_id != user.id:
        raise HTTPException(404, "Project not found.")
    return project


# ─── Shapes ──────────────────────────────────────────────────────────────────


class MessageOut(BaseModel):
    id: str
    role: str
    content: str
    changes: list[str]
    version_id: str | None
    created_at: datetime


class ProjectSummary(BaseModel):
    id: str
    name: str
    updated_at: datetime
    # Enough to draw a thumbnail of the first screen.
    cover: dict[str, Any]


class ProjectOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    name: str
    schema_: dict[str, Any] = Field(alias="schema")
    messages: list[MessageOut]
    created_at: datetime
    updated_at: datetime
    generating: bool


class CreateIn(BaseModel):
    prompt: str | None = Field(None, max_length=8000)
    name: str | None = Field(None, max_length=120)


class PatchIn(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=120)
    schema_: dict[str, Any] | None = Field(None, alias="schema")


class ChatIn(BaseModel):
    prompt: str = Field(min_length=1, max_length=8000)
    selection: dict[str, str | None] | None = None


def _summary(p: Project) -> ProjectSummary:
    schema = p.schema
    nav = schema.get("navigation", {})
    screens = schema.get("screens", [])
    first = next((s for s in screens if s["id"] == nav.get("initialScreenId")), screens[0] if screens else None)
    return ProjectSummary(id=p.id, name=p.name, updated_at=p.updated_at, cover={"theme": schema.get("theme"), "screen": first})


def _out(p: Project) -> ProjectOut:
    return ProjectOut(
        id=p.id, name=p.name, schema=p.schema, created_at=p.created_at, updated_at=p.updated_at, generating=p.id in _running,
        messages=[MessageOut(id=m.id, role=m.role, content=m.content, changes=m.changes or [], version_id=m.version_id, created_at=m.created_at) for m in p.messages],
    )


# ─── CRUD ────────────────────────────────────────────────────────────────────


@router.get("", response_model=list[ProjectSummary])
def list_projects(user: User = Depends(current_user), db: Session = Depends(get_db)):
    rows = db.scalars(select(Project).where(Project.user_id == user.id).order_by(Project.updated_at.desc())).all()
    return [_summary(p) for p in rows]


@router.post("", response_model=ProjectOut, response_model_by_alias=True, status_code=201)
def create_project(body: CreateIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    name = (body.name or "").strip() or (name_from_prompt(body.prompt) if body.prompt else "Untitled App")
    project = Project(user_id=user.id, name=name, schema=blank_schema(name, body.prompt or ""))
    db.add(project)
    db.commit()
    db.refresh(project)
    return _out(project)


@router.get("/{project_id}", response_model=ProjectOut, response_model_by_alias=True)
def get_project(project_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    return _out(owned(project_id, user, db))


@router.patch("/{project_id}", response_model=ProjectSummary)
def patch_project(project_id: str, body: PatchIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    project = owned(project_id, user, db)
    if project_id in _running and body.schema_ is not None:
        raise HTTPException(409, "The AI is editing this project. Wait for it to finish.")
    if body.schema_ is not None:
        try:
            SchemaShape.model_validate(body.schema_)
        except ValidationError as e:
            raise HTTPException(422, f"Invalid schema: {e.errors()[0]['msg']}") from None
        project.schema = body.schema_
    if body.name:
        project.name = body.name.strip()
        project.schema = {**project.schema, "name": project.name}
    db.commit()
    return _summary(project)


@router.delete("/{project_id}", status_code=204)
def delete_project(project_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    from .storage import get_storage

    project = owned(project_id, user, db)
    keys = [b.artifact_key for b in db.scalars(select(Build).where(Build.project_id == project_id)) if b.artifact_key]
    db.delete(project)
    db.commit()
    for key in keys:  # best effort: don't fail the delete over a missing file
        try:
            get_storage().delete(key)
        except Exception:
            log.warning("Couldn't delete stored file %s", key, exc_info=True)


# ─── AI chat ─────────────────────────────────────────────────────────────────


def _sse(event: str, data: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, default=str)}\n\n"


def check_daily_limit(user: User, db: Session) -> None:
    limit = config.DAILY_GENERATION_LIMIT
    if limit <= 0:
        return
    since = utcnow() - timedelta(hours=24)
    used = db.scalar(
        select(func.count(Message.id))
        .join(Project, Project.id == Message.project_id)
        .where(Project.user_id == user.id, Message.role == "user", Message.created_at >= since)
    ) or 0
    if used >= limit:
        raise HTTPException(429, f"You've reached today's limit of {limit} AI requests. It resets over the next 24 hours.")


@router.post("/{project_id}/chat")
async def chat(project_id: str, body: ChatIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    project = owned(project_id, user, db)
    if project_id in _running:
        raise HTTPException(409, "The AI is already working on this project.")
    check_daily_limit(user, db)
    history = [{"role": m.role, "content": m.content} for m in project.messages][-20:]

    version = Version(project_id=project.id, label=body.prompt[:200], schema=project.schema)
    user_msg = Message(project_id=project.id, role="user", content=body.prompt)
    db.add_all([version, user_msg])
    db.commit()
    schema = project.schema
    _running.add(project_id)

    async def stream() -> AsyncIterator[str]:
        # The request's DB session closes once the response starts, so the stream uses its own.
        session = SessionLocal()
        text, changes, error = "", [], None
        try:
            yield _sse("start", {"user_message_id": user_msg.id, "version_id": version.id})
            async for e in run_agent(prompt=body.prompt, schema=schema, history=history, selection=body.selection):
                kind, data = e["event"], e["data"]
                if kind == "text":
                    text += data["delta"]
                elif kind == "change":
                    changes.append(data["text"])
                elif kind == "schema":
                    row = session.get(Project, project_id)
                    if row:
                        row.schema = data["schema"]
                        row.name = data["schema"].get("name") or row.name
                        session.commit()
                elif kind == "error":
                    error = data["message"]
                yield _sse(kind, data)
        except Exception:
            log.exception("AI run failed")
            error = "Something went wrong while generating. Check the server logs."
            yield _sse("error", {"message": error})
        finally:
            # Runs on success, error, and client disconnect alike.
            content = text.strip() or (error or ("Done." if changes else "Stopped."))
            if error and text.strip():
                content += f"\n\n{error}"
            msg = Message(project_id=project_id, role="assistant", content=content, changes=changes, version_id=version.id)
            session.add(msg)
            session.commit()
            session.close()
            _running.discard(project_id)
        yield _sse("message", {"id": msg.id, "content": content, "changes": changes, "version_id": version.id})

    return StreamingResponse(stream(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


# ─── Versions ────────────────────────────────────────────────────────────────


class VersionOut(BaseModel):
    id: str
    label: str
    created_at: datetime


@router.get("/{project_id}/versions", response_model=list[VersionOut])
def list_versions(project_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    owned(project_id, user, db)
    rows = db.scalars(select(Version).where(Version.project_id == project_id).order_by(Version.created_at.desc())).all()
    return [VersionOut(id=v.id, label=v.label, created_at=v.created_at) for v in rows]


@router.post("/{project_id}/versions/{version_id}/restore", response_model=ProjectOut, response_model_by_alias=True)
def restore_version(project_id: str, version_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    project = owned(project_id, user, db)
    version = db.get(Version, version_id)
    if not version or version.project_id != project_id:
        raise HTTPException(404, "Version not found.")
    if project_id in _running:
        raise HTTPException(409, "The AI is editing this project. Wait for it to finish.")
    db.add(Version(project_id=project_id, label="Before restoring an earlier version", schema=project.schema))
    project.schema = version.schema
    db.commit()
    db.refresh(project)
    return _out(project)


# ─── Generated Flutter code ──────────────────────────────────────────────────


class CodeOut(BaseModel):
    files: dict[str, str]
    warnings: list[str]


@router.get("/{project_id}/code", response_model=CodeOut)
def code(project_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    generated = generate_project(owned(project_id, user, db).schema)
    return CodeOut(files=generated.files, warnings=generated.warnings)


def source_zip(schema: dict, folder: str) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for path, content in generate_project(schema).files.items():
            zf.writestr(f"{folder}/{path}", content)
    return buf.getvalue()


@router.get("/{project_id}/source.zip")
def download_source(project_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    project = owned(project_id, user, db)
    folder = (project.schema.get("build", {}).get("bundleId", "app").split(".")[-1]) or "app"
    return Response(
        source_zip(project.schema, folder), media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{folder}-flutter.zip"'},
    )


# ─── Backend connection check ────────────────────────────────────────────────


class BackendTestOut(BaseModel):
    ok: bool
    message: str


@router.post("/{project_id}/backend/test", response_model=BackendTestOut)
async def test_backend(project_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    backend = owned(project_id, user, db).schema.get("backend", {})
    provider: Literal["none", "supabase", "rest", "firebase"] = backend.get("provider", "none")
    url = (backend.get("url") or "").rstrip("/")
    if provider == "none":
        return BackendTestOut(ok=True, message="No backend connected. The app runs with the content in its screens.")
    if provider == "firebase":
        if not backend.get("projectId"):
            return BackendTestOut(ok=False, message="Add your Firebase project id.")
        return BackendTestOut(ok=True, message="Saved. Run `flutterfire configure` in the exported project to finish the Firebase setup.")
    if not url.startswith(("https://", "http://")):
        return BackendTestOut(ok=False, message="Enter a URL starting with https://")
    try:
        async with httpx.AsyncClient(timeout=8) as client:
            if provider == "supabase":
                if not backend.get("anonKey"):
                    return BackendTestOut(ok=False, message="Add your Supabase anon key.")
                key = backend["anonKey"]
                res = await client.get(f"{url}/rest/v1/", headers={"apikey": key, "Authorization": f"Bearer {key}"})
                if res.status_code in (401, 403):
                    return BackendTestOut(ok=False, message="Supabase rejected the anon key.")
            else:
                res = await client.get(url)
    except httpx.HTTPError as e:
        return BackendTestOut(ok=False, message=f"Couldn't reach {url}: {type(e).__name__}.")
    if res.status_code >= 500:
        return BackendTestOut(ok=False, message=f"The server responded with an error ({res.status_code}).")
    return BackendTestOut(ok=True, message=f"Connected to {url}.")
