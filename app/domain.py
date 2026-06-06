"""Shared domain vocabulary for OGTV Writer.

One place for the controlled values that show up across models, schemas, services,
and templates — and the human-readable labels for each. The target model and output
format are no longer app concerns: they live inside each prompt file in
``app/static/prompts/`` (see the prompt catalog + generation service).

Templates get these as Jinja globals (registered in app/templating.py), e.g.:

    {{ SCRIPT_STATUS_LABELS[script.status] }}
    {{ JOB_STATUS_LABELS[job.status] }}
"""

from __future__ import annotations

# --- Script lifecycle --------------------------------------------------------
SCRIPT_STATUSES = ("draft", "ready", "used", "archived")
SCRIPT_STATUS_LABELS: dict[str, str] = {
    "draft": "Draft",
    "ready": "Ready",
    "used": "Used",
    "archived": "Archived",
}

# --- Job lifecycle -----------------------------------------------------------
JOB_STATUSES = ("queued", "running", "done", "failed")
JOB_STATUS_LABELS: dict[str, str] = {
    "queued": "Queued",
    "running": "Running",
    "done": "Done",
    "failed": "Failed",
}

# --- Tag kinds ---------------------------------------------------------------
TAG_KINDS = ("theme", "model", "style")
TAG_KIND_LABELS: dict[str, str] = {
    "theme": "Theme",
    "model": "Model",
    "style": "Style",
}


# --- Gemini model pricing (REFERENCE ONLY) -----------------------------------
# USD per 1M tokens. The Gemini API does not expose pricing, so this is a
# hand-maintained table — verify current numbers against
# https://ai.google.dev/gemini-api/docs/pricing. Models not listed render as "—".
GEMINI_PRICING: dict[str, dict[str, float]] = {
    "gemini-2.5-pro": {"input": 1.25, "output": 10.00},
    "gemini-2.5-flash": {"input": 0.30, "output": 2.50},
    "gemini-2.5-flash-lite": {"input": 0.10, "output": 0.40},
    "gemini-2.0-flash": {"input": 0.10, "output": 0.40},
    "gemini-2.0-flash-lite": {"input": 0.075, "output": 0.30},
}


def price_label(model: str) -> str:
    """Human-readable reference price for a model, or '—' if unknown.

    Approximate — see the note on GEMINI_PRICING. Example:
    ``$0.3 in / $2.5 out · per 1M tok``.
    """
    price = GEMINI_PRICING.get(model)
    if not price:
        return "—"
    return f"${price['input']:g} in / ${price['output']:g} out · per 1M tok"


def parse_tags(raw: str) -> list[str]:
    """Split a comma-separated tag string into a clean, de-duplicated list."""
    seen: list[str] = []
    for part in (raw or "").split(","):
        tag = part.strip()
        if tag and tag.lower() not in {t.lower() for t in seen}:
            seen.append(tag)
    return seen
