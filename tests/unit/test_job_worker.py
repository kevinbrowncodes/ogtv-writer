"""Unit tests for the in-process job worker's unit of work."""

from __future__ import annotations

import pytest

from app.config import get_settings
from app.services import gemini_client, job_service, job_worker

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 16


@pytest.fixture(autouse=True)
def _clear_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _job(db, tmp_path):
    img = tmp_path / "f.png"
    img.write_bytes(PNG)
    return job_service.create_job(
        db,
        prompt_slug="video-review-prompt",
        prompt_filename="video-review-prompt.md",
        addendum="",
        count=None,
        image_path=str(img),
        image_filename="f.png",
    )


def test_process_next_job_empty_queue_returns_none(db):
    assert job_worker.process_next_job(db) is None


def test_process_next_job_claims_oldest_and_runs_one(db, tmp_path, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    get_settings.cache_clear()
    monkeypatch.setattr(gemini_client, "generate", lambda **kwargs: "OK")

    older = _job(db, tmp_path)
    newer = _job(db, tmp_path)

    processed = job_worker.process_next_job(db)
    assert processed is not None
    assert processed.id == older.id

    db.refresh(older)
    db.refresh(newer)
    assert older.status == "done"
    assert older.result_raw == "OK"
    assert newer.status == "queued"  # only one job handled per call
