"""Prompt inbox — paste, save, tag, and search markdown prompts.

Prompts are edited in a modal (their markdown bodies are too big for an inline
table row). Create and edit both submit to #modal; on success the server returns
only an out-of-band list, which closes the modal and refreshes the list.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import ValidationError

from app.dependencies import DbSession
from app.models.prompt import Prompt
from app.routes.common import field_errors
from app.schemas.prompt import PromptCreate, PromptUpdate
from app.services import prompt_service
from app.templating import templates, toast_trigger

router = APIRouter(tags=["prompts"])


def _get_or_404(db: DbSession, prompt_id: int) -> Prompt:
    prompt = prompt_service.get_prompt(db, prompt_id)
    if prompt is None:
        raise HTTPException(status_code=404, detail="Prompt not found")
    return prompt


# --- Page --------------------------------------------------------------------
@router.get("/prompts", response_class=HTMLResponse)
def prompts_page(request: Request, db: DbSession, q: str = "", status: str = "") -> HTMLResponse:
    prompts = prompt_service.list_prompts(db, search=q or None, status=status or None)
    return templates.TemplateResponse(
        request, "pages/prompts.html", {"prompts": prompts, "q": q, "status": status}
    )


# --- HTMX: live search / filter ----------------------------------------------
@router.get("/prompts/search", response_class=HTMLResponse)
def prompts_search(request: Request, db: DbSession, q: str = "", status: str = "") -> HTMLResponse:
    prompts = prompt_service.list_prompts(db, search=q or None, status=status or None)
    return templates.TemplateResponse(
        request, "partials/prompts/_list.html", {"prompts": prompts, "oob": False}
    )


# --- HTMX: create modal ------------------------------------------------------
@router.get("/prompts/new", response_class=HTMLResponse)
def prompts_new_form(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "partials/prompts/_form.html",
        {"prompt": None, "errors": {}, "values": {"status": "draft"}},
    )


@router.post("/prompts", response_class=HTMLResponse)
def prompts_create(
    request: Request,
    db: DbSession,
    title: Annotated[str, Form()] = "",
    body: Annotated[str, Form()] = "",
    tags: Annotated[str, Form()] = "",
    status: Annotated[str, Form()] = "draft",
) -> HTMLResponse:
    values = {"title": title, "body": body, "tags": tags, "status": status}
    try:
        data = PromptCreate(title=title.strip(), body=body, tags=tags.strip(), status=status)
    except ValidationError as exc:
        return templates.TemplateResponse(
            request,
            "partials/prompts/_form.html",
            {"prompt": None, "errors": field_errors(exc), "values": values},
            status_code=422,
        )

    prompt_service.create_prompt(db, data)
    prompts = prompt_service.list_prompts(db)
    return templates.TemplateResponse(
        request,
        "partials/prompts/_list.html",
        {"prompts": prompts, "oob": True},
        headers=toast_trigger("Prompt saved."),
    )


# --- HTMX: edit modal --------------------------------------------------------
@router.get("/prompts/{prompt_id}/edit", response_class=HTMLResponse)
def prompts_edit_form(request: Request, db: DbSession, prompt_id: int) -> HTMLResponse:
    prompt = _get_or_404(db, prompt_id)
    return templates.TemplateResponse(
        request,
        "partials/prompts/_form.html",
        {"prompt": prompt, "errors": {}, "values": {}},
    )


@router.put("/prompts/{prompt_id}", response_class=HTMLResponse)
def prompts_update(
    request: Request,
    db: DbSession,
    prompt_id: int,
    title: Annotated[str, Form()] = "",
    body: Annotated[str, Form()] = "",
    tags: Annotated[str, Form()] = "",
    status: Annotated[str, Form()] = "draft",
) -> HTMLResponse:
    prompt = _get_or_404(db, prompt_id)
    values = {"title": title, "body": body, "tags": tags, "status": status}
    try:
        data = PromptUpdate(title=title.strip(), body=body, tags=tags.strip(), status=status)
    except ValidationError as exc:
        return templates.TemplateResponse(
            request,
            "partials/prompts/_form.html",
            {"prompt": prompt, "errors": field_errors(exc), "values": values},
            status_code=422,
        )

    prompt_service.update_prompt(db, prompt, data)
    prompts = prompt_service.list_prompts(db)
    return templates.TemplateResponse(
        request,
        "partials/prompts/_list.html",
        {"prompts": prompts, "oob": True},
        headers=toast_trigger("Prompt updated."),
    )


# --- HTMX: delete ------------------------------------------------------------
@router.delete("/prompts/{prompt_id}", response_class=HTMLResponse)
def prompts_delete(request: Request, db: DbSession, prompt_id: int) -> HTMLResponse:
    prompt = _get_or_404(db, prompt_id)
    prompt_service.delete_prompt(db, prompt)
    prompts = prompt_service.list_prompts(db)
    return templates.TemplateResponse(
        request,
        "partials/prompts/_list.html",
        {"prompts": prompts, "oob": False},
        headers=toast_trigger("Prompt deleted.", "info"),
    )
