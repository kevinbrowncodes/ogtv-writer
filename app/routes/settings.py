"""App settings area.

OGTV Writer has no accounts, so "settings" is a small view of the app's
configuration (environment, feature flags) plus studio-wide operator
preferences — currently the Shoots page's default channel (STORY_028).
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app.config import get_settings
from app.dependencies import DbSession
from app.services import generation_service, preference_service, shoots
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
            "model_options": generation_service.model_options(),
            "env_default_model": get_settings().gemini_model,
            "default_model_pref": preference_service.get_preference(
                db, preference_service.DEFAULT_MODEL_KEY
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


@router.post("/settings/default-model")
def save_default_model(
    request: Request, db: DbSession, model: Annotated[str, Form()] = ""
) -> RedirectResponse:
    """Persist the model the pickers start on ("" = the .env default) — STORY_030."""
    if model and model not in generation_service.selectable_models():
        flash(request, f"'{model}' is not an available model.", "danger")
    else:
        preference_service.set_preference(db, preference_service.DEFAULT_MODEL_KEY, model)
        flash(
            request,
            f"Model pickers will start on '{model}'."
            if model
            else "Model pickers will use the app default.",
            "success",
        )
    return RedirectResponse("/settings", status_code=303)
