"""User & app settings area.

Demonstrates HTMX *inline form updates*: each settings card posts to its own
endpoint and swaps itself with the server's response (success or error state),
so the page never fully reloads.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse

from app.dependencies import CurrentUser, DbSession
from app.security import verify_password
from app.services import user_service
from app.templating import templates, toast_trigger

router = APIRouter(tags=["settings"])


@router.get("/settings", response_class=HTMLResponse)
def settings_page(request: Request, user: CurrentUser) -> HTMLResponse:
    return templates.TemplateResponse(request, "pages/settings.html", {"user": user})


@router.post("/settings/profile", response_class=HTMLResponse)
def settings_update_profile(
    request: Request,
    db: DbSession,
    user: CurrentUser,
    name: Annotated[str, Form()] = "",
) -> HTMLResponse:
    error = None
    if len(name) > 120:
        error = "Name must be 120 characters or fewer."
    else:
        user_service.update_profile(db, user, name=name)

    return templates.TemplateResponse(
        request,
        "partials/settings/_profile_form.html",
        {"user": user, "saved": error is None, "error": error},
        headers=toast_trigger("Profile saved.") if error is None else None,
    )


@router.post("/settings/password", response_class=HTMLResponse)
def settings_update_password(
    request: Request,
    db: DbSession,
    user: CurrentUser,
    current_password: Annotated[str, Form()] = "",
    new_password: Annotated[str, Form()] = "",
) -> HTMLResponse:
    error = None
    if not verify_password(current_password, user.hashed_password):
        error = "Current password is incorrect."
    elif len(new_password) < 8:
        error = "New password must be at least 8 characters."
    else:
        user_service.set_password(db, user, new_password)

    return templates.TemplateResponse(
        request,
        "partials/settings/_password_form.html",
        {"saved": error is None, "error": error},
        headers=toast_trigger("Password updated.") if error is None else None,
    )
