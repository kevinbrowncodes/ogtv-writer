"""Integration tests for the offline page + service-worker contract (STORY_024).

The behaviour itself (network-only navigations, offline fallback) is service-worker
JavaScript exercised by the e2e suite; here we just assert the pieces the SW depends
on are served and that the SW file encodes the new contract.
"""

from __future__ import annotations


def test_offline_page_is_served_as_static_asset(client):
    resp = client.get("/static/offline.html")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    assert "Server not running" in resp.text
    assert "location.reload()" in resp.text  # the Reload button works without the server


def test_service_worker_encodes_network_only_contract(client):
    resp = client.get("/service-worker.js")
    assert resp.status_code == 200
    body = resp.text
    # Cache bumped so existing clients drop the old stale-page cache.
    assert "ogtv-writer-v2" in body
    # The offline page is precached and served on a failed navigation.
    assert "/static/offline.html" in body
    assert 'req.mode === "navigate"' in body
    # Pages/partials are network-only: fetch with no cache write on the response path.
    assert "fetch(req).catch(async ()" in body
    # The old silent "serve the stale cached page" fallback is gone.
    assert ".catch(() => caches.match(req))" not in body


# --- STORY_034: true-black theme + pencil icon --------------------------------


def test_manifest_uses_black_theme(client):
    resp = client.get("/manifest.webmanifest")
    assert resp.status_code == 200
    data = resp.json()
    assert data["background_color"] == "#000000"
    assert data["theme_color"] == "#000000"


def test_icon_is_white_pencil_on_black(client):
    resp = client.get("/static/icons/icon.svg")
    assert resp.status_code == 200
    body = resp.text
    assert 'fill="#000000"' in body  # black full-bleed background
    assert 'fill="#ffffff"' in body  # white pencil
    assert "linearGradient" not in body  # the old purple/pink gradient is gone


def test_page_meta_theme_color_is_black(client):
    resp = client.get("/shoots")
    assert resp.status_code == 200
    assert '<meta name="theme-color" content="#000000" />' in resp.text
