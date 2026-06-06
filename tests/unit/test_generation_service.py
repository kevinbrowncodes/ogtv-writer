"""Unit tests for the Gemini generation service.

The Gemini client is mocked at its boundary (``gemini_client.generate``), so these
never make a live, paid API call.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.config import get_settings
from app.services import gemini_client, generation_service, job_service

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 16


@pytest.fixture(autouse=True)
def _clear_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


# --- assemble_prompt ---------------------------------------------------------
def test_assemble_prompt_injects_count():
    out = generation_service.assemble_prompt("Make {{COUNT}} clips.", count=8, addendum="")
    assert "Make 8 clips." in out
    assert "{{COUNT}}" not in out


def test_assemble_prompt_without_count_leaves_body():
    out = generation_service.assemble_prompt("Review this.", count=None, addendum="")
    assert "Review this." in out


def test_assemble_prompt_appends_addendum():
    out = generation_service.assemble_prompt("Body.", count=None, addendum="Make it spicy.")
    assert "Additional details for this job" in out
    assert "Make it spicy." in out


def test_assemble_prompt_includes_output_contract():
    out = generation_service.assemble_prompt("Body.", count=None, addendum="")
    assert "<<<SCRIPT" in out


# --- run_job -----------------------------------------------------------------
def _running_job(db, tmp_path: Path, **kwargs):
    img = tmp_path / "frame.png"
    img.write_bytes(PNG)
    defaults = {
        "prompt_slug": "video-review-prompt",
        "prompt_filename": "video-review-prompt.md",
        "addendum": "",
        "count": None,
        "image_path": str(img),
        "image_filename": "frame.png",
    }
    defaults.update(kwargs)
    job = job_service.create_job(db, **defaults)
    job.status = "running"
    db.commit()
    return job


def test_run_job_stores_result(db, tmp_path, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    get_settings.cache_clear()
    monkeypatch.setattr(gemini_client, "generate", lambda **kwargs: "GENERATED TEXT")

    job = _running_job(db, tmp_path)
    generation_service.run_job(db, job)

    db.refresh(job)
    assert job.status == "done"
    assert job.result_raw == "GENERATED TEXT"
    assert job.finished_at is not None
    assert job.error == ""


def test_run_job_uses_job_model(db, tmp_path, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    get_settings.cache_clear()
    captured: dict[str, str] = {}

    def fake_generate(**kwargs):
        captured.update(kwargs)
        return "<<<SCRIPT 1>>>body<<<END SCRIPT>>>"

    monkeypatch.setattr(gemini_client, "generate", fake_generate)

    job = _running_job(db, tmp_path)
    job.model = "gemini-2.5-pro"
    db.commit()
    generation_service.run_job(db, job)

    assert captured["model"] == "gemini-2.5-pro"


def test_run_job_writes_scripts_into_shoot_folder(db, tmp_path, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("SOURCE_ROOT", str(tmp_path))
    get_settings.cache_clear()
    shoot = tmp_path / "only-gains-tv" / "26-brown"
    shoot.mkdir(parents=True)
    (shoot / "01.jpg").write_bytes(PNG)
    monkeypatch.setattr(
        gemini_client, "generate", lambda **kwargs: "<<<SCRIPT 1>>>hello<<<END SCRIPT>>>"
    )

    job = job_service.create_job(
        db,
        prompt_slug="video-review-prompt",
        prompt_filename="video-review-prompt.md",
        addendum="",
        count=None,
        image_path=str(shoot / "01.jpg"),
        image_filename="01.jpg",
        source_dir="only-gains-tv/26-brown",
    )
    job.status = "running"
    db.commit()
    generation_service.run_job(db, job)

    db.refresh(job)
    assert job.status == "done"
    assert (shoot / "script.txt").read_text() == "hello"
    assert "script.txt" in job.output_files


def test_run_job_marks_failed_on_client_error(db, tmp_path, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    get_settings.cache_clear()

    def boom(**kwargs):
        raise RuntimeError("api down")

    monkeypatch.setattr(gemini_client, "generate", boom)

    job = _running_job(db, tmp_path)
    generation_service.run_job(db, job)

    db.refresh(job)
    assert job.status == "failed"
    assert "api down" in job.error


def test_run_job_without_api_key_fails_and_skips_client(db, tmp_path, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "")
    get_settings.cache_clear()
    called: dict[str, int] = {}
    monkeypatch.setattr(gemini_client, "generate", lambda **kwargs: called.setdefault("hit", 1))

    job = _running_job(db, tmp_path)
    generation_service.run_job(db, job)

    db.refresh(job)
    assert job.status == "failed"
    assert "GEMINI_API_KEY" in job.error
    assert "hit" not in called  # never reached the client
