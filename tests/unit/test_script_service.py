"""Unit tests for the Script service."""

from __future__ import annotations

from app.schemas.script import ScriptCreate, ScriptUpdate
from app.services import job_service, script_service


def _make_job(db):
    return job_service.create_job(
        db,
        prompt_slug="p",
        prompt_filename="p.md",
        addendum="",
        count=None,
        image_path="data/uploads/x.png",
        image_filename="x.png",
    )


def test_create_and_get_script(db):
    script = script_service.create_script(
        db, ScriptCreate(title="Hero", target_model="veo", output_format="cinematic")
    )
    assert script.id is not None
    assert script.status == "draft"
    assert script.used_at is None


def test_filter_by_status_model_and_tag(db):
    script_service.create_script(
        db, ScriptCreate(title="A", status="ready", target_model="veo", tags="gym, sunrise")
    )
    script_service.create_script(
        db, ScriptCreate(title="B", status="draft", target_model="wan", tags="hype")
    )

    assert len(script_service.list_scripts(db, status="ready")) == 1
    assert len(script_service.list_scripts(db, target_model="wan")) == 1
    assert len(script_service.list_scripts(db, tag="sunrise")) == 1


def test_search_matches_body(db):
    script_service.create_script(db, ScriptCreate(title="A", body="chalk and iron deadlift"))
    results = script_service.list_scripts(db, search="deadlift")
    assert len(results) == 1


def test_marking_used_stamps_used_at(db):
    script = script_service.create_script(db, ScriptCreate(title="A"))
    assert script.used_at is None

    script_service.update_script(db, script, ScriptUpdate(status="used"))
    refreshed = script_service.get_script(db, script.id)
    assert refreshed.status == "used"
    assert refreshed.used_at is not None


def test_duplicate_creates_independent_draft(db):
    original = script_service.create_script(
        db, ScriptCreate(title="Hero", body="body text", status="ready", tags="gym")
    )
    copy = script_service.duplicate_script(db, original)

    assert copy.id != original.id
    assert copy.title == "Hero (copy)"
    assert copy.status == "draft"
    assert copy.body == "body text"
    assert copy.tags == "gym"


def test_status_breakdown(db):
    script_service.create_script(db, ScriptCreate(title="a", status="draft"))
    script_service.create_script(db, ScriptCreate(title="b", status="ready"))
    script_service.create_script(db, ScriptCreate(title="c", status="ready"))

    breakdown = script_service.status_breakdown(db)
    assert breakdown == {"draft": 1, "ready": 2}


def test_create_generated_scripts_multiple(db):
    job = _make_job(db)
    created = script_service.create_generated_scripts(db, job, ["one", "two"], title_base="Scene")

    assert [s.title for s in created] == ["Scene — 1", "Scene — 2"]
    assert [s.order_index for s in created] == [1, 2]
    assert all(s.job_id == job.id for s in created)
    assert all(s.status == "draft" for s in created)
    assert all(s.source_prompt == "p.md" for s in created)

    listed = script_service.list_for_job(db, job.id)
    assert [s.body for s in listed] == ["one", "two"]


def test_create_generated_scripts_single_has_no_suffix(db):
    job = _make_job(db)
    (created,) = script_service.create_generated_scripts(db, job, ["solo"], title_base="Scene")
    assert created.title == "Scene"
    assert created.order_index == 1
