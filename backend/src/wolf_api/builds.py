"""Builds: compile a project with the Flutter SDK on this machine, and share installable artifacts.

Builds run in a background thread on the API host. Android builds need the Android SDK; iOS builds
need macOS with Xcode and produce an unsigned app (signing and store upload happen outside Wolf).
Finished files go to storage (Firebase Storage in production, see storage.py).
"""

from __future__ import annotations

import os
import platform as host_platform
import re
import secrets
import shutil
import subprocess
import threading
import time
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, RedirectResponse, Response
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session
from wolf_flutter import generate_project

from . import config
from .auth import current_user
from .db import Build, Project, SessionLocal, User, get_db, utcnow
from .projects import owned, source_zip
from .storage import get_storage

router = APIRouter(tags=["builds"])
BUILDS_DIR = config.DATA_DIR / "builds"


# ─── Toolchain ───────────────────────────────────────────────────────────────


def android_sdk() -> Path | None:
    for candidate in (os.getenv("ANDROID_HOME"), os.getenv("ANDROID_SDK_ROOT"), str(Path.home() / "Library/Android/sdk"), str(Path.home() / "Android/Sdk")):
        if candidate and Path(candidate).is_dir():
            return Path(candidate)
    return None


class ToolchainOut(BaseModel):
    flutter: str | None
    android: bool
    ios: bool


_flutter_version: str | None = None


@router.get("/api/toolchain", response_model=ToolchainOut)
def toolchain() -> ToolchainOut:
    global _flutter_version
    flutter = shutil.which("flutter")
    if flutter and _flutter_version is None:
        try:
            out = subprocess.run([flutter, "--version"], capture_output=True, text=True, timeout=60).stdout
            match = re.search(r"Flutter (\S+)", out)
            _flutter_version = match.group(1) if match else "installed"
        except (subprocess.SubprocessError, OSError):
            _flutter_version = "installed"
    return ToolchainOut(
        flutter=_flutter_version if flutter else None,
        android=bool(flutter and android_sdk()),
        ios=bool(flutter and host_platform.system() == "Darwin" and shutil.which("xcodebuild")),
    )


# ─── Running a build ─────────────────────────────────────────────────────────


class _Log:
    """Buffers build output and flushes it to the database about once a second."""

    def __init__(self, build_id: str):
        self.build_id = build_id
        self.lines: list[str] = []
        self.last_flush = 0.0

    def write(self, line: str, force: bool = False) -> None:
        self.lines.append(line.rstrip("\n"))
        if force or time.monotonic() - self.last_flush > 1:
            self.flush()

    def flush(self) -> None:
        with SessionLocal() as db:
            build = db.get(Build, self.build_id)
            if build:
                build.logs = "\n".join(self.lines[-4000:])
                db.commit()
        self.last_flush = time.monotonic()


def _run(cmd: list[str], cwd: Path, log: _Log) -> None:
    log.write(f"$ {' '.join(cmd)}", force=True)
    proc = subprocess.Popen(cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    assert proc.stdout
    for line in proc.stdout:
        log.write(line)
    if proc.wait() != 0:
        raise RuntimeError(f"`{' '.join(cmd[:3])}` failed with exit code {proc.returncode}.")


CONTENT_TYPES = {".apk": "application/vnd.android.package-archive", ".zip": "application/zip"}


def _finish(build_id: str, status: str, artifact: Path | None) -> None:
    key = None
    if artifact:
        with SessionLocal() as db:
            project_id = db.get(Build, build_id).project_id
        key = f"builds/{project_id}/{build_id}/{artifact.name}"
        get_storage().put(key, artifact, CONTENT_TYPES.get(artifact.suffix, "application/octet-stream"))
    with SessionLocal() as db:
        build = db.get(Build, build_id)
        if build:
            build.status = status
            build.artifact_key = key
            build.finished_at = utcnow()
            db.commit()


def _build_worker(build_id: str, schema: dict, target: str) -> None:
    log = _Log(build_id)
    with SessionLocal() as db:
        build = db.get(Build, build_id)
        build.status = "running"
        db.commit()
    work = BUILDS_DIR / build_id
    app_dir = work / "app"
    try:
        app_dir.mkdir(parents=True, exist_ok=True)
        project = generate_project(schema)
        for warning in project.warnings:
            log.write(f"warning: {warning}")
        if target == "source":
            artifact = work / "source.zip"
            artifact.write_bytes(source_zip(schema, "app"))
            log.write("Exported the Flutter source.", force=True)
            _finish(build_id, "succeeded", artifact)
            return

        flutter = shutil.which("flutter")
        if not flutter:
            raise RuntimeError("The Flutter SDK isn't installed on this server. Download the source instead.")
        for rel, content in project.files.items():
            path = app_dir / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)

        bundle = schema.get("build", {}).get("bundleId") or "com.wolf.app"
        org = ".".join(bundle.split(".")[:-1]) or "com.wolf"
        package = re.search(r"^name:\s*(\S+)", project.files["pubspec.yaml"], re.M).group(1)
        _run([flutter, "create", ".", "--org", org, "--project-name", package, "--platforms", target], app_dir, log)
        _run([flutter, "pub", "get"], app_dir, log)

        if target == "android":
            _run([flutter, "build", "apk", "--release"], app_dir, log)
            built = app_dir / "build/app/outputs/flutter-apk/app-release.apk"
            artifact = work / f"{package}.apk"
            shutil.copy(built, artifact)
        else:
            _run([flutter, "build", "ios", "--release", "--no-codesign"], app_dir, log)
            built = app_dir / "build/ios/iphoneos/Runner.app"
            artifact = Path(shutil.make_archive(str(work / f"{package}-ios-unsigned"), "zip", built.parent, built.name))
        log.write(f"Built {artifact.name} ({artifact.stat().st_size / 1_000_000:.1f} MB).", force=True)
        _finish(build_id, "succeeded", artifact)
    except Exception as e:  # report every failure in the build log
        log.write(f"Build failed: {e}", force=True)
        _finish(build_id, "failed", None)
    finally:
        # The artifact now lives in storage; drop the (large) working tree.
        shutil.rmtree(work, ignore_errors=True)


