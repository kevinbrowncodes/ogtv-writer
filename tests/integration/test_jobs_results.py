"""Integration: a processed job is split into library scripts + titles + summary.

Gemini is mocked to return a known, contract-formatted response, so no live call.
"""

from __future__ import annotations

import base64

import pytest

from app.config import get_settings
from app.services import gemini_client, job_service, job_worker, script_service

PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
)

VEO = "video-review-prompt"
WIP = "260601-0000_wip-prompt"

MULTI_RESPONSE = (
    "<<<SCRIPT 1>>>\nAlpha body.\n<<<END SCRIPT>>>\n"
    "<<<SCRIPT 2>>>\nBeta body.\n<<<END SCRIPT>>>\n"
    "<<<TITLES>>>\nT1 🔥\nT2 💪\n<<<END TITLES>>>\n"
    "<<<SUMMARY>>>\nScene summary.\n<<<END SUMMARY>>>"
)


@pytest.fixture(autouse=True)
def _key_and_uploads(tmp_path, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    get_settings.cache_clear()
    monkeypatch.setattr("app.services.uploads.UPLOADS_DIR", tmp_path)
    yield
    get_settings.cache_clear()


def _queue_and_run(client, db, monkeypatch, slug, *, response, count=None):
    monkeypatch.setattr(gemini_client, "generate", lambda **kwargs: response)
    data = {"prompt_slug": slug}
    if count is not None:
        data["count"] = str(count)
    client.post("/jobs", data=data, files={"image": ("f.png", PNG, "image/png")})
    job = job_service.list_jobs(db)[0]
    job_worker.process_next_job(db)
    db.refresh(job)
    return job


def test_multi_script_job_splits_and_renders(client, db, monkeypatch):
    job = _queue_and_run(client, db, monkeypatch, WIP, response=MULTI_RESPONSE, count=2)

    assert job.status == "done"
    assert job.summary == "Scene summary."
    assert job.titles.splitlines() == ["T1 🔥", "T2 💪"]

    scripts = script_service.list_for_job(db, job.id)
    assert [s.body for s in scripts] == ["Alpha body.", "Beta body."]
    assert [s.order_index for s in scripts] == [1, 2]
    assert script_service.count_scripts(db) == 2  # they're in the library

    detail = client.get(f"/jobs/{job.id}")
    assert detail.status_code == 200
    assert "Alpha body." in detail.text
    assert "Beta body." in detail.text
    assert "Scene summary." in detail.text
    assert "T1 🔥" in detail.text


def test_single_script_job(client, db, monkeypatch):
    job = _queue_and_run(
        client, db, monkeypatch, VEO, response="<<<SCRIPT 1>>>\nSolo body.\n<<<END SCRIPT>>>"
    )
    scripts = script_service.list_for_job(db, job.id)
    assert len(scripts) == 1
    assert scripts[0].body == "Solo body."
    assert "—" not in scripts[0].title  # single script gets no "— n" suffix
    assert job.titles == ""
    assert job.summary == ""
