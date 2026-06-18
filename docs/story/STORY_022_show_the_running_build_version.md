# STORY_022 — Show the running build version so you know which deploy is live

> Epic: — (standalone) · Status: Done

**As** the OnlyGainsTV operator, **I want** each deploy to stamp the app with a
date-and-time build number (US Eastern, military time) that I can see in the UI,
**so that** I can confirm at a glance which build is running and be sure we're both
looking at the same deployed version.

## Acceptance Criteria

- [x] A build stamp in the format `Build YYMMDD-HHMM` (e.g. `Build 260618-0921`) is
      visible in the **sidebar footer** on every page.
- [x] The stamp is **US Eastern time** in 24-hour (military) format, produced by a
      single reusable time function (so the format lives in exactly one place).
- [x] In a **deployed Docker image** the stamp is fixed to the moment the image was
      built — it is stable across container restarts/recreations and does **not**
      drift on each request.
- [x] When no build version is supplied (local `make dev`), the app falls back to the
      **dev-server start time** so the slot is never empty and never a ticking clock.
- [x] `/healthz` includes the build stamp, so the running build can be verified with a
      single `curl` (lets the operator — and an assistant — confirm the live build).
- [x] `make deploy` computes the current Eastern stamp, bakes it into the image,
      recreates the container, and prints the build number.
- [x] Eastern time resolves correctly **inside the slim Docker image** (the IANA tz
      database is available there).

## Technical Notes

- **New module `app/version.py`** (kept dependency-light so the Makefile can import it
  standalone): `current_build_stamp(now: datetime | None = None) -> str` returns
  `(<aware datetime> → America/New_York).strftime("%y%m%d-%H%M")`. The injectable
  `now` parameter is what makes it unit-testable. Add module constant
  `STARTUP_BUILD_STAMP = current_build_stamp()` (evaluated once at import) for the
  local fallback, plus a `resolve_build_version()` helper returning
  `get_settings().build_version or STARTUP_BUILD_STAMP`.
- **Config** ([app/config.py](../../app/config.py)): add `build_version: str = ""`
  (reads env `BUILD_VERSION`). Document it in [.env.example](../../.env.example) noting
  it is set automatically at deploy and may be left blank locally.
- **Templating** ([app/templating.py](../../app/templating.py)): add a context
  processor exposing `build_version` (the resolved value) to every template render —
  so it works without each route passing it.
- **Display** ([app/templates/partials/_sidebar.html](../../app/templates/partials/_sidebar.html),
  the existing "Footer / version" block, lines 76-79): render `Build {{ build_version }}`
  next to the existing environment badge.
- **Health** ([app/routes/health.py](../../app/routes/health.py)): add
  `"build": resolve_build_version()` to the JSON (alongside the existing `version`).
- **Docker — bake the stamp into the image** (so "build version" == when the image was
  built, surviving recreation): [Dockerfile](../../Dockerfile) runtime stage gains
  `ARG BUILD_VERSION=""` + `ENV BUILD_VERSION=$BUILD_VERSION`;
  [docker-compose.yml](../../docker-compose.yml) `build:` gains
  `args: { BUILD_VERSION: "${BUILD_VERSION:-}" }`.
- **Deps** ([pyproject.toml](../../pyproject.toml)): add **`tzdata`** so `zoneinfo`
  resolves `America/New_York` inside `python:3.12-slim` (Debian slim ships no IANA tz
  database — without this the container raises `ZoneInfoNotFoundError`).
- **Makefile**: add a `deploy` target — compute the stamp via `app.version`, export
  `BUILD_VERSION`, run `docker compose up -d --build --force-recreate`, then print the
  build number for confirmation.
- **Routes added/changed:** `GET /healthz` (changed: +`build` field). No new routes, no
  new entity, no five-file recipe, no domain-vocab change.
- **Config / `.env` additions:** `BUILD_VERSION` (in both `config.py` and `.env.example`).

## Testing Plan

~70/20/10 unit/integration/e2e.

- **Unit** (`tests/unit/test_version.py`): `current_build_stamp()` with an injected
  fixed **aware** datetime asserts the exact `YYMMDD-HHMM` string; a second case feeds a
  UTC datetime that lands in a different Eastern hour to prove the tz conversion (not
  just formatting). `resolve_build_version()`: with `BUILD_VERSION` env set returns that
  value; unset falls back to the startup stamp. **Required** (pure logic + config seam).
- **Integration** (`tests/integration/`, `TestClient`): (1) a full page render contains
  `Build ` followed by a `\d{6}-\d{4}` match in the sidebar footer; (2) `/healthz` JSON
  has a `build` key matching `\d{6}-\d{4}`; (3) with `BUILD_VERSION` monkeypatched +
  `get_settings.cache_clear()`, both the footer and `/healthz` show that exact value.
  **Required** (changed route + rendered HTML).
- **e2e** (`tests/e2e/`): **N/A** — the build stamp is a passive, non-interactive label
  with no user flow to drive; its render is fully covered by the integration HTML
  assertion above. (Stated explicitly per §3 rather than silently skipped.)

## Estimated Complexity

**M** — individually small pieces of logic, but it threads through several layers
(version module, config, templating, template, `/healthz`, Dockerfile + compose,
Makefile, deps) and must handle the timezone-in-slim-Docker gotcha.
