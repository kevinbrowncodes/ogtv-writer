"""Integration tests for folder-based jobs (shoot folder in, scripts written back)."""

from __future__ import annotations

import base64

import pytest

from app.config import get_settings
from app.services import gemini_client, job_service, job_worker

PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
)
VEO = "video-review-prompt"


@pytest.fixture(autouse=True)
def _source_root(tmp_path, monkeypatch):
    monkeypatch.setenv("SOURCE_ROOT", str(tmp_path))
    get_settings.cache_clear()
    shoot = tmp_path / "only-gains-tv" / "26-brown"
    shoot.mkdir(parents=True)
    (shoot / "01.jpg").write_bytes(PNG)
    yield
    get_settings.cache_clear()


def test_new_job_form_lists_shoots(client):
    resp = client.get("/jobs/new")
    assert resp.status_code == 200
    assert "26-brown" in resp.text
    assert "only-gains-tv" in resp.text


def test_submit_folder_job(client, db):
    resp = client.post(
        "/jobs",
        data={"prompt_slug": VEO, "image_source": "folder", "source_dir": "only-gains-tv/26-brown"},
        follow_redirects=False,
    )
    assert resp.status_code == 303
    job = job_service.list_jobs(db)[0]
    assert job.source_dir == "only-gains-tv/26-brown"
    assert job.image_filename == "01.jpg"


def test_invalid_folder_is_422(client, db):
    resp = client.post(
        "/jobs",
        data={"prompt_slug": VEO, "image_source": "folder", "source_dir": "only-gains-tv/nope"},
    )
    assert resp.status_code == 422
    assert "01.* frame" in resp.text
    assert job_service.count_jobs(db) == 0


def test_folder_job_writes_scripts_back(client, db, tmp_path, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    get_settings.cache_clear()
    monkeypatch.setattr(
        gemini_client, "generate", lambda **kwargs: "<<<SCRIPT 1>>>body<<<END SCRIPT>>>"
    )

    client.post(
        "/jobs",
        data={"prompt_slug": VEO, "image_source": "folder", "source_dir": "only-gains-tv/26-brown"},
    )
    job_worker.process_next_job(db)

    written = tmp_path / "only-gains-tv" / "26-brown" / "script.txt"
    assert written.exists()
    assert written.read_text() == "body"
