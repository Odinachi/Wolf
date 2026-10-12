"""Lazy Firebase Admin setup shared by auth and storage."""

from __future__ import annotations

import base64
import json
from functools import cache

import firebase_admin
from firebase_admin import credentials

from . import config


def service_account_info() -> dict | None:
    """The service account JSON from FIREBASE_SERVICE_ACCOUNT (raw JSON or base64), if set."""
    raw = config.FIREBASE_SERVICE_ACCOUNT.strip()
    if not raw:
        return None
    if not raw.startswith("{"):
        raw = base64.b64decode(raw).decode()
    return json.loads(raw)


@cache
def app() -> firebase_admin.App:
    info = service_account_info()
    project_id = config.FIREBASE_PROJECT_ID or (info or {}).get("project_id", "")
    if not project_id:
        raise RuntimeError("Set FIREBASE_PROJECT_ID to enable sign-in.")
    options = {"projectId": project_id}
    if config.FIREBASE_STORAGE_BUCKET:
        options["storageBucket"] = config.FIREBASE_STORAGE_BUCKET
    # Verifying ID tokens only needs the project id; a service account is needed for storage.
    cred = credentials.Certificate(info) if info else None
    return firebase_admin.initialize_app(cred, options, name="wolf")
