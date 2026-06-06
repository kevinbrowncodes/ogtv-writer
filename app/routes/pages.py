"""Top-level pages: landing redirect + dashboard.

The dashboard demonstrates HTMX *polling*: the stat cards refresh themselves on
an interval via `hx-trigger="every 10s"` pointing at `/dashboard/stats`.
"""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app.config import get_settings
from app.dependencies import DbSession
from app.services import job_service, script_service
from app.templating import templates

router = APIRouter(tags=["pages"])


@router.get("/", include_in_schema=False)
def index() -> RedirectResponse:
    """No login here — go straight to the dashboard."""
    return RedirectResponse("/dashboard", status_code=303)


def _build_stats(db: DbSession) -> list[dict]:
    """Assemble the dashboard summary cards for the OGTV Writer workflow."""
    return [
        {
            "label": "Queued",
            "value": job_service.count_jobs(db, status="queued"),
            "hint": "Jobs waiting to run",
        },
        {
            "label": "Scripts",
            "value": script_service.count_scripts(db),
            "hint": "All scripts in the library",
        },
        {
            "label": "Ready",
            "value": script_service.count_scripts(db, status="ready"),
            "hint": "Scripts ready to shoot",
        },
        {
            "label": "Used",
            "value": script_service.count_scripts(db, status="used"),
            "hint": "Scripts already used",
        },
    ]


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request, db: DbSession) -> HTMLResponse:
    settings = get_settings()
    if not settings.feature_dashboard:
        return templates.TemplateResponse(request, "errors/404.html", {}, status_code=404)
    return templates.TemplateResponse(
        request,
        "pages/dashboard.html",
        {
            "stats": _build_stats(db),
            "recent_scripts": script_service.list_scripts(db, limit=6),
        },
    )


@router.get("/dashboard/stats", response_class=HTMLResponse)
def dashboard_stats(request: Request, db: DbSession) -> HTMLResponse:
    """HTMX partial: just the stat cards, polled by the dashboard page."""
    return templates.TemplateResponse(
        request, "partials/_stat_cards.html", {"stats": _build_stats(db)}
    )
