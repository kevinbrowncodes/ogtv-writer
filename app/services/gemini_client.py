"""Thin wrapper around the Google Gemini (``google-genai``) SDK.

The ONLY place that talks to the Gemini API. Kept tiny so tests mock ``generate``
at this boundary and never make a live, paid call. The SDK is imported lazily, so
importing the app at rest does not require the package to be installed.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


class GenerationError(RuntimeError):
    """Raised when Gemini returns no usable content (e.g. a safety block).

    Terminal: the same prompt + frame blocks deterministically, so the worker does
    NOT retry it (STORY_012).
    """


class RetryableError(RuntimeError):
    """A transient Gemini failure (rate-limit / network / 5xx / timeout).

    The worker retries these up to ``MAX_ATTEMPTS`` (STORY_012).
    """


# HTTP statuses worth retrying: rate-limit, request timeout, conflict, and 5xx.
_TRANSIENT_STATUS = {408, 409, 425, 429, 500, 502, 503, 504}

# Substrings in an exception's type name that signal a transient transport failure
# (matched lower-cased), used when no HTTP status is exposed.
_TRANSIENT_NAME_MARKERS = (
    "timeout",
    "connection",
    "unavailable",
    "deadline",
    "resourceexhausted",
    "toomanyrequests",
)


def _is_transient(exc: Exception) -> bool:
    """Best-effort: is this Gemini/transport error worth retrying?"""
    code = getattr(exc, "code", None)
    if not isinstance(code, int):
        code = getattr(exc, "status_code", None)
    if isinstance(code, int) and code in _TRANSIENT_STATUS:
        return True
    name = type(exc).__name__.lower()
    return any(marker in name for marker in _TRANSIENT_NAME_MARKERS)


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


@dataclass(frozen=True)
class ModelProbe:
    """Result of asking Gemini for the models a key can use.

    ``ok`` is False when the list couldn't be fetched, in which case ``models`` is
    empty and ``reason`` carries a short, operator-readable explanation (e.g. a
    rejected key) for the UI to surface (STORY_023).
    """

    models: list[str]
    ok: bool
    reason: str


def _probe_reason(exc: Exception) -> str:
    """Map a model-list failure to a short, operator-readable reason."""
    text = str(exc)
    if "API_KEY_INVALID" in text or "API key not valid" in text:
        return "API key rejected — check GEMINI_API_KEY (API_KEY_INVALID)."
    if "PERMISSION_DENIED" in text or "SERVICE_DISABLED" in text:
        return "Permission denied — the key can't access this project/API (PERMISSION_DENIED)."
    if _is_transient(exc):
        return "Couldn't reach Gemini (network or rate-limit error) — try again shortly."
    return f"Gemini error: {type(exc).__name__}."


def probe_models(api_key: str) -> ModelProbe:
    """Fetch the usable text-generation models for ``api_key``.

    Keeps models that support ``generateContent`` and drops non-text modalities (see
    ``_NON_TEXT_MARKERS``). Unlike :func:`list_models`, this does NOT swallow the cause:
    on failure it returns ``ok=False`` with a short ``reason``, so the UI can explain
    why only the default model is available. The SDK is imported lazily, same as
    ``generate``.
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
        return ModelProbe(models=sorted(names), ok=True, reason="")
    except Exception as exc:
        return ModelProbe(models=[], ok=False, reason=_probe_reason(exc))


def list_models(api_key: str) -> list[str]:
    """Return the Gemini text-generation models this key can use (best-effort).

    Thin wrapper over :func:`probe_models` for callers that only need the names;
    returns ``[]`` on any error (the reason is available via :func:`probe_models`).
    """
    return probe_models(api_key).models


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
    block — terminal), :class:`RetryableError` on a transient transport/API failure
    (retried by the worker), or re-raises other SDK errors as terminal failures.
    """
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=api_key)
    try:
        response = client.models.generate_content(
            model=model,
            contents=[
                types.Part.from_bytes(data=image_bytes, mime_type=image_mime),
                prompt,
            ],
        )
    except Exception as exc:
        if _is_transient(exc):
            raise RetryableError(str(exc)) from exc
        raise
    # `.text` can raise when a response was blocked and has no candidate.
    try:
        text = response.text
    except Exception:
        text = None
    if text and text.strip():
        return text
    raise GenerationError(f"Gemini returned no content — {_block_reason(response)}.")
