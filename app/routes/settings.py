"""App settings area.

OGTV Writer has no accounts, so "settings" is just a small read-only view of the
app's configuration (environment, feature flags) plus the appearance toggle. It
exists mainly as a place to grow studio-wide preferences later.
"""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from app.templating import templates

router = APIRouter(tags=["settings"])


@router.get("/settings", response_class=HTMLResponse)
def settings_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "pages/settings.html", {})
