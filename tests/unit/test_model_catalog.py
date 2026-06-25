"""Unit tests for model listing/probing, the cached status, and price labels."""

from __future__ import annotations

import google.genai

from app.config import get_settings
from app.domain import price_label
from app.services import gemini_client, generation_service


# --- gemini_client.list_models / probe_models (SDK mocked) -------------------
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


def test_probe_models_ok_filters_and_sorts(monkeypatch):
    monkeypatch.setattr(google.genai, "Client", _FakeClient)
    probe = gemini_client.probe_models("k")
    assert probe.ok is True
    assert probe.reason == ""
    assert probe.models == ["gemini-2.5-flash", "gemini-2.5-pro"]


def test_probe_models_maps_invalid_key_to_reason(monkeypatch):
    def boom(*args, **kwargs):
        raise RuntimeError("400 INVALID_ARGUMENT ... 'reason': 'API_KEY_INVALID'")

    monkeypatch.setattr(google.genai, "Client", boom)
    probe = gemini_client.probe_models("k")
    assert probe.ok is False
    assert probe.models == []
    assert "API_KEY_INVALID" in probe.reason


def test_probe_models_maps_network_error_to_reason(monkeypatch):
    def boom(*args, **kwargs):
        raise ConnectionError("connection reset")

    monkeypatch.setattr(google.genai, "Client", boom)
    probe = gemini_client.probe_models("k")
    assert probe.ok is False
    assert "reach Gemini" in probe.reason


def test_probe_models_generic_error_reason(monkeypatch):
    def boom(*args, **kwargs):
        raise RuntimeError("something odd")

    monkeypatch.setattr(google.genai, "Client", boom)
    probe = gemini_client.probe_models("k")
    assert probe.ok is False
    assert "Gemini error" in probe.reason


# --- generation_service.gemini_status / available_models ---------------------
def test_gemini_status_caches_success_and_includes_default(monkeypatch):
    monkeypatch.setattr(generation_service, "_status_cache", None)
    monkeypatch.setenv("GEMINI_API_KEY", "k")
    get_settings.cache_clear()
    calls = {"n": 0}

    def fake_probe(_key):
        calls["n"] += 1
        return gemini_client.ModelProbe(
            models=["gemini-2.5-pro", "gemini-2.5-flash"], ok=True, reason=""
        )

    monkeypatch.setattr(generation_service.gemini_client, "probe_models", fake_probe)

    first = generation_service.gemini_status()
    second = generation_service.gemini_status()
    assert first.ok is True
    assert "gemini-2.5-flash" in first.models  # default present
    assert second == first
    assert calls["n"] == 1  # cached: probed once
    assert generation_service.available_models() == first.models  # delegates to status
    get_settings.cache_clear()


def test_gemini_status_rejected_key_falls_back_and_is_not_cached(monkeypatch):
    monkeypatch.setattr(generation_service, "_status_cache", None)
    monkeypatch.setenv("GEMINI_API_KEY", "k")
    get_settings.cache_clear()
    monkeypatch.setattr(
        generation_service.gemini_client,
        "probe_models",
        lambda _key: gemini_client.ModelProbe(
            models=[], ok=False, reason="API key rejected (API_KEY_INVALID)."
        ),
    )

    status = generation_service.gemini_status()
    assert status.ok is False
    assert status.models == [get_settings().gemini_model]  # default only
    assert "API_KEY_INVALID" in status.detail
    assert generation_service._status_cache is None  # failure isn't cached → self-heals
    assert generation_service.available_models() == [get_settings().gemini_model]
    get_settings.cache_clear()


def test_gemini_status_no_key(monkeypatch):
    monkeypatch.setattr(generation_service, "_status_cache", None)
    monkeypatch.setenv("GEMINI_API_KEY", "")
    get_settings.cache_clear()

    status = generation_service.gemini_status()
    assert status.ok is False
    assert "GEMINI_API_KEY" in status.detail
    assert status.models == [get_settings().gemini_model]
    assert generation_service._status_cache is None
    get_settings.cache_clear()


# --- domain.price_label ------------------------------------------------------
def test_price_label_known_model():
    label = price_label("gemini-2.5-flash")
    assert "in /" in label and "per 1M tok" in label


def test_price_label_unknown_model():
    assert price_label("gemini-9-imaginary") == "—"
