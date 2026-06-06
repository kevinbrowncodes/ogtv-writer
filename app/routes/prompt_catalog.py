"""Prompt catalog — browse the reusable ``.md`` briefs in ``app/static/prompts/``.

Read-only: the filesystem is the source of truth (see
``app/services/prompt_catalog.py``). Pick a prompt here; a later story uses it to drive
a generation job.

Two routes:
  - ``GET /prompts``        — the catalog list + a preview panel.
  - ``GET /prompts/{slug}`` — a single prompt's full text, returned as an HTMX partial
                              (swapped into the panel) or as a full page on direct nav.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse

from app.services import prompt_catalog
from app.templating import is_htmx, templates

router = APIRouter(tags=["prompts"])


@router.get("/prompts", response_class=HTMLResponse)
def prompts_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request, "pages/prompt_catalog.html", {"prompts": prompt_catalog.list_prompts()}
    )


@router.get("/prompts/{slug}", response_class=HTMLResponse)
def prompt_preview(request: Request, slug: str) -> HTMLResponse:
    prompt = prompt_catalog.get_prompt(slug)
    if prompt is None:
        raise HTTPException(status_code=404, detail="Prompt not found")
    template = (
        "partials/prompt_catalog/_preview.html" if is_htmx(request) else "pages/prompt_preview.html"
    )
    return templates.TemplateResponse(request, template, {"prompt": prompt})
