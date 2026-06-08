"""Shoots dashboard — discover shoot folders by channel and Run the pending ones.

Reads shoot status from the filesystem (does the folder have a script yet?) and turns
each pending shoot into a one-click Run that creates a folder-based job (STORY_009).
The prompt / model / count are chosen at run time via the picker on the page.
"""

from __future__ import annotations

from typing import Annotated
from urllib.parse import urlencode

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app.config import get_settings
from app.dependencies import DbSession
from app.services import generation_service, job_service, prompt_catalog, shoots
from app.templating import flash, templates, toast_trigger

router = APIRouter(tags=["shoots"])

MAX_ADDENDUM = 20000  # mirrors the JobCreate.addendum bound in app/schemas/job.py


def _queue_state(db: DbSession) -> dict:
    """Running/queued counts + whether the dashboard should keep polling."""
    running = job_service.count_jobs(db, status="running")
    queued = job_service.count_jobs(db, status="queued")
    return {"running": running, "queued": queued, "active": bool(running or queued)}


def _shoots_url(channel: str, date: str) -> str:
    """/shoots, carrying the active filter so a run/redirect doesn't reset the view."""
    query = urlencode({k: v for k, v in (("channel", channel), ("date", date)) if v})
    return f"/shoots?{query}" if query else "/shoots"


def _list_context(db: DbSession, channel: str, date: str) -> dict:
    """Shared context for every render of the shoots list (full page + partials).

    One filesystem scan feeds both the filter dropdowns (all channels / recent dates)
    and the filtered tables shown below them, keeping the active filter sticky.
    """
    all_channels = shoots.list_by_channel()
    return {
        "channels": shoots.filter_shoots(all_channels, channel, date),
        "channel_options": list(all_channels),
        "date_options": shoots.recent_dates(all_channels),
        "selected_channel": channel,
        "selected_date": date,
        **_queue_state(db),
    }


@router.get("/shoots", response_class=HTMLResponse)
def shoots_page(request: Request, db: DbSession, channel: str = "", date: str = "") -> HTMLResponse:
    context = _list_context(db, channel, date)
    return templates.TemplateResponse(
        request,
        "pages/shoots.html",
        {
            **context,
            "has_shoots": bool(context["channel_options"]),
            "prompts": prompt_catalog.list_prompts(),
            "models": generation_service.available_models(),
            "default_model": get_settings().gemini_model,
            "source_root": get_settings().source_root,
        },
    )


@router.get("/shoots/list", response_class=HTMLResponse)
def shoots_list(request: Request, db: DbSession, channel: str = "", date: str = "") -> HTMLResponse:
    """The channel tables on their own — HTMX swap/poll target, honouring the filter."""
    return templates.TemplateResponse(
        request,
        "partials/shoots/_list.html",
        _list_context(db, channel, date),
    )


def _queue_shoot(
    db: DbSession, *, rel_dir: str, prompt_slug: str, model: str, count: str
) -> str | None:
    """Create a folder job for one shoot. Returns an error message, or None on success.

    The shoot's saved context (context.txt) is reused as the job addendum.
    """
    shoot = shoots.resolve(rel_dir)
    if shoot is None:
        return f"'{rel_dir}' has no 01.* frame to run."
    prompt = prompt_catalog.get_prompt(prompt_slug)
    if prompt is None:
        return "Pick a valid prompt."
    parsed_count: int | None = None
    if prompt.has_count:
        if count.strip().isdigit() and int(count) >= 1:
            parsed_count = int(count)
        else:
            return "Enter how many scripts to generate (1 or more)."
    models = generation_service.available_models()
    chosen_model = model if model in models else get_settings().gemini_model
    job_service.create_job(
        db,
        prompt_slug=prompt.slug,
        prompt_filename=prompt.filename,
        addendum=shoot.context.strip(),
        count=parsed_count,
        image_path=shoots.frame_abspath(shoot),
        image_filename=shoot.frame or "",
        model=chosen_model,
        source_dir=shoot.rel_dir,
    )
    return None


@router.get("/shoots/context", response_class=HTMLResponse)
def shoots_context(request: Request, source_dir: str = "") -> HTMLResponse:
    """The per-shoot context editor (loaded into #modal by the +/✎ Context button)."""
    return templates.TemplateResponse(
        request,
        "partials/shoots/_context_modal.html",
        {"shoot": shoots.resolve(source_dir), "source_dir": source_dir},
    )


@router.post("/shoots/context", response_class=HTMLResponse)
def shoots_save_context(
    request: Request,
    db: DbSession,
    source_dir: Annotated[str, Form()] = "",
    addendum: Annotated[str, Form()] = "",
    channel: Annotated[str, Form()] = "",
    date: Annotated[str, Form()] = "",
) -> HTMLResponse:
    """Save (or clear) a shoot's context, then re-render the list and close the modal."""
    if len(addendum) > MAX_ADDENDUM:
        message, category = f"Context is too long (max {MAX_ADDENDUM} characters).", "danger"
    elif not shoots.write_context(source_dir, addendum):
        message, category = f"'{source_dir}' has no 01.* frame.", "danger"
    else:
        message, category = (
            ("Context cleared." if not addendum.strip() else "Context saved."),
            "success",
        )
    return templates.TemplateResponse(
        request,
        "partials/shoots/_context_saved.html",
        _list_context(db, channel, date),
        headers=toast_trigger(message, category),
    )


@router.post("/shoots/run")
def shoots_run(
    request: Request,
    db: DbSession,
    source_dir: Annotated[str, Form()] = "",
    prompt_slug: Annotated[str, Form()] = "",
    model: Annotated[str, Form()] = "",
    count: Annotated[str, Form()] = "",
    channel: Annotated[str, Form()] = "",
    date: Annotated[str, Form()] = "",
) -> RedirectResponse:
    error = _queue_shoot(db, rel_dir=source_dir, prompt_slug=prompt_slug, model=model, count=count)
    flash(request, error or "Job queued.", "danger" if error else "success")
    return RedirectResponse(_shoots_url(channel, date), status_code=303)


@router.post("/shoots/run-all")
def shoots_run_all(
    request: Request,
    db: DbSession,
    prompt_slug: Annotated[str, Form()] = "",
    model: Annotated[str, Form()] = "",
    count: Annotated[str, Form()] = "",
    channel: Annotated[str, Form()] = "",
    date: Annotated[str, Form()] = "",
) -> RedirectResponse:
    # Scope to the currently visible (filtered) subset — what you see is what runs.
    visible = shoots.filter_shoots(shoots.list_by_channel(), channel, date)
    pending = [s for shoot_list in visible.values() for s in shoot_list if s.status == "pending"]
    queued = 0
    last_error: str | None = None
    for shoot in pending:
        error = _queue_shoot(
            db, rel_dir=shoot.rel_dir, prompt_slug=prompt_slug, model=model, count=count
        )
        if error:
            last_error = error
        else:
            queued += 1
    if queued:
        flash(request, f"Queued {queued} job{'s' if queued != 1 else ''}.", "success")
    else:
        flash(
            request, last_error or "No pending shoots to run.", "danger" if last_error else "info"
        )
    return RedirectResponse(_shoots_url(channel, date), status_code=303)
