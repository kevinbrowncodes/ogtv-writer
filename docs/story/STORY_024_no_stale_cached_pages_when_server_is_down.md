# STORY_024 — Show a clear "server not running" page instead of a stale cached one

> Epic: — (standalone) · Status: Done

**As** the OnlyGainsTV operator, **I want** the app to tell me plainly when it can't
reach its backend — instead of silently serving the last cached page — **so that** I
never again mistake a stopped container for a live app and act on stale data.

This comes from a recurring, real annoyance: the container gets stopped (or Docker
Desktop quits), but opening the app still renders a normal-looking page because the
**service worker silently falls back to its cache** — so the operator sees stale
shoots/queue state and assumes it's live. The current
[service-worker.js](../../app/static/service-worker.js) is network-first for pages but
ends every page fetch with `.catch(() => caches.match(req))`, which is exactly the
silent-stale path.

**Decision (confirmed with the operator):** this is an internal, single-operator tool
that is useless without its backend, so the **offline app-shell has no value** — drop
it for page navigations. A down server should produce an honest "can't reach the
server" page, never a cached copy.

## Acceptance Criteria

- [x] **Page navigations are network-only.** When the server is reachable the live page
      always renders (no cached HTML is ever served for a navigation); the service
      worker no longer caches rendered pages or HTMX partials.
- [x] **When a navigation fails** (container/Docker down, connection refused), the
      service worker serves a dedicated **"Server not running"** offline page — clearly
      labelled, with a **Reload** button — *not* the previously cached page.
- [x] The **offline page is self-contained** (precached static asset, no server round
      trip) so it renders even with the backend fully down.
- [x] **Static assets stay cached** (css / js / icons / manifest / HTMX) so the offline
      page and shell chrome still style correctly; only *pages/partials* stop being
      cached.
- [x] **Existing clients self-heal:** bumping `CACHE_VERSION` purges the old cache (which
      holds the stale pages) on the next activate, so no manual cache-clear is needed.
- [x] HTMX partial GETs that fail while the server is down do **not** swap in stale
      cached fragments (they simply fail to swap); only full navigations get the
      offline page.

## Technical Notes

- **[app/static/service-worker.js](../../app/static/service-worker.js)** — rework the
  `fetch` handler:
  - Keep the `isStatic` branch **cache-first** (unchanged).
  - For everything else, go **network-only**: `fetch(req)` with **no** `cache.put` and
    **no** cache fallback. On failure, if `req.mode === "navigate"` (a full page load),
    respond with the precached **offline page**; otherwise let the request reject (HTMX
    partial just doesn't swap).
  - Add the offline page to `PRECACHE_URLS`; **bump `CACHE_VERSION`** (`v1` → `v2`) so
    the `activate` handler deletes the old cache that currently stores stale pages.
- **New `app/static/offline.html`** — a tiny, self-contained "Server not running" page
  (inline styles or links to the precached `app.css`): heading, one line of guidance
  ("Start the container, then reload"), and a `Reload` button (`location.reload()`).
  No server dependency.
- **Serving** — `app/static/` is already mounted, and the service worker is served via
  [app/routes/pwa.py](../../app/routes/pwa.py); confirm `offline.html` is reachable as a
  static asset for precache (and add a `pwa` route only if the SW scope needs it).
- No Python model/schema/service/domain/config changes; no new settings.

## Testing Plan

~20/30/50 — this is almost entirely client-side (service worker), so e2e carries the
real proof; unit is N/A.

- **Unit** (`tests/unit/`): **N/A** — the change is service-worker JavaScript + a static
  HTML file; there is no Python service or pure function to test. (Stated explicitly per
  the §3 rule.)
- **Integration** (`tests/integration/`, `TestClient`): assert the **offline page is
  served** as a static asset (`GET /static/offline.html` → 200, contains "Server not
  running" + a Reload control), and that **`service-worker.js` is served** and its body
  reflects the new contract (contains the bumped `CACHE_VERSION` and references
  `offline.html`; no page-caching `cache.put` on the navigation path).
- **e2e** (`tests/e2e/`, Playwright): the key coverage — load the app so the SW
  registers and controls the page, then take the browser **offline**
  (`context.set_offline(True)`), navigate, and assert the **"Server not running"** page
  appears (and that stale page text does **not**). A second case: with the server up,
  a normal navigation renders the live page (no regression).

## Estimated Complexity

**S–M** — a focused service-worker rewrite (network-only nav + offline fallback), one
small static page, a cache-version bump, plus an offline-mode e2e. The fiddly parts are
service-worker activation timing in the e2e and making sure only *navigations* (not
partials) get the full offline page.
