"""Unit tests for model listing, the cached catalog, and price labels."""

from __future__ import annotations

import google.genai

from app.config import get_settings
from app.domain import price_label
from app.services import gemini_client, generation_service


# --- gemini_client.list_models (SDK mocked) ----------------------------------
class _FakeModel:
    def __init__(self, name, actions):
        self.name = name
        self.supported_actions = actions


class _FakeModels:
    def list(self):
        return iter(
            [
                _FakeModel("models/gemini-2.5-flash", ["generateContent"]),
                _FakeModel("models/gemini-2.5-pro", ["generateContent"]),
                _FakeModel("models/gemini-2.5-flash-image", ["generateContent"]),  # image → drop
                _FakeModel("models/lyria-3-pro-preview", ["generateContent"]),  # audio → drop
                _FakeModel("models/embedding-001", ["embedContent"]),  # no generateContent → drop
                _FakeModel("models/gemini-robotics-er-1.5-preview", ["generateContent"]),  # drop
            ]
        )


class _FakeClient:
    def __init__(self, *args, **kwargs):
        self.models = _FakeModels()


def test_list_models_keeps_only_text_gemini_models(monkeypatch):
    monkeypatch.setattr(google.genai, "Client", _FakeClient)
    assert gemini_client.list_models("k") == ["gemini-2.5-flash", "gemini-2.5-pro"]


def test_list_models_returns_empty_on_error(monkeypatch):
    def boom(*args, **kwargs):
        raise RuntimeError("no network")

    monkeypatch.setattr(google.genai, "Client", boom)
    assert gemini_client.list_models("k") == []


# --- generation_service.available_models -------------------------------------
def test_available_models_caches_and_includes_default(monkeypatch):
    monkeypatch.setattr(generation_service, "_models_cache", None)
    monkeypatch.setenv("GEMINI_API_KEY", "k")
    get_settings.cache_clear()
    calls = {"n": 0}

    def fake_list(_key):
        calls["n"] += 1
        return ["gemini-2.5-pro", "gemini-2.5-flash"]

    monkeypatch.setattr(generation_service.gemini_client, "list_models", fake_list)

    first = generation_service.available_models()
    second = generation_service.available_models()
    assert "gemini-2.5-flash" in first
    assert second == first
    assert calls["n"] == 1  # cached: only fetched once
    get_settings.cache_clear()


def test_available_models_falls_back_to_default_and_does_not_cache(monkeypatch):
    monkeypatch.setattr(generation_service, "_models_cache", None)
    monkeypatch.setenv("GEMINI_API_KEY", "k")
    get_settings.cache_clear()
    monkeypatch.setattr(generation_service.gemini_client, "list_models", lambda _key: [])

    out = generation_service.available_models()
    assert out == [get_settings().gemini_model]
    assert generation_service._models_cache is None  # fallback isn't cached
    get_settings.cache_clear()


# --- domain.price_label ------------------------------------------------------
def test_price_label_known_model():
    label = price_label("gemini-2.5-flash")
    assert "in /" in label and "per 1M tok" in label


def test_price_label_unknown_model():
    assert price_label("gemini-9-imaginary") == "—"
