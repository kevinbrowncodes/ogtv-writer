"""End-to-end smoke tests covering the core user journeys.

Covered: login flow, dashboard rendering, an HTMX interaction (live search),
and the Items CRUD flow (create via modal + delete).
"""

from __future__ import annotations

import pytest
from playwright.sync_api import Page, expect

from tests.e2e.conftest import E2E_EMAIL, E2E_PASSWORD

# Every test in this module is an e2e test (excluded from the default run).
pytestmark = pytest.mark.e2e


def _login(page: Page, base_url: str) -> None:
    page.goto(f"{base_url}/login")
    page.fill('input[name="email"]', E2E_EMAIL)
    page.fill('input[name="password"]', E2E_PASSWORD)
    page.click('button[type="submit"]')
    page.wait_for_url("**/dashboard")


def test_login_and_dashboard_render(page: Page, live_server: str):
    _login(page, live_server)
    expect(page.get_by_role("heading", name="Dashboard")).to_be_visible()
    expect(page.locator("#stat-cards")).to_be_visible()


def test_create_item_via_htmx_modal(page: Page, live_server: str):
    _login(page, live_server)
    page.goto(f"{live_server}/items")

    page.get_by_role("button", name="New item").click()
    expect(page.locator("#modal")).to_contain_text("New item")  # modal opened

    page.fill("#title", "Playwright created item")
    page.get_by_role("button", name="Create item").click()

    # The modal closes and the list updates (out-of-band swap).
    expect(page.locator("#item-list")).to_contain_text("Playwright created item")
    expect(page.locator("#modal")).to_be_empty()


def test_live_search_filters_list(page: Page, live_server: str):
    _login(page, live_server)
    page.goto(f"{live_server}/items")

    page.fill('input[name="q"]', "Seeded")
    # Debounced HTMX request swaps in the filtered list; expect auto-waits.
    expect(page.locator("#item-list")).to_contain_text("Seeded item")
    expect(page.locator("#item-list")).not_to_contain_text("Playwright created item")


def test_delete_item(page: Page, live_server: str):
    _login(page, live_server)
    page.goto(f"{live_server}/items")

    # Create a throwaway item to delete.
    page.get_by_role("button", name="New item").click()
    page.fill("#title", "Temp delete me")
    page.get_by_role("button", name="Create item").click()
    row = page.locator("tr", has_text="Temp delete me")
    expect(row).to_be_visible()

    # hx-confirm pops a native dialog — auto-accept it.
    page.on("dialog", lambda dialog: dialog.accept())
    row.get_by_role("button", name="Delete").click()

    expect(page.locator("#item-list")).not_to_contain_text("Temp delete me")
