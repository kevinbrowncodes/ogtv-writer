"""Integration tests for the Shoots dashboard live-refresh (STORY_011).

The channel tables (`/shoots/list`) self-refresh while any job is queued/running and
stop polling once the queue is idle, so statuses flip Pending → Done without a manual
reload.
"""

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
    yield
    get_settings.cache_clear()


def _queue_a_job(db):
    job_service.create_job(
        db,
        prompt_slug=VEO,
        prompt_filename="video-review-prompt.md",
        addendum="",
        count=None,
        image_path="x/01.jpg",
        image_filename="01.jpg",
        source_dir="only-gains-tv/26-orange",
    )


def test_shoots_list_polls_and_shows_activity_while_active(client, db):
    _queue_a_job(db)  # one queued job → dashboard should keep refreshing
    resp = client.get("/shoots/list")
    assert resp.status_code == 200
    assert 'hx-get="/shoots/list"' in resp.text  # polling armed
    assert "auto-refreshing" in resp.text  # activity line visible
    assert "1 queued" in resp.text


def test_shoots_list_idle_does_not_poll(client):
    resp = client.get("/shoots/list")
    assert resp.status_code == 200
    assert 'hx-get="/shoots/list"' not in resp.text  # no jobs → no polling
    assert "auto-refreshing" not in resp.text


def test_shoots_page_embeds_live_list(client, db):
    _queue_a_job(db)
    resp = client.get("/shoots")
    assert resp.status_code == 200
    assert 'id="shoots-list"' in resp.text
    assert 'hx-get="/shoots/list"' in resp.text
