# STORY_019 — Run the container in the background so it starts at login

> Epic: — · Status: Done

**As** the OnlyGainsTV operator, **I want** simple commands to run the app container
detached (and stop it / tail its logs) **so that** it keeps running in the background and
comes back automatically after I log in or restart, without me babysitting a terminal.

## Acceptance Criteria

- [x] `make docker-up` starts the app **detached** (`docker compose up -d --build`) — it keeps running after the terminal closes, and the command returns to the prompt.
- [x] `make docker-down` stops and removes the container cleanly (`docker compose down`); the host `./data` is untouched.
- [x] `make docker-logs` tails the running container's logs (`docker compose logs -f`) so a detached run is still observable.
- [x] The container keeps the existing `restart: unless-stopped` policy, so once started with `make docker-up` it is restarted automatically when the Docker daemon starts (e.g. after a reboot/login), unless the operator explicitly stops it.
- [x] The existing foreground `make docker-run` is unchanged (still handy for a quick, log-in-terminal run).
- [x] [README.md](../../README.md) documents the background workflow (`make docker-up` / `docker-logs` / `docker-down`) and the one manual prerequisite for true start-at-login: enabling **Docker Desktop → Settings → General → "Start Docker Desktop when you sign in"** (macOS starts it at login, not pre-login boot).

## Technical Notes

- **No app code / entity / route / domain changes.** This is developer-ergonomics only — new Makefile targets + docs.
- **Makefile ([Makefile](../../Makefile)), in the `# --- Docker ---` block:**
  - `docker-up` → `docker compose up -d --build` (detached; rebuilds so it picks up changes).
  - `docker-down` → `docker compose down`.
  - `docker-logs` → `docker compose logs -f web`.
  - Add each to `.PHONY` and give each a `## ` help comment so it shows in `make help`.
- **Restart policy stays `unless-stopped`** (already in [docker-compose.yml](../../docker-compose.yml)). It already restarts on daemon start; switching to `always` would only differ by ignoring a deliberate manual stop, which is worse default behaviour — out of scope.
- **Why a manual step remains:** there is no reliable, version-stable CLI to toggle Docker Desktop's "start at login" on macOS, and it's an external-app setting that needs a Docker Desktop restart to take effect. Document the checkbox rather than scripting a fragile settings-file edit.
- **Config / `.env`:** none.

## Testing Plan

A Makefile-ergonomics change; the automated net is a content guard, and the runtime
behaviour is a quick manual check (already exercised: the container is running detached
with `restart=unless-stopped` and `/healthz` 200).

- **Unit** (`tests/unit/test_docker_packaging.py`, extended): assert the Makefile defines a `docker-up` target that runs `docker compose up -d` (the `-d` is the point — a detached run), plus `docker-down`. Fast, offline, no Docker — locks in the detached semantics.
- **Integration** (`tests/integration/`, `TestClient`): **N/A** — Makefile targets aren't routes; the FastAPI app is unchanged, so there's nothing for `TestClient` to exercise.
- **e2e** (`tests/e2e/`, Playwright): **N/A** — no user-visible app flow changes. The container behaviour is verified manually: `make docker-up` → `/healthz` 200 → `docker inspect` shows `running=true` / `restart=unless-stopped` → `make docker-down` removes it with `./data` intact.

## Estimated Complexity

**S** — three thin Makefile targets plus a README section; no app code, no schema, no config.
