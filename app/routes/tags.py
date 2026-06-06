"""Tag catalog — the canonical themes / models / styles you reuse.

Intentionally lightweight: an inline add form plus delete. Tags are cheap, so
there's no edit flow — delete and re-add.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import ValidationError

from app.dependencies import DbSession
from app.models.tag import Tag
from app.schemas.tag import TagCreate
from app.services import tag_service
from app.templating import templates, toast_trigger

router = APIRouter(tags=["tags"])


def _get_or_404(db: DbSession, tag_id: int) -> Tag:
    tag = tag_service.get_tag(db, tag_id)
    if tag is None:
        raise HTTPException(status_code=404, detail="Tag not found")
    return tag


def _list_response(
    request: Request, db: DbSession, *, message: str, category: str = "success", status: int = 200
) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "partials/tags/_list.html",
        {"tags": tag_service.list_tags(db)},
        headers=toast_trigger(message, category),
        status_code=status,
    )


@router.get("/tags", response_class=HTMLResponse)
def tags_page(request: Request, db: DbSession) -> HTMLResponse:
    return templates.TemplateResponse(
        request, "pages/tags.html", {"tags": tag_service.list_tags(db)}
    )


@router.post("/tags", response_class=HTMLResponse)
def tags_create(
    request: Request,
    db: DbSession,
    name: Annotated[str, Form()] = "",
    kind: Annotated[str, Form()] = "theme",
) -> HTMLResponse:
    try:
        data = TagCreate(name=name.strip(), kind=kind)
    except ValidationError:
        return _list_response(
            request, db, message="Enter a tag name.", category="danger", status=422
        )

    if tag_service.get_by_name(db, data.name) is not None:
        return _list_response(request, db, message="That tag already exists.", category="info")

    tag_service.create_tag(db, data)
    return _list_response(request, db, message="Tag added.")


@router.delete("/tags/{tag_id}", response_class=HTMLResponse)
def tags_delete(request: Request, db: DbSession, tag_id: int) -> HTMLResponse:
    tag = _get_or_404(db, tag_id)
    tag_service.delete_tag(db, tag)
    return _list_response(request, db, message="Tag deleted.", category="info")
