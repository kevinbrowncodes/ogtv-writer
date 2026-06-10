# STORY_018 — Run the whole app as a single Docker container

> Epic: — · Status: Done

**As** the OnlyGainsTV operator, **I want** to start the entire app as one Docker
container with a single command **so that** I can run the studio on any machine without
setting up Python, a virtualenv, Node, or Tailwind by hand.

## Acceptance Criteria

- [x] `make docker-run` (`docker compose up --build`) builds the image and serves the app at `http://localhost:8000`, landing on the dashboard.
- [x] On startup the container applies Alembic migrations to head **inside the image** — a fresh database gets the full schema, an existing database upgrades in place, and neither path crashes. (Today it crashes because `alembic.ini` and `migrations/` aren't copied into the image.)
- [x] The container **bind-mounts the host `./data`** onto `/app/data`, so it uses the operator's existing SQLite database (`data/app.db`) and shoot image folders (`data/logline/...`); content the app writes persists straight back to the host `./data`.
- [x] The database is **not seeded** — the container migrates and serves; with the `./data` bind-mount the operator's existing prompts/scripts/shoots are already present. A genuinely empty `./data` starts the app with an empty library (content is created in-app).
- [x] The container reads configuration from `.env` (e.g. the Gemini key); the app still **boots even if generation isn't configured** — a missing/blank key must not block startup, only degrade the generate feature.
- [x] Data **survives a container restart and a rebuild** (it lives on the host `./data`, not inside the image or an ephemeral layer).
- [x] `GET /healthz` returns `200` once started and the compose healthcheck reports the service healthy.
- [x] [README.md](../../README.md) documents the one-command run, the prerequisites (Docker, a `.env` copied from `.env.example`), and that `./data` is the mounted data directory.

## Technical Notes

- **No new entity / route / domain vocab.** This is a packaging change, not the five-file recipe. No new routes, no `app/domain.py` impact.
- **Dockerfile ([Dockerfile](../../Dockerfile)) — the core fix.** In the `runtime` stage, copy the migration assets into the image root so `migrations_runner._config()` (which resolves `_ROOT = parent of app/ = /app`) finds them:
  - `COPY alembic.ini ./`
  - `COPY migrations ./migrations`
  - Place these **before** the `useradd` / `chown -R appuser:appuser /app` block so they end up owned by `appuser`.
- **Why it's broken today:** [app/main.py](../../app/main.py) `lifespan` calls `migrations_runner.upgrade_to_head()` when `auto_migrate` is true (the default), and [app/migrations_runner.py](../../app/migrations_runner.py) loads `<_ROOT>/alembic.ini` and `<_ROOT>/migrations`. The current Dockerfile copies only `pyproject.toml`, `README.md`, and `app/`, so those two paths are absent in the container and startup raises before the server is ready.
- **Keep cwd import intact.** uvicorn runs from `WORKDIR /app` as `app.main:app`, so `__file__` is `/app/app/migrations_runner.py` and `_ROOT` is `/app`. The migration assets must sit at `/app/alembic.ini` and `/app/migrations` (the COPY targets above) — do not nest them under `app/`.
- **docker-compose.yml ([docker-compose.yml](../../docker-compose.yml)):**
  - Swap the persistence from the named volume to a **bind mount**: `volumes: - ./data:/app/data` (drop the top-level `volumes: app-data:` stanza).
  - Keep `env_file: .env`, the healthcheck, and `restart: unless-stopped`.
  - Leave `ENVIRONMENT: production`; `auto_migrate` defaults to `true` and is **not** overridden, so `upgrade_to_head()` still runs on startup. (Do **not** set `AUTO_MIGRATE=false`, which would switch to `verify_at_head()` and refuse to create a fresh schema.)
- **.dockerignore ([.dockerignore](../../.dockerignore)):** confirm it does **not** exclude `alembic.ini` or `migrations/` from the build context (it currently excludes `data/`, `tests/`, `*.md` — none of which hide the migration `.py` files or the `.ini`). `data/` staying excluded is correct: data must arrive via the runtime bind mount, never be baked into the image.
- **Config / `.env` additions:** none required — `auto_migrate` and `database_url` already exist with defaults in [app/config.py](../../app/config.py). No new setting, so no `.env.example` change. (The container relies on the existing `.env` for the Gemini key.)
- **Permissions caveat (note, likely a no-op on this host):** the container runs as non-root `appuser`, while host `./data` is owned by the operator. On macOS Docker Desktop, bind-mount file sharing is uid-permissive, so SQLite writes succeed regardless. If this is ever run on native Linux and writes fail, match the uid or relax ownership — call it out in the README rather than baking a Linux-specific workaround in now.

## Testing Plan

Aim for ~70/20/10. The substance here is infrastructure, so the automated net is a
cheap regression guard and the real acceptance is a documented manual container run.

- **Unit** (`tests/unit/`, e.g. `test_docker_packaging.py`): read the `Dockerfile` text and assert the runtime stage copies **`alembic.ini`** and the **`migrations`** directory (the exact regression that breaks startup), and read `docker-compose.yml` and assert it **bind-mounts `./data`** onto `/app/data`. Fast, offline, no Docker required — locks in the fix so it can't silently regress.
- **Integration** (`tests/integration/`, `TestClient`): **N/A** — the FastAPI `TestClient` runs the app in-process, not in a container, so it cannot exercise image packaging or the bind mount. The startup migration logic itself (`upgrade_to_head` / adopt / verify) is already covered by the existing migrations-runner tests and is unchanged by this story.
- **e2e** (`tests/e2e/`, Playwright): **N/A as an automated pytest-e2e** — the Playwright suite drives `make dev` (a host process), not the container, and a containerized e2e would require Docker-in-CI (out of scope). Instead, **Done requires a manual container verification**, run on the host before flipping Status to Done:
  1. `cp .env.example .env` (if absent) and ensure the Gemini key is set as desired.
  2. `make docker-run` → wait for the healthcheck to report healthy.
  3. `curl -fs http://localhost:8000/healthz` returns `200`; open `http://localhost:8000/` and confirm the dashboard loads with the **existing** library/shoots from `./data`.
  4. Create or edit a record in-app, then `docker compose restart` (and separately `docker compose up --build`) and confirm the change **persisted** via the `./data` bind mount.
  (Optionally wire a CI `docker build` smoke job later — not part of this story.)

## Estimated Complexity

**S–M** — a few `COPY` lines, one compose volume swap, and a README section; small and
self-contained. The size is in *verification*: "Done" means an actual `docker build` +
`docker compose up` on the host proving migrations apply and `./data` persists, plus the
unit guard so it never regresses.
