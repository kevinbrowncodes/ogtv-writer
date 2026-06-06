"""Generation jobs — submit a (prompt + image + addendum + count) and queue it.

STORY_002: this builds the submission form and the queue list, and persists jobs
as ``queued``. The background worker that actually runs them arrives in STORY_003.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from pydantic import ValidationError

from app.dependencies import DbSession
from app.routes.common import field_errors
from app.schemas.job import JobCreate
from app.services import job_service, prompt_catalog
from app.services.uploads import UploadError, save_upload
from app.templating import flash, templates

router = APIRouter(tags=["jobs"])


@router.get("/jobs", response_class=HTMLResponse)
def jobs_page(request: Request, db: DbSession) -> HTMLResponse:
    return templates.TemplateResponse(
        request, "pages/jobs.html", {"jobs": job_service.list_jobs(db)}
    )


@router.get("/jobs/new", response_class=HTMLResponse)
def job_new_page(request: Request, prompt: str = "") -> HTMLResponse:
    selected = prompt_catalog.get_prompt(prompt) if prompt else None
    return templates.TemplateResponse(
        request,
        "pages/job_new.html",
        {
            "prompts": prompt_catalog.list_prompts(),
            "selected": selected,
            "values": {"prompt_slug": prompt, "addendum": "", "count": ""},
            "errors": {},
        },
    )


@router.get("/jobs/new/count-field", response_class=HTMLResponse)
def job_count_field(request: Request, prompt_slug: str = "") -> HTMLResponse:
    """HTMX partial: the count input, rendered only when the prompt uses {{COUNT}}."""
    selected = prompt_catalog.get_prompt(prompt_slug) if prompt_slug else None
    return templates.TemplateResponse(
        request,
        "partials/jobs/_count_field.html",
        {"selected": selected, "values": {"count": ""}, "errors": {}},
    )


@router.post("/jobs")
def jobs_create(
    request: Request,
    db: DbSession,
    prompt_slug: Annotated[str, Form()] = "",
    addendum: Annotated[str, Form()] = "",
    count: Annotated[str, Form()] = "",
    image: Annotated[UploadFile | None, File()] = None,
) -> Response:
    selected = prompt_catalog.get_prompt(prompt_slug) if prompt_slug else None
    values = {"prompt_slug": prompt_slug, "addendum": addendum, "count": count}
    errors: dict[str, str] = {}

    if selected is None:
        errors["prompt_slug"] = "Pick a valid prompt."

    # Count is only meaningful for prompts that declare a {{COUNT}} placeholder.
    parsed_count: int | None = None
    if selected is not None and selected.has_count:
        if count.strip().isdigit() and int(count) >= 1:
            parsed_count = int(count)
        else:
            errors["count"] = "Enter how many scripts to generate (1 or more)."

    # Validate field bounds (addendum length, count ceiling) via the schema.
    if selected is not None:
        try:
            JobCreate(prompt_slug=selected.slug, addendum=addendum, count=parsed_count)
        except ValidationError as exc:
            for field, message in field_errors(exc).items():
                errors.setdefault(field, message)

    # Only touch disk once the rest validates, so failures never orphan a file.
    image_path = image_filename = ""
    if not errors:
        try:
            image_path, image_filename = save_upload(image)
        except UploadError as exc:
            errors["image"] = str(exc)

    if errors:
        return templates.TemplateResponse(
            request,
            "pages/job_new.html",
            {
                "prompts": prompt_catalog.list_prompts(),
                "selected": selected,
                "values": values,
                "errors": errors,
            },
            status_code=422,
        )

    assert selected is not None  # guaranteed: no errors means a valid prompt
    job_service.create_job(
        db,
        prompt_slug=selected.slug,
        prompt_filename=selected.filename,
        addendum=addendum.strip(),
        count=parsed_count,
        image_path=image_path,
        image_filename=image_filename,
    )
    flash(request, "Job queued.", "success")
    return RedirectResponse("/jobs", status_code=303)
