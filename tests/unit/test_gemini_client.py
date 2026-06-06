"""Unit tests for the Gemini client boundary.

The real ``google-genai`` SDK is replaced with a tiny fake injected into
``sys.modules``, so these run without the package installed and never make a live
call. They lock in STORY_011's behavior: an empty / blocked response becomes a
:class:`GenerationError` with a human-readable reason.
"""

from __future__ import annotations

import sys
import types as pytypes
from types import SimpleNamespace

import pytest

from app.services import gemini_client
from app.services.gemini_client import (
    GenerationError,
    RetryableError,
    _block_reason,
    _is_transient,
)

PNG = b"\x89PNG\r\n\x1a\n"


class _ApiError(Exception):
    """Stand-in for a google-genai APIError carrying an HTTP status code."""

    def __init__(self, code: int, message: str = ""):
        super().__init__(message or f"status {code}")
        self.code = code


def _install_fake_sdk(monkeypatch, response):
    """Make ``from google import genai`` return a client that yields ``response``.

    If ``response`` is an ``Exception`` it is raised from ``generate_content`` instead,
    so tests can exercise the transient/terminal SDK-error paths.
    """
    fake_types = pytypes.ModuleType("google.genai.types")

    class Part:
        @staticmethod
        def from_bytes(*, data, mime_type):
            return ("part", mime_type)

    fake_types.Part = Part

    class _Models:
        def generate_content(self, *, model, contents):
            if isinstance(response, Exception):
                raise response
            return response

    class Client:
        def __init__(self, *, api_key):
            self.models = _Models()

    fake_genai = pytypes.ModuleType("google.genai")
    fake_genai.Client = Client
    fake_genai.types = fake_types

    fake_google = pytypes.ModuleType("google")
    fake_google.genai = fake_genai

    monkeypatch.setitem(sys.modules, "google", fake_google)
    monkeypatch.setitem(sys.modules, "google.genai", fake_genai)
    monkeypatch.setitem(sys.modules, "google.genai.types", fake_types)


def _generate():
    return gemini_client.generate(
        prompt="hi", image_bytes=PNG, image_mime="image/png", model="m", api_key="k"
    )


# --- _block_reason -----------------------------------------------------------
def test_block_reason_reports_prompt_block():
    resp = SimpleNamespace(prompt_feedback=SimpleNamespace(block_reason="SAFETY"))
    assert _block_reason(resp) == "prompt blocked (SAFETY)"


def test_block_reason_reports_finish_reason():
    resp = SimpleNamespace(
        prompt_feedback=None, candidates=[SimpleNamespace(finish_reason="MAX_TOKENS")]
    )
    assert _block_reason(resp) == "finish_reason=MAX_TOKENS"


def test_block_reason_falls_back():
    assert _block_reason(SimpleNamespace()) == "no content returned"


# --- generate ----------------------------------------------------------------
def test_generate_returns_text(monkeypatch):
    _install_fake_sdk(monkeypatch, SimpleNamespace(text="a real script"))
    assert _generate() == "a real script"


def test_generate_raises_on_empty_text(monkeypatch):
    resp = SimpleNamespace(text="", prompt_feedback=SimpleNamespace(block_reason="SAFETY"))
    _install_fake_sdk(monkeypatch, resp)
    with pytest.raises(GenerationError) as exc:
        _generate()
    assert "prompt blocked (SAFETY)" in str(exc.value)


def test_generate_raises_when_text_access_throws(monkeypatch):
    class _Resp:
        prompt_feedback = None
        candidates = [SimpleNamespace(finish_reason="SAFETY")]

        @property
        def text(self):
            raise ValueError("no candidates")

    _install_fake_sdk(monkeypatch, _Resp())
    with pytest.raises(GenerationError) as exc:
        _generate()
    assert "finish_reason=SAFETY" in str(exc.value)


# --- transient classification (STORY_012) ------------------------------------
def test_is_transient_retries_rate_limit_and_5xx():
    assert _is_transient(_ApiError(429)) is True
    assert _is_transient(_ApiError(503)) is True


def test_is_transient_skips_client_errors():
    assert _is_transient(_ApiError(400)) is False
    assert _is_transient(_ApiError(403)) is False


def test_is_transient_detects_transport_failures_by_name():
    assert _is_transient(TimeoutError("slow")) is True
    assert _is_transient(ConnectionError("reset")) is True


def test_is_transient_false_for_generic_error():
    assert _is_transient(ValueError("bad input")) is False


def test_generate_wraps_transient_sdk_error_as_retryable(monkeypatch):
    _install_fake_sdk(monkeypatch, _ApiError(503, "server error"))
    with pytest.raises(RetryableError):
        _generate()


def test_generate_reraises_terminal_sdk_error(monkeypatch):
    _install_fake_sdk(monkeypatch, _ApiError(400, "bad request"))
    with pytest.raises(_ApiError):
        _generate()
