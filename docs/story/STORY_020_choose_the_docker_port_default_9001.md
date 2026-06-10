# STORY_020 — Choose the port the Docker app is served on (default 9001)

> Epic: — · Status: Done

**As** the OnlyGainsTV operator, **I want** the Docker container to serve on port 9001
(and to be able to pick a different port without editing files) **so that** it doesn't
collide with anything else I run on 8000.

## Acceptance Criteria

- [x] `make docker-up` / `make docker-run` serve the app at `http://localhost:9001` by default.
- [x] The host port is configurable: setting `WEB_PORT` in `.env` (e.g. `WEB_PORT=8080`) changes the published port without editing `docker-compose.yml`.
- [x] The container still listens internally on `8000`, so the compose **healthcheck (internal `localhost:8000`) keeps working** unchanged.
- [x] Nothing is published on `8000` anymore (the old mapping is gone); `http://localhost:9001` is the way in.
- [x] `.env.example` documents `WEB_PORT` with a safe default, and [README.md](../../README.md) shows the 9001 URL plus how to override the port.
- [x] Local non-Docker `make dev` is unchanged (still binds `PORT`, default 8000) — this story only moves the **published Docker** port.

## Technical Notes

- **docker-compose.yml ([docker-compose.yml](../../docker-compose.yml)):** change the mapping to
  `ports: - "${WEB_PORT:-9001}:8000"`. Left of the colon is the host port (configurable,
  default 9001); right is the container's fixed internal port (8000). Update the file's
  top comment that points at `http://localhost:8000`.
- **`.env.example` ([.env.example](../../.env.example)):** add `WEB_PORT=9001` with a comment that
  it is the **Docker host port only** (consumed by docker-compose's `${WEB_PORT}`
  substitution), distinct from the app's own `PORT` (the in-container/`make dev` bind port).
- **Why `app/config.py` is intentionally NOT changed:** `WEB_PORT` is a docker-compose
  substitution variable, never read by the Python app, so it does not belong in `Settings`
  / `get_settings()`. The app's own listen port stays the existing `port` field (default
  8000), which is what runs inside the container and under `make dev`. Adding a `web_port`
  field the app ignores would be misleading. (The usual "new setting → config.py + .env.example"
  rule is about *app* settings read via `get_settings()`; this is infra-only.)
- **Healthcheck:** unchanged — it curls `http://localhost:8000/healthz` *inside* the
  container, which is the internal port, independent of the host mapping.
- **Single-image `docker run`:** update the README example to `-p 9001:8000`.
- The app's `app_url`/internal links are relative (HTMX), so serving via a remapped host
  port needs no app change.

## Testing Plan

Infra/config change; automated net is a content guard, runtime behaviour is a quick curl.

- **Unit** (`tests/unit/test_docker_packaging.py`, extended): assert `docker-compose.yml`
  publishes via `${WEB_PORT:-9001}` onto the container's `:8000` (i.e. the default host port
  is 9001 and it's overridable), and that the bare `"8000:8000"` mapping is gone. Fast, offline.
- **Integration** (`tests/integration/`, `TestClient`): **N/A** — the published port is a
  docker-compose concern; the in-process `TestClient` doesn't bind host ports and the app
  itself is unchanged.
- **e2e** (`tests/e2e/`, Playwright): **N/A** — no app flow change. Verified manually:
  `make docker-up` → `curl http://localhost:9001/healthz` returns `200`, and `http://localhost:8000`
  refuses (no longer published).

## Estimated Complexity

**S** — one compose line, one `.env.example` entry, a README tweak, and a guard test; no
app code or schema.
