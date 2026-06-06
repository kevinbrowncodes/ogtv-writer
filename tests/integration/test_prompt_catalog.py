"""Integration tests for the prompt catalog routes.

These hit the real ``app/static/prompts/`` folder, which ships two example briefs:
``video-review-prompt.md`` (no count) and ``260601-0000_wip-prompt.md`` (uses {{COUNT}}).
"""

from __future__ import annotations

HX = {"HX-Request": "true"}


def test_catalog_page_lists_seeded_prompts(client) -> None:
    resp = client.get("/prompts")
    assert resp.status_code == 200
    assert "Prompt library" in resp.text
    assert "video-review-prompt.md" in resp.text
    assert "260601-0000_wip-prompt.md" in resp.text


def test_catalog_shows_count_badge(client) -> None:
    # The Wan arc prompt uses {{COUNT}}, so at least one "Count" badge is rendered.
    resp = client.get("/prompts")
    assert "Count" in resp.text


def test_preview_full_page_on_direct_nav(client) -> None:
    resp = client.get("/prompts/video-review-prompt")
    assert resp.status_code == 200
    assert "<html" in resp.text  # full page (no HX-Request header)
    assert "Viral Video Strategist" in resp.text  # the prompt body is shown


def test_preview_htmx_returns_partial_with_count_badge(client) -> None:
    resp = client.get("/prompts/260601-0000_wip-prompt", headers=HX)
    assert resp.status_code == 200
    assert "<html" not in resp.text  # fragment only
    assert "Uses {{COUNT}}" in resp.text  # the count badge is in the preview


def test_unknown_prompt_returns_404(client) -> None:
    resp = client.get("/prompts/does-not-exist")
    assert resp.status_code == 404


def test_odd_slug_returns_404_not_500(client) -> None:
    # A weird-but-routable slug must 404 cleanly, never raise a 500.
    resp = client.get("/prompts/.env")
    assert resp.status_code == 404
