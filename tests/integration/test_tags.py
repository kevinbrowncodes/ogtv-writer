"""Integration tests for the Tag catalog."""

from __future__ import annotations

from app.schemas.tag import TagCreate
from app.services import tag_service

HX = {"HX-Request": "true"}


def test_tags_page_renders(client):
    resp = client.get("/tags")
    assert resp.status_code == 200
    assert "Tags" in resp.text
    assert 'id="tag-list"' in resp.text


def test_create_tag(client, db):
    resp = client.post("/tags", data={"name": "sunrise", "kind": "theme"}, headers=HX)
    assert resp.status_code == 200
    assert "sunrise" in resp.text
    assert "toast" in resp.headers.get("HX-Trigger", "")
    db.expunge_all()
    assert tag_service.get_by_name(db, "sunrise") is not None


def test_create_duplicate_tag_is_rejected(client, db):
    tag_service.create_tag(db, TagCreate(name="gym", kind="theme"))
    resp = client.post("/tags", data={"name": "gym", "kind": "theme"}, headers=HX)
    assert resp.status_code == 200
    assert "already exists" in resp.headers.get("HX-Trigger", "")
    db.expunge_all()
    assert len(tag_service.list_tags(db)) == 1


def test_empty_name_rejected(client):
    resp = client.post("/tags", data={"name": "  ", "kind": "theme"}, headers=HX)
    assert resp.status_code == 422


def test_delete_tag(client, db):
    tag = tag_service.create_tag(db, TagCreate(name="temp", kind="style"))
    resp = client.request("DELETE", f"/tags/{tag.id}", headers=HX)
    assert resp.status_code == 200
    db.expunge_all()
    assert tag_service.get_tag(db, tag.id) is None
