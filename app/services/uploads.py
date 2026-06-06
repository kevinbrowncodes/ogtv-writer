"""Saving uploaded images to disk.

Validates that an upload is a reasonable image, gives it a collision-proof name,
and writes it under ``data/uploads/`` (git-ignored). Returns a repo-relative path
to store on the Job plus the original filename for display.
"""

from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import UploadFile

# Repo root = app/services/uploads.py -> services -> app -> <root>.
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
UPLOADS_DIR = PROJECT_ROOT / "data" / "uploads"

MAX_BYTES = 10 * 1024 * 1024  # 10 MB

# Allowed image extensions (we validate by extension, not the client's content-type).
_ALLOWED_EXTS = {".jpg", ".jpeg", ".png", ".webp"}


class UploadError(ValueError):
    """Raised when an upload is missing, empty, too large, or not an allowed image."""


def save_upload(file: UploadFile | None, *, directory: Path | None = None) -> tuple[str, str]:
    """Validate and persist an uploaded image.

    Returns ``(stored_path, original_filename)``. ``stored_path`` is relative to the
    repo root when saved under the default ``data/uploads/`` dir; otherwise absolute.
    Raises :class:`UploadError` on anything invalid (nothing is written in that case).
    """
    if file is None or not file.filename:
        raise UploadError("Upload a first-frame image.")
    ext = Path(file.filename).suffix.lower()
    if ext not in _ALLOWED_EXTS:
        raise UploadError("Image must be a .jpg, .png, or .webp file.")

    data = file.file.read()
    if not data:
        raise UploadError("That image file is empty.")
    if len(data) > MAX_BYTES:
        raise UploadError("Image is too large (max 10 MB).")

    base = directory if directory is not None else UPLOADS_DIR
    base.mkdir(parents=True, exist_ok=True)
    stored = base / f"{uuid.uuid4().hex}{ext}"
    stored.write_bytes(data)

    try:
        relative = str(stored.relative_to(PROJECT_ROOT))
    except ValueError:
        relative = str(stored)
    return relative, file.filename
