"""Integration tests for the Shoots dashboard + run actions."""

from __future__ import annotations

import pytest

from app.config import get_settings
from app.services import job_service

VEO = "video-review-prompt"  # fixture prompt (no {{COUNT}})


@pytest.fixture(autouse=True)
def _source_root(tmp_path, monkeypatch):
    monkeypatch.setenv("SOURCE_ROOT", str(tmp_path))
    get_settings.cache_clear()
    pending = tmp_path / "only-gains-tv" / "26-orange"
    pending.mkdir(parents=True)
    (pending / "01.jpg").write_bytes(b"img")
    done = tmp_path / "only-gains-tv" / "26-brown"
    done.mkdir(parents=True)
    (done / "01.jpg").write_bytes(b"img")
    (done / "script.txt").write_text("already generated")  # → done
    yield
    get_settings.cache_clear()


def test_dashboard_lists_channels_and_status(client):
    resp = client.get("/shoots")
    assert resp.status_code == 200
    assert "only-gains-tv" in resp.text
    assert "26-orange" in resp.text
    assert "Pending" in resp.text
    assert "Done" in resp.text


def test_run_queues_folder_job_for_pending_shoot(client, db):
    resp = client.post(
        "/shoots/run",
        data={"source_dir": "only-gains-tv/26-orange", "prompt_slug": VEO},
        follow_redirects=False,
    )
    assert resp.status_code == 303
    job = job_service.list_jobs(db)[0]
    assert job.source_dir == "only-gains-tv/26-orange"
    assert job.image_filename == "01.jpg"


def test_run_invalid_shoot_queues_nothing(client, db):
    resp = client.post(
        "/shoots/run",
        data={"source_dir": "only-gains-tv/nope", "prompt_slug": VEO},
        follow_redirects=False,
    )
    assert resp.status_code == 303  # flashes an error, redirects
    assert job_service.count_jobs(db) == 0


def test_run_all_queues_pending_only(client, db):
    resp = client.post("/shoots/run-all", data={"prompt_slug": VEO}, follow_redirects=False)
    assert resp.status_code == 303
    jobs = job_service.list_jobs(db)
    assert len(jobs) == 1  # only 26-orange (pending); 26-brown is done → skipped
    assert jobs[0].source_dir == "only-gains-tv/26-orange"
