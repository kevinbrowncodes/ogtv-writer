"""Integration tests for the dashboard pages."""

from __future__ import annotations


def test_index_redirects_to_login_when_logged_out(client):
    resp = client.get("/", follow_redirects=False)
    assert resp.status_code == 303
    assert resp.headers["location"] == "/login"


def test_index_redirects_to_dashboard_when_logged_in(auth_client):
    resp = auth_client.get("/", follow_redirects=False)
    assert resp.status_code == 303
    assert resp.headers["location"] == "/dashboard"


def test_dashboard_renders_shell_and_stats(auth_client):
    resp = auth_client.get("/dashboard")
    assert resp.status_code == 200
    assert "Dashboard" in resp.text
    assert 'id="stat-cards"' in resp.text  # the polling widget is present


def test_dashboard_stats_partial(auth_client):
    resp = auth_client.get("/dashboard/stats")
    assert resp.status_code == 200
    assert 'id="stat-cards"' in resp.text
    # It's a fragment, not a full page.
    assert "<html" not in resp.text


def test_healthz(client):
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
