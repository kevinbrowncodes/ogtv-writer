"""Integration tests for the Items CRUD + HTMX interactions.

These exercise the same endpoints the browser hits, asserting on the HTML
fragments and HTMX response headers the server returns.
"""

from __future__ import annotations

from app.schemas.item import ItemCreate
from app.services import item_service

HX = {"HX-Request": "true"}


def test_items_page_renders(auth_client):
    resp = auth_client.get("/items")
    assert resp.status_code == 200
    assert "Items" in resp.text
    assert 'id="item-list"' in resp.text


def test_create_item_returns_oob_list_and_toast(auth_client):
    resp = auth_client.post(
        "/items",
        data={"title": "Brand new", "description": "made via htmx", "status": "active"},
        headers=HX,
    )
    assert resp.status_code == 200
    # Out-of-band swap closes the modal while refreshing the list.
    assert 'hx-swap-oob="true"' in resp.text
    assert 'id="item-list"' in resp.text
    assert "Brand new" in resp.text
    # Server asks the client to show a toast.
    assert "toast" in resp.headers.get("HX-Trigger", "")


def test_create_item_validation_error_rerenders_form(auth_client):
    resp = auth_client.post(
        "/items",
        data={"title": "", "description": "", "status": "active"},
        headers=HX,
    )
    assert resp.status_code == 422
    assert 'hx-post="/items"' in resp.text  # the form came back
    assert "field-error" in resp.text  # with an inline error


def test_live_search_returns_filtered_fragment(auth_client, db):
    item_service.create_item(db, ItemCreate(title="Apple pie"))
    item_service.create_item(db, ItemCreate(title="Banana bread"))

    resp = auth_client.get("/items/search", params={"q": "apple"}, headers=HX)
    assert resp.status_code == 200
    assert "Apple pie" in resp.text
    assert "Banana bread" not in resp.text
    assert "<html" not in resp.text  # fragment only


def test_new_form_is_a_modal(auth_client):
    resp = auth_client.get("/items/new", headers=HX)
    assert resp.status_code == 200
    assert "data-modal-overlay" in resp.text
    assert 'hx-post="/items"' in resp.text


def test_toggle_status(auth_client, db):
    item = item_service.create_item(db, ItemCreate(title="Toggle me", status="active"))
    resp = auth_client.post(f"/items/{item.id}/toggle", headers=HX)
    assert resp.status_code == 200
    assert "Archived" in resp.text
    assert f'id="item-{item.id}"' in resp.text


def test_inline_edit_flow(auth_client, db):
    item = item_service.create_item(db, ItemCreate(title="Editable"))

    # Load the inline edit form.
    edit = auth_client.get(f"/items/{item.id}/edit", headers=HX)
    assert edit.status_code == 200
    assert 'name="title"' in edit.text

    # Save changes (HTMX uses PUT).
    saved = auth_client.put(
        f"/items/{item.id}",
        data={"title": "Edited title", "description": "", "status": "active"},
        headers=HX,
    )
    assert saved.status_code == 200
    assert "Edited title" in saved.text
    assert f'hx-get="/items/{item.id}/edit"' in saved.text  # back to read-only row


def test_delete_item(auth_client, db):
    item = item_service.create_item(db, ItemCreate(title="Delete me"))
    resp = auth_client.request("DELETE", f"/items/{item.id}", headers=HX)
    assert resp.status_code == 200
    assert "Delete me" not in resp.text  # removed from the refreshed list
    # The route deletes via its own session; drop this session's cached copy so
    # the check reads fresh from the DB rather than the identity map.
    db.expunge_all()
    assert item_service.get_item(db, item.id) is None
