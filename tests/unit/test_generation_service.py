"""Unit tests for the script generator."""

from __future__ import annotations

from app.services import generation_service, script_service


def test_summarize_strips_markdown():
    summary = generation_service.summarize_prompt("# Scene\n- A lone athlete\n> sprints uphill")
    assert "#" not in summary
    assert ">" not in summary
    assert "athlete" in summary


def test_summarize_empty_has_fallback():
    assert generation_service.summarize_prompt("   \n  ") == "your subject"


def test_build_body_includes_master_prompt_and_structure():
    body = generation_service.build_script_body(
        subject="a lone athlete sprints uphill",
        target_model="veo",
        output_format="cinematic",
        variation=1,
        count=3,
        title="Test v1",
    )
    assert "# Test v1" in body
    assert "## Master prompt" in body
    assert "## Structure" in body
    assert "a lone athlete sprints uphill" in body
    # Cinematic structure markers.
    assert "Scene:" in body
    assert "Camera:" in body


def test_build_body_fills_template_placeholders():
    body = generation_service.build_script_body(
        subject="gym hero",
        target_model="wan",
        output_format="short-form",
        variation=1,
        count=1,
        title="T",
        template_body="Subject is {subject} for {model}",
    )
    assert "Subject is gym hero for Wan" in body
    assert "{subject}" not in body


def test_variations_differ(db):
    scripts = generation_service.create_scripts(
        db,
        source_prompt="# Scene\nA lone athlete sprints up stadium stairs",
        target_model="veo",
        output_format="cinematic",
        count=3,
    )
    assert len(scripts) == 3
    assert all(s.status == "draft" for s in scripts)
    assert all(s.target_model == "veo" for s in scripts)
    # Each variation uses a different lens, so bodies are distinct.
    bodies = {s.body for s in scripts}
    assert len(bodies) == 3
    # They were persisted.
    assert script_service.count_scripts(db) == 3


def test_create_scripts_stores_source_prompt(db):
    source = "# Scene\nChalk and iron"
    scripts = generation_service.create_scripts(
        db,
        source_prompt=source,
        target_model="generic",
        output_format="shot-list",
        count=1,
        tags="gym",
    )
    assert scripts[0].prompt_source == source.strip()
    assert scripts[0].tags == "gym"
