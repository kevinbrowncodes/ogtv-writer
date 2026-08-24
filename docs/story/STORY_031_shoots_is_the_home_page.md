# STORY_031 — Shoots is the home page and the top sidebar item

> Epic: — · Status: Done

**As** the OnlyGainsTV operator, **I want** Shoots to be the first item in the
sidebar and the page the app opens on **so that** the screen I use most —
today's shoots, ready to run — is one click closer, instead of landing on the
Dashboard every time.

## Acceptance Criteria

- [x] The sidebar lists **Shoots** first, above Dashboard.
- [x] Opening the app root (`/`) lands on **/shoots** instead of /dashboard —
      including the installed PWA, whose `start_url` is `/`.
- [x] The Dashboard remains reachable from the sidebar exactly as before.

## Technical Notes

- [app/templates/partials/_sidebar.html](../../app/templates/partials/_sidebar.html)
  — the Shoots `nav_link` block moves above the Dashboard one (pure reorder).
- [app/routes/pages.py](../../app/routes/pages.py) — the `/` landing redirect
  targets `/shoots` (the PWA manifest's `start_url: "/"` then follows along;
  no service-worker change needed).
- The existing root-redirect integration test is updated to the new target.
- Routes added/changed: only the redirect target. Domain vocab / config /
  schema impact: none.

## Testing Plan

- **Unit** (`tests/unit/`): N/A — no service or pure-function change; this is
  a redirect target and a template reorder, both covered below.
- **Integration** (`tests/integration/test_dashboard.py`): `GET /` redirects
  (303) to `/shoots`; the rendered sidebar places the Shoots link before the
  Dashboard link.
- **e2e** (`tests/e2e/test_smoke.py`, Playwright): opening the app root lands
  on the Shoots page (heading visible).

## Estimated Complexity

S — a redirect target and a template block move.
