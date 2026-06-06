"""Integration tests for the generator workspace."""

from __future__ import annotations

from app.schemas.prompt import PromptCreate
from app.services import prompt_service, script_service


def test_generate_page_renders(client):
    resp = client.get("/generate")
    assert resp.status_code == 200
    assert "Generate scripts" in resp.text
    assert 'name="source"' in resp.text


def test_generate_page_prefills_from_prompt(client, db):
    prompt = prompt_service.create_prompt(
        db, PromptCreate(title="Sunrise", body="# Scene\nstadium stairs")
    )
    resp = client.get("/generate", params={"prompt_id": prompt.id})
    assert resp.status_code == 200
    assert "stadium stairs" in resp.text


def test_generate_creates_scripts_and_redirects(client, db):
    resp = client.post(
        "/generate",
        data={
            "source": "# Scene\nA lone athlete sprints uphill",
            "target_model": "veo",
            "output_format": "cinematic",
            "count": 5,
            "title_base": "Sprint",
            "tags": "gym",
        },
        follow_redirects=False,
    )
    assert resp.status_code == 303
    assert resp.headers["location"] == "/scripts?status=draft"
    db.expunge_all()
    assert script_service.count_scripts(db) == 5


def test_generate_requires_source(client, db):
    resp = client.post(
        "/generate",
        data={"source": "  ", "target_model": "veo", "output_format": "cinematic", "count": 3},
    )
    assert resp.status_code == 422
    assert "source prompt" in resp.text.lower()
    assert script_service.count_scripts(db) == 0


def test_generate_rejects_bad_count(client, db):
    resp = client.post(
        "/generate",
        data={"source": "x", "target_model": "veo", "output_format": "cinematic", "count": 7},
    )
    assert resp.status_code == 422
    assert script_service.count_scripts(db) == 0
