"""Top-level pages: landing redirect + dashboard.

The dashboard demonstrates HTMX *polling*: the stat cards refresh themselves on
an interval via `hx-trigger="every 10s"` pointing at `/dashboard/stats`.
"""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import func, select

from app.config import get_settings
from app.dependencies import CurrentUser, DbSession, OptionalUser
from app.models.user import User
from app.services import item_service
from app.templating import templates

router = APIRouter(tags=["pages"])


@router.get("/", include_in_schema=False)
def index(user: OptionalUser) -> RedirectResponse:
    """Send people to the dashboard if signed in, otherwise to login."""
    target = "/dashboard" if user is not None else "/login"
    return RedirectResponse(target, status_code=303)


def _build_stats(db: DbSession) -> list[dict]:
    """Assemble the dashboard summary cards. Replace with your real metrics."""
    breakdown = item_service.status_breakdown(db)
    total_items = sum(breakdown.values())
    total_users = db.scalar(select(func.count()).select_from(User)) or 0
    return [
        {"label": "Total items", "value": total_items, "hint": "All items in the system"},
        {"label": "Active", "value": breakdown.get("active", 0), "hint": "Currently active"},
        {"label": "Archived", "value": breakdown.get("archived", 0), "hint": "Archived items"},
        {"label": "Users", "value": total_users, "hint": "Registered accounts"},
    ]


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request, db: DbSession, user: CurrentUser) -> HTMLResponse:
    settings = get_settings()
    if not settings.feature_dashboard:
        return templates.TemplateResponse(request, "errors/404.html", {}, status_code=404)
    return templates.TemplateResponse(
        request,
        "pages/dashboard.html",
        {
            "stats": _build_stats(db),
            "recent_items": item_service.list_items(db, limit=5),
        },
    )


@router.get("/dashboard/stats", response_class=HTMLResponse)
def dashboard_stats(request: Request, db: DbSession, user: CurrentUser) -> HTMLResponse:
    """HTMX partial: just the stat cards, polled by the dashboard page."""
    return templates.TemplateResponse(
        request, "partials/_stat_cards.html", {"stats": _build_stats(db)}
    )
