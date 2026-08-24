"""End-to-end smoke tests covering the core OGTV Writer journeys.

Covered: dashboard render, browsing the file-based prompt catalog, generating
scripts from the workspace, and the script library.
"""

from __future__ import annotations

import pytest
from playwright.sync_api import Page, expect

# Every test in this module is an e2e test (excluded from the default run).
pytestmark = pytest.mark.e2e


def test_root_opens_shoots(page: Page, live_server: str):
    # STORY_031: the app root lands on the Shoots page.
    page.goto(live_server)
    expect(page.get_by_role("heading", name="Shoots")).to_be_visible()


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
    # Default image source is the shoot folder (one is seeded under SOURCE_ROOT).
    page.select_option("#source_dir", "only-gains-tv/test-shoot")
    page.get_by_role("button", name="Queue job").click()

    # Lands back on the queue with the new job listed as Queued.
    page.wait_for_url("**/jobs")
    expect(page.locator("#job-list")).to_contain_text("video-review-prompt.md")
    expect(page.locator("#job-list")).to_contain_text("Queued")

    # Opening the job shows its detail page with the live status block.
    page.locator("#job-list a").first.click()
    expect(page.get_by_role("heading", name="Job #")).to_be_visible()
    expect(page.locator("#job-status")).to_contain_text("Queued")


def test_shoots_date_defaults_to_today(page: Page, live_server: str):
    # STORY_029: the Date filter starts on today's date (the seed creates a youtube
    # shoot dated today), so the list opens showing today's shoots only.
    from datetime import date

    today = date.today().strftime("%y-%m-%d")
    page.goto(f"{live_server}/shoots")
    expect(page.locator("#shoot-date-filter")).to_have_value(today)
    expect(page.locator("#shoots-list")).to_contain_text(f"{today}-0000")
    expect(page.locator("#shoots-list")).not_to_contain_text("yt-test-shoot")  # undated → hidden


def test_shoots_dashboard_lists_pending(page: Page, live_server: str):
    page.goto(f"{live_server}/shoots")
    expect(page.get_by_role("heading", name="Shoots")).to_be_visible()
    # The page opens on today's date (STORY_029); widen to all dates for the full list.
    page.locator("#shoot-date-filter").select_option("")
    # The seeded shoot (only 01.jpg, no script) shows as Pending.
    expect(page.locator("body")).to_contain_text("test-shoot")
    expect(page.locator("body")).to_contain_text("Pending")
    # The shared picker + live list render: Run-all button and a per-shoot Run button.
    expect(page.get_by_role("button", name="Run all pending")).to_be_visible()
    expect(page.locator("#shoots-list")).to_contain_text("Run")


def test_offline_navigation_shows_server_not_running(page: Page, live_server: str):
    # STORY_024: with the service worker controlling the page, a navigation that can't
    # reach the backend must show the honest "Server not running" page — never a stale
    # cached copy.
    page.goto(f"{live_server}/dashboard")
    # Wait until the service worker has claimed the page (it controls navigations).
    page.wait_for_function(
        "navigator.serviceWorker && navigator.serviceWorker.controller !== null",
        timeout=10000,
    )
    # Simulate the container/Docker being down.
    page.context.set_offline(True)
    page.goto(f"{live_server}/shoots")
    expect(page.locator("body")).to_contain_text("Server not running")
    # The stale dashboard/shoots content is NOT shown.
    expect(page.locator("body")).not_to_contain_text("Run all pending")
    page.context.set_offline(False)


def test_shoots_warns_when_gemini_unavailable(page: Page, live_server: str):
    # The e2e server runs with a blank GEMINI_API_KEY, so the model picker surfaces the
    # "Gemini unavailable" warning rather than silently showing only the default (STORY_023).
    page.goto(f"{live_server}/shoots")
    expect(page.locator("body")).to_contain_text("Gemini unavailable")


def test_shoots_filter_by_channel(page: Page, live_server: str):
    page.goto(f"{live_server}/shoots")
    page.locator("#shoot-date-filter").select_option("")  # widen from today (STORY_029)
    # Both seeded channels are visible with no filter.
    expect(page.locator("#shoots-list")).to_contain_text("test-shoot")
    expect(page.locator("#shoots-list")).to_contain_text("yt-test-shoot")

    # Narrowing to youtube (HTMX) drops the only-gains-tv shoot from the list.
    page.locator("#shoot-channel-filter").select_option("youtube")
    expect(page.locator("#shoots-list")).to_contain_text("yt-test-shoot")
    expect(page.locator("#shoots-list")).not_to_contain_text("only-gains-tv")


