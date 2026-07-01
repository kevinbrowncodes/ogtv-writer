"""Thin wrapper around an OpenAI-compatible local endpoint (the DGX Spark, "AEON").

The ONLY place that talks to the local model API. Kept tiny so tests mock ``generate``
/ ``probe_models`` at this boundary and never hit the network. The ``openai`` SDK is
imported lazily, so importing the app at rest doesn't require the package installed.

Confirmed against the live box (STORY_025): base URL ``http://spark-1.local:8003/v1``,
no API key (send a placeholder), vision via the OpenAI ``image_url`` base64 data-part.
Responses carry a separate ``message.reasoning`` field we ignore, and ``content`` can
lead with whitespace, so we read only ``content`` and strip it.
"""

from __future__ import annotations

import base64
from typing import Any

from app.services.llm_errors import GenerationError, ModelProbe, RetryableError

# AEON generates ~37 tok/s; a long multi-script response can outrun the SDK's default
# timeout and surface as a spurious RetryableError, so we allow generous headroom (s).
REQUEST_TIMEOUT = 180.0

# Explicit generation defaults so local output length/temperature don't drift versus the
# Gemini path (this model emits a separate `reasoning` field and can run long).
DEFAULT_MAX_TOKENS = 8192
DEFAULT_TEMPERATURE = 0.7

# The OpenAI SDK requires a non-empty key; a LAN box ignores it.
_PLACEHOLDER_KEY = "not-needed"

# HTTP statuses worth retrying: request timeout, conflict, too-early, rate-limit, 5xx.
# Every OTHER 4xx (400 bad request / context overflow / malformed image) is TERMINAL.
_TRANSIENT_STATUS = {408, 409, 425, 429, 500, 502, 503, 504}

# Substrings in a transport exception's type name that signal a transient failure
# (matched lower-cased) when no HTTP status is exposed — e.g. APITimeoutError,
# APIConnectionError.
_TRANSIENT_NAME_MARKERS = ("timeout", "connection", "unavailable", "deadline")


def _status_code(exc: Exception) -> int | None:
    """Best-effort HTTP status from an OpenAI SDK error (APIStatusError.status_code)."""
    code = getattr(exc, "status_code", None)
    if not isinstance(code, int):
        code = getattr(exc, "code", None)
    return code if isinstance(code, int) else None


def _classify(exc: Exception) -> Exception:
    """Map a raw SDK/transport error to the exception the worker should see.

    - 408/409/425/429/5xx → :class:`RetryableError` (worker retries).
    - Any other 4xx (400 bad request, context overflow, malformed image) →
      :class:`GenerationError` (terminal — retrying can't help).
    - Timeouts / connection failures with no status → :class:`RetryableError`.
    - Anything else is returned unchanged so the real cause surfaces.
    """
    code = _status_code(exc)
    if isinstance(code, int):
        if code in _TRANSIENT_STATUS:
            return RetryableError(str(exc))
        if 400 <= code < 500:
            return GenerationError(f"Local model rejected the request (HTTP {code}): {exc}")
    name = type(exc).__name__.lower()
    if any(marker in name for marker in _TRANSIENT_NAME_MARKERS):
        return RetryableError(str(exc))
    return exc


def _extract_content(response: Any) -> str:
    """Read ONLY ``choices[0].message.content``, stripped; ignore any ``reasoning`` field."""
    try:
        content = response.choices[0].message.content
    except Exception:
        return ""
    return (content or "").strip()


def generate(
    *,
    prompt: str,
    image_bytes: bytes,
    image_mime: str,
    model: str,
    base_url: str,
    api_key: str,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    temperature: float = DEFAULT_TEMPERATURE,
    timeout: float = REQUEST_TIMEOUT,
) -> str:
    """Send a prompt + image to the local endpoint and return the response text.

    Raises :class:`RetryableError` on a transient transport/API failure (retried by the
    worker) and :class:`GenerationError` when the request is rejected (terminal) or the
    model returns no content.
    """
    from openai import OpenAI

    client = OpenAI(base_url=base_url, api_key=api_key or _PLACEHOLDER_KEY, timeout=timeout)
    data_url = f"data:{image_mime};base64,{base64.b64encode(image_bytes).decode('ascii')}"
    messages: list[Any] = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": data_url}},
            ],
        }
    ]
    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )
    except Exception as exc:
        raise _classify(exc) from exc
    content = _extract_content(response)
    if content:
        return content
    raise GenerationError("Local model returned no content.")


def _probe_reason(exc: Exception) -> str:
    """Map a model-list failure to a short, operator-readable reason."""
    name = type(exc).__name__.lower()
    if any(marker in name for marker in _TRANSIENT_NAME_MARKERS):
        return "Couldn't reach the local endpoint (network/timeout) — check LOCAL_MODEL_BASE_URL."
    return f"Local model error: {type(exc).__name__}."


def probe_models(base_url: str, api_key: str) -> ModelProbe:
    """Fetch the models the local endpoint offers (GET /v1/models).

    Returns ``ok=False`` with a short ``reason`` on any failure (unreachable box, etc.),
    so callers can degrade gracefully. The SDK is imported lazily, same as ``generate``.
    """
    if not base_url:
        return ModelProbe(models=[], ok=False, reason="No LOCAL_MODEL_BASE_URL configured.")
    try:
        from openai import OpenAI

        client = OpenAI(
            base_url=base_url, api_key=api_key or _PLACEHOLDER_KEY, timeout=REQUEST_TIMEOUT
        )
        names = [model.id for model in client.models.list()]
        return ModelProbe(models=names, ok=True, reason="")
    except Exception as exc:
        return ModelProbe(models=[], ok=False, reason=_probe_reason(exc))
