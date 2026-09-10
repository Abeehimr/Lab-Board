from __future__ import annotations

import re
import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile, status

from .config import Settings

_unsafe_name = re.compile(r"[^A-Za-z0-9._-]+")


def safe_original_name(name: str | None) -> str:
    cleaned = Path(name or "attachment").name
    cleaned = _unsafe_name.sub("_", cleaned).strip("._")
    return cleaned[:255] or "attachment"


def extension_for(name: str) -> str:
    return Path(name).suffix.lower()


def validate_upload(upload: UploadFile, settings: Settings) -> str:
    original_name = safe_original_name(upload.filename)
    extension = extension_for(original_name)
    if not extension or extension not in settings.allowed_extensions:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported attachment")
    return original_name


def stored_path(settings: Settings, stored_name: str) -> Path:
    root = settings.upload_dir.resolve()
    candidate = (root / stored_name).resolve()
    if candidate.parent != root or candidate == root:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attachment not found")
    return candidate


async def save_upload(upload: UploadFile, settings: Settings) -> tuple[str, str, int]:
    original_name = validate_upload(upload, settings)
    extension = extension_for(original_name)
    stored_name = f"{uuid.uuid4().hex}{extension}"
    destination = stored_path(settings, stored_name)
    size = 0
    try:
        with destination.open("wb") as output:
            while chunk := await upload.read(1024 * 1024):
                size += len(chunk)
                if size > settings.max_upload_bytes:
                    raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Attachment too large")
                output.write(chunk)
    except Exception:
        destination.unlink(missing_ok=True)
        raise
    finally:
        await upload.close()
    return original_name, stored_name, size
