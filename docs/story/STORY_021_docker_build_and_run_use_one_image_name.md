# STORY_021 — Docker build and run use one consistent image name

> Epic: — · Status: **Done**

**As** the OnlyGainsTV operator, **I want** `make docker-build` and `make docker-up`/`make docker-run` to build and run the **same** Docker image, **so that** I never end up looking at a stale container while a freshly built image sits unused — and I'm not left guessing which of two similarly named images is actually running.

## Background

`make docker-build` runs `docker build -t ogtv-writer .`, tagging the image **`ogtv-writer:latest`**. Compose, however, has no `image:` field, so it auto-names the image it builds `<project>-<service>` = **`ogtv-writer-web`** and runs *that*. The two never line up: `make docker-build` produces an image **nothing ever runs** (a dead-end orphan), while the container quietly runs a different image. Two near-identical image names (`ogtv-writer` vs `ogtv-writer-web`) is exactly what makes "am I on an old build?" impossible to answer at a glance.

## Acceptance Criteria

- [x] `docker-compose.yml` pins an explicit `image: ogtv-writer:latest` on the `web` service, so Compose builds **and tags** that name instead of the auto-generated `ogtv-writer-web`.
- [x] The Makefile `docker-build` target tags the **same** name Compose runs (`ogtv-writer:latest`), so `make docker-build` produces the image that actually runs — no orphan.
- [x] `make docker-up` / `make docker-run` (which already pass `--build`) build and run `ogtv-writer:latest`; a running container reports its image as `ogtv-writer:latest`.
- [x] No behavioural change to the app itself — same ports, bind mount, restart policy, healthcheck, and startup migrations as before.

## Technical Notes

- Entity / files touched (five-file recipe — N/A, this is packaging only):
  - [docker-compose.yml](../../docker-compose.yml) — add `image: ogtv-writer:latest` under `services.web` (alongside the existing `build: .`).
  - [Makefile](../../Makefile) — `docker-build` tags `ogtv-writer:latest` explicitly (was the bare `ogtv-writer`, which resolves to the same `:latest` but is left implicit; making it explicit lets the guard test assert an exact match).
  - [tests/unit/test_docker_packaging.py](../../tests/unit/test_docker_packaging.py) — add guard tests.
- Routes added/changed (method + path): none.
- Domain vocab impact ([app/domain.py](../../app/domain.py)): none.
- Config / `.env` additions: none (the image name is fixed, not a setting).

## Testing Plan

Aim for a ~70/20/10 unit/integration/e2e split. This is a build-packaging change with **no runtime code path**, so it is unit-only by nature.

- **Unit** (`tests/unit/test_docker_packaging.py`): parse `docker-compose.yml` and the `Makefile` as text and assert (1) Compose pins `image: ogtv-writer:latest` on the web service, and (2) the `docker-build` tag **equals** the Compose image name — the invariant that keeps the two from drifting apart again.
- **Integration** (`tests/integration/`, `TestClient`): **N/A** — no route, template, or service is added or changed; the FastAPI app is byte-for-byte the same. Asserting HTTP behaviour would test nothing this story touches.
- **e2e** (`tests/e2e/`, Playwright): **N/A** — no user-visible flow changes; this only affects which image tag the build/run commands produce. Verified manually instead by rebuilding via `make docker-up` and confirming `docker inspect` reports the container's image as `ogtv-writer:latest`.

## Estimated Complexity

S — two one-line config edits plus two guard tests; no application code.
