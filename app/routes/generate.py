"""Script generator workspace.

A full-page form (works without JS): pick a source prompt, a target model, an
output format, and how many variations to generate. On submit we build N draft
scripts, save them to the library, and redirect there with a flash message.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from app.dependencies import DbSession
from app.domain import GENERATION_COUNTS, OUTPUT_FORMATS, TARGET_MODELS
from app.services import (
    generation_service,
    prompt_service,
    script_template_service,
)
from app.templating import flash, templates

router = APIRouter(tags=["generate"])


def _workspace_context(
    db: DbSession, *, values: dict | None = None, error: str | None = None
) -> dict:
    """Shared context for rendering the generator workspace."""
    merged = {
        "source": "",
        "title_base": "",
        "tags": "",
        "target_model": "generic",
        "output_format": "short-form",
        "count": 3,
        "template_id": "",
    }
    if values:
        merged.update(values)
    return {
        "prompts": prompt_service.list_prompts(db, limit=100),
        "script_templates": script_template_service.list_templates(db, limit=100),
        "values": merged,
        "error": error,
    }


@router.get("/generate", response_class=HTMLResponse)
def generate_page(
    request: Request,
    db: DbSession,
    prompt_id: int | None = None,
    template_id: int | None = None,
) -> HTMLResponse:
    values: dict = {}
    if prompt_id is not None:
        prompt = prompt_service.get_prompt(db, prompt_id)
        if prompt is not None:
            values = {"source": prompt.body, "title_base": prompt.title, "tags": prompt.tags}
    if template_id is not None:
        template = script_template_service.get_template(db, template_id)
        if template is not None:
            values["template_id"] = str(template.id)
            values.setdefault("target_model", template.target_model)
            values.setdefault("output_format", template.output_format)
    return templates.TemplateResponse(
        request, "pages/generate.html", _workspace_context(db, values=values)
    )


@router.post("/generate")
def generate_run(
    request: Request,
    db: DbSession,
    source: Annotated[str, Form()] = "",
    target_model: Annotated[str, Form()] = "generic",
    output_format: Annotated[str, Form()] = "short-form",
    count: Annotated[int, Form()] = 3,
    title_base: Annotated[str, Form()] = "",
    tags: Annotated[str, Form()] = "",
    template_id: Annotated[str, Form()] = "",
) -> Response:
    values = {
        "source": source,
        "title_base": title_base,
        "tags": tags,
        "target_model": target_model,
        "output_format": output_format,
        "count": count,
        "template_id": template_id,
    }

    error = _validate(source, target_model, output_format, count)
    template_body = ""
    if not error and template_id:
        template = script_template_service.get_template(db, int(template_id))
        if template is None:
            error = "That template no longer exists."
        else:
            template_body = template.body

    if error:
        return templates.TemplateResponse(
            request,
            "pages/generate.html",
            _workspace_context(db, values=values, error=error),
            status_code=422,
        )

    scripts = generation_service.create_scripts(
        db,
        source_prompt=source,
        target_model=target_model,
        output_format=output_format,
        count=count,
        title_base=title_base,
        tags=tags,
        template_body=template_body,
    )
    flash(request, f"Generated {len(scripts)} script{'s' if len(scripts) != 1 else ''}.", "success")
    return RedirectResponse("/scripts?status=draft", status_code=303)


def _validate(source: str, target_model: str, output_format: str, count: int) -> str | None:
    if not source.strip():
        return "Add a source prompt to generate from."
    if target_model not in TARGET_MODELS:
        return "Pick a valid target model."
    if output_format not in OUTPUT_FORMATS:
        return "Pick a valid output format."
    if count not in GENERATION_COUNTS:
        return "Pick a valid number of scripts."
    return None