def test_run_all_pending_keeps_prompt_selection(page: Page, live_server: str):
    # BUG_004: running shoots must not reset the picker. Pick a prompt, click Run all
    # pending, and the prompt <select> should still hold that choice — the run now swaps
    # only #shoots-list (HTMX) instead of reloading the whole page.
    page.goto(f"{live_server}/shoots")
    page.locator("#shoot-date-filter").select_option("")  # widen from today (STORY_029)
    page.select_option("#prompt_slug", "video-review-prompt")
    page.get_by_role("button", name="Run all pending").click()
    # The list swaps to the queued/running state in place (a job was queued)...
    expect(page.locator("#shoots-list")).to_contain_text("auto-refreshing")
    # ...and the prompt selection survives (the old full-page redirect reset it to "").
    expect(page.locator("#prompt_slug")).to_have_value("video-review-prompt")

    # Back to "All channels" shows everything again.
    page.locator("#shoot-channel-filter").select_option("")
    expect(page.locator("#shoots-list")).to_contain_text("test-shoot")
    expect(page.locator("#shoots-list")).to_contain_text("yt-test-shoot")


def test_shoots_date_options_follow_channel(page: Page, live_server: str):
    from datetime import date, timedelta

    # Same date-relative seed as tests/e2e/conftest.py (same calendar day → same values).
    yt_date = date.today().strftime("%y-%m-%d")
    ogtv_date = (date.today() - timedelta(days=3)).strftime("%y-%m-%d")

    page.goto(f"{live_server}/shoots")
    date_filter = page.locator("#shoot-date-filter")
    # "All channels": the Date dropdown is the union of both channels' dates.
    expect(date_filter).to_contain_text(yt_date)
    expect(date_filter).to_contain_text(ogtv_date)

    # Switching to youtube rebuilds the Date dropdown to youtube's dates only (OOB swap).
    page.locator("#shoot-channel-filter").select_option("youtube")
    expect(date_filter).to_contain_text(yt_date)
    expect(date_filter).not_to_contain_text(ogtv_date)


def test_shoots_refresh_button_picks_up_new_folder(page: Page, live_server: str):
    # STORY_027: drop a new shoot folder on disk, click Refresh, and it appears in the
    # list in place — no full page reload.
    import shutil
    from pathlib import Path

    from app.config import get_settings

    new_shoot = Path(get_settings().source_root) / "only-gains-tv" / "fresh-drop-shoot"
    try:
        page.goto(f"{live_server}/shoots")
        page.locator("#shoot-date-filter").select_option("")  # widen from today (STORY_029)
        expect(page.locator("#shoots-list")).not_to_contain_text("fresh-drop-shoot")
        new_shoot.mkdir(parents=True)
        (new_shoot / "01.jpg").write_bytes(b"img")
        page.get_by_role("link", name="Refresh").click()
        expect(page.locator("#shoots-list")).to_contain_text("fresh-drop-shoot")
    finally:
        # The e2e source root is session-scoped on-disk state — don't leak the folder
        # into later tests or future runs.
        shutil.rmtree(new_shoot, ignore_errors=True)


def test_settings_default_channel_applies_to_shoots(page: Page, live_server: str):
    # STORY_028: pick a default channel in Settings → the Shoots page starts on it.
    from app.database import SessionLocal
    from app.services import preference_service

    try:
        page.goto(f"{live_server}/settings")
        page.locator("#default-channel").select_option("youtube")
        # Two Save buttons exist since STORY_030 — scope to the channel form's.
        page.locator("form[action='/settings/default-channel'] button[type=submit]").click()
        # Back on Settings after the redirect, the saved choice is selected.
        expect(page.locator("#default-channel")).to_have_value("youtube")

        page.goto(f"{live_server}/shoots")
        expect(page.locator("#shoot-channel-filter")).to_have_value("youtube")
        page.locator("#shoot-date-filter").select_option("")  # widen from today (STORY_029)
        expect(page.locator("#shoots-list")).to_contain_text("yt-test-shoot")
        expect(page.locator("#shoots-list")).not_to_contain_text("only-gains-tv")
    finally:
        # The e2e database is session-scoped — reset so later tests start unfiltered.
        with SessionLocal() as db:
            preference_service.set_preference(db, preference_service.DEFAULT_CHANNEL_KEY, "")


def test_settings_default_model_card_saves(page: Page, live_server: str):
    # STORY_030: the Generation card renders and Save round-trips. The e2e server runs
    # with a blank GEMINI_API_KEY (no paid calls), so only the fallback model is offered
    # here — picking a *different* model is covered at the integration layer with a
    # mocked model list.
    page.goto(f"{live_server}/settings")
    model_select = page.locator("#default-model")
    expect(model_select).to_be_visible()
    expect(model_select).to_contain_text("App default")
    page.locator("form[action='/settings/default-model'] button[type=submit]").click()
    page.wait_for_url("**/settings")
    expect(page.locator("#default-model")).to_have_value("")  # "App default" kept


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
