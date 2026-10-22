"""Local file storage for uploaded images + simple image validation."""
from __future__ import annotations

import io
import uuid
from pathlib import Path

from PIL import Image

from .config import settings

ALLOWED_EXT = {".jpg", ".jpeg", ".png", ".webp"}
MEDIA_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
}


class InvalidImageError(ValueError):
    pass


def _ext(filename: str) -> str:
    return Path(filename).suffix.lower()


def validate_and_save(submission_id: int, index: int, filename: str, data: bytes) -> str:
    """Validate an uploaded image and store it. Returns a path relative to uploads dir."""
    ext = _ext(filename)
    if ext not in ALLOWED_EXT:
        raise InvalidImageError(
            f"Unsupported image type '{ext or filename}'. Use JPG, PNG, or WEBP."
        )
    if len(data) == 0:
        raise InvalidImageError("Uploaded file is empty.")
    if len(data) > settings.max_upload_bytes:
        raise InvalidImageError(
            f"Image is too large ({len(data) // (1024 * 1024)} MB). "
            f"Max is {settings.max_upload_mb} MB."
        )
    # Verify it actually decodes as an image.
    try:
        Image.open(io.BytesIO(data)).verify()
    except Exception as exc:  # noqa: BLE001
        raise InvalidImageError("File is not a readable image.") from exc

    sub_dir = settings.uploads_path / str(submission_id)
    sub_dir.mkdir(parents=True, exist_ok=True)
    safe_name = f"{index:02d}_{uuid.uuid4().hex[:8]}{ext}"
    dest = sub_dir / safe_name
    dest.write_bytes(data)
    return f"{submission_id}/{safe_name}"


def absolute_path(rel_path: str) -> Path:
    """Resolve a stored relative path, guarding against path traversal."""
    base = settings.uploads_path.resolve()
    full = (base / rel_path).resolve()
    if base not in full.parents and full != base:
        raise InvalidImageError("Invalid image path.")
    return full


def media_type_for(rel_path: str) -> str:
    return MEDIA_TYPES.get(_ext(rel_path), "application/octet-stream")


def read_bytes(rel_path: str) -> bytes:
    return absolute_path(rel_path).read_bytes()
