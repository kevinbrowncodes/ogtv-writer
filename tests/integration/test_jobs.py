"""Integration tests for the generation-job submission flow + queue."""

from __future__ import annotations

import base64

import pytest

from app.services import job_service

# A valid 1x1 PNG.
PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
)

VEO = "video-review-prompt"  # no {{COUNT}}
WIP = "260601-0000_wip-prompt"  # uses {{COUNT}}


@pytest.fixture(autouse=True)
def _uploads_to_tmp(tmp_path, monkeypatch):
    """Keep test image writes out of the real data/uploads/ folder."""
    monkeypatch.setattr("app.services.uploads.UPLOADS_DIR", tmp_path)


def _image():
    return {"image": ("frame.png", PNG, "image/png")}


def test_new_job_form_lists_prompts(client) -> None:
    resp = client.get("/jobs/new")
    assert resp.status_code == 200
    assert "New generation job" in resp.text
    assert VEO in resp.text


def test_count_field_shown_only_for_count_prompts(client) -> None:
    shown = client.get("/jobs/new/count-field", params={"prompt_slug": WIP})
    assert "Number of scripts" in shown.text
    hidden = client.get("/jobs/new/count-field", params={"prompt_slug": VEO})
    assert "Number of scripts" not in hidden.text


def test_submit_queues_job(client, db) -> None:
    resp = client.post(
        "/jobs", data={"prompt_slug": VEO, "addendum": ""}, files=_image(), follow_redirects=False
    )
    assert resp.status_code == 303
    assert resp.headers["location"] == "/jobs"
    jobs = job_service.list_jobs(db)
    assert len(jobs) == 1
    assert jobs[0].status == "queued"
    assert jobs[0].image_filename == "frame.png"


def test_submitted_job_appears_in_queue(client) -> None:
    client.post("/jobs", data={"prompt_slug": VEO}, files=_image())
    resp = client.get("/jobs")
    assert "frame.png" in resp.text
    assert "Queued" in resp.text


def test_missing_image_is_422(client, db) -> None:
    resp = client.post("/jobs", data={"prompt_slug": VEO})
    assert resp.status_code == 422
    assert "Upload a first-frame image." in resp.text
    assert job_service.count_jobs(db) == 0


def test_non_image_file_is_422(client, db) -> None:
    resp = client.post(
        "/jobs", data={"prompt_slug": VEO}, files={"image": ("notes.txt", b"hello", "text/plain")}
    )
    assert resp.status_code == 422
    assert ".jpg" in resp.text
    assert job_service.count_jobs(db) == 0


def test_unknown_prompt_is_422(client, db) -> None:
    resp = client.post("/jobs", data={"prompt_slug": "nope"}, files=_image())
    assert resp.status_code == 422
    assert "Pick a valid prompt." in resp.text
    assert job_service.count_jobs(db) == 0


def test_count_prompt_requires_a_count(client, db) -> None:
    # Omitting count for a {{COUNT}} prompt is rejected...
    resp = client.post("/jobs", data={"prompt_slug": WIP}, files=_image())
    assert resp.status_code == 422
    assert "how many scripts" in resp.text
    assert job_service.count_jobs(db) == 0

    # ...but providing one succeeds and stores it.
    ok = client.post(
        "/jobs", data={"prompt_slug": WIP, "count": "6"}, files=_image(), follow_redirects=False
    )
    assert ok.status_code == 303
    jobs = job_service.list_jobs(db)
    assert len(jobs) == 1
    assert jobs[0].count == 6
