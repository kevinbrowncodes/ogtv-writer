"""Thin wrapper around the Google Gemini (``google-genai``) SDK.

The ONLY place that talks to the Gemini API. Kept tiny so tests mock ``generate``
at this boundary and never make a live, paid call. The SDK is imported lazily, so
importing the app at rest does not require the package to be installed.
"""

from __future__ import annotations

from typing import Any


class GenerationError(RuntimeError):
    """Raised when Gemini returns no usable content (e.g. a safety block)."""


# Models whose name contains any of these aren't general text generators
# (image / audio / tts / robotics / research / …) — hidden from the script picker.
_NON_TEXT_MARKERS = (
    "image",
    "tts",
    "audio",
    "embedding",
    "aqa",
    "robotics",
    "computer-use",
    "deep-research",
    "lyria",
    "gemma",
    "nano-banana",
    "-er-",
    "customtools",
    "antigravity",
)


def list_models(api_key: str) -> list[str]:
    """Return the Gemini text-generation models this key can use (best-effort).

    Keeps models that support ``generateContent`` and drops non-text modalities
    (see ``_NON_TEXT_MARKERS``). Returns ``[]`` on any error so callers can fall
    back gracefully. The SDK is imported lazily, same as ``generate``.
    """
    try:
        from google import genai

        client = genai.Client(api_key=api_key)
        names: list[str] = []
        for model in client.models.list():
            actions = getattr(model, "supported_actions", None) or []
            if "generateContent" not in actions:
                continue
            name = (model.name or "").split("/")[-1]
            if name and not any(marker in name for marker in _NON_TEXT_MARKERS):
                names.append(name)
        return sorted(names)
    except Exception:
        return []


def _block_reason(response: Any) -> str:
    """Best-effort explanation for an empty response (safety block, etc.)."""
    try:
        feedback = getattr(response, "prompt_feedback", None)
        if feedback is not None and getattr(feedback, "block_reason", None):
            return f"prompt blocked ({feedback.block_reason})"
        candidates = getattr(response, "candidates", None) or []
        if candidates and getattr(candidates[0], "finish_reason", None):
            return f"finish_reason={candidates[0].finish_reason}"
    except Exception:
        pass
    return "no content returned"


def generate(*, prompt: str, image_bytes: bytes, image_mime: str, model: str, api_key: str) -> str:
    """Send a prompt + image to Gemini and return the response text.

    Raises :class:`GenerationError` when the response carries no text (e.g. a safety
    block), or re-raises SDK/transport errors; the caller turns either into a failed job.
    """
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model=model,
        contents=[
            types.Part.from_bytes(data=image_bytes, mime_type=image_mime),
            prompt,
        ],
    )
    # `.text` can raise when a response was blocked and has no candidate.
    try:
        text = response.text
    except Exception:
        text = None
    if text and text.strip():
        return text
    raise GenerationError(f"Gemini returned no content — {_block_reason(response)}.")
