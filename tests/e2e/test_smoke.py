"""End-to-end smoke tests covering the core OGTV Writer journeys.

Covered: dashboard render, browsing the file-based prompt catalog, generating
scripts from the workspace, and the script library.
"""

from __future__ import annotations

import base64

import pytest
from playwright.sync_api import Page, expect

# A valid 1x1 PNG, used to drive the file-upload control.
_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
)

# Every test in this module is an e2e test (excluded from the default run).
pytestmark = pytest.mark.e2e


def test_dashboard_renders(page: Page, live_server: str):
    page.goto(f"{live_server}/dashboard")
    expect(page.get_by_role("heading", name="Dashboard")).to_be_visible()
    expect(page.locator("#stat-cards")).to_be_visible()


def test_browse_prompt_catalog(page: Page, live_server: str):
    page.goto(f"{live_server}/prompts")

    expect(page.get_by_role("heading", name="Prompt library")).to_be_visible()
    # The seeded prompt files from app/static/prompts/ are listed.
    expect(page.locator("#prompt-list")).to_contain_text("video-review-prompt.md")

    # Clicking a prompt loads its full text into the preview panel (HTMX).
    page.locator('a[href="/prompts/video-review-prompt"]').click()
    expect(page.locator("#prompt-preview")).to_contain_text("Viral Video Strategist")


def test_library_shows_seeded_script(page: Page, live_server: str):
    page.goto(f"{live_server}/scripts")
    expect(page.locator("#script-list")).to_contain_text("Seeded script")


def test_submit_generation_job(page: Page, live_server: str):
    page.goto(f"{live_server}/jobs/new")
    expect(page.get_by_role("heading", name="New generation job")).to_be_visible()

    # The model picker is present, defaulting to the configured model.
    expect(page.locator("#model")).to_be_visible()
    expect(page.locator("#model")).to_contain_text("gemini-2.5-flash")

    page.select_option("#prompt_slug", "video-review-prompt")
    page.set_input_files(
        "#image", files=[{"name": "frame.png", "mimeType": "image/png", "buffer": _PNG}]
    )
    page.get_by_role("button", name="Queue job").click()

    # Lands back on the queue with the new job listed as Queued.
    page.wait_for_url("**/jobs")
    expect(page.locator("#job-list")).to_contain_text("frame.png")
    expect(page.locator("#job-list")).to_contain_text("Queued")

    # Opening the job shows its detail page with the live status block.
    page.locator("#job-list a").first.click()
    expect(page.get_by_role("heading", name="Job #")).to_be_visible()
    expect(page.locator("#job-status")).to_contain_text("Queued")


def test_completed_job_shows_split_scripts(page: Page, live_server: str):
    page.goto(f"{live_server}/jobs")
    # Open the seeded completed job (the only row marked Done).
    page.locator("#job-list tr", has_text="Done").first.locator("a").click()
    expect(page.locator("#job-status")).to_contain_text("Seeded script alpha")
    expect(page.locator("#job-status")).to_contain_text("Seeded scene summary.")

    # Copy + export controls are present, and the .zip actually downloads.
    expect(page.get_by_role("button", name="Copy").first).to_be_visible()
    with page.expect_download() as download:
        page.get_by_role("link", name="Download .zip").click()
    assert download.value.suggested_filename.endswith(".zip")
