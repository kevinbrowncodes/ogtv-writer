"""Shared error + probe types for the generation providers.

Both provider clients — ``gemini_client`` (Google) and ``local_client`` (the DGX
Spark, OpenAI-compatible) — raise the SAME two exceptions so the worker's retry loop
in ``generation_service`` is provider-agnostic:

- :class:`RetryableError` — a transient failure (rate-limit / network / 5xx / timeout);
  the worker retries it up to ``MAX_ATTEMPTS`` (STORY_012).
- :class:`GenerationError` — terminal (a safety block, a bad request, empty content);
  the worker fails the job immediately and does NOT retry.

``gemini_client`` re-exports these names, so existing imports keep working.
"""

from __future__ import annotations

from dataclasses import dataclass


class GenerationError(RuntimeError):
    """Terminal: the request can't produce content (safety block, bad request, empty)."""


class RetryableError(RuntimeError):
    """Transient (rate-limit / network / 5xx / timeout) — retried by the worker."""


@dataclass(frozen=True)
class ModelProbe:
    """Result of asking a provider which models are available.

    ``ok`` is False when the list couldn't be fetched, in which case ``models`` is
    empty and ``reason`` carries a short, operator-readable explanation for the UI.
    """

    models: list[str]
    ok: bool
    reason: str
