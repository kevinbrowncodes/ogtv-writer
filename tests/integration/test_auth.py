"""Integration tests for the authentication flow."""

from __future__ import annotations


def test_protected_page_redirects_when_logged_out(client):
    resp = client.get("/dashboard", follow_redirects=False)
    assert resp.status_code == 303
    assert resp.headers["location"].startswith("/login")


def test_login_success_then_access_dashboard(client, user):
    resp = client.post(
        "/login",
        data={"email": "test@example.com", "password": "password123"},
        follow_redirects=False,
    )
    assert resp.status_code == 303
    assert resp.headers["location"] == "/dashboard"

    # The session cookie now grants access.
    page = client.get("/dashboard")
    assert page.status_code == 200
    assert "Dashboard" in page.text


def test_login_with_bad_password_shows_error(client, user):
    resp = client.post(
        "/login",
        data={"email": "test@example.com", "password": "wrong"},
        follow_redirects=False,
    )
    assert resp.status_code == 401
    assert "Invalid email or password" in resp.text


def test_logout_clears_session(auth_client):
    resp = auth_client.post("/logout", follow_redirects=False)
    assert resp.status_code == 303
    assert resp.headers["location"] == "/login"

    after = auth_client.get("/dashboard", follow_redirects=False)
    assert after.status_code == 303
    assert after.headers["location"].startswith("/login")


def test_htmx_request_when_logged_out_gets_hx_redirect(client):
    """HTMX requests should get an HX-Redirect header, not an HTML redirect."""
    resp = client.get("/items/search", headers={"HX-Request": "true"})
    assert resp.status_code == 204
    assert resp.headers["HX-Redirect"].startswith("/login")