# ─── Routes ──────────────────────────────────────────────────────────────────


class BuildIn(BaseModel):
    platform: Literal["android", "ios", "source"]


class BuildOut(BaseModel):
    id: str
    platform: str
    status: str
    logs: str
    has_artifact: bool
    share_token: str | None
    created_at: str
    finished_at: str | None


def _build_out(b: Build) -> BuildOut:
    return BuildOut(
        id=b.id, platform=b.platform, status=b.status, logs=b.logs, has_artifact=bool(b.artifact_key), share_token=b.share_token,
        created_at=b.created_at.isoformat(), finished_at=b.finished_at.isoformat() if b.finished_at else None,
    )


def _owned_build(build_id: str, user: User, db: Session) -> Build:
    build = db.get(Build, build_id)
    if not build:
        raise HTTPException(404, "Build not found.")
    owned(build.project_id, user, db)
    return build


@router.post("/api/projects/{project_id}/builds", response_model=BuildOut, status_code=201)
def start_build(project_id: str, body: BuildIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    project = owned(project_id, user, db)
    busy = db.scalar(select(Build).where(Build.project_id == project_id, Build.status.in_(["queued", "running"])))
    if busy:
        raise HTTPException(409, "A build is already running for this project.")
    tools = toolchain()
    if body.platform == "android" and not tools.android:
        raise HTTPException(400, "Android builds need the Flutter SDK and Android SDK on the server.")
    if body.platform == "ios" and not tools.ios:
        raise HTTPException(400, "iOS builds need a macOS server with Flutter and Xcode.")
    build = Build(project_id=project.id, platform=body.platform)
    db.add(build)
    db.commit()
    threading.Thread(target=_build_worker, args=(build.id, project.schema, body.platform), daemon=True).start()
    return _build_out(build)


@router.get("/api/projects/{project_id}/builds", response_model=list[BuildOut])
def list_builds(project_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    owned(project_id, user, db)
    rows = db.scalars(select(Build).where(Build.project_id == project_id).order_by(Build.created_at.desc()).limit(20)).all()
    return [_build_out(b) for b in rows]


@router.get("/api/builds/{build_id}", response_model=BuildOut)
def get_build(build_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    return _build_out(_owned_build(build_id, user, db))


def _artifact(build: Build) -> Response:
    """Serves a local file, or redirects to a short-lived signed URL in Firebase Storage."""
    if not build.artifact_key:
        raise HTTPException(404, "This build has no downloadable file.")
    filename = build.artifact_key.rsplit("/", 1)[-1]
    storage = get_storage()
    local = storage.local_path(build.artifact_key)
    if local:
        return FileResponse(local, media_type=CONTENT_TYPES.get(local.suffix, "application/octet-stream"), filename=filename)
    url = storage.download_url(build.artifact_key, filename)
    if not url:
        raise HTTPException(404, "This build's file is no longer available.")
    return RedirectResponse(url, status_code=302)


@router.get("/api/builds/{build_id}/artifact")
def download_artifact(build_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    return _artifact(_owned_build(build_id, user, db))


@router.post("/api/builds/{build_id}/share", response_model=BuildOut)
def share_build(build_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    build = _owned_build(build_id, user, db)
    if build.status != "succeeded" or not build.artifact_key:
        raise HTTPException(400, "Only finished builds can be shared.")
    if not build.share_token:
        build.share_token = secrets.token_urlsafe(16)
        db.commit()
    return _build_out(build)


class ShareOut(BaseModel):
    app_name: str
    version: str
    platform: str
    created_at: str


def _shared(token: str, db: Session) -> tuple[Build, Project]:
    build = db.scalar(select(Build).where(Build.share_token == token))
    project = db.get(Project, build.project_id) if build else None
    if not build or not project:
        raise HTTPException(404, "This install link doesn't exist or was removed.")
    return build, project


@router.get("/api/share/{token}", response_model=ShareOut)
def shared_build(token: str, db: Session = Depends(get_db)):
    """Public: the install page for a shared build."""
    build, project = _shared(token, db)
    b = project.schema.get("build", {})
    return ShareOut(app_name=b.get("appName") or project.name, version=f"{b.get('version', '1.0.0')} ({b.get('buildNumber', 1)})",
                    platform=build.platform, created_at=build.created_at.isoformat())


@router.get("/api/share/{token}/download")
def shared_download(token: str, db: Session = Depends(get_db)):
    """Public: download a shared build."""
    build, _ = _shared(token, db)
    return _artifact(build)
