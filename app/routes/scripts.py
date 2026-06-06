"""Script library + detail.

The library page shows HTMX live-search and filters (status / model / tag) plus
inline status changes and delete. The detail page is where a single script is
viewed, edited, copied, exported as markdown, duplicated, and spun into more
variations.
"""

from __future__ import annotations

import re
from typing import Annotated

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, PlainTextResponse, RedirectResponse, Response
from pydantic import ValidationError

from app.dependencies import DbSession
from app.domain import SCRIPT_STATUSES
from app.models.script import Script
from app.routes.common import field_errors
from app.schemas.script import ScriptCreate, ScriptUpdate
from app.services import script_service
from app.templating import flash, templates, toast_trigger

router = APIRouter(tags=["scripts"])


def _get_or_404(db: DbSession, script_id: int) -> Script:
    script = script_service.get_script(db, script_id)
    if script is None:
        raise HTTPException(status_code=404, detail="Script not found")
    return script


def _filters(q: str, status: str, model: str, tag: str) -> dict:
    return {"q": q, "status": status, "model": model, "tag": tag}


# --- Library -----------------------------------------------------------------
@router.get("/scripts", response_class=HTMLResponse)
def scripts_page(
    request: Request,
    db: DbSession,
    q: str = "",
    status: str = "",
    model: str = "",
    tag: str = "",
) -> HTMLResponse:
    scripts = script_service.list_scripts(
        db, search=q or None, status=status or None, target_model=model or None, tag=tag or None
    )
    return templates.TemplateResponse(
        request,
        "pages/scripts.html",
        {"scripts": scripts, "filters": _filters(q, status, model, tag)},
    )


@router.get("/scripts/search", response_class=HTMLResponse)
def scripts_search(
    request: Request,
    db: DbSession,
    q: str = "",
    status: str = "",
    model: str = "",
    tag: str = "",
) -> HTMLResponse:
    scripts = script_service.list_scripts(
        db, search=q or None, status=status or None, target_model=model or None, tag=tag or None
    )
    return templates.TemplateResponse(
        request, "partials/scripts/_list.html", {"scripts": scripts, "oob": False}
    )


# --- Inline status change (HTMX) ---------------------------------------------
@router.post("/scripts/{script_id}/status", response_class=HTMLResponse)
def scripts_set_status(
    request: Request,
    db: DbSession,
    script_id: int,
    status: Annotated[str, Form()] = "draft",
) -> HTMLResponse:
    script = _get_or_404(db, script_id)
    if status in SCRIPT_STATUSES:
        script = script_service.update_script(db, script, ScriptUpdate(status=status))
    return templates.TemplateResponse(
        request,
        "partials/scripts/_row.html",
        {"script": script},
        headers=toast_trigger(f"Marked {status}.", "info"),
    )


# --- Delete (HTMX from the library) ------------------------------------------
@router.delete("/scripts/{script_id}", response_class=HTMLResponse)
def scripts_delete(request: Request, db: DbSession, script_id: int) -> HTMLResponse:
    script = _get_or_404(db, script_id)
    script_service.delete_script(db, script)
    scripts = script_service.list_scripts(db)
    return templates.TemplateResponse(
        request,
        "partials/scripts/_list.html",
        {"scripts": scripts, "oob": False},
        headers=toast_trigger("Script deleted.", "info"),
    )


# --- New blank script (manual authoring) -------------------------------------
@router.post("/scripts/new")
def scripts_new(request: Request, db: DbSession) -> RedirectResponse:
    script = script_service.create_script(
        db, ScriptCreate(title="Untitled script", body="", status="draft")
    )
    return RedirectResponse(f"/scripts/{script.id}/edit", status_code=303)


# --- Detail ------------------------------------------------------------------
@router.get("/scripts/{script_id}", response_class=HTMLResponse)
def scripts_detail(request: Request, db: DbSession, script_id: int) -> HTMLResponse:
    script = _get_or_404(db, script_id)
    return templates.TemplateResponse(request, "pages/script_detail.html", {"script": script})


@router.get("/scripts/{script_id}/edit", response_class=HTMLResponse)
def scripts_edit_page(request: Request, db: DbSession, script_id: int) -> HTMLResponse:
    script = _get_or_404(db, script_id)
    return templates.TemplateResponse(
        request, "pages/script_edit.html", {"script": script, "errors": {}, "values": None}
    )


@router.post("/scripts/{script_id}")
def scripts_update(
    request: Request,
    db: DbSession,
    script_id: int,
    title: Annotated[str, Form()] = "",
    body: Annotated[str, Form()] = "",
    status: Annotated[str, Form()] = "draft",
    target_model: Annotated[str, Form()] = "generic",
    output_format: Annotated[str, Form()] = "short-form",
    tags: Annotated[str, Form()] = "",
    notes: Annotated[str, Form()] = "",
    prompt_source: Annotated[str, Form()] = "",
) -> Response:
    script = _get_or_404(db, script_id)
    values = {
        "title": title,
        "body": body,
        "status": status,
        "target_model": target_model,
        "output_format": output_format,
        "tags": tags,
        "notes": notes,
        "prompt_source": prompt_source,
    }
    try:
        data = ScriptUpdate(
            title=title.strip(),
            body=body,
            status=status,
            target_model=target_model,
            output_format=output_format,
            tags=tags.strip(),
            notes=notes,
            prompt_source=prompt_source,
        )
    except ValidationError as exc:
        return templates.TemplateResponse(
            request,
            "pages/script_edit.html",
            {"script": script, "errors": field_errors(exc), "values": values},
            status_code=422,
        )

    script_service.update_script(db, script, data)
    flash(request, "Script saved.", "success")
    return RedirectResponse(f"/scripts/{script_id}", status_code=303)


# --- Export markdown ---------------------------------------------------------
@router.get("/scripts/{script_id}/export")
def scripts_export(db: DbSession, script_id: int) -> PlainTextResponse:
    script = _get_or_404(db, script_id)
    filename = f"{_slugify(script.title) or 'script'}.md"
    return PlainTextResponse(
        script.body,
        media_type="text/markdown",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# --- Duplicate ---------------------------------------------------------------
@router.post("/scripts/{script_id}/duplicate")
def scripts_duplicate(request: Request, db: DbSession, script_id: int) -> RedirectResponse:
    script = _get_or_404(db, script_id)
    copy = script_service.duplicate_script(db, script)
    flash(request, "Script duplicated.", "success")
    return RedirectResponse(f"/scripts/{copy.id}", status_code=303)


# --- Delete from the detail page (full-page redirect) ------------------------
@router.post("/scripts/{script_id}/delete")
def scripts_delete_redirect(request: Request, db: DbSession, script_id: int) -> RedirectResponse:
    script = _get_or_404(db, script_id)
    script_service.delete_script(db, script)
    flash(request, "Script deleted.", "info")
    return RedirectResponse("/scripts", status_code=303)


def _slugify(value: str) -> str:
    value = re.sub(r"[^\w\s-]", "", value.lower()).strip()
    return re.sub(r"[-\s]+", "-", value)[:60]
