"""Unit tests for the image upload helper."""

from __future__ import annotations

import io
from pathlib import Path

import pytest
from fastapi import UploadFile

from app.services import uploads
from app.services.uploads import UploadError, save_upload

# Just enough bytes to look like a non-empty PNG; the service validates by
# extension + size, not by decoding the image.
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32


def _upload(name: str, data: bytes = PNG) -> UploadFile:
    return UploadFile(file=io.BytesIO(data), filename=name)


def test_saves_valid_image(tmp_path: Path) -> None:
    path, original = save_upload(_upload("frame.png"), directory=tmp_path)
    assert original == "frame.png"
    saved = Path(path)
    assert saved.exists()
    assert saved.read_bytes() == PNG
    assert saved.suffix == ".png"
    assert saved.parent == tmp_path


def test_generates_unique_names(tmp_path: Path) -> None:
    p1, _ = save_upload(_upload("a.png"), directory=tmp_path)
    p2, _ = save_upload(_upload("a.png"), directory=tmp_path)
    assert p1 != p2


def test_rejects_missing_file(tmp_path: Path) -> None:
    with pytest.raises(UploadError):
        save_upload(None, directory=tmp_path)


def test_rejects_empty_filename(tmp_path: Path) -> None:
    with pytest.raises(UploadError):
        save_upload(_upload(""), directory=tmp_path)


def test_rejects_disallowed_extension(tmp_path: Path) -> None:
    with pytest.raises(UploadError):
        save_upload(_upload("notes.txt", b"hello"), directory=tmp_path)


def test_rejects_empty_file(tmp_path: Path) -> None:
    with pytest.raises(UploadError):
        save_upload(_upload("frame.png", b""), directory=tmp_path)


def test_rejects_oversized_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(uploads, "MAX_BYTES", 4)
    with pytest.raises(UploadError):
        save_upload(_upload("frame.png", b"12345"), directory=tmp_path)
