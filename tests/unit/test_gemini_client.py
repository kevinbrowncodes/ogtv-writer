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
from app.services.gemini_client import GenerationError, _block_reason

PNG = b"\x89PNG\r\n\x1a\n"


def _install_fake_sdk(monkeypatch, response):
    """Make ``from google import genai`` return a client that yields ``response``."""
    fake_types = pytypes.ModuleType("google.genai.types")

    class Part:
        @staticmethod
        def from_bytes(*, data, mime_type):
            return ("part", mime_type)

    fake_types.Part = Part

    class _Models:
        def generate_content(self, *, model, contents):
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
