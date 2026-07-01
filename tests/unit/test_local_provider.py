"""Unit tests for local-provider routing + model listing in generation_service (STORY_025).

Both provider clients are mocked at their boundary, so these never make a live call to
Gemini or the DGX Spark.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.config import get_settings
from app.services import gemini_client, generation_service, job_service, local_client
from app.services.llm_errors import ModelProbe

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 16


@pytest.fixture(autouse=True)
def _clear_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


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


# --- routing: run_job picks the right backend --------------------------------
def test_run_job_routes_local_model(db, tmp_path, monkeypatch):
    monkeypatch.setenv("LOCAL_MODEL_BASE_URL", "http://spark-1.local:8003/v1")
    monkeypatch.setenv("LOCAL_MODEL_API_KEY", "")
    get_settings.cache_clear()

    captured: dict = {}
    monkeypatch.setattr(
        local_client,
        "generate",
        lambda **kw: captured.update(kw) or "<<<SCRIPT 1>>>hi<<<END SCRIPT>>>",
    )

    def _gemini_should_not_run(**kw):
        raise AssertionError("gemini_client.generate should not be called for a local model")

    monkeypatch.setattr(gemini_client, "generate", _gemini_should_not_run)

    job = _running_job(db, tmp_path, model="local:aeon-fast")
    generation_service.run_job(db, job)

    db.refresh(job)
    assert job.status == "done"
    assert captured["model"] == "aeon-fast"  # prefix stripped before the call
    assert captured["base_url"] == "http://spark-1.local:8003/v1"


def test_run_job_routes_gemini_model(db, tmp_path, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    get_settings.cache_clear()

    captured: dict = {}
    monkeypatch.setattr(
        gemini_client,
        "generate",
        lambda **kw: captured.update(kw) or "<<<SCRIPT 1>>>hi<<<END SCRIPT>>>",
    )

    def _local_should_not_run(**kw):
        raise AssertionError("local_client.generate should not be called for a Gemini model")

    monkeypatch.setattr(local_client, "generate", _local_should_not_run)

    job = _running_job(db, tmp_path, model="gemini-2.5-pro")
    generation_service.run_job(db, job)

    db.refresh(job)
    assert job.status == "done"
    assert captured["model"] == "gemini-2.5-pro"


def test_run_job_local_without_base_url_fails_and_skips_client(db, tmp_path, monkeypatch):
    monkeypatch.setenv("LOCAL_MODEL_BASE_URL", "")
    get_settings.cache_clear()
    called: dict = {}
    monkeypatch.setattr(local_client, "generate", lambda **kw: called.setdefault("hit", 1))

    job = _running_job(db, tmp_path, model="local:aeon-fast")
    generation_service.run_job(db, job)

    db.refresh(job)
    assert job.status == "failed"
    assert "LOCAL_MODEL_BASE_URL" in job.error
    assert "hit" not in called  # never reached the client


# --- listing: local_models / selectable_models / model_options ---------------
def test_local_models_uses_curated_allowlist(monkeypatch):
    monkeypatch.setenv("LOCAL_MODEL_BASE_URL", "http://spark-1.local:8003/v1")
    monkeypatch.setenv("LOCAL_MODEL_NAMES", "aeon-ultimate, aeon-fast")
    get_settings.cache_clear()

    def _probe_should_not_run(*a, **k):
        raise AssertionError("probe_models should not be called when a curated list is set")

    monkeypatch.setattr(local_client, "probe_models", _probe_should_not_run)

    assert generation_service.local_models() == ["local:aeon-ultimate", "local:aeon-fast"]


def test_local_models_falls_back_to_probe_when_names_blank(monkeypatch):
    monkeypatch.setenv("LOCAL_MODEL_BASE_URL", "http://spark-1.local:8003/v1")
    monkeypatch.setenv("LOCAL_MODEL_NAMES", "")
    get_settings.cache_clear()
    monkeypatch.setattr(
        local_client,
        "probe_models",
        lambda *a, **k: ModelProbe(models=["m1", "m2"], ok=True, reason=""),
    )
    assert generation_service.local_models() == ["local:m1", "local:m2"]


def test_local_models_empty_when_disabled(monkeypatch):
    monkeypatch.setenv("LOCAL_MODEL_BASE_URL", "")
    get_settings.cache_clear()
    assert generation_service.local_models() == []


def test_selectable_models_merges_gemini_and_local(monkeypatch):
    monkeypatch.setattr(generation_service, "available_models", lambda: ["gemini-2.5-flash"])
    monkeypatch.setattr(generation_service, "local_models", lambda: ["local:aeon-fast"])
    assert generation_service.selectable_models() == ["gemini-2.5-flash", "local:aeon-fast"]


def test_model_options_groups_both_providers(monkeypatch):
    monkeypatch.setattr(generation_service, "available_models", lambda: ["gemini-2.5-flash"])
    monkeypatch.setattr(generation_service, "local_models", lambda: ["local:aeon-fast"])

    groups = generation_service.model_options()
    assert [g.provider for g in groups] == ["gemini", "local"]
    assert groups[1].label == "Local (DGX Spark)"
    local_option = groups[1].options[0]
    assert local_option.value == "local:aeon-fast"
    assert local_option.label == "aeon-fast"  # prefix stripped for display
    assert local_option.price == "self-hosted"


def test_model_options_omits_local_group_when_disabled(monkeypatch):
    monkeypatch.setattr(generation_service, "available_models", lambda: ["gemini-2.5-flash"])
    monkeypatch.setattr(generation_service, "local_models", lambda: [])
    groups = generation_service.model_options()
    assert [g.provider for g in groups] == ["gemini"]
