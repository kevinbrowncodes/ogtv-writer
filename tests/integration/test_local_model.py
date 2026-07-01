"""Integration tests for the local (DGX Spark) model in the pickers + run flow (STORY_025).

The local endpoint is configured via env (curated allowlist), so the picker renders a
"Local (DGX Spark)" optgroup without probing the network. The background worker never
runs under tests, so a queued local job persists its model value without generating.
"""

from __future__ import annotations

import pytest

from app.config import get_settings
from app.services import job_service

VEO = "video-review-prompt"  # fixture prompt (no {{COUNT}})


@pytest.fixture(autouse=True)
def _local_provider_and_shoots(tmp_path, monkeypatch):
    monkeypatch.setenv("SOURCE_ROOT", str(tmp_path))
    monkeypatch.setenv("LOCAL_MODEL_BASE_URL", "http://spark-1.local:8003/v1")
    monkeypatch.setenv("LOCAL_MODEL_NAMES", "aeon-ultimate,aeon-fast")
    get_settings.cache_clear()
    pending = tmp_path / "only-gains-tv" / "26-orange"
    pending.mkdir(parents=True)
    (pending / "01.jpg").write_bytes(b"img")
    yield
    get_settings.cache_clear()


def test_shoots_picker_shows_local_optgroup(client):
    resp = client.get("/shoots")
    assert resp.status_code == 200
    assert "<optgroup" in resp.text
    assert "Local (DGX Spark)" in resp.text
    assert 'value="local:aeon-ultimate"' in resp.text
    assert 'value="local:aeon-fast"' in resp.text


def test_new_job_form_shows_local_optgroup(client):
    resp = client.get("/jobs/new")
    assert resp.status_code == 200
    assert "Local (DGX Spark)" in resp.text
    assert 'value="local:aeon-ultimate"' in resp.text


def test_shoots_run_with_local_model_persists_value(client, db):
    resp = client.post(
        "/shoots/run",
        data={
            "source_dir": "only-gains-tv/26-orange",
            "prompt_slug": VEO,
            "model": "local:aeon-fast",
        },
        follow_redirects=False,
    )
    assert resp.status_code == 303
    job = job_service.list_jobs(db)[0]
    assert job.model == "local:aeon-fast"  # routed to the local provider at run time


def test_shoots_run_rejects_unknown_local_model_falls_back(client, db):
    resp = client.post(
        "/shoots/run",
        data={
            "source_dir": "only-gains-tv/26-orange",
            "prompt_slug": VEO,
            "model": "local:not-in-allowlist",
        },
        follow_redirects=False,
    )
    assert resp.status_code == 303
    # Not in the curated allowlist → falls back to the Gemini default, not a local value.
    assert job_service.list_jobs(db)[0].model == get_settings().gemini_model


def test_local_group_absent_when_disabled(client, monkeypatch):
    monkeypatch.setenv("LOCAL_MODEL_BASE_URL", "")
    get_settings.cache_clear()
    resp = client.get("/shoots")
    assert resp.status_code == 200
    assert "Local (DGX Spark)" not in resp.text
