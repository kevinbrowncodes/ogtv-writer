"""Integration tests for the Script library + detail actions."""

from __future__ import annotations

from app.schemas.script import ScriptCreate
from app.services import script_service

HX = {"HX-Request": "true"}


def _make(db, **kwargs):
    defaults = {"title": "Hero", "body": "# Hero\nbody"}
    defaults.update(kwargs)
    return script_service.create_script(db, ScriptCreate(**defaults))


def test_library_page_renders(client):
    resp = client.get("/scripts")
    assert resp.status_code == 200
    assert "Script library" in resp.text
    assert 'id="script-list"' in resp.text


def test_search_and_filter_fragment(client, db):
    _make(db, title="Sunrise", target_model="veo", status="ready")
    _make(db, title="Deadlift", target_model="wan", status="draft")

    resp = client.get("/scripts/search", params={"model": "veo"}, headers=HX)
    assert resp.status_code == 200
    assert "Sunrise" in resp.text
    assert "Deadlift" not in resp.text
    assert "<html" not in resp.text


def test_detail_page_renders(client, db):
    script = _make(db, title="Detail me")
    resp = client.get(f"/scripts/{script.id}")
    assert resp.status_code == 200
    assert "Detail me" in resp.text
    assert 'id="script-body"' in resp.text  # copy target present


def test_inline_status_change_stamps_used(client, db):
    script = _make(db, status="draft")
    resp = client.post(f"/scripts/{script.id}/status", data={"status": "used"}, headers=HX)
    assert resp.status_code == 200
    assert f'id="script-{script.id}"' in resp.text
    db.expunge_all()
    refreshed = script_service.get_script(db, script.id)
    assert refreshed.status == "used"
    assert refreshed.used_at is not None


def test_new_blank_script_redirects_to_edit(client, db):
    resp = client.post("/scripts/new", follow_redirects=False)
    assert resp.status_code == 303
    assert "/edit" in resp.headers["location"]


def test_update_persists_and_redirects(client, db):
    script = _make(db)
    resp = client.post(
        f"/scripts/{script.id}",
        data={
            "title": "Renamed",
            "body": "new body",
            "status": "ready",
            "target_model": "wan",
            "output_format": "montage",
            "tags": "gym",
            "notes": "note",
            "prompt_source": "src",
        },
        follow_redirects=False,
    )
    assert resp.status_code == 303
    assert resp.headers["location"] == f"/scripts/{script.id}"
    db.expunge_all()
    refreshed = script_service.get_script(db, script.id)
    assert refreshed.title == "Renamed"
    assert refreshed.target_model == "wan"


def test_export_returns_markdown_download(client, db):
    script = _make(db, title="My Script", body="# Heading\ncontent")
    resp = client.get(f"/scripts/{script.id}/export")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/markdown")
    assert "my-script.md" in resp.headers.get("content-disposition", "")
    assert "# Heading" in resp.text


def test_duplicate_redirects_to_copy(client, db):
    script = _make(db, title="Original")
    resp = client.post(f"/scripts/{script.id}/duplicate", follow_redirects=False)
    assert resp.status_code == 303
    db.expunge_all()
    assert script_service.count_scripts(db) == 2


def test_variations_creates_drafts(client, db):
    script = _make(db, body="# Scene\nathlete", target_model="veo", output_format="cinematic")
    resp = client.post(
        f"/scripts/{script.id}/variations", data={"count": 3}, follow_redirects=False
    )
    assert resp.status_code == 303
    db.expunge_all()
    assert script_service.count_scripts(db) == 4  # original + 3


def test_delete_via_htmx_refreshes_list(client, db):
    script = _make(db, title="Delete me")
    resp = client.request("DELETE", f"/scripts/{script.id}", headers=HX)
    assert resp.status_code == 200
    assert "Delete me" not in resp.text
    db.expunge_all()
    assert script_service.get_script(db, script.id) is None


def test_delete_from_detail_redirects(client, db):
    script = _make(db)
    resp = client.post(f"/scripts/{script.id}/delete", follow_redirects=False)
    assert resp.status_code == 303
    assert resp.headers["location"] == "/scripts"
