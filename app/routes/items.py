"""Items CRUD — the reference feature that demonstrates every HTMX pattern.

HTMX patterns shown here (see the matching templates for the client side):

  - hx-get          live search (`/items/search`) + load forms/rows
  - hx-post         create (`/items`) and toggle status
  - hx-put          inline edit save (`/items/{id}`)
  - hx-delete       delete (`/items/{id}`)
  - hx-target       swap into #modal, #item-list, or `closest tr`
  - hx-swap         outerHTML / innerHTML
  - hx-swap-oob     close the modal while updating the list (see `_list.html`)
  - HX-Trigger      server -> client "toast" event (see app.js)
  - loading states  hx-indicator on the search box

Copy this file as the blueprint for new entities; the names line up with the
service, schema, model, and templates.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import ValidationError

from app.dependencies import CurrentUser, DbSession
from app.models.item import Item
from app.schemas.item import ItemCreate, ItemUpdate
from app.services import item_service
from app.templating import templates, toast_trigger

router = APIRouter(tags=["items"])


# --- small helpers -----------------------------------------------------------
def _get_or_404(db: DbSession, item_id: int) -> Item:
    item = item_service.get_item(db, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    return item


def _field_errors(exc: ValidationError) -> dict[str, str]:
    """Flatten a pydantic ValidationError into {field: message} for templates."""
    errors: dict[str, str] = {}
    for err in exc.errors():
        field = str(err["loc"][-1]) if err["loc"] else "_"
        errors.setdefault(field, err["msg"])
    return errors


# --- Page --------------------------------------------------------------------
@router.get("/items", response_class=HTMLResponse)
def items_page(request: Request, db: DbSession, user: CurrentUser, q: str = "") -> HTMLResponse:
    """Full Items page (app shell + list)."""
    items = item_service.list_items(db, search=q or None)
    return templates.TemplateResponse(request, "pages/items.html", {"items": items, "q": q})


# --- HTMX: live search (hx-get) ----------------------------------------------
@router.get("/items/search", response_class=HTMLResponse)
def items_search(request: Request, db: DbSession, user: CurrentUser, q: str = "") -> HTMLResponse:
    """Return just the list, filtered. Bound to the search box's keyup."""
    items = item_service.list_items(db, search=q or None)
    return templates.TemplateResponse(
        request, "partials/items/_list.html", {"items": items, "oob": False}
    )


# --- HTMX: create modal (hx-get form, hx-post submit) ------------------------
@router.get("/items/new", response_class=HTMLResponse)
def items_new_form(request: Request, user: CurrentUser) -> HTMLResponse:
    """Return the create form, loaded into #modal."""
    return templates.TemplateResponse(
        request,
        "partials/items/_form.html",
        {"item": None, "errors": {}, "values": {"status": "active"}},
    )


@router.post("/items", response_class=HTMLResponse)
def items_create(
    request: Request,
    db: DbSession,
    user: CurrentUser,
    title: Annotated[str, Form()] = "",
    description: Annotated[str, Form()] = "",
    status: Annotated[str, Form()] = "active",
) -> HTMLResponse:
    values = {"title": title, "description": description, "status": status}
    try:
        data = ItemCreate(title=title.strip(), description=description.strip(), status=status)
    except ValidationError as exc:
        # Re-render the form inside the modal with inline errors.
        return templates.TemplateResponse(
            request,
            "partials/items/_form.html",
            {"item": None, "errors": _field_errors(exc), "values": values},
            status_code=422,
        )

    item_service.create_item(db, data)
    items = item_service.list_items(db)
    # Success: returning ONLY the out-of-band list update means the modal's
    # target (#modal) receives empty content and closes itself.
    return templates.TemplateResponse(
        request,
        "partials/items/_list.html",
        {"items": items, "oob": True},
        headers=toast_trigger("Item created."),
    )


# --- HTMX: inline edit (hx-get row form, hx-put save) ------------------------
@router.get("/items/{item_id}/edit", response_class=HTMLResponse)
def items_edit_form(
    request: Request, db: DbSession, user: CurrentUser, item_id: int
) -> HTMLResponse:
    """Swap a read-only row for an inline edit form (target: closest tr)."""
    item = _get_or_404(db, item_id)
    return templates.TemplateResponse(
        request, "partials/items/_row_edit.html", {"item": item, "errors": {}}
    )


@router.get("/items/{item_id}/row", response_class=HTMLResponse)
def items_row(request: Request, db: DbSession, user: CurrentUser, item_id: int) -> HTMLResponse:
    """Return the read-only row again (used by the edit form's Cancel button)."""
    item = _get_or_404(db, item_id)
    return templates.TemplateResponse(request, "partials/items/_row.html", {"item": item})


@router.put("/items/{item_id}", response_class=HTMLResponse)
def items_update(
    request: Request,
    db: DbSession,
    user: CurrentUser,
    item_id: int,
    title: Annotated[str, Form()] = "",
    description: Annotated[str, Form()] = "",
    status: Annotated[str, Form()] = "active",
) -> HTMLResponse:
    item = _get_or_404(db, item_id)
    try:
        data = ItemUpdate(title=title.strip(), description=description.strip(), status=status)
    except ValidationError as exc:
        return templates.TemplateResponse(
            request,
            "partials/items/_row_edit.html",
            {"item": item, "errors": _field_errors(exc)},
            status_code=422,
        )
    item = item_service.update_item(db, item, data)
    return templates.TemplateResponse(
        request, "partials/items/_row.html", {"item": item}, headers=toast_trigger("Item updated.")
    )


# --- HTMX: inline status toggle (hx-post) ------------------------------------
@router.post("/items/{item_id}/toggle", response_class=HTMLResponse)
def items_toggle(request: Request, db: DbSession, user: CurrentUser, item_id: int) -> HTMLResponse:
    item = _get_or_404(db, item_id)
    new_status = "archived" if item.status == "active" else "active"
    item = item_service.update_item(db, item, ItemUpdate(status=new_status))
    return templates.TemplateResponse(
        request,
        "partials/items/_row.html",
        {"item": item},
        headers=toast_trigger(f"Marked {new_status}.", "info"),
    )


# --- HTMX: delete (hx-delete) ------------------------------------------------
@router.delete("/items/{item_id}", response_class=HTMLResponse)
def items_delete(request: Request, db: DbSession, user: CurrentUser, item_id: int) -> HTMLResponse:
    item = _get_or_404(db, item_id)
    item_service.delete_item(db, item)
    items = item_service.list_items(db)
    return templates.TemplateResponse(
        request,
        "partials/items/_list.html",
        {"items": items, "oob": False},
        headers=toast_trigger("Item deleted.", "info"),
    )
