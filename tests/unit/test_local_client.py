"""Unit tests for the local (DGX Spark) OpenAI-compatible client boundary (STORY_025).

The real ``openai`` SDK is replaced with a tiny fake injected into ``sys.modules``, so
these run without the package installed and never make a live call. Error classification
(``_classify``) is tested directly — no SDK needed.
"""

from __future__ import annotations

import base64
import sys
import types as pytypes
from types import SimpleNamespace

import pytest

from app.services import local_client
from app.services.local_client import (
    GenerationError,
    RetryableError,
    _classify,
    _extract_content,
)

PNG = b"\x89PNG\r\n\x1a\n\x00\x01\x02\x03"


class _ApiError(Exception):
    """Stand-in for an OpenAI APIStatusError carrying an HTTP status code."""

    def __init__(self, status_code: int, message: str = ""):
        super().__init__(message or f"status {status_code}")
        self.status_code = status_code


def _install_fake_openai(monkeypatch, *, response=None, error=None, models=None, capture=None):
    """Make ``from openai import OpenAI`` return a client with canned behaviour."""

    class _Completions:
        def create(self, **kwargs):
            if capture is not None:
                capture.update(kwargs)
            if error is not None:
                raise error
            return response

    class _Models:
        def list(self):
            if error is not None:
                raise error
            return iter(models or [])

    class OpenAI:
        def __init__(self, **kwargs):
            if capture is not None:
                capture.setdefault("_client", {}).update(kwargs)
            self.chat = SimpleNamespace(completions=_Completions())
            self.models = _Models()

    fake = pytypes.ModuleType("openai")
    fake.OpenAI = OpenAI
    monkeypatch.setitem(sys.modules, "openai", fake)


def _msg(content, *, reasoning=None):
    message = SimpleNamespace(content=content, reasoning=reasoning)
    return SimpleNamespace(choices=[SimpleNamespace(message=message)])


def _generate(**overrides):
    kwargs = {
        "prompt": "describe this",
        "image_bytes": PNG,
        "image_mime": "image/png",
        "model": "aeon-fast",
        "base_url": "http://spark-1.local:8003/v1",
        "api_key": "",
    }
    kwargs.update(overrides)
    return local_client.generate(**kwargs)


# --- generate: happy path + request shape ------------------------------------
def test_generate_returns_content(monkeypatch):
    _install_fake_openai(monkeypatch, response=_msg("a real script"))
    assert _generate() == "a real script"


def test_generate_sends_image_data_url_and_params(monkeypatch):
    capture: dict = {}
    _install_fake_openai(monkeypatch, response=_msg("ok"), capture=capture)
    _generate()

    # The client is built against the configured base URL, with a placeholder key + timeout.
    assert capture["_client"]["base_url"] == "http://spark-1.local:8003/v1"
    assert capture["_client"]["api_key"] == "not-needed"  # blank key → placeholder
    assert capture["_client"]["timeout"] == local_client.REQUEST_TIMEOUT

    assert capture["model"] == "aeon-fast"
    assert capture["max_tokens"] == local_client.DEFAULT_MAX_TOKENS
    assert capture["temperature"] == local_client.DEFAULT_TEMPERATURE

    parts = capture["messages"][0]["content"]
    text_part = next(p for p in parts if p["type"] == "text")
    image_part = next(p for p in parts if p["type"] == "image_url")
    assert text_part["text"] == "describe this"
    url = image_part["image_url"]["url"]
    assert url.startswith("data:image/png;base64,")
    assert base64.b64decode(url.split(",", 1)[1]) == PNG


def test_generate_strips_content_and_ignores_reasoning(monkeypatch):
    # Content leads with whitespace and there's a separate `reasoning` field we must ignore.
    _install_fake_openai(
        monkeypatch, response=_msg("\n\nthe body\n\n", reasoning="chain of thought")
    )
    assert _generate() == "the body"


def test_generate_blank_content_raises_generation_error(monkeypatch):
    _install_fake_openai(monkeypatch, response=_msg("   "))
    with pytest.raises(GenerationError):
        _generate()


def test_generate_none_content_raises_generation_error(monkeypatch):
    _install_fake_openai(monkeypatch, response=_msg(None))
    with pytest.raises(GenerationError):
        _generate()


# --- generate: error mapping through the SDK ---------------------------------
def test_generate_wraps_transient_status_as_retryable(monkeypatch):
    _install_fake_openai(monkeypatch, error=_ApiError(503, "server error"))
    with pytest.raises(RetryableError):
        _generate()


def test_generate_wraps_bad_request_as_generation_error(monkeypatch):
    # 400 (context overflow / malformed image) is terminal — retrying can't help.
    _install_fake_openai(monkeypatch, error=_ApiError(400, "bad request"))
    with pytest.raises(GenerationError):
        _generate()


# --- _classify (pure, no SDK) ------------------------------------------------
@pytest.mark.parametrize("code", [408, 409, 425, 429, 500, 502, 503, 504])
def test_classify_transient_statuses_are_retryable(code):
    assert isinstance(_classify(_ApiError(code)), RetryableError)


@pytest.mark.parametrize("code", [400, 401, 403, 404, 413, 422])
def test_classify_other_4xx_are_terminal(code):
    assert isinstance(_classify(_ApiError(code)), GenerationError)


def test_classify_transport_failures_by_name_are_retryable():
    assert isinstance(_classify(TimeoutError("slow")), RetryableError)
    assert isinstance(_classify(ConnectionError("reset")), RetryableError)


def test_classify_unknown_error_passes_through():
    err = ValueError("weird")
    assert _classify(err) is err


# --- _extract_content --------------------------------------------------------
def test_extract_content_reads_and_strips():
    assert _extract_content(_msg("  hi  ")) == "hi"


def test_extract_content_missing_choices_is_empty():
    assert _extract_content(SimpleNamespace(choices=[])) == ""


# --- probe_models ------------------------------------------------------------
def test_probe_models_lists_ids(monkeypatch):
    models = [SimpleNamespace(id="aeon-ultimate"), SimpleNamespace(id="aeon-fast")]
    _install_fake_openai(monkeypatch, models=models)
    probe = local_client.probe_models("http://spark-1.local:8003/v1", "")
    assert probe.ok is True
    assert probe.models == ["aeon-ultimate", "aeon-fast"]


def test_probe_models_blank_base_url_is_not_ok():
    probe = local_client.probe_models("", "")
    assert probe.ok is False
    assert "LOCAL_MODEL_BASE_URL" in probe.reason


def test_probe_models_maps_network_error_to_reason(monkeypatch):
    _install_fake_openai(monkeypatch, error=ConnectionError("no route to host"))
    probe = local_client.probe_models("http://spark-1.local:8003/v1", "")
    assert probe.ok is False
    assert "local endpoint" in probe.reason
