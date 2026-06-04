"""Unit tests for the Item service (no HTTP layer — just DB logic)."""

from __future__ import annotations

from app.schemas.item import ItemCreate, ItemUpdate
from app.services import item_service


def test_create_and_get_item(db):
    item = item_service.create_item(db, ItemCreate(title="Hello", description="World"))
    assert item.id is not None
    assert item.status == "active"

    fetched = item_service.get_item(db, item.id)
    assert fetched is not None
    assert fetched.title == "Hello"


def test_list_orders_newest_first(db):
    a = item_service.create_item(db, ItemCreate(title="First"))
    b = item_service.create_item(db, ItemCreate(title="Second"))
    items = item_service.list_items(db)
    assert [i.id for i in items] == [b.id, a.id]


def test_search_filters_by_title(db):
    item_service.create_item(db, ItemCreate(title="Apple pie"))
    item_service.create_item(db, ItemCreate(title="Banana bread"))

    results = item_service.list_items(db, search="apple")
    assert len(results) == 1
    assert results[0].title == "Apple pie"


def test_update_only_changes_provided_fields(db):
    item = item_service.create_item(db, ItemCreate(title="Original", description="keep me"))
    item_service.update_item(db, item, ItemUpdate(title="Renamed"))

    refreshed = item_service.get_item(db, item.id)
    assert refreshed.title == "Renamed"
    assert refreshed.description == "keep me"  # untouched


def test_delete_item(db):
    item = item_service.create_item(db, ItemCreate(title="Temp"))
    item_service.delete_item(db, item)
    assert item_service.get_item(db, item.id) is None


def test_status_breakdown(db):
    item_service.create_item(db, ItemCreate(title="a", status="active"))
    item_service.create_item(db, ItemCreate(title="b", status="active"))
    item_service.create_item(db, ItemCreate(title="c", status="archived"))

    breakdown = item_service.status_breakdown(db)
    assert breakdown == {"active": 2, "archived": 1}
