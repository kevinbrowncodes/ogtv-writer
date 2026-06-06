"""Shared domain vocabulary for OGTV Writer.

One place for the controlled values that show up across models, schemas,
services, and templates — and the human-readable labels for each. Keeping them
here means a new target model or output format is a one-line change that the
whole app (filters, badges, generator) picks up.

Templates get these as Jinja globals (registered in app/templating.py), e.g.:

    {{ MODEL_LABELS[script.target_model] }}
    {{ FORMAT_LABELS[script.output_format] }}
"""

from __future__ import annotations

# --- Target AI video models --------------------------------------------------
TARGET_MODELS = ("veo", "wan", "generic")
MODEL_LABELS: dict[str, str] = {
    "veo": "Google Veo",
    "wan": "Wan",
    "generic": "Generic",
}

# --- Output formats ----------------------------------------------------------
OUTPUT_FORMATS = ("short-form", "cinematic", "montage", "narrated", "shot-list")
FORMAT_LABELS: dict[str, str] = {
    "short-form": "Short-form",
    "cinematic": "Cinematic scene",
    "montage": "Montage",
    "narrated": "Narrated story",
    "shot-list": "Shot list",
}

# --- Script lifecycle --------------------------------------------------------
SCRIPT_STATUSES = ("draft", "ready", "used", "archived")
SCRIPT_STATUS_LABELS: dict[str, str] = {
    "draft": "Draft",
    "ready": "Ready",
    "used": "Used",
    "archived": "Archived",
}

# --- Prompt lifecycle --------------------------------------------------------
PROMPT_STATUSES = ("draft", "ready", "archived")
PROMPT_STATUS_LABELS: dict[str, str] = {
    "draft": "Draft",
    "ready": "Ready",
    "archived": "Archived",
}

# --- Script template categories ----------------------------------------------
TEMPLATE_CATEGORIES = ("general", "model-pattern", "shot-structure")
TEMPLATE_CATEGORY_LABELS: dict[str, str] = {
    "general": "General",
    "model-pattern": "Model pattern",
    "shot-structure": "Shot structure",
}

# --- Tag kinds ---------------------------------------------------------------
TAG_KINDS = ("theme", "model", "style")
TAG_KIND_LABELS: dict[str, str] = {
    "theme": "Theme",
    "model": "Model",
    "style": "Style",
}

# Counts of script generations offered in the workspace.
GENERATION_COUNTS = (1, 3, 5, 10)


def parse_tags(raw: str) -> list[str]:
    """Split a comma-separated tag string into a clean, de-duplicated list."""
    seen: list[str] = []
    for part in (raw or "").split(","):
        tag = part.strip()
        if tag and tag.lower() not in {t.lower() for t in seen}:
            seen.append(tag)
    return seen
