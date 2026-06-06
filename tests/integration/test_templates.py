"""Integration tests for the Script template library."""

from __future__ import annotations

from app.schemas.script_template import ScriptTemplateCreate
from app.services import script_template_service

HX = {"HX-Request": "true"}


def test_templates_page_renders(client):
    resp = client.get("/templates")
    assert resp.status_code == 200
    assert "Templates" in resp.text
    assert 'id="template-list"' in resp.text


def test_create_template_returns_oob_grid(client, db):
    resp = client.post(
        "/templates",
        data={
            "name": "Veo hero",
            "description": "cinematic",
            "category": "model-pattern",
            "target_model": "veo",
            "output_format": "cinematic",
            "body": "{subject}",
        },
        headers=HX,
    )
    assert resp.status_code == 200
    assert 'hx-swap-oob="true"' in resp.text
    assert "Veo hero" in resp.text
    db.expunge_all()
    assert script_template_service.count_templates(db) == 1


def test_create_template_validation_error(client):
    resp = client.post("/templates", data={"name": ""}, headers=HX)
    assert resp.status_code == 422
    assert "field-error" in resp.text


def test_edit_and_delete_template(client, db):
    template = script_template_service.create_template(
        db, ScriptTemplateCreate(name="Original", target_model="wan")
    )

    form = client.get(f"/templates/{template.id}/edit", headers=HX)
    assert form.status_code == 200
    assert f'hx-put="/templates/{template.id}"' in form.text

    client.put(
        f"/templates/{template.id}",
        data={
            "name": "Renamed",
            "description": "",
            "category": "general",
            "target_model": "wan",
            "output_format": "short-form",
            "body": "",
        },
        headers=HX,
    )
    db.expunge_all()
    assert script_template_service.get_template(db, template.id).name == "Renamed"

    client.request("DELETE", f"/templates/{template.id}", headers=HX)
    db.expunge_all()
    assert script_template_service.get_template(db, template.id) is None
