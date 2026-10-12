"""File storage for build artifacts: Firebase Storage in production, a local folder otherwise."""

from __future__ import annotations

import shutil
from datetime import timedelta
from functools import cache
from pathlib import Path
from typing import Protocol

from . import config, firebase


class Storage(Protocol):
    def put(self, key: str, path: Path, content_type: str) -> None: ...
    def local_path(self, key: str) -> Path | None:
        """For local storage: the file on disk. None for remote storage."""
    def download_url(self, key: str, filename: str) -> str | None:
        """For remote storage: a short-lived signed URL. None for local storage."""
    def delete(self, key: str) -> None: ...


class LocalStorage:
    def __init__(self, root: Path):
        self.root = root

    def _path(self, key: str) -> Path:
        path = (self.root / key).resolve()
        if self.root.resolve() not in path.parents:
            raise ValueError("Invalid storage key.")
        return path

    def put(self, key: str, path: Path, content_type: str) -> None:
        target = self._path(key)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)

    def local_path(self, key: str) -> Path | None:
        path = self._path(key)
        return path if path.is_file() else None

    def download_url(self, key: str, filename: str) -> str | None:
        return None

    def delete(self, key: str) -> None:
        self._path(key).unlink(missing_ok=True)


class FirebaseStorage:
    def __init__(self):
        from firebase_admin import storage

        self.bucket = storage.bucket(app=firebase.app())

    def put(self, key: str, path: Path, content_type: str) -> None:
        self.bucket.blob(key).upload_from_filename(str(path), content_type=content_type)

    def local_path(self, key: str) -> Path | None:
        return None

    def download_url(self, key: str, filename: str) -> str | None:
        blob = self.bucket.blob(key)
        if not blob.exists():
            return None
        return blob.generate_signed_url(
            expiration=timedelta(minutes=15), version="v4", response_disposition=f'attachment; filename="{filename}"',
        )

    def delete(self, key: str) -> None:
        blob = self.bucket.blob(key)
        if blob.exists():
            blob.delete()


@cache
def get_storage() -> Storage:
    if config.FIREBASE_STORAGE_BUCKET and config.FIREBASE_SERVICE_ACCOUNT:
        return FirebaseStorage()
    return LocalStorage(config.DATA_DIR / "files")
