"""Jinja2 templating setup + small view helpers.

This centralizes the `templates` object so every route renders the same way and
shares the same global context (app settings, flash messages, HTMX detection).

Two patterns routes use:
  1. Full page:  `templates.TemplateResponse(request, "pages/x.html", {...})`
  2. HTMX partial: same call, but with a template under `partials/` that does
     NOT extend base.html — so only a fragment is returned and swapped in.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import Request
from fastapi.templating import Jinja2Templates

from app.config import get_settings

TEMPLATES_DIR = Path(__file__).parent / "templates"


# --- Context processors: injected into EVERY template render -----------------
def _settings_context(request: Request) -> dict[str, Any]:
    return {"settings": get_settings()}


def _request_context(request: Request) -> dict[str, Any]:
    """Expose handy request-derived values to templates."""
    return {
        "is_htmx": request.headers.get("HX-Request") == "true",
        "current_path": request.url.path,
    }


def _flash_context(request: Request) -> dict[str, Any]:
    """Pop one-shot flash messages off the session so they show exactly once."""
    messages: list[dict[str, str]] = []
    if "session" in request.scope:
        messages = request.session.pop("_flashes", [])
    return {"flashed_messages": messages}


templates = Jinja2Templates(
    directory=str(TEMPLATES_DIR),
    context_processors=[_settings_context, _request_context, _flash_context],
)

# Reload templates from disk on each render in development (set on the Jinja
# Environment directly — Starlette's constructor signature varies by version).
templates.env.auto_reload = get_settings().is_development

# Make a couple of helpers available inside templates.
templates.env.globals["app_name"] = get_settings().app_name

# Domain vocabulary → labels, so templates can render friendly names for the
# controlled values stored on scripts, jobs, and tags.
from app import domain  # noqa: E402  (after templates is defined; avoids a cycle)

templates.env.globals.update(
    {
        "SCRIPT_STATUS_LABELS": domain.SCRIPT_STATUS_LABELS,
        "TAG_KIND_LABELS": domain.TAG_KIND_LABELS,
        "JOB_STATUS_LABELS": domain.JOB_STATUS_LABELS,
        "parse_tags": domain.parse_tags,
    }
)


# --- Flash messages ----------------------------------------------------------
def flash(request: Request, message: str, category: str = "info") -> None:
    """Queue a one-shot message to render on the next page the user sees.

    `category` is one of: "info" | "success" | "danger" (maps to styling in
    partials/_flash.html). Requires SessionMiddleware (added in main.py).
    """
    request.session.setdefault("_flashes", []).append({"message": message, "category": category})


def is_htmx(request: Request) -> bool:
    """True when the request came from HTMX (so we can return a partial)."""
    return request.headers.get("HX-Request") == "true"


def toast_trigger(message: str, category: str = "success") -> dict[str, str]:
    """Build an `HX-Trigger` response header that app.js turns into a toast.

    Pass the result as `headers=` to a TemplateResponse:

        return templates.TemplateResponse(..., headers=toast_trigger("Saved."))
    """
    return {"HX-Trigger": json.dumps({"toast": {"message": message, "category": category}})}
