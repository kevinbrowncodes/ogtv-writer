"""Integration tests for per-job model selection."""

from __future__ import annotations

import base64

import pytest

from app.config import get_settings
from app.services import gemini_client, generation_service, job_service, job_worker

PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
)
VEO = "video-review-prompt"


@pytest.fixture(autouse=True)
def _models_and_uploads(tmp_path, monkeypatch):
    # Patch the catalog to a known set (incl. the default), and redirect uploads.
    monkeypatch.setattr(
        generation_service, "available_models", lambda: ["gemini-2.5-pro", "gemini-2.5-flash"]
    )
    monkeypatch.setattr("app.services.uploads.UPLOADS_DIR", tmp_path)


def _image():
    return {"image": ("f.png", PNG, "image/png")}


def test_new_job_form_lists_models_with_price(client):
    resp = client.get("/jobs/new")
    assert resp.status_code == 200
    assert "gemini-2.5-pro" in resp.text
    assert "gemini-2.5-flash" in resp.text
    assert "per 1M tok" in resp.text  # a known model's reference price renders


def test_new_job_form_warns_when_gemini_unavailable(client):
    # available_models is patched to a known list (fixture), but gemini_status sees the
    # blank test key — so the form still surfaces the "unavailable" warning (STORY_023).
    resp = client.get("/jobs/new")
    assert resp.status_code == 200
    assert "Gemini unavailable" in resp.text


def test_submit_stores_chosen_model(client, db):
    resp = client.post(
        "/jobs",
        data={"prompt_slug": VEO, "model": "gemini-2.5-pro"},
        files=_image(),
        follow_redirects=False,
    )
    assert resp.status_code == 303
    assert job_service.list_jobs(db)[0].model == "gemini-2.5-pro"


def test_invalid_model_falls_back_to_default(client, db):
    resp = client.post(
        "/jobs",
        data={"prompt_slug": VEO, "model": "totally-made-up"},
        files=_image(),
        follow_redirects=False,
    )
    assert resp.status_code == 303
    assert job_service.list_jobs(db)[0].model == get_settings().gemini_model


def test_worker_uses_chosen_model(client, db, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    get_settings.cache_clear()
    captured: dict[str, str] = {}

    def fake_generate(**kwargs):
        captured.update(kwargs)
        return "<<<SCRIPT 1>>>body<<<END SCRIPT>>>"

    monkeypatch.setattr(gemini_client, "generate", fake_generate)

    client.post("/jobs", data={"prompt_slug": VEO, "model": "gemini-2.5-pro"}, files=_image())
    job_worker.process_next_job(db)

    assert captured["model"] == "gemini-2.5-pro"
    get_settings.cache_clear()
