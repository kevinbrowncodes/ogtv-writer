"""Script templates — reusable script/prompt patterns for Veo, Wan, etc.

Same modal-based CRUD shape as Prompts. Each template can be dropped straight
into the generator ("Use in generator" links to /generate?template_id=...).
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import ValidationError

from app.dependencies import DbSession
from app.models.script_template import ScriptTemplate
from app.routes.common import field_errors
from app.schemas.script_template import ScriptTemplateCreate, ScriptTemplateUpdate
from app.services import script_template_service
from app.templating import templates, toast_trigger

router = APIRouter(tags=["templates"])


def _get_or_404(db: DbSession, template_id: int) -> ScriptTemplate:
    template = script_template_service.get_template(db, template_id)
    if template is None:
        raise HTTPException(status_code=404, detail="Template not found")
    return template


@router.get("/templates", response_class=HTMLResponse)
def templates_page(
    request: Request, db: DbSession, q: str = "", category: str = ""
) -> HTMLResponse:
    items = script_template_service.list_templates(db, search=q or None, category=category or None)
    return templates.TemplateResponse(
        request, "pages/templates.html", {"templates": items, "q": q, "category": category}
    )


@router.get("/templates/search", response_class=HTMLResponse)
def templates_search(
    request: Request, db: DbSession, q: str = "", category: str = ""
) -> HTMLResponse:
    items = script_template_service.list_templates(db, search=q or None, category=category or None)
    return templates.TemplateResponse(
        request, "partials/templates/_list.html", {"templates": items, "oob": False}
    )


@router.get("/templates/new", response_class=HTMLResponse)
def templates_new_form(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "partials/templates/_form.html",
        {
            "template": None,
            "errors": {},
            "values": {
                "category": "general",
                "target_model": "generic",
                "output_format": "short-form",
            },
        },
    )


@router.post("/templates", response_class=HTMLResponse)
def templates_create(
    request: Request,
    db: DbSession,
    name: Annotated[str, Form()] = "",
    description: Annotated[str, Form()] = "",
    category: Annotated[str, Form()] = "general",
    target_model: Annotated[str, Form()] = "generic",
    output_format: Annotated[str, Form()] = "short-form",
    body: Annotated[str, Form()] = "",
) -> HTMLResponse:
    values = {
        "name": name,
        "description": description,
        "category": category,
        "target_model": target_model,
        "output_format": output_format,
        "body": body,
    }
    try:
        data = ScriptTemplateCreate(
            name=name.strip(),
            description=description.strip(),
            category=category,
            target_model=target_model,
            output_format=output_format,
            body=body,
        )
    except ValidationError as exc:
        return templates.TemplateResponse(
            request,
            "partials/templates/_form.html",
            {"template": None, "errors": field_errors(exc), "values": values},
            status_code=422,
        )

    script_template_service.create_template(db, data)
    items = script_template_service.list_templates(db)
    return templates.TemplateResponse(
        request,
        "partials/templates/_list.html",
        {"templates": items, "oob": True},
        headers=toast_trigger("Template saved."),
    )


@router.get("/templates/{template_id}/edit", response_class=HTMLResponse)
def templates_edit_form(request: Request, db: DbSession, template_id: int) -> HTMLResponse:
    template = _get_or_404(db, template_id)
    return templates.TemplateResponse(
        request,
        "partials/templates/_form.html",
        {"template": template, "errors": {}, "values": {}},
    )


@router.put("/templates/{template_id}", response_class=HTMLResponse)
def templates_update(
    request: Request,
    db: DbSession,
    template_id: int,
    name: Annotated[str, Form()] = "",
    description: Annotated[str, Form()] = "",
    category: Annotated[str, Form()] = "general",
    target_model: Annotated[str, Form()] = "generic",
    output_format: Annotated[str, Form()] = "short-form",
    body: Annotated[str, Form()] = "",
) -> HTMLResponse:
    template = _get_or_404(db, template_id)
    values = {
        "name": name,
        "description": description,
        "category": category,
        "target_model": target_model,
        "output_format": output_format,
        "body": body,
    }
    try:
        data = ScriptTemplateUpdate(
            name=name.strip(),
            description=description.strip(),
            category=category,
            target_model=target_model,
            output_format=output_format,
            body=body,
        )
    except ValidationError as exc:
        return templates.TemplateResponse(
            request,
            "partials/templates/_form.html",
            {"template": template, "errors": field_errors(exc), "values": values},
            status_code=422,
        )

    script_template_service.update_template(db, template, data)
    items = script_template_service.list_templates(db)
    return templates.TemplateResponse(
        request,
        "partials/templates/_list.html",
        {"templates": items, "oob": True},
        headers=toast_trigger("Template updated."),
    )


@router.delete("/templates/{template_id}", response_class=HTMLResponse)
def templates_delete(request: Request, db: DbSession, template_id: int) -> HTMLResponse:
    template = _get_or_404(db, template_id)
    script_template_service.delete_template(db, template)
    items = script_template_service.list_templates(db)
    return templates.TemplateResponse(
        request,
        "partials/templates/_list.html",
        {"templates": items, "oob": False},
        headers=toast_trigger("Template deleted.", "info"),
    )
