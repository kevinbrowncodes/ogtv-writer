"""App settings area.

OGTV Writer has no accounts, so "settings" is a small view of the app's
configuration (environment, feature flags) plus studio-wide operator
preferences — currently the Shoots page's default channel (STORY_028).
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app.dependencies import DbSession
from app.services import preference_service, shoots
from app.templating import flash, templates

router = APIRouter(tags=["settings"])


@router.get("/settings", response_class=HTMLResponse)
def settings_page(request: Request, db: DbSession) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "pages/settings.html",
        {
            "channel_options": list(shoots.list_by_channel()),
            "default_channel": preference_service.get_preference(
                db, preference_service.DEFAULT_CHANNEL_KEY
            ),
        },
    )


@router.post("/settings/default-channel")
def save_default_channel(
    request: Request, db: DbSession, channel: Annotated[str, Form()] = ""
) -> RedirectResponse:
    """Persist the Shoots page's starting channel ("" = All channels)."""
    if channel and channel not in shoots.list_by_channel():
        flash(request, f"'{channel}' is not a known channel.", "danger")
    else:
        preference_service.set_preference(db, preference_service.DEFAULT_CHANNEL_KEY, channel)
        flash(
            request,
            f"Shoots will start on '{channel}'." if channel else "Shoots will start on all channels.",
            "success",
        )
    return RedirectResponse("/settings", status_code=303)
