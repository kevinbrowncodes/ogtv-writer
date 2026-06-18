"""Unit tests for the build-version stamp (app/version.py)."""

from __future__ import annotations

from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from app import version
from app.config import get_settings


def test_stamp_formats_eastern_datetime_as_yymmdd_hhmm() -> None:
    # An already-Eastern aware datetime formats straight through.
    eastern = datetime(2026, 6, 18, 9, 21, tzinfo=ZoneInfo("America/New_York"))
    assert version.current_build_stamp(eastern) == "260618-0921"


def test_stamp_converts_to_eastern_before_formatting() -> None:
    # 01:30 UTC on 2026-06-18 is 21:30 the PREVIOUS day in Eastern (EDT, UTC-4):
    # proves the function converts the zone, not just formats the wall clock.
    utc = datetime(2026, 6, 18, 1, 30, tzinfo=UTC)
    assert version.current_build_stamp(utc) == "260617-2130"


def test_resolve_uses_build_version_env_when_set(monkeypatch) -> None:
    monkeypatch.setenv("BUILD_VERSION", "991231-2359")
    get_settings.cache_clear()
    try:
        assert version.resolve_build_version() == "991231-2359"
    finally:
        get_settings.cache_clear()


def test_resolve_falls_back_to_startup_stamp_when_blank(monkeypatch) -> None:
    monkeypatch.setenv("BUILD_VERSION", "")
    get_settings.cache_clear()
    try:
        assert version.resolve_build_version() == version.STARTUP_BUILD_STAMP
    finally:
        get_settings.cache_clear()
