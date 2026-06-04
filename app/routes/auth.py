"""Authentication: login, logout, optional signup.

Login/logout use plain full-page form submits (no JS required) so auth works
even if scripts fail — progressive enhancement. The HTMX-heavy demos live in the
Items area instead.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from app.config import get_settings
from app.dependencies import SESSION_USER_KEY, DbSession, OptionalUser
from app.services import user_service
from app.templating import flash, templates

router = APIRouter(tags=["auth"])


def _safe_next(next_url: str | None) -> str:
    """Prevent open-redirects: only allow same-site relative paths."""
    if next_url and next_url.startswith("/") and not next_url.startswith("//"):
        return next_url
    return "/dashboard"


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request, user: OptionalUser, next: str = "") -> Response:
    if user is not None:  # already signed in
        return RedirectResponse(_safe_next(next), status_code=303)
    return templates.TemplateResponse(request, "pages/login.html", {"next": next, "error": None})


@router.post("/login", response_class=HTMLResponse)
def login_submit(
    request: Request,
    db: DbSession,
    email: Annotated[str, Form()],
    password: Annotated[str, Form()],
    next: Annotated[str, Form()] = "",
) -> Response:
    user = user_service.authenticate(db, email, password)
    if user is None:
        # Re-render with a generic error (don't reveal which field was wrong).
        return templates.TemplateResponse(
            request,
            "pages/login.html",
            {"next": next, "error": "Invalid email or password.", "email": email},
            status_code=401,
        )
    request.session[SESSION_USER_KEY] = user.id
    flash(request, f"Welcome back, {user.name or user.email}.", "success")
    return RedirectResponse(_safe_next(next), status_code=303)


@router.post("/logout")
def logout(request: Request) -> RedirectResponse:
    request.session.clear()
    flash(request, "You have been signed out.", "info")
    return RedirectResponse("/login", status_code=303)


# --- Optional signup (gated by FEATURE_SIGNUPS) ------------------------------
@router.get("/signup", response_class=HTMLResponse)
def signup_page(request: Request, user: OptionalUser) -> Response:
    settings = get_settings()
    if not settings.feature_signups:
        return templates.TemplateResponse(request, "errors/404.html", {}, status_code=404)
    if user is not None:
        return RedirectResponse("/dashboard", status_code=303)
    return templates.TemplateResponse(request, "pages/signup.html", {"error": None})


@router.post("/signup", response_class=HTMLResponse)
def signup_submit(
    request: Request,
    db: DbSession,
    email: Annotated[str, Form()],
    password: Annotated[str, Form()],
    name: Annotated[str, Form()] = "",
) -> Response:
    settings = get_settings()
    if not settings.feature_signups:
        return templates.TemplateResponse(request, "errors/404.html", {}, status_code=404)

    error: str | None = None
    if len(password) < 8:
        error = "Password must be at least 8 characters."
    elif user_service.get_by_email(db, email) is not None:
        error = "An account with that email already exists."

    if error:
        return templates.TemplateResponse(
            request,
            "pages/signup.html",
            {"error": error, "email": email, "name": name},
            status_code=400,
        )

    user = user_service.create_user(db, email=email, password=password, name=name)
    request.session[SESSION_USER_KEY] = user.id
    flash(request, "Account created. Welcome!", "success")
    return RedirectResponse("/dashboard", status_code=303)
