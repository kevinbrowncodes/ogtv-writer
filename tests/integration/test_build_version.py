"""Integration tests: the build stamp shows in the sidebar footer + /healthz."""

from __future__ import annotations

import re

from app.config import get_settings

STAMP_RE = re.compile(r"\d{6}-\d{4}")


def test_healthz_reports_a_build_stamp(client) -> None:
    data = client.get("/healthz").json()
    assert "build" in data
    assert STAMP_RE.fullmatch(data["build"])


def test_sidebar_footer_shows_build(client) -> None:
    html = client.get("/dashboard").text
    assert re.search(r"Build\s+\d{6}-\d{4}", html)


def test_build_version_env_is_surfaced(client, monkeypatch) -> None:
    monkeypatch.setenv("BUILD_VERSION", "991231-2359")
    get_settings.cache_clear()
    try:
        assert client.get("/healthz").json()["build"] == "991231-2359"
        assert "Build 991231-2359" in client.get("/dashboard").text
    finally:
        get_settings.cache_clear()
