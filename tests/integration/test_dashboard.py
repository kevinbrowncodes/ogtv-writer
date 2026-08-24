"""Integration tests for the dashboard + top-level pages (no auth)."""

from __future__ import annotations


def test_index_redirects_to_shoots(client):
    # STORY_031: the app opens on the Shoots page, the daily driver.
    resp = client.get("/", follow_redirects=False)
    assert resp.status_code == 303
    assert resp.headers["location"] == "/shoots"


def _sidebar_html(page_text: str) -> str:
    """Just the sidebar markup (between the aside's id and its closing tag)."""
    return page_text.split('id="sidebar"')[1].split("</aside>")[0]


def test_sidebar_lists_only_core_nav_shoots_first(client):
    # STORY_031/032: the nav is Shoots (first), Prompts, Queue — nothing else.
    resp = client.get("/dashboard")
    assert resp.status_code == 200
    sidebar = _sidebar_html(resp.text)
    assert sidebar.index('href="/shoots"') < sidebar.index('href="/prompts"') < sidebar.index(
        'href="/jobs"'
    )
    for gone in ("/dashboard", "/scripts", "/tags", "/settings"):
        assert f'href="{gone}"' not in sidebar
    # Settings stays one click away via the topbar gear.
    assert 'href="/settings"' in resp.text


def test_sidebar_is_an_unpinned_drawer_everywhere(client):
    # STORY_032: no lg: pin on the aside/backdrop, and the hamburger shows at all sizes.
    resp = client.get("/shoots")
    assert resp.status_code == 200
    aside_tag = resp.text.split('id="sidebar"')[1].split(">")[0]
    assert "lg:static" not in aside_tag and "lg:translate-x-0" not in aside_tag
    backdrop_tag = resp.text.split('id="sidebar-backdrop"')[1].split(">")[0]
    assert "lg:hidden" not in backdrop_tag
    hamburger_tag = resp.text.split("data-sidebar-open")[0].rsplit("<button", 1)[1]
    assert "lg:hidden" not in hamburger_tag


def test_dashboard_renders_shell_and_stats(client):
    resp = client.get("/dashboard")
    assert resp.status_code == 200
    assert "Dashboard" in resp.text
    assert 'id="stat-cards"' in resp.text  # the polling widget is present
    # OGTV stat labels.
    assert "Queued" in resp.text
    assert "Scripts" in resp.text


def test_dashboard_stats_partial(client):
    resp = client.get("/dashboard/stats")
    assert resp.status_code == 200
    assert 'id="stat-cards"' in resp.text
    assert "<html" not in resp.text  # fragment only


def test_healthz(client):
    resp = client.get("/healthz")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["app"] == "OGTV Writer"
