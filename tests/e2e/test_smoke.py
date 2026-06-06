"""End-to-end smoke tests covering the core OGTV Writer journeys.

Covered: dashboard render, creating a prompt via the HTMX modal, generating
scripts from the workspace, and the script library.
"""

from __future__ import annotations

import pytest
from playwright.sync_api import Page, expect

# Every test in this module is an e2e test (excluded from the default run).
pytestmark = pytest.mark.e2e


def test_dashboard_renders(page: Page, live_server: str):
    page.goto(f"{live_server}/dashboard")
    expect(page.get_by_role("heading", name="Dashboard")).to_be_visible()
    expect(page.locator("#stat-cards")).to_be_visible()


def test_create_prompt_via_htmx_modal(page: Page, live_server: str):
    page.goto(f"{live_server}/prompts")

    page.get_by_role("button", name="New prompt").click()
    expect(page.locator("#modal")).to_contain_text("New prompt")

    page.fill("#title", "Playwright prompt")
    page.fill("#body", "# Scene\na test prompt")
    page.get_by_role("button", name="Save prompt").click()

    # The modal closes (out-of-band swap) and the list updates.
    expect(page.locator("#prompt-list")).to_contain_text("Playwright prompt")
    expect(page.locator("#modal")).to_be_empty()


def test_generate_scripts_flow(page: Page, live_server: str):
    page.goto(f"{live_server}/generate")

    page.fill("#source", "# Scene\nA lone athlete sprints up stadium stairs")
    page.select_option("#count", "3")
    page.get_by_role("button", name="Generate scripts").click()

    # Lands on the library, filtered to the new drafts.
    page.wait_for_url("**/scripts**")
    expect(page.locator("#script-list")).to_be_visible()


def test_library_shows_seeded_script(page: Page, live_server: str):
    page.goto(f"{live_server}/scripts")
    expect(page.locator("#script-list")).to_contain_text("Seeded script")
