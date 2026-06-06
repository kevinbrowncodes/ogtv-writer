"""Integration tests for the dashboard + top-level pages (no auth)."""

from __future__ import annotations


def test_index_redirects_to_dashboard(client):
    resp = client.get("/", follow_redirects=False)
    assert resp.status_code == 303
    assert resp.headers["location"] == "/dashboard"


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
