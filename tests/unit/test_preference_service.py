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


# --- STORY_030: the effective default model -----------------------------------


def test_default_model_unset_uses_env_default(db):
    from app.config import get_settings
    from app.services import generation_service

    assert generation_service.default_model(db) == get_settings().gemini_model


def test_default_model_saved_and_selectable_wins(db, monkeypatch):
    from app.services import generation_service

    monkeypatch.setattr(
        generation_service, "selectable_models", lambda: ["gemini-2.5-flash", "gemini-2.5-pro"]
    )
    preference_service.set_preference(db, preference_service.DEFAULT_MODEL_KEY, "gemini-2.5-pro")
    assert generation_service.default_model(db) == "gemini-2.5-pro"


def test_default_model_stale_falls_back_to_env_default(db):
    from app.config import get_settings
    from app.services import generation_service

    # No API key in tests → only the .env model is selectable, so a saved local
    # model that no longer exists must fall back rather than stick.
    preference_service.set_preference(db, preference_service.DEFAULT_MODEL_KEY, "local:gone")
    assert generation_service.default_model(db) == get_settings().gemini_model
