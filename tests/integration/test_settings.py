"""Integration tests for the Settings page + the Shoots default channel (STORY_028)."""

from __future__ import annotations

import pytest

from app.config import get_settings
from app.services import preference_service


@pytest.fixture(autouse=True)
def _source_root(tmp_path, monkeypatch):
    """Two channels with one shoot each, so the default-channel select has options."""
    monkeypatch.setenv("SOURCE_ROOT", str(tmp_path))
    get_settings.cache_clear()
    for rel in ("only-gains-tv/26-orange", "youtube/26-yt-clip"):
        d = tmp_path / rel
        d.mkdir(parents=True)
        (d / "01.jpg").write_bytes(b"img")
    yield
    get_settings.cache_clear()


def test_settings_page_lists_channel_options(client):
    resp = client.get("/settings")
    assert resp.status_code == 200
    assert "Default channel" in resp.text
    assert 'action="/settings/default-channel"' in resp.text
    assert "All channels" in resp.text
    assert 'value="only-gains-tv"' in resp.text and 'value="youtube"' in resp.text


def test_save_default_channel_persists_and_redirects(client, db):
    resp = client.post(
        "/settings/default-channel", data={"channel": "youtube"}, follow_redirects=False
    )
    assert resp.status_code == 303
    assert resp.headers["location"] == "/settings"
    assert preference_service.get_preference(db, preference_service.DEFAULT_CHANNEL_KEY) == "youtube"
    # Reopening Settings shows the saved choice selected.
    page = client.get("/settings")
    assert 'value="youtube" selected' in page.text


def test_save_unknown_channel_rejected(client, db):
    resp = client.post(
        "/settings/default-channel", data={"channel": "not-a-channel"}, follow_redirects=False
    )
    assert resp.status_code == 303  # flashes the error, redirects back
    assert preference_service.get_preference(db, preference_service.DEFAULT_CHANNEL_KEY) == ""


def test_save_all_channels_clears_default(client, db):
    client.post("/settings/default-channel", data={"channel": "youtube"}, follow_redirects=False)
    client.post("/settings/default-channel", data={"channel": ""}, follow_redirects=False)
    assert preference_service.get_preference(db, preference_service.DEFAULT_CHANNEL_KEY) == ""


def test_shoots_page_preselects_saved_default(client, db):
    preference_service.set_preference(db, preference_service.DEFAULT_CHANNEL_KEY, "youtube")
    resp = client.get("/shoots")
    assert resp.status_code == 200
    assert 'value="youtube" selected' in resp.text  # the dropdown starts on the default
    assert "26-yt-clip" in resp.text  # youtube's shoot is listed
    assert "26-orange" not in resp.text  # the other channel is filtered out


def test_shoots_explicit_all_channels_overrides_default(client, db):
    preference_service.set_preference(db, preference_service.DEFAULT_CHANNEL_KEY, "youtube")
    resp = client.get("/shoots", params={"channel": ""})
    assert resp.status_code == 200
    assert "26-yt-clip" in resp.text and "26-orange" in resp.text  # everything shows


def test_shoots_stale_default_falls_back_to_all(client, db):
    preference_service.set_preference(db, preference_service.DEFAULT_CHANNEL_KEY, "gone-channel")
    resp = client.get("/shoots")
    assert resp.status_code == 200
    assert "No shoots match this filter" not in resp.text
    assert "26-yt-clip" in resp.text and "26-orange" in resp.text  # all channels shown
