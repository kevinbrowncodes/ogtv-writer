"""Unit tests for the key/value preference service (STORY_028)."""

from __future__ import annotations

from app.services import preference_service


def test_get_returns_default_when_unset(db):
    assert preference_service.get_preference(db, "default_channel") == ""
    assert preference_service.get_preference(db, "default_channel", "fallback") == "fallback"


def test_set_then_get_roundtrip(db):
    preference_service.set_preference(db, "default_channel", "youtube")
    assert preference_service.get_preference(db, "default_channel") == "youtube"


def test_set_overwrites_existing_value(db):
    preference_service.set_preference(db, "default_channel", "youtube")
    preference_service.set_preference(db, "default_channel", "only-gains-tv")
    assert preference_service.get_preference(db, "default_channel") == "only-gains-tv"


def test_set_empty_clears_value(db):
    preference_service.set_preference(db, "default_channel", "youtube")
    preference_service.set_preference(db, "default_channel", "")
    assert preference_service.get_preference(db, "default_channel", "fallback") == ""
